"""Subscription / billing plan model."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID

from app.models.types import JSONBType
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.schemas import SCHEMA_APP


class Subscription(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A user's active billing plan and Stripe linkage."""

    __tablename__ = "subscriptions"
    __table_args__ = {"schema": SCHEMA_APP}

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app.users.id", ondelete="CASCADE"), nullable=False
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), index=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255))
    plan_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    current_period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    max_marks: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    max_users: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    max_clients: Mapped[int] = mapped_column(Integer, default=0)
    features: Mapped[dict[str, Any]] = mapped_column(JSONBType, default=dict)
