"""Portfolios router — client portfolio management and prospection."""
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
from app.models.portfolio import ClientPortfolio
from app.models.team import TeamMember
from app.models.user import User
from app.models.watchlist import Watchlist, WatchlistItem
from app.services.prospection import ProspectionService

router = APIRouter(prefix="/portfolios", tags=["portfolios"])

_NOT_FOUND = "Portfólio não encontrado"


class PortfolioCreate(BaseModel):
    """Payload for creating a client portfolio."""

    name: str
    client_name: str
    client_email: str | None = None
    notes: str | None = None


class PortfolioOut(ORMModel):
    """Public representation of a client portfolio."""

    id: StrId
    team_id: StrId
    client_name: str
    client_email: str | None = None
    notes: str | None = None
    created_at: datetime | None = None


class MarkAdd(BaseModel):
    """Payload for attaching a mark to a portfolio."""

    trademark_id: str


class OpportunityOut(BaseModel):
    """A prospection opportunity surfaced for a portfolio."""

    trademark_id: str
    word_mark: str | None = None
    owner: str | None = None
    representative: str | None = None
    status: str | None = None
    nice_classes: list[int] | None = None
    jurisdiction: str | None = None
    expiry_date: str | None = None
    district: str | None = None
    opportunity_type: str


async def _team_ids(db: AsyncSession, user: User) -> list[UUID]:
    """Return the ids of all teams the user belongs to."""
    result = await db.execute(
        select(TeamMember.team_id).where(TeamMember.user_id == user.id)
    )
    return list(result.scalars().all())


async def _get_owned_portfolio(
    portfolio_id: UUID, db: AsyncSession, user: User
) -> ClientPortfolio:
    """Fetch a portfolio the user can access via team membership, or raise 404."""
    portfolio = await db.get(ClientPortfolio, portfolio_id)
    if portfolio is None or portfolio.team_id not in await _team_ids(db, user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND)
    return portfolio


@router.post("", response_model=PortfolioOut, status_code=status.HTTP_201_CREATED)
async def create_portfolio(
    payload: PortfolioCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ClientPortfolio:
    """Create a client portfolio within the user's first team.

    Raises:
        HTTPException: 400 if the user does not belong to any team.
    """
    result = await db.execute(
        select(TeamMember).where(TeamMember.user_id == current_user.id)
    )
    membership = result.scalars().first()
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Utilizador não pertence a nenhuma equipa",
        )
    portfolio = ClientPortfolio(
        team_id=membership.team_id,
        client_name=payload.client_name,
        client_email=payload.client_email,
        notes=payload.notes,
    )
    db.add(portfolio)
    await db.commit()
    await db.refresh(portfolio)
    return portfolio


@router.get("", response_model=list[PortfolioOut])
async def list_portfolios(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ClientPortfolio]:
    """List every portfolio accessible to the current user."""
    team_ids = await _team_ids(db, current_user)
    if not team_ids:
        return []
    result = await db.execute(
        select(ClientPortfolio).where(ClientPortfolio.team_id.in_(team_ids))
    )
    return list(result.scalars().all())


@router.get("/{portfolio_id}", response_model=PortfolioOut)
async def get_portfolio(
    portfolio_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ClientPortfolio:
    """Return a single accessible portfolio."""
    return await _get_owned_portfolio(portfolio_id, db, current_user)


@router.post("/{portfolio_id}/marks", status_code=status.HTTP_201_CREATED)
async def add_mark(
    portfolio_id: UUID,
    payload: MarkAdd,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Attach a mark to a portfolio via its dedicated watchlist.

    A per-portfolio watchlist is created lazily on first use.
    """
    portfolio = await _get_owned_portfolio(portfolio_id, db, current_user)

    result = await db.execute(
        select(Watchlist).where(Watchlist.client_portfolio_id == portfolio_id)
    )
    watchlist = result.scalar_one_or_none()
    if watchlist is None:
        watchlist = Watchlist(
            user_id=current_user.id,
            client_portfolio_id=portfolio_id,
            name=f"Vigilância {portfolio.client_name}",
        )
        db.add(watchlist)
        await db.commit()
        await db.refresh(watchlist)

    item = WatchlistItem(
        watchlist_id=watchlist.id,
        mark_text=payload.trademark_id,
        notes="Adicionado via portfólio",
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return {"id": str(item.id), "watchlist_id": str(watchlist.id)}


@router.delete(
    "/{portfolio_id}/marks/{mark_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def remove_mark(
    portfolio_id: UUID,
    mark_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Detach a mark from a portfolio's watchlist."""
    await _get_owned_portfolio(portfolio_id, db, current_user)

    item = await db.get(WatchlistItem, mark_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Item não encontrado"
        )
    watchlist = await db.get(Watchlist, item.watchlist_id)
    if watchlist is None or str(watchlist.client_portfolio_id) != str(portfolio_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item não pertence a este portfólio",
        )
    await db.delete(item)
    await db.commit()


@router.get("/{portfolio_id}/opportunities", response_model=list[OpportunityOut])
async def portfolio_opportunities(
    portfolio_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    """Aggregate prospection opportunities relevant to a portfolio."""
    await _get_owned_portfolio(portfolio_id, db, current_user)
    service = ProspectionService(db)
    opportunities: list[dict] = []
    opportunities.extend(
        await service.find_expiring_without_representative(months_ahead=6, limit=100)
    )
    opportunities.extend(
        await service.find_new_filings_without_agent(days_back=30, limit=100)
    )
    opportunities.extend(
        await service.find_recently_expired_active_companies(days_back=90, limit=100)
    )
    return opportunities
