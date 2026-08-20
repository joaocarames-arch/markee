"""markee FastAPI application entrypoint.

Wires together the API routers, CORS, static frontend serving and the database
lifespan. The FastAPI app serves both the JSON API (under ``/api/v1``) and the
vanilla static frontend.

Middleware stack (outermost first; Starlette applies them in reverse
``add_middleware`` order, so they are added below in innermost-first order):

    security_headers (HTTP middleware) → CORSMiddleware →
        TrustedHostEnforcerMiddleware → ProxyHeadersMiddleware →
            router / static mounts

- ``security_headers`` emits HSTS only when the (now-validated) request
  scheme is HTTPS, and never carries ``includeSubDomains`` unless explicitly
  opted in. It also attaches the baseline ``X-Content-Type-Options`` /
  ``X-Frame-Options`` / ``Referrer-Policy`` headers so a TrustedHost 400
  response does not leak a less-protected page.
- ``CORSMiddleware`` is configured from ``CORS_ORIGINS`` which the config
  validator refuses to leave empty or wildcard outside development.
- ``TrustedHostEnforcerMiddleware`` rejects unknown ``Host`` headers with
  ``400`` outside the configured ``TRUSTED_HOSTS`` allow-list.
- ``ProxyHeadersMiddleware`` honours ``X-Forwarded-*`` and the RFC 7239
  ``Forwarded`` header only when the immediate peer is in
  ``TRUSTED_FORWARDED_PROXIES`` (cloudflared, reverse proxy) and strips
  those headers from every other request so scheme/host cannot be spoofed
  by a direct caller.

The middleware factories receive ``lambda: settings.*`` callables instead of
the underlying values: this lets the integration tests monkey-patch
``app.core.config.settings`` and observe the patched values without rebuilding
the FastAPI app — the modules import side-effect (``from app.main import app``)
happens before any fixture runs, but the middleware re-reads the live settings
on every request.
"""
from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.api import api_router
from app.core import config
from app.core.database import Base, engine
from app.core.proxy import (
    ProxyHeadersMiddleware,
    RedirectHostSanitizerMiddleware,
    TrustedHostEnforcerMiddleware,
    parse_trusted_hosts,
    parse_trusted_proxies,
)
from app.models.schemas import ALL_SCHEMAS

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LANDING_DIR = PROJECT_ROOT / config.settings.FRONTEND_DIR
DASHBOARD_DIR = PROJECT_ROOT / "frontend" / "dashboard"
ASSETS_DIR = PROJECT_ROOT / "assets"


def _current_environment() -> str:
    """Return the live ``ENVIRONMENT`` value.

    Wrapped in a function so the middleware factory can read it lazily on
    every request without rebuilding the app — tests rely on monkey-patching
    ``settings.ENVIRONMENT`` to flip development-mode behaviour.
    """
    return config.settings.ENVIRONMENT


def _is_dev() -> bool:
    """Return ``True`` only when the running environment is development."""
    return _current_environment() == "development"


def _docs_paths() -> tuple[str | None, str | None, str | None]:
    """Return ``(docs_url, redoc_url, openapi_url)`` for the current env.

    The URLs are recomputed lazily because the FastAPI constructor captures
    them at import time and the tests rely on monkey-patching
    ``settings.ENVIRONMENT`` *after* import. ``FastAPI`` only uses these
    URLs as route hints, so it is safe to resolve them lazily: a route
    under ``/docs`` is only registered when ``docs_url`` is truthy at
    construction time.
    """
    if _is_dev():
        return "/docs", "/redoc", "/openapi.json"
    return None, None, None


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
    if config.settings.DB_CREATE_ALL_ON_STARTUP:
        try:
            async with engine.begin() as conn:
                if conn.dialect.name == "postgresql":
                    for schema in ALL_SCHEMAS:
                        await conn.execute(
                            text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
                        )
                await conn.run_sync(Base.metadata.create_all)
        except Exception:
            logger.exception("Could not create tables on startup")
    yield
    await engine.dispose()


_docs_url, _redoc_url, _openapi_url = _docs_paths()

app = FastAPI(
    title="markee",
    description="API de monitorização de marcas (INPI e EUIPO)",
    version="0.1.0",
    lifespan=lifespan,
    # API schema/docs are development-only surfaces. The URLs are resolved at
    # startup time but ``_is_dev`` is recomputed on every HSTS / CORS decision
    # so monkey-patching ``settings.ENVIRONMENT`` in tests takes effect for
    # headers and CORS without rebuilding the app.
    docs_url=_docs_url,
    redoc_url=_redoc_url,
    openapi_url=_openapi_url,
)


@app.middleware("http")
async def security_headers(request: Any, call_next: Any) -> Any:
    """Attach baseline security headers to every response.

    HSTS is emitted only when the request scheme is ``https`` *after* the
    ``ProxyHeadersMiddleware`` has had a chance to promote it from
    ``X-Forwarded-Proto``. A plain http request never sees HSTS. This
    middleware also wraps the response status code by going through the
    Starlette middleware stack (it is registered first, so Starlette applies
    it last and therefore outermost), which means it also covers the
    400 responses produced by the inner ``TrustedHostEnforcerMiddleware``.
    Production also denies the interactive API documentation paths here,
    rather than relying only on the routes selected when ``FastAPI`` was
    constructed. This keeps the gate fail-closed when tests or runtime
    configuration replace ``config.settings`` after module import.
    """
    if not _is_dev() and request.url.path in {"/docs", "/redoc", "/openapi.json"}:
        response = PlainTextResponse("Not Found", status_code=404)
    else:
        response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    if not _is_dev() and request.scope.get("scheme") == "https":
        hsts_value = "max-age=31536000"
        if config.settings.HSTS_INCLUDE_SUBDOMAINS:
            hsts_value += "; includeSubDomains"
        response.headers.setdefault("Strict-Transport-Security", hsts_value)
    return response


# ── Middleware wiring ──────────────────────────────────────────────────────
#
# Starlette applies ``add_middleware`` in reverse order: the LAST middleware
# added runs FIRST. To get the documented execution order
#   security_headers → CORS → TrustedHost → ProxyHeaders → RedirectHostSanitizer → router
# we add them in the opposite order below. ``security_headers`` is the
# ``@app.middleware("http")`` decorator above, which Starlette wraps around
# the outermost user-middleware layer automatically.


def _trusted_hosts_factory() -> list[str]:
    raw = config.settings.TRUSTED_HOSTS
    if not isinstance(raw, str):
        raw = ",".join(str(item) for item in raw)
    return parse_trusted_hosts(raw)


def _trusted_proxies_factory() -> list[str]:
    raw = config.settings.TRUSTED_FORWARDED_PROXIES
    if not isinstance(raw, str):
        raw = ",".join(str(item) for item in raw)
    try:
        return parse_trusted_proxies(raw)
    except ValueError:
        # Config error: validator should have rejected this at startup.
        # Return an empty allow-list so the middleware fails closed.
        return []


def _cors_origins_factory() -> list[str]:
    origins = config.settings.CORS_ORIGINS
    if isinstance(origins, str):
        return [o.strip() for o in origins.split(",") if o.strip()]
    return list(origins)


# Hosts that may never appear in a public ``Location`` header. ``127.0.0.1``
# is what the cloudflared tunnel terminates at locally; redirecting a public
# client to it would leak the internal origin and bypass CDN caching. The
# set is extended at runtime with whatever the ASGI server reports as
# ``scope["server"][0]`` so a dev tunnel on a non-default host is also
# covered.
def _internal_hosts_factory() -> list[str]:
    return [
        "127.0.0.1",
        "localhost",
        "::1",
        "0.0.0.0",
    ]


# 1) CORSMiddleware added first → runs outermost after security_headers.
# A preflight from an allowed origin must still be answered even when the
# Host check would otherwise reject the request.
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins_factory(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2) TrustedHostEnforcerMiddleware runs *inside* CORS so the CORS preflight
# gets a chance to answer before the Host check rejects the request, and
# *outside* the proxy gate so the proxy gate has already rewritten the Host
# from the forwarded headers.
app.add_middleware(
    TrustedHostEnforcerMiddleware,
    allowed_hosts=_trusted_hosts_factory,
    is_dev=_is_dev,
)

# 3) ProxyHeadersMiddleware runs *inside* TrustedHost so it mutates
# ``scope`` first; the TrustedHost enforcer then sees the forwarded host
# and either accepts or rejects accordingly.
app.add_middleware(
    ProxyHeadersMiddleware,
    trusted_proxies=_trusted_proxies_factory,
)

# 4) RedirectHostSanitizerMiddleware runs *closest* to the router so it
# rewrites the ``Location`` header that Starlette / StaticFiles /
# ``redirect_slashes`` produce before any other middleware has a chance
# to layer extra headers on top.
app.add_middleware(
    RedirectHostSanitizerMiddleware,
    internal_hosts=_internal_hosts_factory,
    public_origins=_trusted_hosts_factory,
    is_trusted_proxy=lambda: True,
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Return a top-level liveness response.

    Returns:
        A status payload indicating the service is up.
    """
    return {"status": "ok"}


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