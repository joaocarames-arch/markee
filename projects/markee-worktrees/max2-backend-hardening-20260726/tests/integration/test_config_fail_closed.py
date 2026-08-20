"""Config fail-closed regression tests.

These tests pin the production configuration invariants enforced by
``app.core.config._validate``. The ``Settings`` model exposes new fields
(``TRUSTED_HOSTS``, ``TRUSTED_FORWARDED_PROXIES``, ``HSTS_INCLUDE_SUBDOMAINS``)
that must be validated outside development.

Each test invokes ``_validate`` directly with a synthetic ``Settings`` so it
runs deterministically regardless of the host environment.
"""
from __future__ import annotations

import pytest

from app.core.config import Settings, _validate


def test_development_accepts_empty_proxy_list() -> None:
    """Development may keep ``TRUSTED_FORWARDED_PROXIES`` empty.

    The validator only enforces the empty list outside development. Tests
    and local tunnels rely on this convenience.
    """
    settings = Settings(TRUSTED_FORWARDED_PROXIES="")
    assert _validate(settings) is settings


def test_development_accepts_wildcard_hosts() -> None:
    settings = Settings(TRUSTED_HOSTS="*")
    assert _validate(settings) is settings


def test_production_refuses_empty_trusted_hosts() -> None:
    settings = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="x" * 64,
        CORS_ORIGINS=["https://markee.batata.cc"],
        TRUSTED_HOSTS="",
        TRUSTED_FORWARDED_PROXIES="127.0.0.1",
    )
    with pytest.raises(RuntimeError, match="TRUSTED_HOSTS"):
        _validate(settings)


def test_production_refuses_wildcard_trusted_hosts() -> None:
    settings = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="x" * 64,
        CORS_ORIGINS=["https://markee.batata.cc"],
        TRUSTED_HOSTS="*",
        TRUSTED_FORWARDED_PROXIES="127.0.0.1",
    )
    with pytest.raises(RuntimeError, match="TRUSTED_HOSTS"):
        _validate(settings)


@pytest.mark.parametrize("environment", ["production", "staging"])
@pytest.mark.parametrize(
    "trusted_hosts",
    [
        "*,markee.batata.cc",
        "markee.batata.cc,*,app.markee.batata.cc",
        "markee.batata.cc,*",
        "markee.batata.cc, *",
    ],
)
def test_non_development_refuses_wildcard_entry_in_trusted_hosts(
    environment: str, trusted_hosts: str
) -> None:
    settings = Settings(
        ENVIRONMENT=environment,
        SECRET_KEY="x" * 64,
        CORS_ORIGINS=["https://markee.batata.cc"],
        TRUSTED_HOSTS=trusted_hosts,
        TRUSTED_FORWARDED_PROXIES="127.0.0.1",
    )
    with pytest.raises(RuntimeError, match="TRUSTED_HOSTS"):
        _validate(settings)


def test_production_refuses_empty_trusted_forwarded_proxies() -> None:
    settings = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="x" * 64,
        CORS_ORIGINS=["https://markee.batata.cc"],
        TRUSTED_HOSTS="markee.batata.cc",
        TRUSTED_FORWARDED_PROXIES="",
    )
    with pytest.raises(RuntimeError, match="TRUSTED_FORWARDED_PROXIES"):
        _validate(settings)


def test_production_refuses_empty_cors_origins() -> None:
    settings = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="x" * 64,
        CORS_ORIGINS=[],
        TRUSTED_HOSTS="markee.batata.cc",
        TRUSTED_FORWARDED_PROXIES="127.0.0.1",
    )
    with pytest.raises(RuntimeError, match="CORS_ORIGINS"):
        _validate(settings)


def test_staging_refuses_dev_secret() -> None:
    settings = Settings(
        ENVIRONMENT="staging",
        SECRET_KEY="dev-secret-change-me",
        CORS_ORIGINS=["https://markee.batata.cc"],
        TRUSTED_HOSTS="markee.batata.cc",
        TRUSTED_FORWARDED_PROXIES="127.0.0.1",
    )
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        _validate(settings)


def test_production_accepts_minimal_safe_config() -> None:
    """A minimal production-shape config must pass validation."""
    settings = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="x" * 64,
        CORS_ORIGINS=["https://markee.batata.cc"],
        TRUSTED_HOSTS="markee.batata.cc,app.markee.batata.cc",
        TRUSTED_FORWARDED_PROXIES="127.0.0.1",
    )
    assert _validate(settings) is settings


def test_trusted_hosts_default_is_wildcard_in_development() -> None:
    """The default ``TRUSTED_HOSTS="*"`` keeps dev tunnels working.

    Operators running local ngrok/lvh.me tunnels rely on the wildcard to
    not break the host check before they configure the deployment.
    """
    settings = Settings()
    assert settings.TRUSTED_HOSTS == "*"


def test_hsts_include_subdomains_default_is_false() -> None:
    """``includeSubDomains`` is opt-in; the default policy must NOT enable it.

    Until the operator explicitly opts in, HSTS only protects the apex host.
    """
    settings = Settings()
    assert settings.HSTS_INCLUDE_SUBDOMAINS is False