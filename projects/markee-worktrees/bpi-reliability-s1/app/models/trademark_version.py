"""TrademarkVersion model — append-only version history (see ADR 0002)."""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.models.types import JSONBType
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin
from app.models.schemas import SCHEMA_CORE


class TrademarkVersion(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """A full snapshot of a trademark at a point in time, never deleted."""

    __tablename__ = "trademark_versions"
    __table_args__ = (
        UniqueConstraint(
            "trademark_id", "version_number", name="uq_versions_trademark_version"
        ),
        {"schema": SCHEMA_CORE},
    )

    trademark_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("core.trademarks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Sequential per trademark (1, 2, 3...), not global.
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSONBType, nullable=False)
    diff_from_previous: Mapped[dict[str, Any] | None] = mapped_column(JSONBType)
    change_source: Mapped[str] = mapped_column(String(64), nullable=False)
    change_type: Mapped[str] = mapped_column(String(32), nullable=False)
    # Soft reference into raw.api_responses (raw is purgeable, so no FK).
    raw_response_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
