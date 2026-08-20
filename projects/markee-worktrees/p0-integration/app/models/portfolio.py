"""ClientPortfolio and ProspectionOpportunity models."""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.types import IntArray

from app.models.database import Base
from app.models.mixins import CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.schemas import SCHEMA_APP


class ClientPortfolio(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """A client managed on behalf of a team (agency / law firm use case)."""

    __tablename__ = "client_portfolios"
    __table_args__ = {"schema": SCHEMA_APP}

    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app.teams.id", ondelete="CASCADE"), nullable=False
    )
    client_name: Mapped[str] = mapped_column(String(255), nullable=False)
    client_email: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)


class ProspectionOpportunity(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A prospecting lead surfaced by the prospection engine."""

    __tablename__ = "prospection_opportunities"
    __table_args__ = {"schema": SCHEMA_APP}

    trademark_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("core.trademarks.id", ondelete="CASCADE"),
        nullable=False,
    )
    opportunity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    holder_name: Mapped[str | None] = mapped_column(String(500))
    holder_type: Mapped[str | None] = mapped_column(String(50))
    holder_district: Mapped[str | None] = mapped_column(String(100))
    holder_cae: Mapped[str | None] = mapped_column(String(50))
    nice_classes: Mapped[list[int] | None] = mapped_column(IntArray)
    expiry_date: Mapped[date | None] = mapped_column(Date)
    score: Mapped[float | None] = mapped_column(Float)
    is_exported: Mapped[bool] = mapped_column(Boolean, default=False)
    exported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
