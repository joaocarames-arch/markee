"""STG00-WP1: alert creation must deny BPI-rooted trademarks."""
from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import func, select

from app.models.alert import Alert
from app.services.alerts import AlertService

from tests.stg00.factories import make_trademark, make_user


async def _alert_count(session) -> int:
    return (await session.execute(select(func.count()).select_from(Alert))).scalar_one()


@pytest.mark.asyncio
async def test_similarity_alert_denied_for_bpi_trademark(db_session):
    user = await make_user(db_session)
    trademark = await make_trademark(db_session, source_name="inpi_bpi")

    service = AlertService(db_session)
    alert = await service.generate_similarity_alert(
        user_id=str(user.id),
        watchlist_id=None,
        watchlist_item_id=None,
        trademark_id=str(trademark.id),
        similarity_score=91.0,
        phonetic_score=88.0,
        class_overlap_score=100.0,
    )

    assert alert is None
    assert await _alert_count(db_session) == 0


@pytest.mark.asyncio
async def test_deadline_alert_denied_for_bpi_trademark(db_session):
    user = await make_user(db_session)
    trademark = await make_trademark(db_session, source_name="inpi_bpi")

    service = AlertService(db_session)
    alert = await service.generate_deadline_alert(
        user_id=str(user.id),
        trademark_id=str(trademark.id),
        deadline_type="opposition",
        due_date=date(2026, 9, 1),
        days_remaining=30,
    )

    assert alert is None
    assert await _alert_count(db_session) == 0


@pytest.mark.asyncio
async def test_non_bpi_similarity_alert_accepts_string_ids(db_session):
    """Similarity generation normalizes the public string-ID contract."""
    user = await make_user(db_session)
    trademark = await make_trademark(
        db_session, source_name="euipo_api", jurisdiction="EUIPO"
    )

    alert = await AlertService(db_session).generate_similarity_alert(
        user_id=str(user.id),
        watchlist_id=None,
        watchlist_item_id=None,
        trademark_id=str(trademark.id),
        similarity_score=91.0,
        phonetic_score=88.0,
        class_overlap_score=100.0,
    )

    assert alert is not None
    assert alert.user_id == user.id
    assert alert.trademark_id == trademark.id
    assert alert.watchlist_id is None
    assert alert.watchlist_item_id is None
    assert await _alert_count(db_session) == 1


@pytest.mark.asyncio
async def test_non_bpi_deadline_alert_accepts_string_ids(db_session):
    """Deadline generation normalizes the public string-ID contract."""
    user = await make_user(db_session)
    trademark = await make_trademark(
        db_session, source_name="euipo_api", jurisdiction="EUIPO"
    )

    alert = await AlertService(db_session).generate_deadline_alert(
        user_id=str(user.id),
        trademark_id=str(trademark.id),
        deadline_type="renewal",
        due_date=date(2026, 9, 1),
        days_remaining=30,
    )

    assert alert is not None
    assert alert.user_id == user.id
    assert alert.trademark_id == trademark.id
    assert await _alert_count(db_session) == 1


@pytest.mark.asyncio
async def test_deduplicate_accepts_string_ids(db_session):
    """Duplicate lookup normalizes IDs supplied by production callers."""
    user = await make_user(db_session)
    trademark = await make_trademark(
        db_session, source_name="euipo_api", jurisdiction="EUIPO"
    )
    db_session.add(
        Alert(
            user_id=user.id,
            trademark_id=trademark.id,
            alert_type="renewal",
            title="Renovação em breve",
        )
    )
    await db_session.commit()

    duplicate = await AlertService(db_session).deduplicate(
        user_id=str(user.id),
        alert_type="renewal",
        trademark_id=str(trademark.id),
    )

    assert duplicate is True
