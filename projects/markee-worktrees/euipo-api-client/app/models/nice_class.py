"""NiceClass model — the Nice Classification catalogue (classes 1-45)."""
from __future__ import annotations

from sqlalchemy import CheckConstraint, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin
from app.models.schemas import SCHEMA_CORE


class NiceClass(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One class of the Nice Classification (1-34 goods, 35-45 services)."""

    __tablename__ = "nice_classes"
    __table_args__ = (
        CheckConstraint(
            "class_number >= 1 AND class_number <= 45", name="ck_nice_class_number"
        ),
        {"schema": SCHEMA_CORE},
    )

    class_number: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    description_pt: Mapped[str | None] = mapped_column(Text)
    description_en: Mapped[str | None] = mapped_column(Text)
