"""Tests that the frontend HTML / CSS / JS references assets and routes
that are actually served by the FastAPI application.

The app mounts three directories (per ``app/main.py``):

* ``/`` serves ``frontend/landing/index.html``
* ``/static/*`` serves ``frontend/landing/*`` (static files)
* ``/app/*`` serves ``frontend/dashboard/*`` (html=True, hash router)
* ``/assets/*`` serves ``assets/*`` (Brand v2 lives here)

The tests below therefore assert:

* No reference to ``/frontend/landing/*`` or ``/frontend/dashboard/*``
  (paths that the app does not mount).
* No reference to ``/app/login`` (the dashboard is hash-routed and the
  login screen is at ``/app/#/login``).
* All Brand v2 wordmark assets used in HTML must resolve to a file that
  exists on disk and is committed.
* The dashboard HTML keeps ``<html lang="pt-PT">`` and a single root
  element where the hash router mounts.
"""
from __future__ import annotations

import re
from html import unescape
from pathlib import Path

import pytest

from . import _helpers as H


# Routes the FastAPI app actually serves.
LANDING_ROOT = "/"
LANDING_STATIC = "/static/"
DASHBOARD_APP = "/app"
DASHBOARD_LOGIN = "/app/#/login"
ASSETS_BRAND_V2 = "/assets/brand-v2/logos/"


def _auth_cta_targets(body: str) -> list[tuple[str, str]]:
    """Return normalized ``(text, href)`` pairs for intended login CTAs."""
    auth_keywords = re.compile(
        r"\b(entrar|login|iniciar\s+(?:sess[aã]o|[a-zá-ú]+)|"
        r"criar\s+conta|come[çc]ar|ativar\s+vigil|iniciar\s+conta)\b",
        re.IGNORECASE,
    )
    anchor_re = re.compile(
        r"<a\b[^>]*?href=\"([^\"]*)\"[^>]*>(.*?)</a>",
        re.IGNORECASE | re.DOTALL,
    )
    targets = []
    for href, inner in anchor_re.findall(body):
        text = " ".join(unescape(re.sub(r"<[^>]+>", " ", inner)).split())
        if auth_keywords.search(text):
            targets.append((text, unescape(href).strip()))
    return targets


def _production_html_texts() -> dict[str, str]:
    """Return every HTML file in the production frontend bundle."""
    return {
        str(H.LANDING_HTML.relative_to(H.REPO_ROOT)): H.read_text(H.LANDING_HTML),
        str(H.DASHBOARD_HTML.relative_to(H.REPO_ROOT)): H.read_text(H.DASHBOARD_HTML),
    }


# ---------------------------------------------------------------------------
# Anti-routes (paths the app does NOT mount)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "forbidden_path",
    [
        "/frontend/landing/",
        "/frontend/dashboard/",
        "/app/login",
        "/app/login/",
        "/static/assets/",
    ],
)
def test_no_reference_to_unmounted_paths(forbidden_path):
    """The frontend must never reference paths the FastAPI app does not
    mount. ``/frontend/landing/*`` / ``/frontend/dashboard/*`` /
    ``/app/login`` return 404 in production. ``/static/assets/`` is a
    legacy duplicate that the canonical mounts under ``/assets`` already
    cover.
    """
    for rel, body in _production_html_texts().items():
        assert forbidden_path not in body, (
            f"{rel} still references unmounted path {forbidden_path!r}"
        )


def test_landing_does_not_link_to_dashboard_login_path():
    """``/app/login`` is a 404 because the dashboard uses hash routing.
    Login CTAs must therefore point to ``/app/#/login`` (or simply
    ``/app`` which lets the router dispatch to login when no token is
    present). They must never use the legacy ``/app/login`` form.
    """
    body = H.read_text(H.LANDING_HTML)
    assert body, "landing index.html missing"
    # A bare /app/login with a query string would also break routing.
    assert 'href="/app/login"' not in body
    assert "href='/app/login'" not in body


def test_landing_login_ctas_use_hash_login_route():
    """Primary login CTAs in the landing page must point to
    ``/app/#/login`` so that the hash router takes over. A bare
    ``/app`` fallback is acceptable for footer / utility links, but any
    anchor whose visible text reads as an authentication CTA (e.g.
    "Entrar", "Login", "Iniciar", "Criar conta", "Começar", "Ativar")
    must target ``/app/#/login`` to avoid the dead ``/app/login`` path.
    """
    body = H.read_text(H.LANDING_HTML)
    hrefs = re.findall(r'href="(/app[^"]*)"', body)
    assert hrefs, "landing must contain at least one /app CTA"

    # The legacy dead form is forbidden outright in every CTA.
    for href in hrefs:
        assert not re.fullmatch(r"/app/login/?", href), f"dead /app/login CTA: {href!r}"
        assert href.startswith(("/app", "/app/#")), f"unexpected /app target: {href!r}"

    # Generic footer / utility links without authentication wording stay
    # exempted. Intended login CTAs must equal the normalized destination;
    # prefix lookalikes such as ``#/login-evil`` are not valid routes.
    auth_ctas = _auth_cta_targets(body)
    assert auth_ctas, "landing must contain at least one intended login CTA"
    for text, href in auth_ctas:
        assert href == DASHBOARD_LOGIN, (
            f"auth CTA {text!r} targets {href!r}, expected exactly {DASHBOARD_LOGIN!r}"
        )


# ---------------------------------------------------------------------------
# Brand v2 asset references must resolve
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "rel_path",
    [
        "markee-wordmark-dark.svg",
        "markee-wordmark-light.svg",
        "markee-wordmark-mono-white.svg",
        "markee-wordmark-mono-black.svg",
        "markee-brand-sheet.svg",
    ],
)
def test_brand_v2_assets_are_present(rel_path):
    """Every Brand v2 asset that the integration may reference must
    exist on disk so the FastAPI ``/assets`` mount can serve it.
    """
    target = H.BRAND_V2_LOGOS / rel_path
    assert target.is_file(), f"missing brand-v2 asset: {rel_path}"


def test_landing_references_brand_v2_dark_wordmark():
    """The landing navigation must use the canonical dark wordmark
    served by FastAPI at ``/assets/brand-v2/logos/markee-wordmark-dark.svg``.
    Legacy logos in ``/static/assets/logos/`` are not committed.
    """
    body = H.read_text(H.LANDING_HTML)
    assert body, "landing index.html missing"
    assert (
        "/assets/brand-v2/logos/markee-wordmark-dark.svg" in body
    ), "landing nav does not reference the canonical Brand v2 dark wordmark"


def test_landing_does_not_use_legacy_wordmark_svg():
    """The landing must not point at the legacy
    ``/static/assets/logos/markee_logo_2_icon_wordmark_dark.svg`` that
    the FastAPI mount does not serve (the directory ``static/assets``
    is not mounted).
    """
    body = H.read_text(H.LANDING_HTML)
    assert (
        "/static/assets/logos/markee_logo_2_icon_wordmark_dark.svg" not in body
    ), "landing still references the unmounted legacy wordmark SVG"


def test_dashboard_html_uses_hash_router():
    """The dashboard keeps the SPA hash router root and a single mount
    element so that ``#/login`` and ``#/dashboard`` resolve.
    """
    body = H.read_text(H.DASHBOARD_HTML)
    assert body, "dashboard index.html missing"
    assert 'id="root"' in body, "dashboard missing #root mount"
    # The dashboard does NOT load styles.css / app.js via absolute path;
    # siblings are resolved by StaticFiles(html=True).
    assert '<link rel="stylesheet" href="styles.css?v=logo-unified-20260820"' in body
    assert '<script src="app.js?v=logo-unified-20260820" defer' in body
    assert 'lang="pt-PT"' in body, "dashboard must keep lang=pt-PT"


# ---------------------------------------------------------------------------
# app/main.py must keep the expected mounts (smoke)
# ---------------------------------------------------------------------------


def test_app_main_keeps_expected_mounts():
    """The FastAPI entrypoint still wires ``/app``, ``/static`` and
    ``/assets`` so that the routes the frontend relies on actually
    serve. A regression here would 404 every navigation.
    """
    main_py = (H.REPO_ROOT / "app" / "main.py").read_text(encoding="utf-8")
    assert '"/app"' in main_py, "missing /app mount"
    assert '"/static"' in main_py, "missing /static mount"
    assert '"/assets"' in main_py, "missing /assets mount"