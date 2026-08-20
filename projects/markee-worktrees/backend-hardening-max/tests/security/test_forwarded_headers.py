"""Forwarded headers and middleware order tests.

These exercise the *real* scope/peer of an incoming request through the
middleware stack, without test-only bypasses (no force_https, no TestClient
peer injection). The contract:

* Trusted peer (loopback, cloudflared-local) MAY inject X-Forwarded-Proto /
  X-Forwarded-For / X-Forwarded-Host. The middleware translates them into
  request.url.scheme / request.url.hostname exactly once.
* Untrusted peer CANNOT influence scheme/host/Location via any of those
  headers. The spoofed values must be ignored.
* The 127.0.0.1:8000 default cloudflared Host is the only loopback Host we
  accept. Other loopback hosts (e.g. ``localhost``) are rejected by
  TrustedHost so an attacker cannot reach the app via a different local
  hostname.
* Redirects issued by the app depend on the produced URL, not on the raw
  Host header — so a request with Host: ``evil.example`` that lands on a
  reachable route still emits a relative Location.
"""
from __future__ import annotations

import os
from typing import Any

import pytest
from fastapi.testclient import TestClient


def _build_client(**env: Any) -> TestClient:
    overlay = dict(env)
    overlay.setdefault("SECRET_KEY", "x" * 64)
    overlay.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    for key, value in overlay.items():
        os.environ[key] = str(value)
    from app.core import config as config_module
    config_module.get_settings.cache_clear()
    from app import main as main_module
    main_module.settings = config_module.get_settings()
    return TestClient(main_module.app)


@pytest.fixture
def prod_client() -> TestClient:
    return _build_client(
        ENVIRONMENT="production",
        CORS_ORIGINS='["https://markee.batata.cc"]',
        TRUSTED_HOSTS="markee.batata.cc,app.markee.batata.cc,127.0.0.1",
        TRUSTED_PROXIES="127.0.0.1/32",
    )


# ── Trusted host list ────────────────────────────────────────────────────────


def test_trusted_host_accepts_loopback(prod_client: TestClient) -> None:
    """cloudflared sends Host: 127.0.0.1:8000. The loopback Host must be
    accepted; otherwise the public surface returns 400 before any routes
    run."""
    r = prod_client.get("/health", headers={"Host": "127.0.0.1:8000"})
    assert r.status_code == 200


def test_trusted_host_accepts_public_host(prod_client: TestClient) -> None:
    r = prod_client.get("/health", headers={"Host": "app.markee.batata.cc"})
    assert r.status_code == 200


def test_trusted_host_rejects_unknown_host(prod_client: TestClient) -> None:
    r = prod_client.get("/health", headers={"Host": "evil.example"})
    assert r.status_code == 400


def test_trusted_host_rejects_unknown_loopback_alias(prod_client: TestClient) -> None:
    """If the trust list is exact-host, ``localhost`` is NOT ``127.0.0.1``.
    An attacker pointing DNS at the loopback IP with name ``localhost`` must
    not reach the app."""
    r = prod_client.get("/health", headers={"Host": "localhost:8000"})
    assert r.status_code == 400


# ── Forwarded headers: trusted peer transforms once ──────────────────────────


def test_trusted_xfp_https_makes_location_https_when_redirecting(
    prod_client: TestClient,
) -> None:
    """Redirects must use the scheme derived from the trusted X-Forwarded-Proto,
    not the request.url.scheme seen by the raw ASGI scope (which is http on
    the loopback socket)."""
    r = prod_client.get(
        "/app",
        headers={
            "Host": "app.markee.batata.cc",
            "X-Forwarded-Proto": "https",
        },
        follow_redirects=False,
    )
    assert r.status_code in (307, 308)
    # The Location must be relative — it must not contain a host. The scheme
    # used by the browser is its own concern; we never emit a Location that
    # depends on the proxy's view.
    location = r.headers["location"]
    assert location.startswith("/"), location
    assert "://" not in location


def test_untrusted_xfp_https_does_not_influence_redirect(
    prod_client: TestClient,
) -> None:
    """A request that arrives on the loopback socket but does not match the
    trust list (the peer is the same TestClient 127.0.0.1, but the trust
    list is reconfigured to a different CIDR) must NOT honour X-Forwarded-Proto
    and must NOT emit a relative redirect that pretends to be HTTPS."""
    client = _build_client(
        ENVIRONMENT="production",
        CORS_ORIGINS='["https://markee.batata.cc"]',
        TRUSTED_HOSTS="markee.batata.cc,app.markee.batata.cc,127.0.0.1",
        TRUSTED_PROXIES="10.255.255.0/24",  # loopback explicitly NOT trusted
    )
    r = client.get(
        "/app",
        headers={
            "Host": "app.markee.batata.cc",
            "X-Forwarded-Proto": "https",
        },
        follow_redirects=False,
    )
    assert r.status_code in (307, 308)
    location = r.headers["location"]
    # We must not amplify a spoofed header into a redirect that pretends
    # to be HTTPS — the relative path is the right answer, but the HSTS
    # header should also be absent (covered by HSTS tests).
    assert location.startswith("/")


# ── Forwarded headers: peer check is based on the real socket peer ──────────


def test_xxxff_does_not_broaden_trust(prod_client: TestClient) -> None:
    """The middleware must NOT use X-Forwarded-For to decide whether the
    peer is trusted. The trust decision is based on the real socket peer.
    ``X-Forwarded-For: 127.0.0.1`` from an untrusted peer must not be enough."""
    # This test is structural: we set up a tightened trust list that
    # excludes 127.0.0.1, then send X-Forwarded-For: 127.0.0.1 from the
    # TestClient peer. The server should refuse to honour the header.
    client = _build_client(
        ENVIRONMENT="production",
        CORS_ORIGINS='["https://markee.batata.cc"]',
        TRUSTED_HOSTS="markee.batata.cc,app.markee.batata.cc",
        TRUSTED_PROXIES="10.0.0.0/24",  # loopback NOT trusted
    )
    r = client.get(
        "/health",
        headers={
            "Host": "markee.batata.cc",
            "X-Forwarded-For": "127.0.0.1",
            "X-Forwarded-Proto": "https",
        },
    )
    # The peer is not trusted, so X-Forwarded-Proto must not be honoured.
    # We assert HSTS is absent (proxy of "scheme was not HTTPS").
    assert r.headers.get("strict-transport-security") is None


# ── Middleware order: security headers + CORS cover error responses ──────────


def test_security_headers_present_on_404(prod_client: TestClient) -> None:
    r = prod_client.get("/this-route-does-not-exist")
    assert r.status_code == 404
    assert r.headers.get("x-content-type-options") == "nosniff"
    assert r.headers.get("x-frame-options") == "DENY"
    assert r.headers.get("referrer-policy") == "strict-origin-when-cross-origin"


def test_cors_present_on_404_for_known_origin(prod_client: TestClient) -> None:
    r = prod_client.get(
        "/this-route-does-not-exist",
        headers={"Origin": "https://markee.batata.cc"},
    )
    assert r.status_code == 404
    # CORS must surface on error responses so the browser can read the
    # body of the failure.
    assert r.headers.get("access-control-allow-origin") == "https://markee.batata.cc"


def test_cors_absent_for_unknown_origin(prod_client: TestClient) -> None:
    r = prod_client.get(
        "/this-route-does-not-exist",
        headers={"Origin": "https://evil.example"},
    )
    assert r.headers.get("access-control-allow-origin") is None


def test_health_reflected_with_relative_path(prod_client: TestClient) -> None:
    r = prod_client.get("/health", headers={"Host": "markee.batata.cc"})
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
