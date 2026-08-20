"""Application configuration loaded from environment variables.

Uses Pydantic v2 ``BaseSettings``. Every value has a development-friendly
default so the application boots without a fully populated ``.env`` file,
while production deployments override the relevant keys.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.proxy import parse_trusted_hosts, parse_trusted_proxies


def _coerce_str_list(value: Any) -> list[str]:
    """Accept ``list[str]`` from code and a comma-separated string from env.

    Pydantic-settings does not natively split comma-separated env values into
    a ``list[str]``; the JSON path it uses rejects plain CSV. We accept both
    so the configuration can be expressed in a ``.env`` file (one
    comma-separated line per variable) or in code (a real list).
    """
    if value is None:
        return []
    if isinstance(value, str):
        # Strip JSON-list decorations: ``["a", "b"]`` is what pydantic-settings
        # would produce for a structured list. Strip and split on commas.
        stripped = value.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            inner = stripped[1:-1].strip()
            if not inner:
                return []
            # Naive split — quoted strings with embedded commas are not in
            # scope for these variables.
            return [chunk.strip().strip('"\'') for chunk in inner.split(",") if chunk.strip()]
        return [chunk.strip() for chunk in value.split(",") if chunk.strip()]
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value]
    raise ValueError(f"Cannot coerce {type(value).__name__} to list[str]")


class Settings(BaseSettings):
    """Runtime configuration for the markee backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # ── Environment ─────────────────────────────────────────────────────────
    # "development" | "staging" | "production". Gates dev-only behaviour
    # (mock fallback, create_all, /docs exposure, permissive CORS).
    ENVIRONMENT: str = "development"

    # Dev convenience: when True the app runs Base.metadata.create_all on
    # startup. Must stay False outside development — schema provenance belongs
    # to Alembic migrations only.
    DB_CREATE_ALL_ON_STARTUP: bool = False

    # When True, empty search results fall back to the EUIPO mock dataset
    # (clearly labelled). Never enable outside development.
    ENABLE_MOCK_FALLBACK: bool = False

    # ── Core infrastructure ────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://markee:markee_dev@db:5432/markee"
    REDIS_URL: str = "redis://redis:6379/0"
    DB_PASSWORD: str = "markee_dev"

    # ── Security / JWT ──────────────────────────────────────────────────────
    SECRET_KEY: str = "dev-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # one week

    # ── CORS ────────────────────────────────────────────────────────────────
    # Same-origin frontend means no cross-origin browsing is needed by
    # default; add explicit origins per environment instead of "*".
    CORS_ORIGINS: list[str] = ["http://localhost:8000", "http://127.0.0.1:8000"]

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

    # ── Trust boundary ───────────────────────────────────────────────────────
    # The deployment topology (docs/execution/STG-00_CONTAINMENT_AUDIT.md)
    # routes public traffic through cloudflared on the loopback socket.
    # The Host header the app receives on the loopback is 127.0.0.1:8000.
    # The cloudflared process on the loopback is the only peer we trust to
    # rewrite scheme/host via X-Forwarded-*.
    #
    # The ``env_parse_none_str`` field declares an environment override as a
    # comma-separated string. Pydantic-settings does not parse comma-lists
    # out of the box; we accept both shapes (list literal in code, single
    # comma-string in env) by routing the value through ``parse_trusted_*``
    # in the validator.
    #
    # Required in staging/production: ``_validate`` refuses to boot if these
    # are empty or contain a wildcard host. Defaults listed here are for the
    # documented deployment (cloudflared → 127.0.0.1:8000, public hostnames
    # ``markee.batata.cc`` and ``app.markee.batata.cc``); different
    # deployments must override these via the environment.
    TRUSTED_HOSTS: list[str] = [
        "127.0.0.1:8000",
        "markee.batata.cc",
        "app.markee.batata.cc",
    ]
    TRUSTED_PROXIES: list[str] = ["127.0.0.1/32"]


_DEV_SECRET_SENTINEL = "dev-secret-change-me"


def _validate(settings: Settings) -> Settings:
    """Refuse to boot with development-grade security outside development.

    The validator accumulates every problem, never the first one, so a
    caller that adds a new override will not silently miss a regression in
    a sibling guard. Staging and production enforce the same set of
    constraints; only development tolerates the dev defaults.

    Args:
        settings: The candidate settings instance.

    Returns:
        The same instance, unchanged, on success.

    Raises:
        RuntimeError: When staging or production is configured with the
            dev secret, wildcard CORS, mock fallback, startup ``create_all``,
            or with no trust boundary (empty / wildcard ``TRUSTED_HOSTS``,
            empty ``TRUSTED_PROXIES``).
    """
    if settings.ENVIRONMENT == "development":
        # Development accepts every default; we still validate the format
        # of the trust boundary so a typo surfaces early.
        try:
            parse_trusted_hosts(settings.TRUSTED_HOSTS, allow_wildcard=True)
            parse_trusted_proxies(settings.TRUSTED_PROXIES)
        except ValueError as exc:
            raise RuntimeError(
                f"Invalid trust boundary for development: {exc}"
            ) from exc
        return settings

    problems: list[str] = []
    if settings.SECRET_KEY == _DEV_SECRET_SENTINEL:
        problems.append("SECRET_KEY is the development default")
    if "*" in settings.CORS_ORIGINS:
        problems.append("CORS_ORIGINS contains '*'")
    if settings.ENABLE_MOCK_FALLBACK:
        problems.append("ENABLE_MOCK_FALLBACK must be False")
    if settings.DB_CREATE_ALL_ON_STARTUP:
        problems.append("DB_CREATE_ALL_ON_STARTUP must be False")
    try:
        trusted_hosts = parse_trusted_hosts(
            settings.TRUSTED_HOSTS, allow_wildcard=False
        )
    except ValueError as exc:
        problems.append(f"TRUSTED_HOSTS invalid: {exc}")
        trusted_hosts = ()
    if any(host == "*" for host, _ in trusted_hosts):
        problems.append("TRUSTED_HOSTS contains '*'")
    try:
        parse_trusted_proxies(settings.TRUSTED_PROXIES)
    except ValueError as exc:
        problems.append(f"TRUSTED_PROXIES invalid: {exc}")
    if not problems:
        return settings
    raise RuntimeError(
        f"Unsafe configuration for ENVIRONMENT={settings.ENVIRONMENT}: "
        + "; ".join(problems)
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached, validated ``Settings`` instance.

    Returns:
        The singleton settings object for the running process.
    """
    return _validate(Settings())


settings = get_settings()
