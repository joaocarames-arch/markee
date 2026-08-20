"""Application configuration loaded from environment variables.

Uses Pydantic v2 ``BaseSettings``. Every value has a development-friendly
default so the application boots without a fully populated ``.env`` file,
while production deployments override the relevant keys.

Configuration invariants enforced by ``_validate``:

- ``SECRET_KEY`` outside development must not be the development default.
- ``CORS_ORIGINS`` outside development must not be wildcard (``*``) nor empty.
- ``TRUSTED_HOSTS`` outside development must be non-empty and contain no
  wildcard entry; either case leaves the TrustedHost enforcer wide open.
- ``TRUSTED_FORWARDED_PROXIES`` outside development must be non-empty so
  forwarded headers from cloudflared / another edge are honoured but headers
  from a direct caller can never be trusted.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.proxy import parse_trusted_proxies


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

    # ── TrustedHost / forward-proxy gating ──────────────────────────────────
    # Comma-separated list of ``Host`` header values the TrustedHost enforcer
    # accepts. Entries may be bare (``markee.batata.cc``) or with an explicit
    # port (``127.0.0.1:8000``); bare entries do NOT match arbitrary ports.
    # Defaults to permissive in development so local tunnels keep working.
    # The model accepts a string (typical env-var) or a list (typical test
    # call); ``_coerce_to_csv`` collapses both into the canonical string form.
    TRUSTED_HOSTS: str | list[str] = "*"

    # Comma-separated list of exact IPv4/IPv6 literals or CIDR ranges that
    # are allowed to send X-Forwarded-* / RFC 7239 ``Forwarded`` headers.
    # Cloudflare Tunnel terminates at ``127.0.0.1:8000`` locally, so this
    # list must include the loopback IP (or its range) in production.
    # Defaults to empty: no peer is allowed to influence scheme/host/client
    # IP until the operator configures it.
    TRUSTED_FORWARDED_PROXIES: str | list[str] = ""

    # HSTS ``includeSubDomains`` flag is opt-in. The default policy is
    # ``max-age=...`` only, without ``includeSubDomains``. Set to ``True``
    # only after a deliberate decision about every subdomain.
    HSTS_INCLUDE_SUBDOMAINS: bool = False

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

    @field_validator("TRUSTED_HOSTS", "TRUSTED_FORWARDED_PROXIES", mode="before")
    @classmethod
    def _normalise_csv_field(cls, value: object) -> str:
        """Collapse ``str`` or ``list[str]`` into a CSV string for the helper.

        The runtime uses ``parse_trusted_hosts`` which expects a CSV string;
        tests typically pass a list for readability. Both are accepted.
        """
        return _coerce_to_csv(value)


_DEV_SECRET_SENTINEL = "dev-secret-change-me"


def _coerce_to_csv(value: object) -> str:
    """Normalise ``TRUSTED_HOSTS`` / ``TRUSTED_FORWARDED_PROXIES`` to a CSV string.

    Accepts either a string (the env-var form, comma-separated) or a list of
    strings (the Python-call form). Anything else is rejected so misconfig
    surfaces loudly instead of silently disabling the safety check.
    """
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return ",".join(str(item) for item in value)
    raise TypeError(f"expected str or list[str], got {type(value).__name__}")


def _validate(settings: Settings) -> Settings:
    """Refuse to boot with development-grade security outside development.

    Raises:
        RuntimeError: When staging/production is configured with the dev
            secret, wildcard CORS, mock fallback, startup ``create_all``,
            empty/wildcard ``TRUSTED_HOSTS`` or empty
            ``TRUSTED_FORWARDED_PROXIES``.
    """
    if settings.ENVIRONMENT != "development":
        problems: list[str] = []
        if settings.SECRET_KEY == _DEV_SECRET_SENTINEL:
            problems.append("SECRET_KEY is the development default")
        if not settings.CORS_ORIGINS:
            problems.append("CORS_ORIGINS is empty")
        if "*" in settings.CORS_ORIGINS:
            problems.append("CORS_ORIGINS contains '*'")
        if settings.ENABLE_MOCK_FALLBACK:
            problems.append("ENABLE_MOCK_FALLBACK must be False")
        if settings.DB_CREATE_ALL_ON_STARTUP:
            problems.append("DB_CREATE_ALL_ON_STARTUP must be False")
        trusted_hosts_raw = _coerce_to_csv(settings.TRUSTED_HOSTS)
        trusted_hosts = [host.strip() for host in trusted_hosts_raw.split(",")]
        if not trusted_hosts_raw.strip() or "*" in trusted_hosts:
            problems.append(
                "TRUSTED_HOSTS must be an explicit allow-list outside development"
            )
        if not settings.TRUSTED_FORWARDED_PROXIES.strip():
            problems.append(
                "TRUSTED_FORWARDED_PROXIES must list at least one peer/CIDR "
                "outside development (cloudflared loopback, etc.)"
            )
        else:
            # Fail-closed: every entry in the allow-list MUST parse as an
            # exact IPv4/IPv6 literal or a non-wildcard CIDR. We refuse to
            # silently drop malformed entries because doing so would leave
            # the production deploy unable to honour X-Forwarded-* from its
            # actual edge while still appearing configured.
            proxies_raw = settings.TRUSTED_FORWARDED_PROXIES
            if not isinstance(proxies_raw, str):
                # The Pydantic ``field_validator`` collapses the list form
                # to a CSV string before ``_validate`` runs; if for any
                # reason we end up with a list here we coerce it explicitly
                # so the parse step below sees a stable contract.
                proxies_raw = ",".join(str(item) for item in proxies_raw)
            try:
                parse_trusted_proxies(proxies_raw)
            except ValueError as exc:
                problems.append(
                    f"TRUSTED_FORWARDED_PROXIES contains an invalid entry: {exc}"
                )
        if problems:
            raise RuntimeError(
                f"Unsafe configuration for ENVIRONMENT={settings.ENVIRONMENT}: "
                + "; ".join(problems)
            )
    return settings


@lru_cache
def get_settings() -> Settings:
    """Return a cached, validated ``Settings`` instance.

    Returns:
        The singleton settings object for the running process.
    """
    return _validate(Settings())


settings = get_settings()