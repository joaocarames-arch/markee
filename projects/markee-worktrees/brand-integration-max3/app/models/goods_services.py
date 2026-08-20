"""GoodsServices model — per-class goods/services terms of a trademark."""
from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin
from app.models.schemas import SCHEMA_CORE


class GoodsServices(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """A single goods/services term inside a Nice class for a trademark."""

    __tablename__ = "goods_services"
    __table_args__ = {"schema": SCHEMA_CORE}

    trademark_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("core.trademarks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    nice_class_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("core.nice_classes.id"),
        nullable=False,
    )
    term: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(8), nullable=False, default="pt")
