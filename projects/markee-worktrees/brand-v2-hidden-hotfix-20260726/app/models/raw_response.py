"""RawApiResponse model — immutable raw API responses (raw schema, partitioned).

On PostgreSQL the table is partitioned by month on ``created_at``; partitions
are created on demand by :func:`app.services.raw_responses.ensure_month_partition`.
PostgreSQL requires the partition key inside the primary key, hence the
composite ``(id, created_at)`` primary key.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.types import JSONBType

from app.models.database import Base
from app.models.mixins import _utcnow
from app.models.schemas import SCHEMA_RAW


class RawApiResponse(Base):
    """One raw HTTP interaction with an external source, kept for audit/replay."""

    __tablename__ = "api_responses"
    __table_args__ = {
        "schema": SCHEMA_RAW,
        "postgresql_partition_by": "RANGE (created_at)",
    }

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True, default=_utcnow
    )
    # Soft references into core (raw must stay truncatable without FK churn).
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    source_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    endpoint: Mapped[str] = mapped_column(Text, nullable=False)
    request_params: Mapped[dict[str, Any] | None] = mapped_column(JSONBType)
    response_status: Mapped[int | None] = mapped_column(Integer)
    response_headers: Mapped[dict[str, Any] | None] = mapped_column(JSONBType)
    response_body: Mapped[Any | None] = mapped_column(JSONBType)
    response_size_bytes: Mapped[int | None] = mapped_column(Integer)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)
