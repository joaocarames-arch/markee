"""User account model."""
from __future__ import annotations

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.schemas import SCHEMA_APP


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A registered markee user (IP professional, lawyer or company)."""

    __tablename__ = "users"
    __table_args__ = {"schema": SCHEMA_APP}

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255))
    company_name: Mapped[str | None] = mapped_column(String(255))
    telegram_chat_id: Mapped[str | None] = mapped_column(String(64))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
