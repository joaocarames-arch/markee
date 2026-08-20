"""Unified trademark model (EUIPO / TMview / INPI)."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import Date, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.types import IntArray, JSONBType

from app.models.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.schemas import SCHEMA_CORE


class Trademark(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A trademark record normalised from any supported jurisdiction."""

    __tablename__ = "trademarks"
    __table_args__ = {"schema": SCHEMA_CORE}

    source_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    application_number: Mapped[str | None] = mapped_column(String(100), index=True)
    application_date: Mapped[date | None] = mapped_column(Date)
    registration_number: Mapped[str | None] = mapped_column(String(100))
    registration_date: Mapped[date | None] = mapped_column(Date)
    word_mark: Mapped[str | None] = mapped_column(String(500))
    figurative_mark_url: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str | None] = mapped_column(String(100))
    renewal_status: Mapped[str | None] = mapped_column(String(100))
    nice_classes: Mapped[list[int] | None] = mapped_column(IntArray)
    applicants: Mapped[list[Any] | None] = mapped_column(JSONBType)
    representatives: Mapped[list[Any] | None] = mapped_column(JSONBType)
    goods_services: Mapped[str | None] = mapped_column(Text)
    jurisdiction: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    raw_data: Mapped[dict[str, Any] | None] = mapped_column(JSONBType)
    # Last modification timestamp reported by the source (incremental polling cursor).
    update_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    # Overall extraction confidence for this record (0..1, NULL when unknown).
    confidence_score: Mapped[float | None] = mapped_column(Float)
    # Data source that last wrote this record (core.sources).
    ingest_source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("core.sources.id", ondelete="SET NULL")
    )
