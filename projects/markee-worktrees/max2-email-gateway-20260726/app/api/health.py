"""Health-check router."""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    """Return a simple liveness response.

    Returns:
        A status payload indicating the service is up.
    """
    return {"status": "ok", "service": "markee"}
