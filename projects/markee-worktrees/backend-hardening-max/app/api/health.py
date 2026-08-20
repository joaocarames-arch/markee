"""Health-check router."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import RedirectResponse

router = APIRouter(redirect_slashes=False)


@router.get("/health", name="health")
async def health() -> dict[str, str]:
    """Return a simple liveness response.

    Returns:
        A status payload indicating the service is up.
    """
    return {"status": "ok", "service": "markee"}


@router.get("/health/", include_in_schema=False, name="health_with_slash")
async def health_with_slash() -> RedirectResponse:
    """Issue a relative 307 to the canonical ``/api/v1/health`` path.

    Starlette's default trailing-slash redirect builds an absolute URL
    from the request's scheme/host; this explicit version emits a relative
    Location so the browser resolves the redirect against the URL it
    actually issued. The relative redirect is the contract documented in
    ``docs/execution/STG-00_CONTAINMENT_AUDIT.md`` (the cloudflared
    loopback socket never appears in user-facing URLs).
    """
    return RedirectResponse(url="/api/v1/health", status_code=307)
