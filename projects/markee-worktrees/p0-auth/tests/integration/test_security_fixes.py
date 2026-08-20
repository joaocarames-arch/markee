"""Regression tests for the 2026-07-24 security review fixes.

Covers:
- FIX-01: /deadlines is scoped to the authenticated user (no global leak).
- FIX-02: inactive users are rejected by ``get_current_user`` (403), even with
  a previously valid token.
- FIX-03: the EUIPO mock fallback is off by default in search and detail.
- FIX-04: /quality/metrics requires a superuser.
- FIX-05: staging/production config with dev-grade security refuses to boot.
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest

from app.core.config import Settings, _validate


# ── FIX-05: config guard ────────────────────────────────────────────────────


def test_production_refuses_dev_secret() -> None:
    settings = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="dev-secret-change-me",
        CORS_ORIGINS=["https://markee.pt"],
    )
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        _validate(settings)


def test_production_refuses_wildcard_cors_and_mock() -> None:
    settings = Settings(
        ENVIRONMENT="staging",
        SECRET_KEY="x" * 64,
        CORS_ORIGINS=["*"],
        ENABLE_MOCK_FALLBACK=True,
        DB_CREATE_ALL_ON_STARTUP=True,
    )
    with pytest.raises(RuntimeError) as exc:
        _validate(settings)
    message = str(exc.value)
    assert "CORS_ORIGINS" in message
    assert "ENABLE_MOCK_FALLBACK" in message
    assert "DB_CREATE_ALL_ON_STARTUP" in message


def test_development_accepts_dev_defaults() -> None:
    settings = Settings(ENVIRONMENT="development")
    assert _validate(settings) is settings


# ── FIX-01: deadline scoping ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_deadlines_scoped_to_user(db_session) -> None:
    """A user must only see deadlines for trademarks linked via their alerts."""
    from app.models.alert import Alert
    from app.models.lifecycle import Deadline
    from app.models.trademark import Trademark
    from app.models.user import User

    user_a = User(email=f"a-{uuid.uuid4().hex[:8]}@ex.pt", hashed_password="h")
    user_b = User(email=f"b-{uuid.uuid4().hex[:8]}@ex.pt", hashed_password="h")
    db_session.add_all([user_a, user_b])
    await db_session.flush()

    tm_a = Trademark(
        source_id=f"EUIPO-{uuid.uuid4().hex[:10]}",
        jurisdiction="EUIPO",
        word_mark="MARCA-A",
    )
    tm_b = Trademark(
        source_id=f"EUIPO-{uuid.uuid4().hex[:10]}",
        jurisdiction="EUIPO",
        word_mark="MARCA-B",
    )
    db_session.add_all([tm_a, tm_b])
    await db_session.flush()

    db_session.add_all(
        [
            Alert(
                user_id=user_a.id,
                trademark_id=tm_a.id,
                alert_type="similar_filing",
                title="match A",
            ),
            Alert(
                user_id=user_b.id,
                trademark_id=tm_b.id,
                alert_type="similar_filing",
                title="match B",
            ),
        ]
    )
    due = date.today() + timedelta(days=30)
    db_session.add_all(
        [
            Deadline(
                trademark_id=tm_a.id,
                deadline_type="renewal",
                due_date=due,
                status="pending",
            ),
            Deadline(
                trademark_id=tm_b.id,
                deadline_type="renewal",
                due_date=due,
                status="pending",
            ),
        ]
    )
    await db_session.commit()

    from app.api.deadlines import list_deadlines

    rows_a = await list_deadlines(upcoming_only=True, db=db_session, current_user=user_a)
    rows_b = await list_deadlines(upcoming_only=True, db=db_session, current_user=user_b)

    assert {r.trademark_id for r in rows_a} == {tm_a.id}
    assert {r.trademark_id for r in rows_b} == {tm_b.id}


@pytest.mark.asyncio
async def test_deadlines_empty_for_user_without_alerts(db_session) -> None:
    from app.api.deadlines import list_deadlines
    from app.models.lifecycle import Deadline
    from app.models.trademark import Trademark
    from app.models.user import User

    user = User(email=f"c-{uuid.uuid4().hex[:8]}@ex.pt", hashed_password="h")
    tm = Trademark(
        source_id=f"INPI-{uuid.uuid4().hex[:10]}",
        jurisdiction="INPI",
        word_mark="MARCA-GLOBAL",
    )
    db_session.add_all([user, tm])
    await db_session.flush()
    db_session.add(
        Deadline(
            trademark_id=tm.id,
            deadline_type="renewal",
            due_date=date.today() + timedelta(days=10),
            status="pending",
        )
    )
    await db_session.commit()

    rows = await list_deadlines(upcoming_only=True, db=db_session, current_user=user)
    assert rows == []


# ── FIX-02: inactive user rejected on authenticated requests ────────────────


@pytest.mark.asyncio
async def test_get_current_user_rejects_inactive(db_session) -> None:
    from fastapi import HTTPException

    from app.api.auth import get_current_user
    from app.core.security import create_access_token
    from app.models.user import User

    user = User(
        email=f"inactive-{uuid.uuid4().hex[:8]}@ex.pt",
        hashed_password="h",
        is_active=False,
    )
    db_session.add(user)
    await db_session.commit()

    token = create_access_token({"sub": str(user.id)})
    with pytest.raises(HTTPException) as exc:
        await get_current_user(token=token, db=db_session)
    assert exc.value.status_code == 403


# ── FIX-03: mock fallback off by default ────────────────────────────────────


@pytest.mark.asyncio
async def test_search_no_mock_fallback_by_default(db_session, monkeypatch) -> None:
    from app.api import trademarks as tm_module

    monkeypatch.setattr(tm_module.settings, "ENABLE_MOCK_FALLBACK", False)
    rows = await tm_module.list_trademarks(
        q="inexistente-xyz",
        jurisdiction=None,
        nice_class=None,
        limit=10,
        offset=0,
        db=db_session,
    )
    assert rows == []


@pytest.mark.asyncio
async def test_search_mock_fallback_labelled_when_enabled(
    db_session, monkeypatch
) -> None:
    from app.api import trademarks as tm_module

    monkeypatch.setattr(tm_module.settings, "ENABLE_MOCK_FALLBACK", True)
    rows = await tm_module.list_trademarks(
        q="cafe",
        jurisdiction=None,
        nice_class=None,
        limit=5,
        offset=0,
        db=db_session,
    )
    assert rows, "mock fallback should return labelled records when enabled"
    assert all((r.status or "").startswith("MOCK/") for r in rows)


# ── FIX-04: quality metrics restricted to superusers ────────────────────────


@pytest.mark.asyncio
async def test_quality_metrics_forbidden_for_regular_user(db_session) -> None:
    from fastapi import HTTPException

    from app.api.quality import quality_metrics
    from app.models.user import User

    user = User(email=f"q-{uuid.uuid4().hex[:8]}@ex.pt", hashed_password="h")
    db_session.add(user)
    await db_session.commit()

    with pytest.raises(HTTPException) as exc:
        await quality_metrics(db=db_session, current_user=user)
    assert exc.value.status_code == 403
