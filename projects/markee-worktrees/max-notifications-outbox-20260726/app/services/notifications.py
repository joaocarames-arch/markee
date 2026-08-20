"""Small, transactional notification outbox service.

All operations are transaction-neutral: they never commit or roll back the
caller's session. The caller owns the transaction boundary.
"""
from __future__ import annotations

import hashlib
import random
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import Update, and_, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.notification import NotificationOutbox

ALERT_EVENT_SCHEMA_VERSION = 1
ALERT_TEMPLATE_VERSION = "1"
ALERT_EVENT_TYPES = frozenset(
    {
        "similar_filing",
        "renewal_deadline",
        "opposition_deadline",
        "response_refusal_deadline",
        "grace_period_deadline",
    }
)
DEADLINE_EVENT_TYPES = ALERT_EVENT_TYPES - {"similar_filing"}
TERMINAL_STATUSES = ("sent", "dead")


class StaleLeaseError(RuntimeError):
    """Raised when a worker tries to finish a row it no longer owns."""


@dataclass(frozen=True)
class AlertNotificationEvent:
    """Versioned, minimal notification intent for one alert email."""

    event_type: str
    aggregate_id: str | uuid.UUID
    recipient: str
    template_key: str
    payload: dict[str, Any]
    event_version: int = ALERT_EVENT_SCHEMA_VERSION
    channel: str = "email"
    template_version: str = ALERT_TEMPLATE_VERSION

    def validate(self) -> None:
        """Reject unsupported or unsafe event metadata before persistence."""
        if self.event_type not in ALERT_EVENT_TYPES:
            raise ValueError(f"unsupported alert event_type: {self.event_type!r}")
        if self.event_version != ALERT_EVENT_SCHEMA_VERSION:
            raise ValueError("unsupported alert event_version")
        if self.channel != "email":
            raise ValueError("alert notifications currently support email only")
        expected_template = (
            "alert_deadline" if self.event_type in DEADLINE_EVENT_TYPES else "alert_generic"
        )
        if self.template_key != expected_template:
            raise ValueError("event_type and template_key do not match")
        if self.template_version != ALERT_TEMPLATE_VERSION:
            raise ValueError("unsupported alert template_version")
        uuid.UUID(str(self.aggregate_id))
        normalized = normalize_recipient(self.recipient)
        if not normalized or "@" not in normalized:
            raise ValueError("recipient must be a valid email address")
        required = {"alert_id", "alert_type", "title", "body"}
        if not required.issubset(self.payload):
            raise ValueError("alert event payload is incomplete")
        forbidden_fragments = ("password", "token", "authorization", "auth_header")
        for key in self.payload:
            if any(fragment in key.lower() for fragment in forbidden_fragments):
                raise ValueError("alert event payload contains forbidden secret field")

    @classmethod
    def from_alert(
        cls,
        *,
        alert: Alert,
        recipient: str,
        due_date: date | None = None,
        days_remaining: int | None = None,
    ) -> AlertNotificationEvent:
        """Build a catalogued intent from real Alert fields."""
        event_type = notification_event_type(alert.alert_type)
        template_key = (
            "alert_deadline" if event_type in DEADLINE_EVENT_TYPES else "alert_generic"
        )
        payload: dict[str, Any] = {
            "alert_id": str(alert.id),
            "alert_type": alert.alert_type,
            "title": alert.title,
            "body": alert.body or "",
        }
        if template_key == "alert_deadline":
            if due_date is None or days_remaining is None:
                raise ValueError("deadline notification requires due_date and days_remaining")
            payload.update(
                due_date=due_date.isoformat(),
                days_remaining=days_remaining,
            )
        return cls(
            event_type=event_type,
            aggregate_id=alert.id,
            recipient=recipient,
            template_key=template_key,
            payload=payload,
        )


def notification_event_type(alert_type: str) -> str:
    """Map existing alert labels onto the frozen notification event catalog."""
    mapping = {
        "similar_filing": "similar_filing",
        "renewal": "renewal_deadline",
        "opposition": "opposition_deadline",
        "response_refusal": "response_refusal_deadline",
        "grace_period": "grace_period_deadline",
    }
    try:
        return mapping[alert_type]
    except KeyError as exc:
        raise ValueError(f"unsupported alert event_type: {alert_type!r}") from exc


def normalize_recipient(recipient: str) -> str:
    """Return a deterministic email representation for delivery and dedupe."""
    return recipient.strip().lower()


def build_alert_dedupe_key(
    alert_id: str | uuid.UUID,
    channel: str,
    recipient: str,
    template_key: str,
    template_version: str,
) -> str:
    """Build a PII-safe key from alert, channel, recipient and template identity."""
    normalized = normalize_recipient(recipient)
    recipient_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return (
        f"markee:alert:v1:{alert_id}:{channel}:{recipient_hash}:"
        f"{template_key}:{template_version}"
    )


def retry_delay_seconds(attempt: int, jitter_seed: str = "") -> int:
    """Return the deterministic backoff delay in seconds for a retry."""
    if attempt < 0:
        raise ValueError("attempt must be non-negative")
    rng = random.Random(f"{attempt}:{jitter_seed}")
    return min(3600, 2 ** min(attempt, 10) + rng.randint(0, 30))


def build_claim_statement(
    worker_id: str, limit: int, lease_seconds: int, now: datetime
) -> Update:
    """Build an atomic PostgreSQL claim with expired-lease recovery."""
    due = or_(
        NotificationOutbox.next_attempt_at.is_(None),
        NotificationOutbox.next_attempt_at <= now,
    )
    claimable = or_(
        and_(NotificationOutbox.status == "pending", due),
        and_(
            NotificationOutbox.status == "sending",
            NotificationOutbox.lease_expires_at.is_not(None),
            NotificationOutbox.lease_expires_at <= now,
        ),
    )
    candidates = (
        select(NotificationOutbox.id)
        .where(claimable)
        .order_by(NotificationOutbox.created_at)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    return (
        update(NotificationOutbox)
        .where(NotificationOutbox.id.in_(candidates))
        .values(
            status="sending",
            lease_owner=worker_id,
            lease_expires_at=now + timedelta(seconds=lease_seconds),
            attempts=NotificationOutbox.attempts + 1,
        )
        .returning(NotificationOutbox)
    )


class NotificationOutboxService:
    """Transaction-neutral operations over the notification outbox."""

    def __init__(self, db: AsyncSession, max_attempts: int = 5) -> None:
        if max_attempts <= 0:
            raise ValueError("max_attempts must be positive")
        self.db = db
        self.max_attempts = max_attempts

    async def enqueue_event(
        self, event: AlertNotificationEvent
    ) -> NotificationOutbox:
        """Persist a structured alert intent without committing the outer transaction."""
        event.validate()
        recipient = normalize_recipient(event.recipient)
        dedupe_key = build_alert_dedupe_key(
            event.aggregate_id,
            event.channel,
            recipient,
            event.template_key,
            event.template_version,
        )
        row = NotificationOutbox(
            dedupe_key=dedupe_key,
            event_type=event.event_type,
            event_version=event.event_version,
            aggregate_id=uuid.UUID(str(event.aggregate_id)),
            recipient=recipient,
            channel=event.channel,
            template_key=event.template_key,
            template_version=event.template_version,
            payload=dict(event.payload),
        )
        return await self._insert_deduplicated(row)

    async def enqueue(
        self,
        dedupe_key: str,
        recipient: str,
        subject: str,
        text_body: str,
        html_body: str,
        template_key: str = "alert",
        template_version: str = "1",
    ) -> NotificationOutbox:
        """Compatibility helper for N0 lifecycle tests; no rendered body is stored."""
        synthetic_id = uuid.uuid5(uuid.NAMESPACE_URL, dedupe_key)
        row = NotificationOutbox(
            dedupe_key=dedupe_key,
            event_type="similar_filing",
            event_version=ALERT_EVENT_SCHEMA_VERSION,
            aggregate_id=synthetic_id,
            recipient=normalize_recipient(recipient),
            channel="email",
            template_key=template_key,
            template_version=template_version,
            payload={"title": subject, "body": text_body},
        )
        return await self._insert_deduplicated(row)

    async def _insert_deduplicated(
        self, row: NotificationOutbox
    ) -> NotificationOutbox:
        """Insert under a savepoint so duplicates preserve the caller transaction."""
        try:
            async with self.db.begin_nested():
                self.db.add(row)
                await self.db.flush()
        except IntegrityError:
            existing = await self.db.scalar(
                select(NotificationOutbox).where(
                    NotificationOutbox.dedupe_key == row.dedupe_key
                )
            )
            if existing is None:
                raise
            return existing
        return row

    async def claim_batch(
        self,
        worker_id: str,
        limit: int = 10,
        lease_seconds: int = 300,
        now: datetime | None = None,
    ) -> list[NotificationOutbox]:
        """Atomically claim due rows; never commit the caller's transaction."""
        now = now or datetime.now(UTC)
        result = await self.db.scalars(
            build_claim_statement(worker_id, limit, lease_seconds, now),
            execution_options={
                "synchronize_session": False,
                "populate_existing": True,
            },
        )
        return list(result.all())

    async def _owned_sending_row(
        self, row_id: uuid.UUID, worker_id: str, now: datetime
    ) -> NotificationOutbox:
        row = await self.db.scalar(
            select(NotificationOutbox)
            .where(
                NotificationOutbox.id == row_id,
                NotificationOutbox.status == "sending",
                NotificationOutbox.lease_owner == worker_id,
                NotificationOutbox.lease_expires_at.is_not(None),
                NotificationOutbox.lease_expires_at > now,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if row is None:
            raise StaleLeaseError(
                f"worker does not hold a live lease on outbox row {row_id}"
            )
        return row

    async def assert_live_lease(
        self, row_id: uuid.UUID, worker_id: str, now: datetime
    ) -> NotificationOutbox:
        """Verify ownership immediately before invoking a delivery gateway."""
        return await self._owned_sending_row(row_id, worker_id, now)

    async def mark_sent(
        self,
        row_id: uuid.UUID,
        provider_message_id: str,
        worker_id: str,
        now: datetime | None = None,
    ) -> NotificationOutbox:
        """Mark a live, owned lease sent without committing."""
        now = now or datetime.now(UTC)
        row = await self._owned_sending_row(row_id, worker_id, now)
        row.status = "sent"
        row.provider_message_id = provider_message_id
        row.sent_at = now
        row.lease_owner = None
        row.lease_expires_at = None
        row.next_attempt_at = None
        await self.db.flush()
        return row

    async def mark_failure(
        self,
        row_id: uuid.UUID,
        code: str,
        worker_id: str,
        retryable: bool = True,
        now: datetime | None = None,
    ) -> NotificationOutbox:
        """Record a retryable or permanent failure without committing."""
        now = now or datetime.now(UTC)
        row = await self._owned_sending_row(row_id, worker_id, now)
        row.last_error_code = code
        row.failed_at = now
        row.lease_owner = None
        row.lease_expires_at = None
        if retryable and row.attempts < self.max_attempts:
            row.status = "pending"
            row.next_attempt_at = now + timedelta(
                seconds=retry_delay_seconds(row.attempts, str(row.id))
            )
        else:
            row.status = "dead"
            row.next_attempt_at = None
        await self.db.flush()
        return row
