"""Watchlist and WatchlistItem models."""
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.types import IntArray, StrArray

from app.models.database import Base
from app.models.mixins import CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.schemas import SCHEMA_APP


class Watchlist(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A monitoring configuration owned by a user (optionally scoped to a client)."""

    __tablename__ = "watchlists"
    __table_args__ = {"schema": SCHEMA_APP}

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app.users.id", ondelete="CASCADE"), nullable=False
    )
    team_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app.teams.id", ondelete="SET NULL")
    )
    client_portfolio_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app.client_portfolios.id", ondelete="SET NULL")
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    similarity_threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=80)
    phonetic_weight: Mapped[float] = mapped_column(Float, default=0.3)
    class_weight: Mapped[float] = mapped_column(Float, default=0.2)
    nice_classes_filter: Mapped[list[int] | None] = mapped_column(IntArray)
    jurisdictions: Mapped[list[str] | None] = mapped_column(
        StrArray, default=lambda: ["EUIPO", "INPI"]
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class WatchlistItem(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """A single watched mark inside a :class:`Watchlist`."""

    __tablename__ = "watchlist_items"
    __table_args__ = {"schema": SCHEMA_APP}

    watchlist_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("app.watchlists.id", ondelete="CASCADE"),
        nullable=False,
    )
    mark_text: Mapped[str] = mapped_column(String(500), nullable=False)
    nice_classes: Mapped[list[int] | None] = mapped_column(IntArray)
    notes: Mapped[str | None] = mapped_column(Text)
