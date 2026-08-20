"""Tests for the ingestion service: idempotency, versioning, upserts."""
from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import func, select

from app.models.goods_services import GoodsServices
from app.models.holder import Holder, TrademarkHolder
from app.models.lifecycle import LifecycleEvent
from app.models.nice_class import NiceClass
from app.models.raw_response import RawApiResponse
from app.models.representative import Representative, TrademarkRepresentative
from app.models.review_queue import ReviewQueueItem
from app.models.source import Source, SourceRun
from app.models.trademark import Trademark
from app.models.trademark_version import TrademarkVersion
from app.services.bpi_parser import BPIEvent
from app.services.euipo_service import EUIPOService
from app.services.ingestion import (
    IngestionService,
    add_months,
    classify_change,
    compute_diff,
    get_or_create_source,
    normalize_trademark_record,
)


def sample_record(**overrides) -> dict:
    record = {
        "source_id": "EUIPO-018765432",
        "application_number": "018765432",
        "application_date": "2024-01-15",
        "registration_number": "018765432",
        "registration_date": "2024-06-01",
        "word_mark": "ACME TECH",
        "status": "Registered",
        "renewal_status": "Active",
        "nice_classes": [9, 42],
        "applicants": [{"name": "Acme Corp", "address": "Lisbon", "country": "PT"}],
        "representatives": [{"name": "Agente Silva"}],
        "goods_services": "Software; IT services",
        "jurisdiction": "EUIPO",
    }
    record.update(overrides)
    return record


async def _count(session, model) -> int:
    return (await session.execute(select(func.count()).select_from(model))).scalar_one()


class TestNormalization:
    def test_snake_case_passthrough(self):
        normalized = normalize_trademark_record(sample_record())
        assert normalized["source_id"] == "EUIPO-018765432"
        assert normalized["application_date"] == date(2024, 1, 15)
        assert normalized["nice_classes"] == [9, 42]

    def test_camel_case_mapping(self):
        normalized = normalize_trademark_record(
            {
                "applicationNumber": "018999999",
                "wordMark": "CAMEL MARK",
                "applicationDate": "2025-02-01",
                "niceClasses": [3],
                "jurisdiction": "EUIPO",
                "updateDate": "2026-07-01T10:00:00Z",
            }
        )
        assert normalized["source_id"] == "EUIPO-018999999"
        assert normalized["word_mark"] == "CAMEL MARK"
        assert normalized["application_date"] == date(2025, 2, 1)
        assert normalized["update_date"] is not None
        assert normalized["update_date"].tzinfo is not None


class TestDiffAndClassification:
    def test_no_diff_for_identical_snapshots(self):
        snap = {"status": "Registered", "word_mark": "X"}
        assert compute_diff(snap, dict(snap)) == {}

    def test_diff_sections(self):
        diff = compute_diff(
            {"status": "Published", "word_mark": "X", "renewal_status": "Old"},
            {"status": "Registered", "word_mark": "X", "renewal_status": None,
             "registration_number": "123"},
        )
        assert diff["changed"]["status"] == {"old": "Published", "new": "Registered"}
        assert diff["added"]["registration_number"] == "123"
        assert diff["removed"]["renewal_status"] == "Old"

    def test_classify_change_priorities(self):
        assert classify_change({"changed": {"status": {}}}) == "status_change"
        assert classify_change({"changed": {"applicants": {}}}) == "owner_change"
        assert classify_change({"changed": {"renewal_status": {}}}) == "renewal"
        assert classify_change({"changed": {"nice_classes": {}}}) == "classification_change"
        assert classify_change({"changed": {"word_mark": {}}}) == "update"

    def test_add_months(self):
        assert add_months(date(2026, 7, 24), 2) == date(2026, 9, 24)
        assert add_months(date(2026, 12, 15), 2) == date(2027, 2, 15)
        assert add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)


class TestTrademarkIngestion:
    @pytest.mark.asyncio
    async def test_create_new_trademark(self, db_session):
        service = IngestionService(db_session)
        result = await service.ingest_trademark(sample_record())
        await db_session.commit()

        assert result.status == "created"
        assert result.version_number == 1
        assert result.confidence is not None

        trademark = (
            await db_session.execute(
                select(Trademark).where(Trademark.source_id == "EUIPO-018765432")
            )
        ).scalar_one()
        assert trademark.word_mark == "ACME TECH"
        assert trademark.confidence_score == result.confidence

        versions = (
            await db_session.execute(
                select(TrademarkVersion).where(
                    TrademarkVersion.trademark_id == trademark.id
                )
            )
        ).scalars().all()
        assert len(versions) == 1
        assert versions[0].change_type == "created"
        assert versions[0].diff_from_previous is None
        assert versions[0].snapshot["word_mark"] == "ACME TECH"

        assert await _count(db_session, Holder) == 1
        assert await _count(db_session, Representative) == 1
        assert await _count(db_session, TrademarkHolder) == 1
        assert await _count(db_session, TrademarkRepresentative) == 1
        # "Software; IT services" → 2 terms paired with classes 9 and 42.
        assert await _count(db_session, GoodsServices) == 2
        assert await _count(db_session, NiceClass) == 2

    @pytest.mark.asyncio
    async def test_reingest_identical_record_is_idempotent(self, db_session):
        service = IngestionService(db_session)
        await service.ingest_trademark(sample_record())
        await db_session.commit()

        result = await service.ingest_trademark(sample_record())
        await db_session.commit()

        assert result.status == "unchanged"
        assert await _count(db_session, Trademark) == 1
        assert await _count(db_session, TrademarkVersion) == 1
        assert await _count(db_session, Holder) == 1
        assert await _count(db_session, TrademarkHolder) == 1
        assert await _count(db_session, GoodsServices) == 2

    @pytest.mark.asyncio
    async def test_status_change_creates_version_two(self, db_session):
        service = IngestionService(db_session)
        await service.ingest_trademark(sample_record(status="Published"))
        await db_session.commit()

        result = await service.ingest_trademark(sample_record(status="Registered"))
        await db_session.commit()

        assert result.status == "updated"
        assert result.version_number == 2

        version = (
            await db_session.execute(
                select(TrademarkVersion).where(TrademarkVersion.version_number == 2)
            )
        ).scalar_one()
        assert version.change_type == "status_change"
        assert version.diff_from_previous["changed"]["status"] == {
            "old": "Published",
            "new": "Registered",
        }

        trademark = (
            await db_session.execute(select(Trademark))
        ).scalar_one()
        assert trademark.status == "Registered"

    @pytest.mark.asyncio
    async def test_owner_change_syncs_holder_links(self, db_session):
        service = IngestionService(db_session)
        await service.ingest_trademark(sample_record())
        await db_session.commit()

        result = await service.ingest_trademark(
            sample_record(
                applicants=[{"name": "New Owner SA", "country": "ES"}],
            )
        )
        await db_session.commit()

        assert result.status == "updated"
        version = (
            await db_session.execute(
                select(TrademarkVersion).where(TrademarkVersion.version_number == 2)
            )
        ).scalar_one()
        assert version.change_type == "owner_change"

        # Both holder entities survive; only the active link is replaced.
        assert await _count(db_session, Holder) == 2
        links = (
            await db_session.execute(select(TrademarkHolder))
        ).scalars().all()
        assert len(links) == 1
        new_holder = (
            await db_session.execute(
                select(Holder).where(Holder.name == "New Owner SA")
            )
        ).scalar_one()
        assert links[0].holder_id == new_holder.id

    @pytest.mark.asyncio
    async def test_holder_upsert_updates_in_place(self, db_session):
        service = IngestionService(db_session)
        await service.ingest_trademark(sample_record())
        await db_session.commit()

        await service.ingest_trademark(
            sample_record(
                applicants=[
                    {"name": "Acme Corp", "address": "Porto", "country": "PT"}
                ],
            )
        )
        await db_session.commit()

        holders = (await db_session.execute(select(Holder))).scalars().all()
        assert len(holders) == 1
        assert holders[0].address == "Porto"

    @pytest.mark.asyncio
    async def test_low_confidence_record_is_queued_for_review(self, db_session):
        service = IngestionService(db_session)
        result = await service.ingest_trademark(
            {
                "source_id": "EUIPO-BAD-1",
                "application_number": None,
                "word_mark": "",
                "jurisdiction": "EUIPO",
            }
        )
        await db_session.commit()

        assert result.status == "created"
        assert result.queued_for_review

        item = (
            await db_session.execute(select(ReviewQueueItem))
        ).scalar_one()
        assert item.item_type == "trademark_record"
        assert item.status == "pending"
        assert item.confidence_score == result.confidence

    @pytest.mark.asyncio
    async def test_record_without_source_id_is_skipped(self, db_session):
        service = IngestionService(db_session)
        result = await service.ingest_trademark({"word_mark": "NO ID"})
        assert result.status == "skipped"
        assert await _count(db_session, Trademark) == 0


class TestBPIEventIngestion:
    def _event(self, **overrides) -> BPIEvent:
        defaults = dict(
            event_type="publication",
            event_date=date(2026, 7, 20),
            application_number="N-123456",
            description="Publicação do pedido | Nº de pedido N-123456 | MARCA LUSA",
            source="BPI",
            raw_text="Publicação do pedido",
            page_number=3,
            source_excerpt="Publicação do pedido | Nº de pedido N-123456 | MARCA LUSA",
            confidence_score=0.95,
        )
        defaults.update(overrides)
        return BPIEvent(**defaults)

    @pytest.mark.asyncio
    async def test_event_created_with_provenance_and_deadline(self, db_session):
        service = IngestionService(db_session)
        await service.ingest_trademark(
            sample_record(
                source_id="INPI-N-123456",
                application_number="N-123456",
                jurisdiction="INPI",
            )
        )
        await db_session.commit()

        summary = await service.ingest_bpi_events([self._event()])
        await db_session.commit()

        assert summary.created == 1
        event = (await db_session.execute(select(LifecycleEvent))).scalar_one()
        assert event.page_number == 3
        assert event.source_excerpt.startswith("Publicação")
        assert event.confidence_score == 0.95
        # PT opposition window: publication + 2 months.
        assert event.deadline_date == date(2026, 9, 20)

    @pytest.mark.asyncio
    async def test_reingesting_same_bulletin_is_idempotent(self, db_session):
        service = IngestionService(db_session)
        await service.ingest_trademark(
            sample_record(
                source_id="INPI-N-123456",
                application_number="N-123456",
                jurisdiction="INPI",
            )
        )
        await db_session.commit()

        first = await service.ingest_bpi_events([self._event()])
        second = await service.ingest_bpi_events([self._event()])
        await db_session.commit()

        assert first.created == 1
        assert second.created == 0
        assert second.duplicates == 1
        assert await _count(db_session, LifecycleEvent) == 1

    @pytest.mark.asyncio
    async def test_unmatched_event_goes_to_review_queue(self, db_session):
        service = IngestionService(db_session)
        summary = await service.ingest_bpi_events(
            [self._event(application_number="999999")]
        )
        await db_session.commit()

        assert summary.unmatched == 1
        assert await _count(db_session, LifecycleEvent) == 0
        item = (await db_session.execute(select(ReviewQueueItem))).scalar_one()
        assert item.source == "inpi_bpi"
        assert "999999" in item.reason

    @pytest.mark.asyncio
    async def test_low_confidence_event_goes_to_review_queue(self, db_session):
        service = IngestionService(db_session)
        await service.ingest_trademark(
            sample_record(
                source_id="INPI-N-123456",
                application_number="N-123456",
                jurisdiction="INPI",
            )
        )
        await db_session.commit()

        summary = await service.ingest_bpi_events(
            [self._event(confidence_score=0.3)]
        )
        await db_session.commit()

        assert summary.queued_for_review == 1
        assert await _count(db_session, LifecycleEvent) == 0
        item = (await db_session.execute(select(ReviewQueueItem))).scalar_one()
        assert item.trademark_id is not None
        assert item.confidence_score == 0.3


class TestSourcesAndRuns:
    @pytest.mark.asyncio
    async def test_get_or_create_source_is_idempotent(self, db_session):
        first = await get_or_create_source(db_session, "euipo_api")
        second = await get_or_create_source(db_session, "euipo_api")
        assert first.id == second.id
        assert first.source_type == "api_rest"
        assert await _count(db_session, Source) == 1

    @pytest.mark.asyncio
    async def test_euipo_incremental_import_pipeline(self, db_session):
        """Mock-mode end-to-end: poll → raw preserved → ingest → run tracked."""
        service = EUIPOService(client_id="", client_secret="", session=db_session)
        assert service.mock_mode

        summary = await service.run_incremental_import(session=db_session)

        assert summary["status"] == "completed"
        assert summary["processed"] == 3
        assert summary["new"] == 3
        assert summary["failed"] == 0

        assert await _count(db_session, Trademark) == 3
        assert await _count(db_session, TrademarkVersion) == 3
        assert await _count(db_session, RawApiResponse) == 1

        run = (await db_session.execute(select(SourceRun))).scalar_one()
        assert run.status == "completed"
        assert run.items_new == 3
        assert run.cursor_value is not None

    @pytest.mark.asyncio
    async def test_euipo_reimport_is_idempotent(self, db_session):
        service = EUIPOService(client_id="", client_secret="", session=db_session)
        await service.run_incremental_import(session=db_session)

        second = EUIPOService(client_id="", client_secret="", session=db_session)
        summary = await second.run_incremental_import(session=db_session)

        assert summary["new"] == 0
        assert summary["unchanged"] == 3
        assert await _count(db_session, Trademark) == 3
        assert await _count(db_session, TrademarkVersion) == 3
        assert await _count(db_session, SourceRun) == 2
        assert await _count(db_session, Source) == 1
