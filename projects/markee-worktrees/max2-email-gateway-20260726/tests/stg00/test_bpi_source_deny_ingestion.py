"""STG00-WP1: BPI ingestion must early-exit while BPI is disabled."""
from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import func, select

from app.models.lifecycle import LifecycleEvent
from app.models.review_queue import ReviewQueueItem
from app.services.bpi_parser import BPIEvent
from app.services.ingestion import IngestionService

from tests.stg00.factories import make_trademark


async def _count(session, model) -> int:
    return (await session.execute(select(func.count()).select_from(model))).scalar_one()


def make_bpi_event(**overrides) -> BPIEvent:
    defaults = dict(
        event_type="publication",
        event_date=date(2026, 7, 1),
        application_number="N-777001",
        description="Publicação do pedido",
        source="BPI",
        raw_text="Publicação do pedido | Nº de pedido N-777001 | MARCA TESTE",
        page_number=3,
        source_excerpt="Publicação do pedido | Nº de pedido N-777001 | MARCA TESTE",
        confidence_score=0.95,
    )
    defaults.update(overrides)
    return BPIEvent(**defaults)


@pytest.mark.asyncio
async def test_bpi_event_not_ingested_when_disabled(db_session):
    """With default settings, ingest_bpi_events writes zero rows of any kind."""
    await make_trademark(db_session, application_number="N-777001")

    service = IngestionService(db_session)
    events = [
        make_bpi_event(),
        make_bpi_event(application_number="", confidence_score=0.2),
        make_bpi_event(application_number="N-999999"),
    ]
    summary = await service.ingest_bpi_events(events)

    assert summary.created == 0
    assert summary.skipped_disabled == len(events)
    assert summary.queued_for_review == 0
    assert summary.unmatched == 0
    assert await _count(db_session, LifecycleEvent) == 0
    assert await _count(db_session, ReviewQueueItem) == 0


@pytest.mark.asyncio
async def test_bpi_ingestion_works_when_explicitly_enabled(db_session, monkeypatch):
    """The gate is a switch, not a lobotomy: explicit local enablement (still
    gated by João for any deployment) restores the existing behaviour."""
    from app.core import config

    monkeypatch.setattr(config.settings, "BPI_ENABLED", True)
    monkeypatch.setattr(config.settings, "BPI_INGESTION_ALLOWED", True)

    await make_trademark(db_session, application_number="N-777001")
    service = IngestionService(db_session)
    summary = await service.ingest_bpi_events([make_bpi_event()])

    assert summary.created == 1
    assert summary.skipped_disabled == 0
    assert await _count(db_session, LifecycleEvent) == 1


def test_parse_bpi_task_early_exits_when_disabled(monkeypatch):
    """The Celery task returns a factual skip before any download or DB use."""
    from app.services.bpi_parser import BPIParser
    from app.tasks.parse_bpi import download_and_parse

    def _explode(*args, **kwargs):  # pragma: no cover - must never run
        raise AssertionError("BPI download attempted while BPI is disabled")

    monkeypatch.setattr(BPIParser, "download_latest", _explode)

    result = download_and_parse("2026-07-01")
    assert result == {
        "status": "skipped",
        "reason": "bpi_disabled",
        "date": "2026-07-01",
    }
