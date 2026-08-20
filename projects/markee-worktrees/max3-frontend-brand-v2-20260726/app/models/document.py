"""Document model — official documents associated with trademarks (BPI PDFs, ...)."""
from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.models.types import JSONBType
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin
from app.models.schemas import SCHEMA_CORE


class Document(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """An official document (bulletin, certificate, filing) kept for provenance."""

    __tablename__ = "documents"
    __table_args__ = {"schema": SCHEMA_CORE}

    # NULL for generic documents such as a full BPI bulletin.
    trademark_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("core.trademarks.id"),
        index=True,
    )
    document_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    storage_path: Mapped[str | None] = mapped_column(Text)
    # SHA-256 hex digest of the file contents (idempotency key).
    file_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    publication_date: Mapped[date | None] = mapped_column(Date)
    language: Mapped[str | None] = mapped_column(String(8), default="pt")
    # "metadata" is reserved by SQLAlchemy's declarative API, hence the attribute name.
    meta: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONBType)
