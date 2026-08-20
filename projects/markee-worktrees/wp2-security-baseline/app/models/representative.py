"""Representative (IP agent/lawyer) and the trademark↔representative association."""
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


class Representative(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An industrial-property agent or lawyer representing holders."""

    __tablename__ = "representatives"
    __table_args__ = (
        CheckConstraint(
            "type IN ('natural', 'legal', 'association')", name="ck_representatives_type"
        ),
        {"schema": SCHEMA_CORE},
    )

    source_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    address: Mapped[str | None] = mapped_column(Text)
    country: Mapped[str | None] = mapped_column(String(2))
    type: Mapped[str | None] = mapped_column(String(32))
    raw_data: Mapped[dict[str, Any] | None] = mapped_column(JSONBType)
    confidence_score: Mapped[float | None] = mapped_column(Float)


class TrademarkRepresentative(CreatedAtMixin, Base):
    """N:M association between trademarks and representatives."""

    __tablename__ = "trademark_representatives"
    __table_args__ = {"schema": SCHEMA_CORE}

    trademark_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("core.trademarks.id", ondelete="CASCADE"),
        primary_key=True,
    )
    representative_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("core.representatives.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="representative")
    since_date: Mapped[date | None] = mapped_column(Date)
