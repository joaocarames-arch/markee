"""Fail-closed scans for the production frontend bundle.

The brief and BRAND_MANUAL.md §6.3 / §9 forbid the following patterns:

* No amber color anywhere (CSS or HTML). The Brand v2 palette explicitly
  bans ``#f5a623`` and any orange tone. Warning state is communicated
  with icon + text on neutral surfaces.
* No radar / scan-line / glow shapes — these are the visual identity
  the manual rejects. ``.scanlines-glyph``, ``.crosshair-glyph`` and
  cyan ``box-shadow`` glows must not survive.
* No glow effects on text or surface elements (cyan ``text-shadow``,
  ``box-shadow`` glow, ``shadow-glow`` custom property).
* No reintroduction of the cinematic preloader grain overlay
  (``.noise-overlay``) — manual forbids scan-line style noise.
* Final CTA must not reintroduce a glow halo
  (``.final-cta__glow``).

Each test fails closed if a forbidden token is present in any committed
file under ``frontend/landing`` or ``frontend/dashboard``. Tests are
whitelisted per file (no spurious failures from third-party CSS — we
own every byte in those directories).
"""
from __future__ import annotations

import re

import pytest

from . import _helpers as H


# Regexes for forbidden tokens. Tests intentionally use lowercase
# comparisons so case-variant CSS values still fail.
FORBIDDEN_HEX_LOWER = [
    "#f5a623",  # amber / orange
    "#ffa500",  # alias
    "rgb(245, 166, 35)",  # same color in rgb()
]

FORBIDDEN_CSS_RULES = [
    r"--color-warning\s*:",
    r"--shadow-glow\s*:",
    r"\.noise-overlay",
    r"\.final-cta__glow",
    r"\.scanlines-glyph",
    r"@keyframes\s+scanline-run",
    r"@keyframes\s+grain-shift",
    r"@keyframes\s+crosshair-blink",
    r"\.crosshair-glyph",
    r"\.orbit-rings",
]

FORBIDDEN_HTML_TERMS = [
    "noise-overlay",
    "final-cta__glow",
    "scanlines-glyph",
    "crosshair-glyph",
    "orbit-rings",
]


# Files we own outright. The dashboard styles.css imports nothing, the
# landing styles.css imports nothing. We assert the whole file.
PRODUCTION_CSS_FILES = (H.LANDING_CSS, H.DASHBOARD_CSS)
PRODUCTION_HTML_FILES = (H.LANDING_HTML, H.DASHBOARD_HTML)
ALL_FILES = PRODUCTION_CSS_FILES + PRODUCTION_HTML_FILES + (H.LANDING_JS, H.DASHBOARD_JS)


# ---------------------------------------------------------------------------
# Amber color
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", PRODUCTION_CSS_FILES, ids=lambda p: str(p.relative_to(H.REPO_ROOT)))
def test_css_does_not_define_amber(path):
    body = H.read_text(path).lower()
    for forbidden in FORBIDDEN_HEX_LOWER:
        assert forbidden not in body, f"{path.name} still defines amber {forbidden!r}"


def test_no_amber_anywhere_in_production_html():
    for path in PRODUCTION_HTML_FILES:
        body = H.read_text(path).lower()
        for forbidden in FORBIDDEN_HEX_LOWER:
            assert forbidden not in body, f"{path.name} references amber {forbidden!r}"


def test_no_amber_string_in_css():
    """Even without an exact hex match, an explicit ``amber`` keyword
    inside the CSS would indicate a regression.
    """
    for path in PRODUCTION_CSS_FILES:
        body = H.read_text(path).lower()
        assert "amber" not in body, f"{path.name} mentions 'amber'"


# ---------------------------------------------------------------------------
# Radar / scan-lines / glow
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", PRODUCTION_CSS_FILES, ids=lambda p: str(p.relative_to(H.REPO_ROOT)))
@pytest.mark.parametrize("pattern", FORBIDDEN_CSS_RULES)
def test_css_does_not_contain_forbidden_visual_rules(path, pattern):
    body = H.read_text(path)
    match = re.search(pattern, body)
    assert not match, f"{path.name} still contains forbidden rule matching {pattern!r}: {match.group(0)!r}"


@pytest.mark.parametrize("path", PRODUCTION_HTML_FILES, ids=lambda p: str(p.relative_to(H.REPO_ROOT)))
@pytest.mark.parametrize("term", FORBIDDEN_HTML_TERMS)
def test_html_does_not_contain_forbidden_visual_terms(path, term):
    body = H.read_text(path)
    assert term not in body, f"{path.name} still references forbidden visual term {term!r}"


def test_css_does_not_use_cyan_text_shadow_glow():
    """Cyan ``text-shadow`` glows on hero / stat / CTA numbers were the
    cinematic look the manual forbids. After the integration the CSS
    must not declare any text-shadow whose color is the cyan accent.
    """
    pattern = re.compile(
        r"text-shadow\s*:[^;]*?(?:53\s*,\s*208\s*,\s*224|35d0e0|35\s+208\s+224)",
        re.IGNORECASE,
    )
    for path in PRODUCTION_CSS_FILES:
        body = H.read_text(path)
        match = pattern.search(body)
        assert not match, (
            f"{path.name} still has cyan text-shadow glow: {match.group(0)!r}"
        )


def test_css_does_not_use_cyan_box_shadow_glow():
    """A direct cyan ``box-shadow`` glow replaces the removed
    ``shadow-glow`` token. The colour must not appear in any box-shadow.
    """
    pattern = re.compile(
        r"box-shadow\s*:[^;]*?(?:53\s*,\s*208\s*,\s*224|35d0e0|0\s+0\s+(?:20|24|32|40|60)px)",
        re.IGNORECASE,
    )
    for path in PRODUCTION_CSS_FILES:
        body = H.read_text(path)
        match = pattern.search(body)
        assert not match, (
            f"{path.name} still has a cyan/halo box-shadow: {match.group(0)!r}"
        )


def test_landing_drops_preloader_grain_overlay():
    """The cinematic grain overlay (.noise-overlay) is an artefact of the
    rejected aesthetic; the integration must not re-introduce it.
    """
    body = H.read_text(H.LANDING_HTML)
    assert "noise-overlay" not in body
    css = H.read_text(H.LANDING_CSS)
    assert ".noise-overlay" not in css
    assert "@keyframes grain-shift" not in css