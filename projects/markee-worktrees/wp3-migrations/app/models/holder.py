"""Holder (trademark owner/applicant) and the trademark↔holder association."""
from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from sqlalchemy import CheckConstraint, Date, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.models.types import JSONBType
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base
from app.models.mixins import CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.schemas import SCHEMA_CORE


class Holder(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A natural or legal person that holds (or applied for) trademarks."""

    __tablename__ = "holders"
    __table_args__ = (
        CheckConstraint("type IN ('natural', 'legal')", name="ck_holders_type"),
        {"schema": SCHEMA_CORE},
    )

    source_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    address: Mapped[str | None] = mapped_column(Text)
    country: Mapped[str | None] = mapped_column(String(2))
    type: Mapped[str | None] = mapped_column(String(32))
    raw_data: Mapped[dict[str, Any] | None] = mapped_column(JSONBType)
    confidence_score: Mapped[float | None] = mapped_column(Float)


class TrademarkHolder(CreatedAtMixin, Base):
    """N:M association between trademarks and holders."""

    __tablename__ = "trademark_holders"
    __table_args__ = {"schema": SCHEMA_CORE}

    trademark_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("core.trademarks.id", ondelete="CASCADE"),
        primary_key=True,
    )
    holder_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("core.holders.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role: Mapped[str] = mapped_column(
        String(32), primary_key=True, default="applicant"
    )
    since_date: Mapped[date | None] = mapped_column(Date)
