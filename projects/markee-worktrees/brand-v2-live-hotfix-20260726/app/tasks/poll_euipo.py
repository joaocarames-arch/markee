"""Celery task: poll the EUIPO API for recently changed trademarks.

The task drives the full incremental pipeline: poll ``updateDate`` → preserve
raw responses in ``raw.api_responses`` → ingest through the ingestion service
(versioning, holder/representative upserts) → track the run in
``core.source_runs``.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from app.models.database import AsyncSessionLocal
from app.services.euipo_service import EUIPOService
from app.tasks import celery_app, run_async


@celery_app.task(name="app.tasks.poll_euipo.poll_recent_changes")
def poll_recent_changes(since: str | None = None) -> dict[str, Any]:
    """Poll EUIPO for trademarks changed since a given time and ingest them.

    Args:
        since: Optional ISO timestamp; defaults to the last completed run's
            cursor (with a one-hour overlap), or six hours ago on first run.

    Returns:
        A summary dict with the run id and per-outcome record counts.
    """
    since_dt = datetime.fromisoformat(since) if since else None

    async def _run() -> dict[str, Any]:
        async with AsyncSessionLocal() as db:
            service = EUIPOService(session=db)
            summary = await service.run_incremental_import(since_dt, session=db)
            return {"status": "ok", "count": summary["processed"], **summary}

    return run_async(_run())
