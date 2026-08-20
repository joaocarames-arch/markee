"""STG00-WP1: dispatch must drop BPI-rooted pending alerts, never invoking
the email/Telegram adapters for them."""
from __future__ import annotations

import pytest
from sqlalchemy import func, select

from app.models.alert import Alert, Notification
from app.services.alerts import AlertService

from tests.stg00.factories import make_trademark, make_user


async def _make_pending_alert(session, user, trademark) -> Alert:
    alert = Alert(
        user_id=user.id,
        trademark_id=trademark.id,
        alert_type="opposition",
        title="Prazo de oposição",
        body="Corpo do alerta",
    )
    session.add(alert)
    await session.flush()
    return alert


@pytest.fixture
def adapter_spies(monkeypatch):
    """Fail the test if any delivery adapter is invoked."""

    async def _no_email(self, to, subject, html_body):  # pragma: no cover
        raise AssertionError("send_email invoked for a denied-source alert")

    async def _no_telegram(self, chat_id, message):  # pragma: no cover
        raise AssertionError("send_telegram invoked for a denied-source alert")

    monkeypatch.setattr(AlertService, "send_email", _no_email)
    monkeypatch.setattr(AlertService, "send_telegram", _no_telegram)


@pytest.mark.asyncio
async def test_send_alerts_dispatcher_drops_bpi_alerts(db_session, adapter_spies):
    from app.tasks.send_alerts import dispatch_pending

    user = await make_user(db_session)
    trademark = await make_trademark(db_session, source_name="inpi_bpi")
    alert = await _make_pending_alert(db_session, user, trademark)

    result = await dispatch_pending(db_session)

    assert result["blocked"] == 1
    assert result["sent"] == 0
    assert result["failed"] == 0
    await db_session.refresh(alert)
    assert alert.sent_at is None
    assert alert.is_dismissed is True  # dropped from the pending queue
    notifications = (
        await db_session.execute(select(func.count()).select_from(Notification))
    ).scalar_one()
    assert notifications == 0


@pytest.mark.asyncio
async def test_dispatch_alert_itself_refuses_denied_alert(db_session, adapter_spies):
    """Defense in depth: even a direct dispatch_alert call must not deliver."""
    user = await make_user(db_session)
    trademark = await make_trademark(db_session, source_name="inpi_bpi")
    alert = await _make_pending_alert(db_session, user, trademark)

    service = AlertService(db_session)
    notifications = await service.dispatch_alert(alert)

    assert notifications == []
    assert alert.sent_at is None


@pytest.mark.asyncio
async def test_non_bpi_alert_still_dispatched(db_session):
    """Authorized alerts keep flowing (SMTP unconfigured → recorded skip,
    no external call)."""
    from app.tasks.send_alerts import dispatch_pending

    user = await make_user(db_session)
    trademark = await make_trademark(
        db_session, source_name="euipo_api", jurisdiction="EUIPO"
    )
    alert = await _make_pending_alert(db_session, user, trademark)

    result = await dispatch_pending(db_session)

    assert result["sent"] == 1
    assert result["blocked"] == 0
    await db_session.refresh(alert)
    assert alert.sent_at is not None
    channels = (
        (await db_session.execute(select(Notification.channel))).scalars().all()
    )
    assert channels == ["email"]
