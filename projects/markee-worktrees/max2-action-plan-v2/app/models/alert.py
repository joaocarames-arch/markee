"""Alert and Notification (delivery) models."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin
from app.models.schemas import SCHEMA_APP


class Alert(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """A user-facing alert (similar filing or approaching deadline)."""

    __tablename__ = "alerts"
    __table_args__ = {"schema": SCHEMA_APP}

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app.users.id", ondelete="CASCADE"), nullable=False
    )
    watchlist_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app.watchlists.id", ondelete="SET NULL")
    )
    watchlist_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app.watchlist_items.id", ondelete="SET NULL")
    )
    trademark_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("core.trademarks.id", ondelete="SET NULL")
    )
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)
    similarity_score: Mapped[float | None] = mapped_column(Float)
    phonetic_score: Mapped[float | None] = mapped_column(Float)
    class_overlap_score: Mapped[float | None] = mapped_column(Float)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    is_dismissed: Mapped[bool] = mapped_column(Boolean, default=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Notification(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """A record of a single delivery attempt for an :class:`Alert`."""

    __tablename__ = "alert_deliveries"
    __table_args__ = {"schema": SCHEMA_APP}

    alert_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app.alerts.id", ondelete="CASCADE")
    )
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    recipient: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
