"""Source and SourceRun models — data-source registry and run tracking."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.models.types import JSONBType
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin
from app.models.schemas import SCHEMA_CORE


class Source(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """A configured external data source (see config/sources.yaml)."""

    __tablename__ = "sources"
    __table_args__ = (
        CheckConstraint("priority >= 1", name="ck_sources_priority"),
        {"schema": SCHEMA_CORE},
    )

    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    base_url: Mapped[str | None] = mapped_column(Text)
    auth_method: Mapped[str | None] = mapped_column(String(32))
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    config_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONBType)


class SourceRun(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """A single polling/parsing execution against a :class:`Source`."""

    __tablename__ = "source_runs"
    __table_args__ = {"schema": SCHEMA_CORE}

    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("core.sources.id"),
        nullable=False,
        index=True,
    )
    run_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    items_processed: Mapped[int] = mapped_column(Integer, default=0)
    items_new: Mapped[int] = mapped_column(Integer, default=0)
    items_updated: Mapped[int] = mapped_column(Integer, default=0)
    items_failed: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    # Resume cursor for the next run (e.g. the max update_date seen).
    cursor_value: Mapped[str | None] = mapped_column(String(128))
