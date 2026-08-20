"""Deadlines router — upcoming lifecycle deadlines scoped to the user.

Multi-tenant containment: a user only sees deadlines for trademarks they are
linked to through their own alerts (watchlist matches). There is no direct
``user_id`` on ``app.deadlines`` yet; until a dedicated monitored-marks link
exists, the alert linkage is the authoritative ownership path and prevents the
previous global-table leak.
"""
from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.api.common import ORMModel, StrId
from app.models.alert import Alert
from app.models.database import get_db
from app.models.lifecycle import Deadline
from app.models.user import User

router = APIRouter(prefix="/deadlines", tags=["deadlines"])


class DeadlineOut(ORMModel):
    """Public representation of a computed deadline."""

    id: StrId
    trademark_id: StrId
    deadline_type: str
    due_date: date
    description: str | None = None
    status: str
    alert_dates: list[date] | None = None
    created_at: datetime | None = None


@router.get("", response_model=list[DeadlineOut])
async def list_deadlines(
    upcoming_only: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Deadline]:
    """List the current user's deadlines, optionally only future ones.

    Scope: deadlines whose trademark is referenced by at least one alert
    belonging to the authenticated user. Never returns the global table.

    Args:
        upcoming_only: When ``True``, exclude deadlines already in the past.
        db: Database session.
        current_user: The authenticated user.

    Returns:
        Deadlines ordered by due date (soonest first).
    """
    owned_trademarks = (
        select(Alert.trademark_id)
        .where(Alert.user_id == current_user.id, Alert.trademark_id.is_not(None))
        .distinct()
    )
    stmt = select(Deadline).where(Deadline.trademark_id.in_(owned_trademarks))
    if upcoming_only:
        stmt = stmt.where(Deadline.due_date >= date.today())
    stmt = stmt.order_by(Deadline.due_date.asc())
    result = await db.execute(stmt)
    return list(result.scalars().all())
