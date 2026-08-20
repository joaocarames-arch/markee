"""Fail-closed configuration tests for staging/production.

Validates the production guard rejects the documented misconfigurations even
after every supported override field is mutated. The test deliberately
``Settings(...)`` instances with raw defaults plus a single attacker override
each, so a regression that adds a new dev-grade default but forgets to wire
it through ``_validate`` is caught immediately.
"""
from __future__ import annotations

import pytest

from app.core.config import Settings, _validate


# ── Helpers ──────────────────────────────────────────────────────────────────


def _production(**overrides):
    """Return a Settings() shaped for production with caller-supplied overrides."""
    base = {
        "ENVIRONMENT": "production",
        "SECRET_KEY": "x" * 64,
        "CORS_ORIGINS": ["https://markee.batata.cc"],
        "TRUSTED_HOSTS": ["markee.batata.cc", "app.markee.batata.cc"],
        "TRUSTED_PROXIES": ["127.0.0.1/32"],
    }
    base.update(overrides)
    return Settings(**base)


# ── RED: production refuses dev defaults ─────────────────────────────────────


def test_production_refuses_dev_secret_sentinel() -> None:
    s = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="dev-secret-change-me",
        CORS_ORIGINS=["https://markee.batata.cc"],
        TRUSTED_HOSTS=["markee.batata.cc"],
        TRUSTED_PROXIES=["127.0.0.1/32"],
    )
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        _validate(s)


def test_production_refuses_wildcard_cors() -> None:
    s = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="x" * 64,
        CORS_ORIGINS=["*"],
        TRUSTED_HOSTS=["markee.batata.cc"],
        TRUSTED_PROXIES=["127.0.0.1/32"],
    )
    with pytest.raises(RuntimeError, match="CORS_ORIGINS"):
        _validate(s)


def test_production_refuses_mock_fallback() -> None:
    s = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="x" * 64,
        CORS_ORIGINS=["https://markee.batata.cc"],
        TRUSTED_HOSTS=["markee.batata.cc"],
        TRUSTED_PROXIES=["127.0.0.1/32"],
        ENABLE_MOCK_FALLBACK=True,
    )
    with pytest.raises(RuntimeError, match="MOCK_FALLBACK"):
        _validate(s)


def test_production_refuses_create_all_on_startup() -> None:
    s = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="x" * 64,
        CORS_ORIGINS=["https://markee.batata.cc"],
        TRUSTED_HOSTS=["markee.batata.cc"],
        TRUSTED_PROXIES=["127.0.0.1/32"],
        DB_CREATE_ALL_ON_STARTUP=True,
    )
    with pytest.raises(RuntimeError, match="CREATE_ALL"):
        _validate(s)


# ── RED: production MUST declare TRUSTED_HOSTS and TRUSTED_PROXIES ───────────


def test_production_refuses_empty_trusted_hosts() -> None:
    s = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="x" * 64,
        CORS_ORIGINS=["https://markee.batata.cc"],
        TRUSTED_HOSTS=[],
        TRUSTED_PROXIES=["127.0.0.1/32"],
    )
    with pytest.raises(RuntimeError, match="TRUSTED_HOSTS"):
        _validate(s)


def test_production_refuses_empty_trusted_proxies() -> None:
    s = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="x" * 64,
        CORS_ORIGINS=["https://markee.batata.cc"],
        TRUSTED_HOSTS=["markee.batata.cc"],
        TRUSTED_PROXIES=[],
    )
    with pytest.raises(RuntimeError, match="TRUSTED_PROXIES"):
        _validate(s)


def test_production_refuses_wildcard_trusted_hosts() -> None:
    s = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="x" * 64,
        CORS_ORIGINS=["https://markee.batata.cc"],
        TRUSTED_HOSTS=["*"],
        TRUSTED_PROXIES=["127.0.0.1/32"],
    )
    with pytest.raises(RuntimeError, match="TRUSTED_HOSTS"):
        _validate(s)


# ── RED: cannot fake production by keeping dev secret & bumping CORS ─────────


def test_production_called_with_single_bad_field_still_rejects() -> None:
    """Regression: previously a single bad field could pass if another guard
    was weaker. The validator must accumulate every problem and refuse boot."""
    s = _production(
        SECRET_KEY="dev-secret-change-me",
        CORS_ORIGINS=["*"],
        ENABLE_MOCK_FALLBACK=True,
    )
    with pytest.raises(RuntimeError) as exc:
        _validate(s)
    msg = str(exc.value)
    assert "SECRET_KEY" in msg
    assert "CORS_ORIGINS" in msg
    assert "MOCK_FALLBACK" in msg


# ── GREEN: staging mirrors the production guard ──────────────────────────────


def test_staging_refuses_dev_secret() -> None:
    s = Settings(
        ENVIRONMENT="staging",
        SECRET_KEY="dev-secret-change-me",
        CORS_ORIGINS=["https://staging.markee.batata.cc"],
        TRUSTED_HOSTS=["staging.markee.batata.cc"],
        TRUSTED_PROXIES=["127.0.0.1/32"],
    )
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        _validate(s)


# ── GREEN: development accepts dev defaults — no false positives ─────────────


def test_development_accepts_default_settings() -> None:
    s = Settings(ENVIRONMENT="development")
    assert _validate(s) is s


def test_development_accepts_explicit_trusted_hosts() -> None:
    s = Settings(
        ENVIRONMENT="development",
        TRUSTED_HOSTS=["127.0.0.1", "localhost"],
        TRUSTED_PROXIES=["127.0.0.1/32"],
    )
    assert _validate(s) is s
