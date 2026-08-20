"""Deadlines router — upcoming lifecycle deadlines."""
from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.api.common import ORMModel, StrId
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
    """List deadlines, optionally restricted to future ones.

    Args:
        upcoming_only: When ``True``, exclude deadlines already in the past.
        db: Database session.
        current_user: The authenticated user.

    Returns:
        Deadlines ordered by due date (soonest first).
    """
    stmt = select(Deadline)
    if upcoming_only:
        stmt = stmt.where(Deadline.due_date >= date.today())
    stmt = stmt.order_by(Deadline.due_date.asc())
    result = await db.execute(stmt)
    return list(result.scalars().all())
