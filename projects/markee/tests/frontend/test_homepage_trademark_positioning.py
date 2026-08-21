"""Homepage positioning contract for the Markee trademark-protection funnel."""
from __future__ import annotations

import re

from . import _helpers as H


def _html() -> str:
    return H.read_text(H.LANDING_HTML)


def _js() -> str:
    return H.read_text(H.LANDING_JS)


def test_homepage_navigation_matches_trademark_services():
    html = _html()
    js = _js()
    combined = html + "\n" + js

    for label in (
        "Services",
        "Start here",
        "Protection",
        "Support levels",
        "FAQ",
        "Trust",
    ):
        assert label in combined

    assert "The Engine" not in html
    assert "Features" not in html


def test_homepage_hero_is_trademark_protection_first_not_monitoring_saas():
    html = _html()
    js = _js()
    hero_match = re.search(r'<section\b[^>]*id="hero"[^>]*>(.*?)</section>', html, re.DOTALL)
    assert hero_match, 'hero section missing'
    hero_source = hero_match.group(1) + js

    assert "EU trademark protection, made simpler." in hero_source
    assert "professional expertise" in hero_source
    assert "proprietary technology" in hero_source
    assert "Explore our services" in hero_source
    assert "Check your trademark" not in hero_match.group(1)
    assert "monitoring SaaS" not in hero_source.lower()
    assert "continuous trademark monitoring" not in hero_source.lower()
    assert "under absolute watch" not in hero_source.lower()


def test_homepage_explains_five_step_customer_journey():
    combined = _html() + "\n" + _js()

    for step in ("Search", "Understand", "Expert Review", "Register", "Monitor"):
        assert re.search(rf"\b{re.escape(step)}\b", combined), f"missing journey step: {step}"

    assert "Search → Understand → Expert Review → Register → Monitor" in combined


def test_monitoring_is_present_but_not_primary_hero_product():
    html = _html()
    hero_match = re.search(r'<section\b[^>]*id="hero"[^>]*>(.*?)</section>', html, re.DOTALL)
    assert hero_match, 'hero section missing'
    hero_text = hero_match.group(1).lower()
    full_text = html.lower() + _js().lower()

    assert "monitor" in full_text
    assert "monitoring" not in hero_text
