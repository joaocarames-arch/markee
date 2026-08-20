"""ReviewQueueItem model — uncertain extraction results awaiting human review."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.models.types import JSONBType
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin
from app.models.schemas import SCHEMA_APP


class ReviewQueueItem(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """An extraction result that scored below the confidence threshold."""

    __tablename__ = "review_queue"
    __table_args__ = {"schema": SCHEMA_APP}

    # Source that produced the item (e.g. 'euipo_api', 'inpi_bpi').
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    # Kind of payload (e.g. 'lifecycle_event', 'trademark_record').
    item_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONBType, nullable=False)
    # Why the item was queued (PT-PT, shown to reviewers).
    reason: Mapped[str | None] = mapped_column(Text)
    confidence_score: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    # Optional linkage for context; soft reference for documents (core is
    # authoritative but review items must survive document purges).
    trademark_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("core.trademarks.id", ondelete="SET NULL")
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app.users.id", ondelete="SET NULL")
    )
