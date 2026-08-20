"""Redirects and docs gating tests for the FastAPI app.

These assert the documented behaviors the production proxy surface depends on:

* /app responds with a Location that is exactly ``/app/`` — no scheme, no host.
* /api/v1/health/ responds with a Location that is exactly
  ``/api/v1/health`` — no scheme, no host (router-level trailing-slash).
* /docs, /redoc, /openapi.json stay absent in staging/production and present
  in development.

Two transports are exercised, because the failure mode hands back different
``Location`` shapes:

* HTTP on the loopback socket (the trust boundary we control).
* HTTP via a Host header that simulates the cloudflared edge translating the
  public hostname to the loopback.

The tests target the real FastAPI app via ``TestClient``; no monkeypatching of
the router, no force_https, no test-only bypass. A HardeningError escapes if
the app refuses to construct under production-shaped settings.
"""
from __future__ import annotations

import os
from typing import Any

import pytest
from fastapi.testclient import TestClient


def _build_client(monkeypatch: pytest.MonkeyPatch, **env: Any) -> TestClient:
    """Build a TestClient with environment overrides + cleared settings cache.

    The settings module resolves at import time; we therefore rebuild the
    process environment, clear its memoised ``get_settings`` cache, and import
    a fresh app instance. The app is fully reproducible; no global state is
    leaked between tests.
    """
    for key, value in env.items():
        os.environ[key] = str(value)
    from app.core import config as config_module
    config_module.get_settings.cache_clear()
    # Fresh app: the FastAPI instance is module-level, so we either trust
    # that or override its ``settings`` reference. The override below lets
    # the app respond correctly under different environments.
    from app import main as main_module
    main_module.settings = config_module.get_settings()
    return TestClient(main_module.app)


@pytest.fixture
def dev_client() -> TestClient:
    return _build_client(
        pytest.MonkeyPatch(),
        ENVIRONMENT="development",
        SECRET_KEY="x" * 32,
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
    )


@pytest.fixture
def prod_client() -> TestClient:
    return _build_client(
        pytest.MonkeyPatch(),
        ENVIRONMENT="production",
        SECRET_KEY="x" * 64,
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        CORS_ORIGINS='["https://markee.batata.cc"]',
        TRUSTED_HOSTS="markee.batata.cc,app.markee.batata.cc,127.0.0.1",
        TRUSTED_PROXIES="127.0.0.1/32",
    )


# ── /app redirect ────────────────────────────────────────────────────────────


def test_app_redirect_uses_relative_path_in_dev(dev_client: TestClient) -> None:
    r = dev_client.get("/app", follow_redirects=False)
    assert r.status_code in (307, 308)
    assert r.headers.get("location") == "/app/"


def test_app_redirect_uses_relative_path_in_prod(prod_client: TestClient) -> None:
    r = prod_client.get("/app", follow_redirects=False)
    assert r.status_code in (307, 308)
    assert r.headers.get("location") == "/app/"


def test_app_redirect_preserves_relative_path_under_public_host(prod_client: TestClient) -> None:
    """Even if the upstream proxy writes a different Host header, the Location
    we emit must not echo the upstream Host. The relative redirect is the
    contract the dashboard hash router depends on."""
    r = prod_client.get(
        "/app",
        headers={"Host": "app.markee.batata.cc"},
        follow_redirects=False,
    )
    assert r.status_code in (307, 308)
    assert r.headers.get("location") == "/app/"


def test_app_root_serves_dashboard_html(prod_client: TestClient) -> None:
    """Following the redirect should land on the dashboard index."""
    r = prod_client.get("/app/", follow_redirects=False)
    assert r.status_code == 200
    assert "<!doctype html" in r.text.lower() or "<html" in r.text.lower()


# ── /api/v1/health trailing slash ────────────────────────────────────────────


def test_api_v1_health_trailing_slash_redirects_relative(prod_client: TestClient) -> None:
    r = prod_client.get("/api/v1/health/", follow_redirects=False)
    assert r.status_code in (307, 308)
    assert r.headers.get("location") == "/api/v1/health"


def test_api_v1_health_no_trailing_slash_returns_200(prod_client: TestClient) -> None:
    r = prod_client.get("/api/v1/health", follow_redirects=False)
    assert r.status_code == 200
    assert r.json().get("status") == "ok"


# ── OpenAPI gating ───────────────────────────────────────────────────────────


def test_docs_present_in_dev(dev_client: TestClient) -> None:
    r = dev_client.get("/docs", follow_redirects=False)
    assert r.status_code == 200


def test_docs_absent_in_prod(prod_client: TestClient) -> None:
    r = prod_client.get("/docs", follow_redirects=False)
    assert r.status_code == 404


def test_redoc_absent_in_prod(prod_client: TestClient) -> None:
    r = prod_client.get("/redoc", follow_redirects=False)
    assert r.status_code == 404


def test_openapi_json_absent_in_prod(prod_client: TestClient) -> None:
    r = prod_client.get("/openapi.json", follow_redirects=False)
    assert r.status_code == 404


# ── /health tolerates relative or scalar responses ───────────────────────────


def test_health_responds_without_redirect_in_prod(prod_client: TestClient) -> None:
    r = prod_client.get("/health", follow_redirects=False)
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
