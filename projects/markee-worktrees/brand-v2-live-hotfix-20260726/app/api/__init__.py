"""API routers aggregated under a single versioned router."""
from __future__ import annotations

from fastapi import APIRouter

from app.api import (
    alerts,
    auth,
    billing,
    deadlines,
    health,
    portfolios,
    quality,
    trademarks,
    watchlists,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router)
api_router.include_router(trademarks.router)
api_router.include_router(watchlists.router)
api_router.include_router(alerts.router)
api_router.include_router(deadlines.router)
api_router.include_router(billing.router)
api_router.include_router(portfolios.router)
api_router.include_router(quality.router)

__all__ = ["api_router"]
