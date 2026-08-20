"""LifecycleEvent and Deadline models."""
from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from sqlalchemy import Date, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.types import DateArray, JSONBType

from app.models.database import Base
from app.models.mixins import CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.schemas import SCHEMA_APP, SCHEMA_EVENTS


class LifecycleEvent(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """A discrete event in a trademark's lifecycle (e.g. publication, grant)."""

    __tablename__ = "lifecycle_events"
    __table_args__ = {"schema": SCHEMA_EVENTS}

    trademark_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("core.trademarks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    # Deadline started by this event (e.g. end of the opposition window).
    deadline_date: Mapped[date | None] = mapped_column(Date, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    # Reference inside the source (e.g. opposition number, BPI despacho number).
    source_reference: Mapped[str | None] = mapped_column(String(128))
    # Provenance inside a parsed document (BPI PDFs).
    page_number: Mapped[int | None] = mapped_column(Integer)
    source_excerpt: Mapped[str | None] = mapped_column(Text)
    # Extraction confidence (0..1, NULL when unknown).
    confidence_score: Mapped[float | None] = mapped_column(Float)
    raw_data: Mapped[dict[str, Any] | None] = mapped_column(JSONBType)


class Deadline(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A computed, actionable deadline derived from lifecycle events."""

    __tablename__ = "deadlines"
    __table_args__ = {"schema": SCHEMA_APP}

    trademark_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("core.trademarks.id", ondelete="CASCADE"),
        nullable=False,
    )
    deadline_type: Mapped[str] = mapped_column(String(100), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    alert_dates: Mapped[list[date] | None] = mapped_column(DateArray)
