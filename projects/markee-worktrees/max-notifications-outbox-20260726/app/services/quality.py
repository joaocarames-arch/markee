"""Data-quality metrics over the ingestion pipeline.

Computes, per registered source and globally: run outcomes and durations,
item counts (processed/new/updated/failed), documents archived, raw responses
preserved, review-queue backlog, average extraction confidence and field
completeness of the core trademark data.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.lifecycle import LifecycleEvent
from app.models.raw_response import RawApiResponse
from app.models.review_queue import ReviewQueueItem
from app.models.source import Source, SourceRun
from app.models.trademark import Trademark


def _iso(value: datetime | None) -> str | None:
    """Return an ISO string for a datetime, or ``None``."""
    return value.isoformat() if value is not None else None


async def _source_metrics(session: AsyncSession, source: Source) -> dict[str, Any]:
    """Aggregate run/document/raw metrics for one source."""
    run_stats = (
        await session.execute(
            select(
                func.count(SourceRun.id),
                func.sum(case((SourceRun.status == "completed", 1), else_=0)),
                func.sum(case((SourceRun.status == "failed", 1), else_=0)),
                func.sum(SourceRun.items_processed),
                func.sum(SourceRun.items_new),
                func.sum(SourceRun.items_updated),
                func.sum(SourceRun.items_failed),
            ).where(SourceRun.source_id == source.id)
        )
    ).one()
    (
        runs_total,
        runs_completed,
        runs_failed,
        items_processed,
        items_new,
        items_updated,
        items_failed,
    ) = run_stats

    last_run = (
        await session.execute(
            select(SourceRun)
            .where(SourceRun.source_id == source.id)
            .order_by(SourceRun.started_at.desc())
            .limit(1)
        )
    ).scalars().first()

    last_duration_seconds: float | None = None
    if last_run is not None and last_run.completed_at is not None:
        last_duration_seconds = (
            last_run.completed_at - last_run.started_at
        ).total_seconds()

    raw_responses = (
        await session.execute(
            select(func.count()).select_from(RawApiResponse).where(
                RawApiResponse.source_id == source.id
            )
        )
    ).scalar_one()

    return {
        "name": source.name,
        "source_type": source.source_type,
        "is_enabled": source.is_enabled,
        "runs": {
            "total": runs_total or 0,
            "completed": runs_completed or 0,
            "failed": runs_failed or 0,
        },
        "items": {
            "processed": items_processed or 0,
            "new": items_new or 0,
            "updated": items_updated or 0,
            "failed": items_failed or 0,
        },
        "raw_responses_stored": raw_responses or 0,
        "last_run": {
            "run_type": last_run.run_type if last_run else None,
            "status": last_run.status if last_run else None,
            "started_at": _iso(last_run.started_at) if last_run else None,
            "completed_at": _iso(last_run.completed_at) if last_run else None,
            "duration_seconds": last_duration_seconds,
            "cursor_value": last_run.cursor_value if last_run else None,
        },
    }


async def _completeness_metrics(session: AsyncSession) -> dict[str, Any]:
    """Compute empty-field counts over the core trademark data."""
    total = (
        await session.execute(select(func.count()).select_from(Trademark))
    ).scalar_one()

    empty_counts: dict[str, int] = {}
    checks = {
        "word_mark": Trademark.word_mark.is_(None),
        "application_number": Trademark.application_number.is_(None),
        "application_date": Trademark.application_date.is_(None),
        "status": Trademark.status.is_(None),
        "nice_classes": Trademark.nice_classes.is_(None),
    }
    for name, condition in checks.items():
        empty_counts[name] = (
            await session.execute(
                select(func.count()).select_from(Trademark).where(condition)
            )
        ).scalar_one()

    return {"total_trademarks": total, "empty_fields": empty_counts}


async def compute_quality_metrics(session: AsyncSession) -> dict[str, Any]:
    """Compute the full data-quality report.

    Args:
        session: An active async session.

    Returns:
        A JSON-serialisable dict with per-source and global metrics.
    """
    sources = (
        await session.execute(select(Source).order_by(Source.priority))
    ).scalars().all()
    per_source = [await _source_metrics(session, source) for source in sources]

    avg_trademark_confidence = (
        await session.execute(select(func.avg(Trademark.confidence_score)))
    ).scalar_one()
    avg_event_confidence = (
        await session.execute(select(func.avg(LifecycleEvent.confidence_score)))
    ).scalar_one()

    documents_total = (
        await session.execute(select(func.count()).select_from(Document))
    ).scalar_one()

    review_pending = (
        await session.execute(
            select(func.count())
            .select_from(ReviewQueueItem)
            .where(ReviewQueueItem.status == "pending")
        )
    ).scalar_one()
    review_total = (
        await session.execute(select(func.count()).select_from(ReviewQueueItem))
    ).scalar_one()

    events_total = (
        await session.execute(select(func.count()).select_from(LifecycleEvent))
    ).scalar_one()

    return {
        "sources": per_source,
        "documents": {"total": documents_total},
        "lifecycle_events": {"total": events_total},
        "review_queue": {"pending": review_pending, "total": review_total},
        "confidence": {
            "avg_trademark": (
                round(float(avg_trademark_confidence), 4)
                if avg_trademark_confidence is not None
                else None
            ),
            "avg_lifecycle_event": (
                round(float(avg_event_confidence), 4)
                if avg_event_confidence is not None
                else None
            ),
        },
        "completeness": await _completeness_metrics(session),
    }
