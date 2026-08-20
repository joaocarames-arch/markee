"""End-to-end brand integration tests.

These tests verify the integration of the canonical Brand v2 wordmark
into both the landing and the dashboard, plus the use of the canonical
design tokens.
"""
from __future__ import annotations

import json
import re

import pytest

from . import _helpers as H


# ---------------------------------------------------------------------------
# Landing integration
# ---------------------------------------------------------------------------


def test_landing_html_branding_token_count():
    """The landing must use the canonical accent color in its tokens and
    drop the divergent ``--color-bg-abyss: #050505`` declared in the
    legacy file (Brand v2 ink is ``#08090A``).
    """
    body = H.read_text(H.LANDING_CSS)
    assert "--color-accent: #35d0e0" in body, "accent token wrong or missing"
    assert "--color-bg-primary: #08090a" in body, "ink token wrong or missing"
    assert "--color-bg-secondary: #111214" in body, "charcoal token wrong or missing"
    assert "--color-bg-surface: #1a1c1f" in body, "surface token wrong or missing"
    assert "--color-text-primary: #e8e8e8" in body, "text-primary token wrong or missing"
    assert "--color-text-secondary: #8a8d93" in body, "text-secondary token wrong or missing"


def test_landing_html_wordmark_src_matches_brand_v2():
    """The header logo must point at the canonical Brand v2 file."""
    body = H.read_text(H.LANDING_HTML)
    match = re.search(
        r'src="(/assets/brand-v2/logos/markee-wordmark-\w+\.svg)\?v=brand-v2-unified-20260820"',
        body,
    )
    assert match, "landing nav does not point at /assets/brand-v2/logos/"
    filename = match.group(1).rsplit("/", 1)[-1]
    assert (H.BRAND_V2_LOGOS / filename).is_file(), f"missing asset: {filename}"


def test_landing_css_keeps_glassmorphism():
    """Brand v2 keeps glassmorphism in the visual system."""
    css = H.read_text(H.LANDING_CSS)
    assert ".glass-card" in css, "glass-card removed"
    assert "backdrop-filter: blur(16px)" in css or "backdrop-filter:blur(16px)" in css, "glass-pill blur removed"
    assert ".glass-pill" in css, "glass-pill class removed"


def test_landing_css_uses_brand_v2_warning_as_icon_plus_text():
    """After removing amber we still keep the lifecycle states
    (`--ok`, `--warn`) but communicate them through icon + neutral text
    instead of a colour."""
    css = H.read_text(H.LANDING_CSS).lower()
    # We permit ``--warn`` as a modifier class — the colour is gone.
    assert ".lifecycle__item--warn" in css
    # But it must not bind ``--color-warning`` or any amber hex.
    assert "--color-warning" not in css


# ---------------------------------------------------------------------------
# Dashboard integration
# ---------------------------------------------------------------------------


def test_dashboard_html_branding_tokens_match_canonical():
    """The dashboard styles.css must keep the canonical Brand v2 tokens
    (no divergent hard-coded hexes).
    """
    css = H.read_text(H.DASHBOARD_CSS)
    assert "--color-accent: #35d0e0" in css
    assert "--color-bg-primary: #08090a" in css
    assert "--color-bg-secondary: #111214" in css
    assert "--color-bg-surface: #1a1c1f" in css
    assert "--color-text-primary: #e8e8e8" in css


def test_dashboard_html_lang_and_aria():
    """The dashboard keeps PT-PT, accessibility and auth subtitle styling."""
    body = H.read_text(H.DASHBOARD_HTML)
    app_js = H.read_text(H.DASHBOARD_JS)
    css = H.read_text(H.DASHBOARD_CSS)
    assert 'lang="pt-PT"' in body
    assert 'aria-live' in body
    assert re.search(
        r'<div class="auth-brand">.*?</div>\s*<p class="auth-sub">',
        app_js,
        flags=re.DOTALL,
    ), "auth subtitle must remain a sibling immediately after auth-brand"
    assert re.search(r"(?:^|})\s*\.auth-sub\s*\{", css), (
        "auth subtitle styles must target the sibling .auth-sub element"
    )
    assert ".auth-brand .auth-sub" not in css, (
        "descendant selector cannot match the real auth subtitle structure"
    )


def test_dashboard_api_base_contract_is_declared_once_and_used():
    """Every dashboard API request must resolve against the v1 API base."""
    body = H.read_text(H.DASHBOARD_JS)
    declarations = re.findall(
        r"^const\s+API_BASE\s*=\s*'/api/v1';$", body, flags=re.MULTILINE
    )
    assert len(declarations) == 1, "API_BASE must have one canonical declaration"
    assert body.count("API_BASE") >= 3, "API_BASE declaration must have real users"
    assert "fetch(`${API_BASE}${path}`" in body, "apiRequest bypasses API_BASE"
    assert "brandWordmark" not in body, "dead placeholder wordmark must not remain"


def test_dashboard_renders_accessible_canonical_wordmark_asset():
    """Sidebar and auth render the canonical chromatic wordmark asset."""
    body = H.read_text(H.DASHBOARD_JS)
    asset = "/assets/brand-v2/logos/markee-wordmark-dark.svg?v=brand-v2-unified-20260820"
    wordmark_tags = re.findall(r"<img\b[^>]*class=\"dashboard-wordmark\"[^>]*>", body)

    assert len(wordmark_tags) == 2, "sidebar and auth must each render the wordmark"
    for tag in wordmark_tags:
        assert f'src="{asset}"' in tag, "dashboard wordmark is not canonical"
        assert 'alt="markee"' in tag, "dashboard wordmark needs an accessible name"
    assert "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 1481.95 240.00\"" not in body
    assert 'class="wordmark"' not in body, "legacy textual wordmark still injected"
    assert 'class="accent"' not in body, "legacy accent span still injected"
    duplicate = H.REPO_ROOT / "frontend" / "dashboard" / "assets" / "wordmark.svg"
    assert not duplicate.exists(), (
        "unreferenced duplicate wordmark must be removed; use only "
        "/assets/brand-v2/logos/markee-wordmark-dark.svg"
    )


def test_dashboard_wordmark_asset_encodes_canonical_paths_without_symbol():
    """The rendered asset is deterministic paths, with only the final e in cyan."""
    import xml.etree.ElementTree as ET

    asset = H.BRAND_V2_LOGOS / "markee-wordmark-dark.svg"
    root = ET.fromstring(asset.read_text(encoding="utf-8"))
    namespace = {"svg": "http://www.w3.org/2000/svg"}
    assert root.attrib.get("viewBox") == "0 0 1481.95 240.00"
    paths = root.findall(".//svg:path", namespace)
    assert len(paths) == 6
    assert {p.attrib.get("fill", "").upper() for p in paths[:-1]} == {"#E8E8E8"}
    assert paths[-1].attrib.get("fill", "").upper() == "#35D0E0"
    assert not root.findall(".//svg:text", namespace), "text rendering would change logo proportions"
    assert not root.findall(".//svg:circle", namespace), "radar/symbol circles are forbidden"
    assert not root.findall(".//svg:line", namespace), "pictogram lines are forbidden"
    assert not root.findall(".//svg:polygon", namespace), "pictograms are forbidden"
