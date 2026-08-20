"""Application configuration loaded from environment variables.

Uses Pydantic v2 ``BaseSettings``. Every value has a development-friendly
default so the application boots without a fully populated ``.env`` file,
while production deployments override the relevant keys.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the markee backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # ── Core infrastructure ────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://markee:markee_dev@db:5432/markee"
    REDIS_URL: str = "redis://redis:6379/0"
    DB_PASSWORD: str = "markee_dev"

    # ── Security / JWT ──────────────────────────────────────────────────────
    SECRET_KEY: str = "dev-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # one week

    # ── CORS ────────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["*"]

    # ── EUIPO / TMview API ──────────────────────────────────────────────────
    EUIPO_API_CLIENT_ID: str = ""
    EUIPO_API_CLIENT_SECRET: str = ""

    # ── Stripe billing ──────────────────────────────────────────────────────
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_INDIVIDUAL: str = "price_1Individual"
    STRIPE_PRICE_PRO: str = "price_1Pro"
    STRIPE_PRICE_PROFISSIONAL: str = "price_1Profissional"
    STRIPE_PRICE_ENTERPRISE: str = "price_1Enterprise"

    # ── Email (SMTP) ────────────────────────────────────────────────────────
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "markee <no-reply@markee.pt>"

    # ── Telegram ────────────────────────────────────────────────────────────
    TELEGRAM_BOT_TOKEN: str = ""

    # ── Application ─────────────────────────────────────────────────────────
    APP_BASE_URL: str = "http://localhost:8000"
    API_BASE_URL: str = "http://app:8000"
    FRONTEND_DIR: str = "frontend/landing"

    # ── Data infrastructure ─────────────────────────────────────────────────
    DOCUMENT_STORAGE_DIR: str = "data/documents"

    # ── BPI containment (kill switch, default-off) ──────────────────────────
    # BPI is NO-GO: the INPI BPI pipeline must not schedule, ingest, create
    # deadlines, create alerts or dispatch notifications unless every flag
    # below is explicitly enabled AND the deny list is cleared. Defaults are
    # fail-closed; flipping them locally does not deploy anything.
    BPI_ENABLED: bool = False
    BPI_SCHEDULE_ENABLED: bool = False
    BPI_INGESTION_ALLOWED: bool = False
    # Source labels denied across ingestion/deadlines/alerts/dispatch.
    # "inpi_bpi" is the core.sources registry name; "BPI" is the label the
    # parser stamps on lifecycle events.
    BPI_DENY_SOURCES: list[str] = ["inpi_bpi", "BPI"]


@lru_cache
def get_settings() -> Settings:
    """Return a cached ``Settings`` instance.

    Returns:
        The singleton settings object for the running process.
    """
    return Settings()


settings = get_settings()
