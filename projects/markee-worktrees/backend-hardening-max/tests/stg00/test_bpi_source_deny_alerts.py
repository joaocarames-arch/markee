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
async def test_non_bpi_alerts_still_created(db_session):
    """Alert generation for authorized sources must not regress."""
    user = await make_user(db_session)
    trademark = await make_trademark(
        db_session, source_name="euipo_api", jurisdiction="EUIPO"
    )

    service = AlertService(db_session)
    similarity = await service.generate_similarity_alert(
        user_id=str(user.id),
        watchlist_id=None,
        watchlist_item_id=None,
        trademark_id=str(trademark.id),
        similarity_score=91.0,
        phonetic_score=88.0,
        class_overlap_score=100.0,
    )
    deadline = await service.generate_deadline_alert(
        user_id=str(user.id),
        trademark_id=str(trademark.id),
        deadline_type="renewal",
        due_date=date(2026, 9, 1),
        days_remaining=30,
    )

    assert similarity is not None
    assert deadline is not None
    assert await _alert_count(db_session) == 2
