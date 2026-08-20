"""markee FastAPI application entrypoint.

Wires together the API routers, CORS, static frontend serving and the database
lifespan. The FastAPI app serves both the JSON API (under ``/api/v1``) and the
vanilla static frontend.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.api import api_router
from app.core.config import settings
from app.core.database import Base, engine
from app.models.schemas import ALL_SCHEMAS

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LANDING_DIR = PROJECT_ROOT / settings.FRONTEND_DIR
DASHBOARD_DIR = PROJECT_ROOT / "frontend" / "dashboard"
ASSETS_DIR = PROJECT_ROOT / "assets"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup and shutdown.

    On startup the ORM metadata is created (development convenience; production
    should rely on Alembic migrations). On shutdown the engine is disposed.

    Args:
        app: The FastAPI application instance.

    Yields:
        Control back to the running application.
    """
    try:
        async with engine.begin() as conn:
            if conn.dialect.name == "postgresql":
                for schema in ALL_SCHEMAS:
                    await conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
            await conn.run_sync(Base.metadata.create_all)
    except Exception:  # noqa: BLE001 - never block startup on a DB hiccup
        logger.exception("Could not create tables on startup")
    yield
    await engine.dispose()


app = FastAPI(
    title="markee",
    description="API de monitorização de marcas (INPI e EUIPO)",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
