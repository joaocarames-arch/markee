"""Watchlist router — CRUD for watchlists and their watched items."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.api.common import ORMModel, StrId
from app.models.database import get_db
from app.models.user import User
from app.models.watchlist import Watchlist, WatchlistItem

router = APIRouter(prefix="/watchlists", tags=["watchlists"])

_NOT_FOUND = "Vigilância não encontrada"


class WatchlistCreate(BaseModel):
    """Payload for creating a watchlist."""

    name: str
    similarity_threshold: int = 80
    phonetic_weight: float = 0.3
    class_weight: float = 0.2
    nice_classes_filter: list[int] | None = None
    jurisdictions: list[str] | None = None


class WatchlistUpdate(BaseModel):
    """Payload for partially updating a watchlist."""

    name: str | None = None
    similarity_threshold: int | None = None
    is_active: bool | None = None


class WatchlistItemCreate(BaseModel):
    """Payload for adding a watched item."""

    mark_text: str
    nice_classes: list[int] | None = None
    notes: str | None = None


class WatchlistOut(ORMModel):
    """Public representation of a watchlist."""

    id: StrId
    user_id: StrId
    name: str
    similarity_threshold: int
    phonetic_weight: float
    class_weight: float
    nice_classes_filter: list[int] | None = None
    jurisdictions: list[str] | None = None
    is_active: bool
    created_at: datetime | None = None


class WatchlistItemOut(ORMModel):
    """Public representation of a watched item."""

    id: StrId
    watchlist_id: StrId
    mark_text: str
    nice_classes: list[int] | None = None
    notes: str | None = None
    created_at: datetime | None = None


async def _get_owned_watchlist(
    watchlist_id: UUID, db: AsyncSession, user: User
) -> Watchlist:
    """Fetch a watchlist owned by ``user`` or raise 404.

    Args:
        watchlist_id: The watchlist id.
        db: Database session.
        user: The requesting user.

    Returns:
        The owned watchlist.

    Raises:
        HTTPException: 404 if not found or not owned by the user.
    """
    result = await db.execute(
        select(Watchlist).where(
            Watchlist.id == watchlist_id, Watchlist.user_id == user.id
        )
    )
    watchlist = result.scalar_one_or_none()
    if watchlist is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND)
    return watchlist


@router.get("", response_model=list[WatchlistOut])
async def list_watchlists(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Watchlist]:
    """List the current user's watchlists."""
    result = await db.execute(
        select(Watchlist).where(Watchlist.user_id == current_user.id)
    )
    return list(result.scalars().all())


@router.post("", response_model=WatchlistOut, status_code=status.HTTP_201_CREATED)
async def create_watchlist(
    payload: WatchlistCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Watchlist:
    """Create a watchlist for the current user."""
    watchlist = Watchlist(
        user_id=current_user.id,
        name=payload.name,
        similarity_threshold=payload.similarity_threshold,
        phonetic_weight=payload.phonetic_weight,
        class_weight=payload.class_weight,
        nice_classes_filter=payload.nice_classes_filter,
        jurisdictions=payload.jurisdictions or ["EUIPO", "INPI"],
    )
    db.add(watchlist)
    await db.commit()
    await db.refresh(watchlist)
    return watchlist


@router.get("/{watchlist_id}", response_model=WatchlistOut)
async def get_watchlist(
    watchlist_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Watchlist:
    """Return a single watchlist owned by the current user."""
    return await _get_owned_watchlist(watchlist_id, db, current_user)


@router.put("/{watchlist_id}", response_model=WatchlistOut)
async def update_watchlist(
    watchlist_id: UUID,
    payload: WatchlistUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Watchlist:
    """Update mutable fields of a watchlist."""
    watchlist = await _get_owned_watchlist(watchlist_id, db, current_user)
    if payload.name is not None:
        watchlist.name = payload.name
    if payload.similarity_threshold is not None:
        watchlist.similarity_threshold = payload.similarity_threshold
    if payload.is_active is not None:
        watchlist.is_active = payload.is_active
    await db.commit()
    await db.refresh(watchlist)
    return watchlist


@router.delete(
    "/{watchlist_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
async def delete_watchlist(
    watchlist_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a watchlist owned by the current user."""
    watchlist = await _get_owned_watchlist(watchlist_id, db, current_user)
    await db.delete(watchlist)
    await db.commit()


@router.get("/{watchlist_id}/items", response_model=list[WatchlistItemOut])
async def list_items(
    watchlist_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[WatchlistItem]:
    """List the watched items of a watchlist."""
    await _get_owned_watchlist(watchlist_id, db, current_user)
    result = await db.execute(
        select(WatchlistItem).where(WatchlistItem.watchlist_id == watchlist_id)
    )
    return list(result.scalars().all())


@router.post(
    "/{watchlist_id}/items",
    response_model=WatchlistItemOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_item(
    watchlist_id: UUID,
    payload: WatchlistItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WatchlistItem:
    """Add a watched item to a watchlist."""
    await _get_owned_watchlist(watchlist_id, db, current_user)
    item = WatchlistItem(
        watchlist_id=watchlist_id,
        mark_text=payload.mark_text,
        nice_classes=payload.nice_classes,
        notes=payload.notes,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.delete(
    "/{watchlist_id}/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def remove_item(
    watchlist_id: UUID,
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Remove a watched item from a watchlist."""
    await _get_owned_watchlist(watchlist_id, db, current_user)
    result = await db.execute(
        select(WatchlistItem).where(
            WatchlistItem.id == item_id, WatchlistItem.watchlist_id == watchlist_id
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Item não encontrado"
        )
    await db.delete(item)
    await db.commit()
