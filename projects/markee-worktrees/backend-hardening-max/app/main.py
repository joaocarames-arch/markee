"""markee FastAPI application entrypoint.

Wires together the API routers, CORS, static frontend serving and the database
lifespan. The FastAPI app serves both the JSON API (under ``/api/v1``) and the
vanilla static frontend.
"""
from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware

from app.api import api_router
from app.core.config import settings
from app.core.database import Base, engine
from app.core.proxy import (
    extract_external_scheme,
    host_matches_trusted,
    is_trusted_peer,
    parse_trusted_hosts,
    parse_trusted_proxies,
)
from app.models.schemas import ALL_SCHEMAS

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LANDING_DIR = PROJECT_ROOT / settings.FRONTEND_DIR
DASHBOARD_DIR = PROJECT_ROOT / "frontend" / "dashboard"
ASSETS_DIR = PROJECT_ROOT / "assets"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup and shutdown.

    In development (``DB_CREATE_ALL_ON_STARTUP=True``) the ORM metadata is
    created on startup as a convenience. Outside development the schema is
    owned exclusively by Alembic migrations and startup never mutates it.

    Args:
        app: The FastAPI application instance.

    Yields:
        Control back to the running application.
    """
    if settings.DB_CREATE_ALL_ON_STARTUP:
        try:
            async with engine.begin() as conn:
                if conn.dialect.name == "postgresql":
                    for schema in ALL_SCHEMAS:
                        await conn.execute(
                            text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
                        )
                await conn.run_sync(Base.metadata.create_all)
        except Exception:  # noqa: BLE001 - never block startup on a DB hiccup
            logger.exception("Could not create tables on startup")
    yield
    await engine.dispose()


def _is_dev() -> bool:
    """Return whether the current settings point at development.

    Centralised so the production-staging differentiation (docs, HSTS,
    create_all) always re-reads the resolved settings rather than a value
    captured at import time.
    """
    return settings.ENVIRONMENT == "development"


app = FastAPI(
    title="markee",
    description="API de monitorização de marcas (INPI e EUIPO)",
    version="0.1.0",
    lifespan=lifespan,
    # API schema/docs are development-only surfaces.
    docs_url="/docs" if _is_dev() else None,
    redoc_url="/redoc" if _is_dev() else None,
    openapi_url="/openapi.json" if _is_dev() else None,
)


@app.middleware("http")
async def security_headers(request: Request, call_next):  # type: ignore[no-untyped-def]
    """Attach baseline security headers to every response.

    HSTS is conditional on the externally-visible scheme being HTTPS, and
    only outside development. The trust boundary that promotes the
    request's scheme to ``https`` is the real socket peer being a trusted
    proxy (the local cloudflared process); an untrusted peer that fakes
    ``X-Forwarded-Proto`` cannot earn an HSTS promise.

    The ``includeSubDomains`` directive is intentionally omitted: the
    production deployment only covers ``markee.batata.cc`` and
    ``app.markee.batata.cc``, and we have not made the product decision to
    opt every subdomain into HTTPS. ``max-age`` matches the HSTS spec
    recommendation for first deployment (RFC 6797 §7.2).
    """
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")

    if not _is_dev():
        peer_is_trusted = is_trusted_peer(
            request.client.host if request.client else None,
            parse_trusted_proxies(settings.TRUSTED_PROXIES),
        )
        external_scheme = extract_external_scheme(
            request_scheme=request.url.scheme,
            forwarded_proto=request.headers.get("x-forwarded-proto"),
            peer_is_trusted=peer_is_trusted,
        )
        if external_scheme == "https":
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000"
            )
    return response


class _ProxyAwareHostCheck(BaseHTTPMiddleware):
    """Reject requests whose ``Host`` header is not on the trust list.

    Replaces :class:`starlette.middleware.trustedhost.TrustedHostMiddleware`
    with a version that uses the same exact-match rules the
    ``parse_trusted_hosts`` helper produces — ``(host, port|None)`` tuples
    compared against the request's Host header. Wildcards are stripped
    before this middleware is constructed; production never accepts ``"*"``.
    """

    def __init__(
        self, app, *, allowed_hosts: tuple[tuple[str, int | None], ...]
    ) -> None:
        super().__init__(app)
        cleaned = tuple((host, port) for host, port in allowed_hosts if host != "*")
        if not cleaned:
            raise RuntimeError(
                "TrustedHost middleware requires a non-empty non-wildcard list"
            )
        self._allowed_hosts = cleaned

    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        host = request.headers.get("host")
        if not host_matches_trusted(host, self._allowed_hosts):
            return PlainTextResponse("Invalid host header", status_code=400)
        return await call_next(request)


# The trust boundary is enforced by the outer wrapper. Starlette applies
# ``add_middleware`` in reverse order at runtime, so the LAST-added
# middleware is the outermost wrapper. Order therefore ends up:
#   request -> _ProxyAwareHostCheck -> CORS -> security_headers -> router
# which keeps Host validation outside the response-shaping middlewares so
# an unknown Host returns 400 before any header leakage happens.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    _ProxyAwareHostCheck,
    allowed_hosts=parse_trusted_hosts(settings.TRUSTED_HOSTS),
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Return a top-level liveness response.

    Returns:
        A status payload indicating the service is up.
    """
    return {"status": "ok"}


# Explicit relative redirect for /app. The StaticFiles mount serves
# ``/app/`` but its built-in redirect to the trailing slash emits an
# absolute URL built from the request's scheme/host. The dashboard hash
# router, the OAuth callbacks and the SEO surface all depend on the
# relative path; an absolute Location leaks an internal endpoint and
# breaks the redirect when the public Host differs from the proxy Host.
@app.get("/app", include_in_schema=False)
async def app_root_redirect() -> RedirectResponse:
    """Redirect bare ``/app`` to ``/app/`` with a relative Location."""
    return RedirectResponse(url="/app/", status_code=307)


# Static frontend + brand assets (best-effort: absence must not break the API).
# Brand assets (logos, favicons) shared by the landing page and dashboard.
if ASSETS_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")

# Dashboard SPA served under /app. ``html=True`` serves ``index.html`` for the
# directory request, so the client-side (hash) router owns every in-app route
# while its ``styles.css`` / ``app.js`` resolve as siblings under ``/app/``.
if DASHBOARD_DIR.is_dir():
    app.mount(
        "/app",
        StaticFiles(directory=str(DASHBOARD_DIR), html=True),
        name="dashboard",
    )

# Landing page: its own assets live under ``/static`` and the document is served
# at the site root.
if LANDING_DIR.is_dir():
    app.mount(
        "/static", StaticFiles(directory=str(LANDING_DIR)), name="landing-static"
    )

    @app.get("/", include_in_schema=False)
    async def landing_page() -> FileResponse:
        """Serve the landing page HTML."""
        return FileResponse(str(LANDING_DIR / "index.html"))
