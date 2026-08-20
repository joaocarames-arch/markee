"""Light/dark theme contract for the public landing.

The landing ships a manual theme switch on top of the existing Portuguese
default and the PT/EN language switch. These tests fail when:

* the switch markup, its accessible name or its data hooks disappear,
* the theme choice stops being persisted in ``localStorage``,
* the first visit stops honouring ``prefers-color-scheme``,
* the light or dark token block is missing or leaks hard-coded colours
  that cannot follow the active theme,
* the legacy cyan accent reappears on a surface a visitor can reach,
* the wordmarks or the canonical tokens stop carrying the green accent.
"""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET

import pytest

from . import _helpers as H


SVG_NS = "http://www.w3.org/2000/svg"

# The credible light olive green, in its two working values. The bright brand
# green carries the logo and the dark theme; the deep green is the light
# theme's interactive colour because #A7C957 on white is unreadable.
BRAND_GREEN = "#a7c957"
DEEP_GREEN = "#5f7f2a"

# Every spelling of the retired cyan accent, including its rgba() form.
LEGACY_CYAN = re.compile(
    r"#35d0e0|#5edcf0|#25a8b8|0x35d0e0|53\s*,\s*208\s*,\s*224",
    re.IGNORECASE,
)


def _rel(path) -> str:
    return str(path.relative_to(H.REPO_ROOT))


# ---------------------------------------------------------------------------
# Switch markup and accessibility
# ---------------------------------------------------------------------------


def test_landing_html_declares_a_default_theme_on_the_root_element():
    """Themes are driven by ``data-theme`` on ``<html>`` so the CSS token
    blocks can switch without touching a single component rule. The served
    markup keeps ``dark`` so the page is never unstyled.
    """
    html = H.read_text(H.LANDING_HTML)

    root = re.search(r"<html\b[^>]*>", html)
    assert root, "landing has no <html> tag"
    assert 'data-theme="dark"' in root.group(0), (
        "the served <html> must declare the default theme"
    )
    assert 'lang="pt-PT"' in root.group(0), "Portuguese must remain the default"


def test_landing_head_bootstraps_the_theme_before_first_paint():
    """A blocking inline script in ``<head>`` resolves the stored/system
    theme before the body renders. Without it a light-mode visitor sees a
    black flash on every navigation.
    """
    html = H.read_text(H.LANDING_HTML)

    head = html.split("</head>", 1)[0]
    assert "markee-theme" in head, "theme bootstrap missing from <head>"
    assert "prefers-color-scheme" in head, "bootstrap ignores the system preference"
    assert "setAttribute('data-theme'" in head or 'setAttribute("data-theme"' in head

    # It must run before the stylesheet-dependent body, and must not be
    # deferred or moved into the module bundle.
    bootstrap = re.search(r"<script>(?!\s*</script>)(.*?)</script>", head, re.DOTALL)
    assert bootstrap, "the bootstrap must be an inline, non-deferred <script>"
    assert "localStorage" in bootstrap.group(1)


@pytest.mark.parametrize("scope", ["nav", "mobile"])
def test_landing_exposes_an_accessible_theme_switch(scope):
    """Both the desktop nav and the mobile menu carry a switch, mirroring
    how the language switcher is duplicated.
    """
    html = H.read_text(H.LANDING_HTML)

    toggles = re.findall(r"<button\b[^>]*data-theme-toggle[^>]*>", html)
    assert len(toggles) == 2, (
        f"expected one theme switch in the nav and one in the mobile menu, got {len(toggles)}"
    )
    for tag in toggles:
        assert 'type="button"' in tag, "theme switch must not submit anything"
        assert 'role="switch"' in tag, "theme switch must expose the switch role"
        assert re.search(r'aria-checked="(true|false)"', tag), (
            "theme switch must publish its state via aria-checked"
        )
        assert "aria-label=" in tag, "theme switch needs an accessible name"

    marker = "theme-toggle--mobile" if scope == "mobile" else "theme-toggle"
    assert marker in html


def test_theme_switch_copy_is_translatable_in_both_dictionaries():
    """The switch must not become a Portuguese-only island: its accessible
    name and the mobile label go through the existing i18n pipeline.
    """
    html = H.read_text(H.LANDING_HTML)
    js = H.read_text(H.LANDING_JS)

    keys = set(re.findall(r'data-i18n="([^"]+)"', html))
    assert "theme.aria" in keys, "theme switch label is not translatable"
    assert "theme.label" in keys, "mobile theme row label is not translatable"

    for tag in re.findall(r"<button\b[^>]*data-theme-toggle[^>]*>", html):
        assert 'data-i18n-attr="aria-label"' in tag, (
            "the accessible name must be bound to the aria-label attribute"
        )

    pt_block = js.split('"pt": {', 1)[1].split('"en": {', 1)[0]
    en_block = js.split('"en": {', 1)[1].split("};", 1)[0]
    for key in ("theme.aria", "theme.label"):
        assert f'"{key}"' in pt_block, f"{key} missing from the PT dictionary"
        assert f'"{key}"' in en_block, f"{key} missing from the EN dictionary"


# ---------------------------------------------------------------------------
# Persistence and system preference
# ---------------------------------------------------------------------------


def test_theme_choice_is_persisted_in_local_storage():
    js = H.read_text(H.LANDING_JS)

    assert "localStorage.getItem('markee-theme')" in js
    assert "localStorage.setItem('markee-theme'" in js
    # Storage access is refused in locked-down browsers; the switch must
    # keep working there instead of throwing on click.
    persistence = js.split("function setStoredTheme", 1)[-1].split("\nfunction ", 1)[0]
    assert "try {" in persistence and "catch" in persistence


def test_first_visit_follows_the_system_preference():
    js = H.read_text(H.LANDING_JS)

    assert "prefers-color-scheme: light" in js
    init = js.split("function initThemeSwitch", 1)[-1].split("\nfunction ", 1)[0]
    assert "getStoredTheme()" in init, "the stored choice must win over the system"
    assert "getSystemTheme()" in init, "first visit must fall back to the system"
    assert "addEventListener('change'" in init, (
        "an unset visitor should follow the OS when it flips"
    )


def test_theme_switch_keeps_the_browser_chrome_in_sync():
    html = H.read_text(H.LANDING_HTML)
    js = H.read_text(H.LANDING_JS)

    assert '<meta name="theme-color"' in html
    apply_theme = js.split("function applyTheme", 1)[-1].split("\nfunction ", 1)[0]
    assert 'meta[name="theme-color"]' in apply_theme
    assert "aria-checked" in apply_theme, "the switch state must follow the theme"


def test_theme_switch_does_not_disturb_the_language_switch():
    """Theme and language are independent: two storage keys, two appliers."""
    js = H.read_text(H.LANDING_JS)

    assert "markee-language" in js and "markee-theme" in js
    assert "applyLanguage" in js and "applyTheme" in js
    boot = js.split("function boot()", 1)[-1]
    assert "initLanguageSwitch()" in boot and "initThemeSwitch()" in boot


def test_webgl_hero_field_follows_the_active_theme():
    """Additive blending over a white page renders the hero field invisible,
    so the particle material has to be re-tinted when the theme flips.
    """
    js = H.read_text(H.LANDING_JS)

    assert "onThemeChange(" in js, "no theme subscription hook"
    webgl = js.split("async function initWebGL", 1)[-1]
    assert "onThemeChange(" in webgl, "the hero field ignores theme changes"
    assert "NormalBlending" in webgl and "AdditiveBlending" in webgl


# ---------------------------------------------------------------------------
# CSS token blocks
# ---------------------------------------------------------------------------


def test_landing_css_defines_both_theme_token_blocks():
    css = H.read_text(H.LANDING_CSS)

    assert re.search(r":root\[data-theme=['\"]light['\"]\]\s*\{", css), (
        "light theme token block missing"
    )
    assert "color-scheme: dark" in css and "color-scheme: light" in css, (
        "color-scheme keeps native form controls and scrollbars in the right mode"
    )


def test_light_theme_uses_white_or_off_white_surfaces_and_zinc_text():
    css = H.read_text(H.LANDING_CSS)
    light = css.split(":root[data-theme='light']", 1)[-1].split("}", 1)[0]

    assert "--color-bg-primary: #fbfcf7" in light, "light page must be off-white"
    assert "--color-bg-secondary: #ffffff" in light, "raised blocks must be white"
    assert "--color-text-primary: #27272a" in light, "body text must be zinc"
    assert "--color-text-strong: #09090b" in light, "headings must be near-black"
    assert f"--color-accent: {DEEP_GREEN}" in light, (
        "the light accent must be the deep green, readable on white"
    )


def test_dark_theme_keeps_the_canonical_brand_v2_surfaces():
    """The theme work must not drift the ink/charcoal/surface values."""
    css = H.read_text(H.LANDING_CSS)
    dark = css.split(":root,", 1)[-1].split("}", 1)[0]

    assert "--color-bg-primary: #08090a" in dark
    assert "--color-bg-secondary: #111214" in dark
    assert "--color-bg-surface: #1a1c1f" in dark
    assert "--color-text-primary: #e8e8e8" in dark
    assert "--color-text-secondary: #8a8d93" in dark
    assert f"--color-accent: {BRAND_GREEN}" in dark


def test_theme_dependent_colours_are_tokenised_not_hardcoded():
    """Any raw ``#ffffff`` text colour or opaque ink veil left in a
    component rule would survive into light mode and become invisible.
    """
    css = H.read_text(H.LANDING_CSS)
    # Drop the two token blocks; everything after them is component CSS.
    components = css.split("/* --- end theme tokens --- */", 1)
    assert len(components) == 2, "theme token blocks must be delimited"
    body = components[1]

    offenders = re.findall(r"color:\s*#ffffff", body, re.IGNORECASE)
    assert not offenders, (
        f"{len(offenders)} hard-coded white text colours cannot follow the theme; "
        "use var(--color-text-strong)"
    )
    assert "rgba(8, 9, 10," not in body, (
        "opaque ink veils must come from the glass tokens so light mode can invert them"
    )


def test_theme_switch_is_laid_out_to_never_wrap_the_nav():
    css = H.read_text(H.LANDING_CSS)

    actions = re.search(r"\.site-nav__actions\s*\{([^}]*)\}", css)
    assert actions and "flex-wrap: nowrap" in actions.group(1), (
        "the nav action cluster must be pinned to a single line"
    )
    toggle = re.search(r"\.theme-toggle\s*\{([^}]*)\}", css)
    assert toggle, ".theme-toggle rule missing"
    assert "flex-shrink: 0" in toggle.group(1), (
        "the switch must not be squeezed out of shape on narrow viewports"
    )


# ---------------------------------------------------------------------------
# Green accent rollout
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", H.ACTIVE_BRAND_SURFACES, ids=_rel)
def test_active_surfaces_dropped_the_legacy_cyan_accent(path):
    """No visitor-reachable surface may still paint #35D0E0 or its
    hover/pressed siblings. Historical drafts and evidence bundles are
    deliberately out of scope.
    """
    match = LEGACY_CYAN.search(H.read_text(path))
    assert not match, f"{_rel(path)} still carries the cyan accent: {match.group(0)!r}"


def test_brand_tokens_declare_the_green_accent():
    css = H.BRAND_V2_TOKENS_CSS.read_text(encoding="utf-8").lower()
    assert f"--color-accent: {BRAND_GREEN}" in css
    assert f"--logo-accent: {BRAND_GREEN}" in css

    tokens = json.loads(H.BRAND_V2_TOKENS_JSON.read_text(encoding="utf-8"))
    assert tokens["color"]["accent"]["$value"].lower() == BRAND_GREEN


def test_wordmarks_carry_the_green_accent_readable_on_their_background():
    """Both chromatic wordmarks keep six glyphs with only the last ``e``
    accented. The dark variant uses the light olive brand green; the light
    variant uses the deep green so the letter survives on white.
    """
    expected = {
        "markee-wordmark-dark.svg": (BRAND_GREEN, "#e8e8e8"),
        "markee-wordmark-light.svg": (DEEP_GREEN, "#08090a"),
    }
    for filename, (accent, main) in expected.items():
        root = ET.fromstring(
            (H.BRAND_V2_LOGOS / filename).read_text(encoding="utf-8")
        )
        paths = root.findall(f".//{{{SVG_NS}}}path")
        assert len(paths) == 6, f"glyph count drift in {filename}"
        fills = [p.attrib.get("fill", "").strip().lower() for p in paths]
        assert fills[-1] == accent, f"{filename} accent glyph is {fills[-1]!r}"
        assert set(fills[:-1]) == {main}, f"{filename} main glyphs drifted: {set(fills[:-1])}"


def test_landing_and_dashboard_paint_the_green_accent():
    landing = H.read_text(H.LANDING_CSS).lower()
    dashboard = H.read_text(H.DASHBOARD_CSS).lower()

    assert BRAND_GREEN in landing and DEEP_GREEN in landing
    assert BRAND_GREEN in dashboard, "the dashboard accent must match the brand"


def test_favicon_referenced_by_the_landing_uses_the_green_accent():
    html = H.read_text(H.LANDING_HTML)
    href = re.search(r'<link rel="icon" href="([^"]+)"', html)
    assert href, "landing declares no favicon"

    favicon = H.REPO_ROOT / href.group(1).lstrip("/")
    assert favicon.is_file(), f"favicon {href.group(1)} is not served from disk"
    assert BRAND_GREEN in favicon.read_text(encoding="utf-8").lower()
