"""Behavioral contract for alert notification orchestration and delivery."""
from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.models.alert import Alert
from app.models.notification import NotificationOutbox
from app.services.alerts import AlertService
from app.services.email import InMemoryEmailGateway
from app.services.notification_delivery import (
    AlertNotificationDeliveryService,
    DeliveryError,
)
from app.services.notification_templates import render_alert_email
from app.services.notifications import (
    ALERT_EVENT_SCHEMA_VERSION,
    ALERT_TEMPLATE_VERSION,
    AlertNotificationEvent,
    NotificationOutboxService,
    build_alert_dedupe_key,
)
from tests.stg00.factories import make_trademark, make_user

NOW = datetime(2026, 7, 26, 13, 0, tzinfo=UTC)
SENDER = "markee <no-reply@markee.pt>"


async def _counts(db_session) -> tuple[int, int]:
    alerts = (await db_session.scalar(select(func.count()).select_from(Alert))) or 0
    outbox = (
        await db_session.scalar(select(func.count()).select_from(NotificationOutbox))
    ) or 0
    return alerts, outbox


async def _similarity_alert(db_session, *, email: str = "USER@Example.COM ") -> Alert:
    user = await make_user(db_session, email=email)
    trademark = await make_trademark(
        db_session,
        source_name="euipo_api",
        jurisdiction="EUIPO",
        word_mark='ATLAS <script>alert("x")</script> & FILHOS',
    )
    alert = await AlertService(db_session).generate_similarity_alert(
        user_id=str(user.id),
        watchlist_id=None,
        watchlist_item_id=None,
        trademark_id=str(trademark.id),
        similarity_score=91.0,
        phonetic_score=88.0,
        class_overlap_score=100.0,
    )
    assert alert is not None
    return alert


@pytest.mark.asyncio
async def test_alert_and_outbox_share_transaction_and_outer_rollback(db_session):
    alert = await _similarity_alert(db_session)

    assert await _counts(db_session) == (1, 1)
    row = await db_session.scalar(
        select(NotificationOutbox).where(NotificationOutbox.aggregate_id == alert.id)
    )
    assert row is not None
    assert row.event_type == "similar_filing"
    assert row.event_version == ALERT_EVENT_SCHEMA_VERSION
    assert row.recipient == "user@example.com"
    assert row.channel == "email"
    assert row.template_key == "alert_generic"
    assert row.template_version == ALERT_TEMPLATE_VERSION
    assert row.payload == {
        "alert_id": str(alert.id),
        "alert_type": "similar_filing",
        "title": alert.title,
        "body": alert.body,
    }
    assert not hasattr(row, "subject")
    assert not hasattr(row, "text_body")
    assert not hasattr(row, "html_body")

    await db_session.rollback()
    assert await _counts(db_session) == (0, 0)


@pytest.mark.asyncio
async def test_alert_notification_dedupe_is_deterministic(db_session):
    alert = await _similarity_alert(db_session)
    row = await db_session.scalar(select(NotificationOutbox))
    assert row is not None

    assert row.dedupe_key == build_alert_dedupe_key(
        alert.id,
        "email",
        " USER@example.com ",
        row.template_key,
        row.template_version,
    )
    assert "user@example.com" not in row.dedupe_key

    event = AlertNotificationEvent.from_alert(
        alert=alert,
        recipient="USER@example.com",
    )
    duplicate = await NotificationOutboxService(db_session).enqueue_event(event)
    assert duplicate.id == row.id
    assert await _counts(db_session) == (1, 1)


@pytest.mark.asyncio
async def test_deadline_alert_uses_versioned_deadline_template(db_session):
    user = await make_user(db_session)
    trademark = await make_trademark(
        db_session,
        source_name="euipo_api",
        word_mark="MARCA PRAZO",
    )
    alert = await AlertService(db_session).generate_deadline_alert(
        user_id=str(user.id),
        trademark_id=str(trademark.id),
        deadline_type="renewal",
        due_date=date(2026, 9, 1),
        days_remaining=37,
    )
    assert alert is not None
    row = await db_session.scalar(select(NotificationOutbox))
    assert row is not None
    assert row.event_type == "renewal_deadline"
    assert row.template_key == "alert_deadline"
    assert row.payload["due_date"] == "2026-09-01"
    assert row.payload["days_remaining"] == 37


@pytest.mark.asyncio
async def test_unknown_alert_event_type_is_rejected_without_outbox_write(db_session):
    event = AlertNotificationEvent(
        event_type="made_up_event",
        aggregate_id="00000000-0000-0000-0000-000000000001",
        recipient="user@example.com",
        template_key="alert_generic",
        payload={"alert_id": "00000000-0000-0000-0000-000000000001"},
    )
    with pytest.raises(ValueError, match="event_type"):
        await NotificationOutboxService(db_session).enqueue_event(event)
    assert (await db_session.scalars(select(NotificationOutbox))).all() == []


@pytest.mark.parametrize(
    "template_key,payload,expected",
    [
        (
            "alert_generic",
            {
                "title": 'Marca <nova> & "relevante"',
                "body": "Foi detetado <script>roubar()</script> um resultado & outro.",
            },
            "Foi detetado",
        ),
        (
            "alert_deadline",
            {
                "title": "Renovação <urgente>",
                "body": "A marca A&B tem um prazo associado.",
                "due_date": "2026-09-01",
                "days_remaining": 37,
            },
            "2026-09-01",
        ),
    ],
)
def test_alert_templates_are_pt_pt_text_html_and_escape_user_content(
    template_key, payload, expected
):
    rendered = render_alert_email(template_key, ALERT_TEMPLATE_VERSION, payload)

    assert rendered.subject
    assert "\r" not in rendered.subject and "\n" not in rendered.subject
    assert expected in rendered.text_body
    assert expected in rendered.html_body
    assert '<html lang="pt-PT">' in rendered.html_body
    assert '<meta charset="UTF-8">' in rendered.html_body
    assert "<script>" not in rendered.html_body
    assert "&lt;" in rendered.html_body or "A&amp;B" in rendered.html_body
    assert "cliente compatível com HTML" not in rendered.text_body


@pytest.mark.asyncio
async def test_delivery_success_uses_in_memory_gateway_and_marks_sent(db_session):
    await _similarity_alert(db_session)
    outbox = NotificationOutboxService(db_session)
    claimed = await outbox.claim_batch("worker-safe", now=NOW)
    gateway = InMemoryEmailGateway()

    result = await AlertNotificationDeliveryService(
        outbox=outbox,
        gateway=gateway,
        sender=SENDER,
    ).deliver(claimed[0], worker_id="worker-safe", now=NOW)

    assert result.status == "sent"
    assert result.provider_message_id is not None
    assert len(gateway.sent) == 1
    envelope = gateway.sent[0]
    assert envelope.recipients == ["user@example.com"]
    assert envelope.text_body
    assert envelope.html_body
    assert envelope.headers["X-Markee-Event-Type"] == "similar_filing"
    assert envelope.headers["X-Markee-Template"] == "alert_generic/1"


class _FailingGateway:
    @property
    def sent(self):
        return []

    def __init__(self, *, retryable: bool, code: str) -> None:
        self.retryable = retryable
        self.code = code

    async def send(self, envelope) -> None:
        raise DeliveryError(code=self.code, retryable=self.retryable)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "retryable,expected_status",
    [(True, "pending"), (False, "dead")],
)
async def test_delivery_classifies_retryable_and_permanent_failures(
    db_session, retryable, expected_status
):
    await _similarity_alert(db_session)
    outbox = NotificationOutboxService(db_session)
    claimed = await outbox.claim_batch("worker-safe", now=NOW)

    row = await AlertNotificationDeliveryService(
        outbox=outbox,
        gateway=_FailingGateway(retryable=retryable, code="provider_rejected"),
        sender=SENDER,
    ).deliver(claimed[0], worker_id="worker-safe", now=NOW)

    assert row.status == expected_status
    assert row.last_error_code == "provider_rejected"
    assert (row.next_attempt_at is not None) is retryable


@pytest.mark.asyncio
async def test_delivery_rejects_stale_lease_without_calling_gateway(db_session):
    await _similarity_alert(db_session)
    outbox = NotificationOutboxService(db_session)
    claimed = await outbox.claim_batch(
        "old-worker", lease_seconds=30, now=NOW
    )
    gateway = InMemoryEmailGateway()

    from app.services.notifications import StaleLeaseError

    with pytest.raises(StaleLeaseError):
        await AlertNotificationDeliveryService(
            outbox=outbox,
            gateway=gateway,
            sender=SENDER,
        ).deliver(
            claimed[0],
            worker_id="old-worker",
            now=NOW + timedelta(seconds=31),
        )
    assert gateway.sent == []


@pytest.mark.asyncio
async def test_delivery_logs_exclude_pii_content_and_secrets(db_session, caplog):
    await _similarity_alert(db_session, email="private.person@example.com")
    outbox = NotificationOutboxService(db_session)
    claimed = await outbox.claim_batch("worker-safe", now=NOW)
    secret = "token-MUST-NOT-LEAK"

    with caplog.at_level(logging.INFO):
        await AlertNotificationDeliveryService(
            outbox=outbox,
            gateway=_FailingGateway(retryable=True, code="connection_timeout"),
            sender=SENDER,
        ).deliver(claimed[0], worker_id="worker-safe", now=NOW)

    logs = caplog.text
    assert "private.person@example.com" not in logs
    assert claimed[0].payload["title"] not in logs
    assert claimed[0].payload["body"] not in logs
    assert secret not in logs
    assert "similar_filing" in logs
    assert "connection_timeout" in logs
