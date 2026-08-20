"""Storage helpers for ``raw.api_responses`` (monthly-partitioned on PostgreSQL).

The parent table is created by the Alembic migration with
``PARTITION BY RANGE (created_at)``; inserts fail until a partition covering
the target month exists, so writers call :func:`ensure_month_partition` first.
On non-PostgreSQL engines (SQLite tests) the table is a plain table and the
partition step is a no-op.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.raw_response import RawApiResponse


def _month_bounds(when: datetime) -> tuple[str, str, str]:
    """Return (partition suffix, month start, next month start) for a timestamp."""
    start = when.replace(day=1)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    suffix = f"{start.year:04d}_{start.month:02d}"
    return suffix, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


async def ensure_month_partition(session: AsyncSession, when: datetime | None = None) -> None:
    """Create the monthly partition of ``raw.api_responses`` covering ``when``.

    Args:
        session: An active async session (PostgreSQL or other).
        when: The timestamp the partition must cover; defaults to now (UTC).
    """
    if session.bind is None or session.bind.dialect.name != "postgresql":
        return
    when = when or datetime.now(timezone.utc)
    suffix, start, end = _month_bounds(when)
    await session.execute(
        text(
            f"CREATE TABLE IF NOT EXISTS raw.api_responses_{suffix} "
            f"PARTITION OF raw.api_responses "
            f"FOR VALUES FROM ('{start}') TO ('{end}')"
        )
    )


def _jsonable(value: Any) -> Any:
    """Best-effort conversion of a value into JSON-serialisable content."""
    if value is None:
        return None
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return json.loads(json.dumps(value, default=str))


async def record_api_response(
    session: AsyncSession,
    *,
    source_id: uuid.UUID,
    endpoint: str,
    source_run_id: uuid.UUID | None = None,
    request_params: dict[str, Any] | None = None,
    response_status: int | None = None,
    response_headers: dict[str, Any] | None = None,
    response_body: Any | None = None,
    duration_ms: int | None = None,
    error_message: str | None = None,
) -> RawApiResponse:
    """Persist one raw API interaction, creating the partition when needed.

    The row is flushed (not committed) so the caller controls the transaction
    and can link ``raw_response_id`` into version rows before committing.

    Args:
        session: An active async session.
        source_id: The ``core.sources`` id the response belongs to.
        endpoint: Full endpoint URL that was called.
        source_run_id: Optional ``core.source_runs`` id.
        request_params: Request parameters as sent.
        response_status: HTTP status code.
        response_headers: Response headers.
        response_body: Parsed response body (JSON-serialisable).
        duration_ms: Request duration in milliseconds.
        error_message: Error description when the request failed.

    Returns:
        The flushed :class:`RawApiResponse` row (id populated).
    """
    now = datetime.now(timezone.utc)
    await ensure_month_partition(session, now)
    body = _jsonable(response_body)
    size = len(json.dumps(body)) if body is not None else None
    row = RawApiResponse(
        created_at=now,
        source_id=source_id,
        source_run_id=source_run_id,
        endpoint=endpoint,
        request_params=_jsonable(request_params),
        response_status=response_status,
        response_headers=_jsonable(response_headers),
        response_body=body,
        response_size_bytes=size,
        duration_ms=duration_ms,
        error_message=error_message,
    )
    session.add(row)
    await session.flush()
    return row
