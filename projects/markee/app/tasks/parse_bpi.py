"""Celery task: download and parse the daily BPI PDF.

Pipeline: download → archive the PDF in ``core.documents`` (checksummed) →
extract page-referenced events with confidence scores → ingest them via the
ingestion service (deduplicated; uncertain results go to ``app.review_queue``)
→ track the run in ``core.source_runs``.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from app.core.source_policy import get_source_policy
from app.models.database import AsyncSessionLocal
from app.services import ingestion
from app.services.bpi_parser import BPIParser
from app.tasks import celery_app, run_async


@celery_app.task(name="app.tasks.parse_bpi.download_and_parse")
def download_and_parse(date_str: str | None = None) -> dict[str, Any]:
    """Download the BPI PDF for a date and persist its lifecycle events.

    Events are attached to trademarks matched by application number; events
    without a match, or scored below the confidence threshold, are queued in
    ``app.review_queue`` instead of being silently dropped.

    Args:
        date_str: Optional ISO date; defaults to today.

    Returns:
        A summary dict with per-outcome event counts.
    """
    target_date = date.fromisoformat(date_str) if date_str else datetime.now().date()

    if not get_source_policy().bpi_ingestion_active:
        # BPI containment: no download, no parsing, no DB writes.
        return {
            "status": "skipped",
            "reason": "bpi_disabled",
            "date": target_date.isoformat(),
        }

    parser = BPIParser()

    async def _run() -> dict[str, Any]:
        try:
            pdf_bytes = await parser.download_latest(target_date)
        except Exception:  # noqa: BLE001 - network failures must not crash the beat
            pdf_bytes = b""

        if not pdf_bytes:
            return {
                "status": "skipped",
                "reason": "download_failed",
                "date": target_date.isoformat(),
            }

        async with AsyncSessionLocal() as db:
            source = await ingestion.get_or_create_source(db, "inpi_bpi")
            run = await ingestion.start_run(db, source, "daily_parse")
            try:
                document = await parser.store_document(
                    db,
                    pdf_bytes,
                    source_url=parser.download_url_for(target_date),
                    publication_date=target_date,
                )
                events = parser.parse_pdf(pdf_bytes, event_date=target_date)
                service = ingestion.IngestionService(db)
                summary = await service.ingest_bpi_events(
                    events, document_id=document.id
                )
            except Exception as exc:  # noqa: BLE001 - the run row must record failures
                ingestion.finish_run(run, status="failed", error_message=str(exc))
                await db.commit()
                raise

            run.items_processed = len(events)
            run.items_new = summary.created
            run.items_failed = summary.unmatched + summary.queued_for_review
            ingestion.finish_run(
                run, status="completed", cursor_value=target_date.isoformat()
            )
            await db.commit()
            return {
                "status": "ok",
                "date": target_date.isoformat(),
                "count": summary.created,
                "events_extracted": len(events),
                "duplicates": summary.duplicates,
                "queued_for_review": summary.queued_for_review,
                "unmatched": summary.unmatched,
                "document_id": str(document.id),
            }

    return run_async(_run())
