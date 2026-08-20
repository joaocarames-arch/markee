"""Quality router — data-quality metrics for the ingestion pipeline."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.models.database import get_db
from app.models.user import User
from app.services.quality import compute_quality_metrics

router = APIRouter(prefix="/quality", tags=["quality"])


@router.get("/metrics")
async def quality_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Return the data-quality report for all registered sources.

    Includes run outcomes and durations, item counts, archived documents,
    preserved raw responses, review-queue backlog, average extraction
    confidence and field completeness of the trademark data.

    Args:
        db: Database session.
        current_user: The authenticated user.

    Returns:
        The metrics payload (see :func:`compute_quality_metrics`).
    """
    return await compute_quality_metrics(db)
