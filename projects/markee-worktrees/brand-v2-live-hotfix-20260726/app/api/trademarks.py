"""Trademark router — search and detail lookup with EUIPO fallback."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.common import ORMModel, StrId
from app.models.database import get_db
from app.models.trademark import Trademark
from app.core.config import settings
from app.services.euipo_service import get_euipo_service

router = APIRouter(prefix="/trademarks", tags=["trademarks"])


class TrademarkOut(ORMModel):
    """Public representation of a trademark record."""

    id: StrId | None = None
    source_id: str
    application_number: str | None = None
    application_date: date | None = None
    registration_number: str | None = None
    registration_date: date | None = None
    word_mark: str | None = None
    status: str | None = None
    nice_classes: list[int] | None = None
    jurisdiction: str
    applicants: list | None = None
    goods_services: str | None = None


@router.get("", response_model=list[TrademarkOut])
async def list_trademarks(
    q: str | None = Query(None, description="Texto a pesquisar"),
    jurisdiction: str | None = Query(None),
    nice_class: int | None = Query(None, ge=1, le=45),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[TrademarkOut]:
    """List trademarks, falling back to the EUIPO service when the DB is empty.

    Args:
        q: Optional free-text query matched against the word mark.
        jurisdiction: Optional jurisdiction filter.
        limit: Maximum number of results (1–200).
        offset: Pagination offset.
        db: Database session.

    Returns:
        A list of matching trademarks.
    """
    stmt = select(Trademark)
    if q:
        stmt = stmt.where(Trademark.word_mark.ilike(f"%{q}%"))
    if jurisdiction:
        stmt = stmt.where(Trademark.jurisdiction == jurisdiction)
    if nice_class is not None:
        stmt = stmt.where(Trademark.nice_classes.contains([nice_class]))
    stmt = stmt.limit(limit).offset(offset)

    result = await db.execute(stmt)
    rows = result.scalars().all()

    if not rows and q and settings.ENABLE_MOCK_FALLBACK:
        # Development-only fallback so the UI is never empty in dev. Records
        # are explicitly labelled as mock and this path is disabled by
        # default (and forbidden outside development by config validation).
        service = get_euipo_service()
        return [
            TrademarkOut(**{**record, "status": f"MOCK/{record.get('status', '')}"})
            for record in service._mock_search(q, limit)
        ]

    return [TrademarkOut.model_validate(row) for row in rows]


@router.get("/{application_number}", response_model=TrademarkOut)
async def get_trademark(
    application_number: str, db: AsyncSession = Depends(get_db)
) -> TrademarkOut:
    """Return a single trademark by application number.

    Args:
        application_number: The application number to look up.
        db: Database session.

    Returns:
        The matching trademark.

    Raises:
        HTTPException: 404 if the trademark cannot be found locally or via the
            EUIPO fallback.
    """
    result = await db.execute(
        select(Trademark).where(Trademark.application_number == application_number)
    )
    row = result.scalar_one_or_none()
    if row is not None:
        return TrademarkOut.model_validate(row)

    if settings.ENABLE_MOCK_FALLBACK:
        service = get_euipo_service()
        record = service._mock_details(application_number)
        if record:
            return TrademarkOut(
                **{**record, "status": f"MOCK/{record.get('status', '')}"}
            )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Marca não encontrada"
    )
