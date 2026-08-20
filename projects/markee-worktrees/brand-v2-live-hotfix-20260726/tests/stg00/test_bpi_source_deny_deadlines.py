"""STG00-WP1: deadline recalculation must never create BPI-rooted deadlines."""
from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import select

from app.models.lifecycle import Deadline

from tests.stg00.factories import make_publication_event, make_trademark


async def _deadlines(session) -> list[Deadline]:
    return list((await session.execute(select(Deadline))).scalars().all())


@pytest.mark.asyncio
async def test_calculate_deadlines_skips_bpi_trademarks(db_session):
    """A trademark ingested from inpi_bpi produces zero deadlines of any type."""
    from app.tasks.calculate_deadlines import recalculate_deadlines

    trademark = await make_trademark(
        db_session,
        source_name="inpi_bpi",
        registration_date=date(2020, 3, 10),
    )
    await make_publication_event(db_session, trademark, source="BPI")

    result = await recalculate_deadlines(db_session)

    assert result["count"] == 0
    assert await _deadlines(db_session) == []


@pytest.mark.asyncio
async def test_bpi_publication_never_creates_deadline(db_session):
    """A BPI publication event on a non-BPI trademark yields no opposition
    deadline; renewal deadlines from the trademark itself are unaffected."""
    from app.tasks.calculate_deadlines import recalculate_deadlines

    trademark = await make_trademark(
        db_session,
        source_name="euipo_api",
        registration_date=date(2020, 3, 10),
    )
    await make_publication_event(db_session, trademark, source="BPI")

    await recalculate_deadlines(db_session)

    deadlines = await _deadlines(db_session)
    types = sorted(d.deadline_type for d in deadlines)
    assert types == ["grace_period", "renewal"]
    assert not any(d.deadline_type == "opposition" for d in deadlines)


@pytest.mark.asyncio
async def test_non_bpi_sources_still_create_deadlines(db_session):
    """Authorized sources keep the full deadline pipeline (renewal, grace
    period and opposition)."""
    from app.tasks.calculate_deadlines import recalculate_deadlines

    trademark = await make_trademark(
        db_session,
        source_name="euipo_api",
        registration_date=date(2020, 3, 10),
        jurisdiction="EUIPO",
    )
    await make_publication_event(db_session, trademark, source="euipo_api")

    result = await recalculate_deadlines(db_session)

    deadlines = await _deadlines(db_session)
    types = sorted(d.deadline_type for d in deadlines)
    assert types == ["grace_period", "opposition", "renewal"]
    assert result["count"] == 3
