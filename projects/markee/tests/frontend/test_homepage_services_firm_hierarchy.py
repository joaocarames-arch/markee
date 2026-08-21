"""Homepage hierarchy contract for Markee as a services firm with technology."""
from __future__ import annotations

import re

from . import _helpers as H


def _html() -> str:
    return H.read_text(H.LANDING_HTML)


def _js() -> str:
    return H.read_text(H.LANDING_JS)


def _combined() -> str:
    return _html() + "\n" + _js()


def _section_source(section_id: str) -> str:
    match = re.search(rf'<section\b[^>]*id="{re.escape(section_id)}"[^>]*>(.*?)</section>', _html(), re.DOTALL)
    assert match, f"missing section: {section_id}"
    return match.group(1)


def test_hero_positions_markee_as_services_firm_before_checker():
    hero = _section_source("hero") + _js()

    assert "EU trademark protection, made simpler." in hero
    assert "search, registration and protection" in hero
    assert "professional expertise" in hero
    assert "proprietary technology" in hero
    assert "Explore our services" in hero
    assert "How it works" in hero

    first_cta = re.search(r'<div class="hero__ctas".*?</div>', hero, re.DOTALL)
    assert first_cta, "hero CTA block missing"
    assert "Check your trademark" not in first_cta.group(0)


def test_services_checker_conflict_analysis_and_support_levels_are_ordered():
    html = _html()
    combined = _combined()

    ordered_ids = ["services", "trademark-check", "support-levels", "features", "monitoring", "trust", "faq"]
    positions = {section_id: html.index(f'id="{section_id}"') for section_id in ordered_ids}
    assert positions == dict(sorted(positions.items(), key=lambda item: item[1]))

    for text in (
        "What we do",
        "Trademark Search & Clearance",
        "EU Trademark Registration",
        "Monitoring and Renewals",
        "Already have a name in mind? Start here.",
        "See how Markee analyses potential conflicts",
        "What Markee looks for",
        "Free Preliminary Check",
        "Detailed Automated Report",
        "Expert Review",
        "Trademark Registration",
    ):
        assert text in combined


def test_journey_is_compact_and_visual_effect_hooks_are_preserved():
    html = _html()
    css = H.read_text(H.LANDING_CSS)
    js = _js()

    journey = _section_source("features")
    assert "journey-compact" in journey
    assert "Search → Understand → Expert Review → Register → Monitor" in journey
    assert "features__viewport" not in journey
    assert "feature-panel" not in journey
    assert "journey-compact" in css

    for marker in (
        "data-split-lines",
        "data-split-words",
        'id="webglCanvas"',
        "gsap.registerPlugin(ScrollTrigger)",
        "Lenis",
        "THREE",
    ):
        assert marker in html or marker in js


def test_mobile_spacing_is_tightened_for_reworked_sections():
    css = H.read_text(H.LANDING_CSS)

    assert "@media (max-width: 640px)" in css
    assert ".services__grid" in css
    assert ".checker__layout" in css
    assert "padding: clamp(56px, 10vh, 120px) var(--space-lg);" in css
    assert "min-height: 86svh" in css
