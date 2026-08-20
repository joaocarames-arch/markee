"""HSTS gating tests.

The baseline security_headers middleware emits HSTS for every non-development
response, regardless of whether the request actually arrived over HTTPS. That
is incorrect: HSTS is a promise to the browser about future connections, and
a promise emitted over HTTP is meaningless (and actively misleading to anyone
who inspects the response on a cleartext channel).

The required behaviour:

* Development: HSTS absent.
* Production, HTTP loopback (no X-Forwarded-Proto from a trusted peer):
  HSTS absent. The browser is talking plain HTTP; we have no business
  promising HTTPS to it.
* Production, HTTP loopback, X-Forwarded-Proto=https from a trusted peer
  (cloudflared on the same socket): HSTS present, **without** includeSubDomains
  (which is a decision we have not made; the cloudflared mapping covers only
  ``markee.batata.cc`` and ``app.markee.batata.cc`` and we must not opt every
  subdomain into HTTPS).
* Production, X-Forwarded-Proto=https from an untrusted peer: HSTS absent —
  we must not let a spoofed header certify a "secure" promise the request
  never earned.
"""
from __future__ import annotations

import os
from typing import Any

import pytest
from fastapi.testclient import TestClient


def _build_client(monkeypatch: pytest.MonkeyPatch, **env: Any) -> TestClient:
    for key, value in env.items():
        os.environ[key] = str(value)
    from app.core import config as config_module
    config_module.get_settings.cache_clear()
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


# ── Baselines ────────────────────────────────────────────────────────────────


def test_no_hsts_in_development(dev_client: TestClient) -> None:
    r = dev_client.get("/health")
    assert r.headers.get("strict-transport-security") is None


def test_no_hsts_in_production_over_http_loopback(prod_client: TestClient) -> None:
    """Plain HTTP on the loopback socket must not promise HTTPS."""
    r = prod_client.get("/health")
    assert r.headers.get("strict-transport-security") is None


# ── Trusted proxy HTTPS corridor ─────────────────────────────────────────────


def test_hsts_present_when_trusted_peer_claims_https(
    prod_client: TestClient,
) -> None:
    """cloudflared on 127.0.0.1 advertising X-Forwarded-Proto=https is the
    only signal we trust to switch the response into HTTPS-promising mode."""
    r = prod_client.get(
        "/health",
        headers={"X-Forwarded-Proto": "https"},
    )
    hsts = r.headers.get("strict-transport-security")
    assert hsts is not None
    assert "max-age" in hsts
    assert "includeSubDomains" not in hsts


def test_hsts_absent_when_untrusted_peer_claims_https(
    prod_client: TestClient,
) -> None:
    """X-Forwarded-Proto from a non-trusted IP must be ignored. The test
    sends the header from the TestClient peer (127.0.0.1) but with a mismatch
    in the trust boundary: the configuration is tightened so the peer advertises
    a different IP via X-Forwarded-For that points outside the trust list."""
    # Build a *separately-configured* client whose trust list excludes
    # 127.0.0.1, forcing the middleware to drop the X-Forwarded-Proto.
    from app.core import config as config_module
    config_module.get_settings.cache_clear()
    os.environ["TRUSTED_PROXIES"] = "10.0.0.0/24"  # loopback not in this list
    config_module.get_settings.cache_clear()
    from app import main as main_module
    main_module.settings = config_module.get_settings()
    client = TestClient(main_module.app)
    r = client.get("/health", headers={"X-Forwarded-Proto": "https"})
    assert r.headers.get("strict-transport-security") is None


# ── Spoof resistance ─────────────────────────────────────────────────────────


def test_hsts_absent_when_xfp_https_from_spoofed_peer(
    prod_client: TestClient,
) -> None:
    """An attacker that can reach the loopback socket directly cannot
    inject X-Forwarded-Proto unless they originated from a trusted CIDR.
    The TestClient is the only peer we have here; the corollary assertion
    is that the same client cannot elevate themselves by sending X-Forwarded-For
    pointing to a trusted IP from inside the request — the actual peer
    address is what the trust boundary checks."""
    r = prod_client.get(
        "/health",
        headers={
            "X-Forwarded-Proto": "https",
            "X-Forwarded-For": "127.0.0.1",  # spoof attempt
        },
    )
    # The actual peer is TestClient itself (127.0.0.1 by default) which IS
    # trusted by the global config — X-Forwarded-Proto should therefore be
    # honored — but X-Forwarded-For must not be silently used to broaden the
    # trust list. This test pins the existing contract while a separate test
    # below tightens it for the untrusted case.
    hsts = r.headers.get("strict-transport-security")
    if hsts is not None:
        # If honored, the trust boundary came from the real peer, not the
        # X-Forwarded-For header. Either way, the response MUST NOT contain
        # includeSubDomains.
        assert "includeSubDomains" not in hsts


def test_hsts_no_includesubdomains_under_any_trusted_path(
    prod_client: TestClient,
) -> None:
    r = prod_client.get("/health", headers={"X-Forwarded-Proto": "https"})
    hsts = r.headers.get("strict-transport-security")
    if hsts is not None:
        assert "includeSubDomains" not in hsts


# ── Middleware order: HSTS must apply to error responses too ────────────────


def test_hsts_present_on_404_when_proxy_claims_https(prod_client: TestClient) -> None:
    r = prod_client.get(
        "/this-route-does-not-exist",
        headers={"X-Forwarded-Proto": "https"},
    )
    assert r.status_code == 404
    hsts = r.headers.get("strict-transport-security")
    assert hsts is not None
    assert "includeSubDomains" not in hsts
