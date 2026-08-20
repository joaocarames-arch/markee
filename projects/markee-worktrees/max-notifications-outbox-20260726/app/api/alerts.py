"""Alerts router — list alerts and mark them read/dismissed."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.api.common import ORMModel, StrId
from app.models.alert import Alert
from app.models.database import get_db
from app.models.user import User

router = APIRouter(prefix="/alerts", tags=["alerts"])

_NOT_FOUND = "Alerta não encontrado"


class AlertOut(ORMModel):
    """Public representation of an alert."""

    id: StrId
    user_id: StrId
    alert_type: str
    title: str
    body: str | None = None
    similarity_score: float | None = None
    phonetic_score: float | None = None
    class_overlap_score: float | None = None
    is_read: bool
    is_dismissed: bool
    created_at: datetime | None = None


async def _get_owned_alert(alert_id: UUID, db: AsyncSession, user: User) -> Alert:
    """Fetch an alert owned by ``user`` or raise 404."""
    result = await db.execute(
        select(Alert).where(Alert.id == alert_id, Alert.user_id == user.id)
    )
    alert = result.scalar_one_or_none()
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND)
    return alert


@router.get("", response_model=list[AlertOut])
async def list_alerts(
    unread_only: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Alert]:
    """List the current user's active (non-dismissed) alerts.

    Args:
        unread_only: When ``True``, return only unread alerts.
        db: Database session.
        current_user: The authenticated user.

    Returns:
        Matching alerts, newest first.
    """
    stmt = select(Alert).where(
        Alert.user_id == current_user.id, Alert.is_dismissed.is_(False)
    )
    if unread_only:
        stmt = stmt.where(Alert.is_read.is_(False))
    stmt = stmt.order_by(Alert.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("/{alert_id}/read", response_model=AlertOut)
async def mark_read(
    alert_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Alert:
    """Mark an alert as read."""
    alert = await _get_owned_alert(alert_id, db, current_user)
    alert.is_read = True
    await db.commit()
    await db.refresh(alert)
    return alert


@router.post("/{alert_id}/dismiss", response_model=AlertOut)
async def dismiss_alert(
    alert_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Alert:
    """Dismiss an alert so it no longer appears in the active list."""
    alert = await _get_owned_alert(alert_id, db, current_user)
    alert.is_dismissed = True
    await db.commit()
    await db.refresh(alert)
    return alert
