"""Regression tests for the Brand v2 live visual hotfix."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from . import _helpers as H


SVG_NS = "http://www.w3.org/2000/svg"


def test_dark_wordmark_is_deterministic_lowercase_lettering_only():
    """The live wordmark must spell only ``markee`` without overlapping glyphs."""
    root = ET.fromstring(
        (H.BRAND_V2_LOGOS / "markee-wordmark-dark.svg").read_text(encoding="utf-8")
    )
    namespace = {"svg": SVG_NS}
    text_nodes = root.findall("./svg:text", namespace)

    assert root.attrib["viewBox"] == "0 0 600 128"
    assert root.attrib["preserveAspectRatio"] == "xMinYMid meet"
    assert root.attrib["role"] == "img"
    assert len(text_nodes) == 1, "wordmark needs one deterministic lettering run"

    text = text_nodes[0]
    spans = text.findall("./svg:tspan", namespace)
    assert "".join(text.itertext()) == "markee"
    assert [span.text for span in spans] == ["marke", "e"]
    assert text.attrib["font-family"] == "Inter, Arial, Helvetica, sans-serif"
    assert text.attrib["fill"].upper() == "#E8E8E8"
    assert spans[0].attrib.get("fill", "#E8E8E8").upper() == "#E8E8E8"
    assert spans[1].attrib["fill"].upper() == "#35D0E0"

    first_x = float(spans[0].attrib["x"])
    first_width = float(spans[0].attrib["textLength"])
    last_x = float(spans[1].attrib["x"])
    last_width = float(spans[1].attrib["textLength"])
    view_width = float(root.attrib["viewBox"].split()[2])
    font_size = float(text.attrib["font-size"])
    baseline = float(text.attrib["y"])
    view_height = float(root.attrib["viewBox"].split()[3])

    assert first_x + first_width <= last_x, "lettering runs overlap"
    assert last_x + last_width <= view_width, "last e is clipped horizontally"
    assert 0 <= baseline - font_size and baseline <= view_height, "lettering is clipped vertically"

    forbidden = {"path", "circle", "line", "polygon", "polyline", "rect", "image", "use"}
    local_tags = {element.tag.rsplit("}", 1)[-1] for element in root.iter()}
    assert not (local_tags & forbidden), "wordmark must not contain an icon or pictogram"


def test_active_frontend_uses_cyan_demo_and_cache_busted_stylesheet():
    """The active landing bundle must not retain the cached amber demo styling."""
    html = H.read_text(H.LANDING_HTML)
    landing_css = H.read_text(H.LANDING_CSS).lower()
    dashboard_css = H.read_text(H.DASHBOARD_CSS).lower()

    assert 'href="/static/styles.css?v=brand-v2-hidden-hotfix-20260726"' in html
    rule = re.search(r"\.sim-versus__mark--intruder\s*\{([^}]*)\}", landing_css)
    assert rule and "color: var(--color-accent)" in rule.group(1)
    for body in (html.lower(), landing_css, dashboard_css):
        assert "#f5a623" not in body
        assert "#ffa500" not in body
        assert "orange" not in body
        assert "amber" not in body


def test_landing_does_not_load_tailwind_cdn_or_depend_on_its_utilities():
    """The landing's owned CSS must replace every Tailwind utility still in use."""
    html = H.read_text(H.LANDING_HTML)
    css = H.read_text(H.LANDING_CSS)

    assert "cdn.tailwindcss.com" not in html
    assert "tailwind.config" not in html
    body_tag = re.search(r"<body\b[^>]*>", html).group(0)
    for utility in ("bg-ink", "text-txt-primary", "font-sans", "antialiased"):
        assert utility not in body_tag
    assert re.search(r"(?:^|})\s*\.font-mono\s*\{", css), (
        "font-mono must be owned locally before removing Tailwind"
    )


def test_mobile_menu_hidden_state_is_owned_locally_and_toggleable():
    """The mobile menu must start closed while JS can still toggle ``hidden``."""
    html = H.read_text(H.LANDING_HTML)
    css = H.read_text(H.LANDING_CSS)
    script = H.read_text(H.LANDING_JS)

    menu = re.search(r'<div class="site-nav__mobile[^"]*" id="mobileMenu"([^>]*)>', html)
    assert menu and re.search(r"\bhidden\b", menu.group(1)), (
        "mobile menu must be hidden in the initial DOM"
    )
    assert re.search(r"\.site-nav__mobile\[hidden\]\s*\{[^}]*display:\s*none\s*!important", css), (
        "owned CSS must enforce the hidden state over the menu's display rule"
    )
    assert "menu.hidden = !open" in script
    assert "toggle.addEventListener('click', () => setMenu(menu.hidden))" in script
