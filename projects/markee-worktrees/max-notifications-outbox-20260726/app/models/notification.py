"""Transactional notification outbox model."""
from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin
from app.models.schemas import SCHEMA_APP
from app.models.types import JSONBType


class NotificationOutbox(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Outbox row for a notification pending reliable delivery."""

    __tablename__ = "notification_outbox"
    __table_args__ = (
        UniqueConstraint("dedupe_key", name="uq_notification_outbox_dedupe"),
        CheckConstraint(
            "channel IN ('email')",
            name="ck_notification_outbox_channel_valid",
        ),
        CheckConstraint(
            "event_version > 0",
            name="ck_notification_outbox_event_version_positive",
        ),
        CheckConstraint(
            "status IN ('pending', 'sending', 'sent', 'dead')",
            name="ck_notification_outbox_status_valid",
        ),
        CheckConstraint(
            "attempts >= 0",
            name="ck_notification_outbox_attempts_nonneg",
        ),
        CheckConstraint(
            "(status = 'sending' AND lease_owner IS NOT NULL"
            " AND lease_expires_at IS NOT NULL)"
            " OR (status != 'sending' AND lease_owner IS NULL"
            " AND lease_expires_at IS NULL)",
            name="ck_notification_outbox_lease_coherent",
        ),
        CheckConstraint(
            "(status = 'sent' AND sent_at IS NOT NULL)"
            " OR (status != 'sent' AND sent_at IS NULL)",
            name="ck_notification_outbox_sent_at_coherent",
        ),
        CheckConstraint(
            "status != 'dead' OR failed_at IS NOT NULL",
            name="ck_notification_outbox_dead_failed_at",
        ),
        CheckConstraint(
            "status NOT IN ('sent', 'dead') OR next_attempt_at IS NULL",
            name="ck_notification_outbox_terminal_no_retry",
        ),
        {"schema": SCHEMA_APP},
    )

    dedupe_key: Mapped[str] = mapped_column(String(512), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    event_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    aggregate_id: Mapped[Any] = mapped_column(UUID(as_uuid=True), nullable=False)
    recipient: Mapped[str] = mapped_column(String(320), nullable=False)
    channel: Mapped[str] = mapped_column(String(16), nullable=False, default="email")
    template_key: Mapped[str] = mapped_column(String(100), nullable=False)
    template_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1")
    payload: Mapped[dict[str, Any]] = mapped_column(JSONBType, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_owner: Mapped[str | None] = mapped_column(String(128))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    provider_message_id: Mapped[str | None] = mapped_column(String(255))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_code: Mapped[str | None] = mapped_column(String(64))
