"""Behavioural tests for the trademark-assessment dashboard surface.

These assert on the committed dashboard source (``app.js`` / ``styles.css``)
without starting a server or a browser: the check page must be routable, wired
to ``POST /assessments``, expose a print/PDF affordance and carry a legal
disclaimer.
"""
from __future__ import annotations

from . import _helpers as H


def _js() -> str:
    return H.read_text(H.DASHBOARD_JS)


def _css() -> str:
    return H.read_text(H.DASHBOARD_CSS)


def test_assessment_route_is_registered():
    js = _js()
    assert "'/assessment'" in js, "assessment route missing from ROUTES/renderers"
    # It must be reachable from the sidebar navigation.
    assert "renderAssessment" in js, "assessment view renderer missing"


def test_assessment_nav_item_present():
    js = _js()
    # A nav item pointing at /assessment with a PT label.
    assert "path: '/assessment'" in js


def test_assessment_calls_api_endpoint():
    js = _js()
    assert "/assessments" in js, "assessment view must call POST /assessments"


def test_assessment_has_print_affordance():
    js = _js()
    assert "window.print" in js, "report must offer a print/PDF affordance"


def test_assessment_has_disclaimer():
    js = _js()
    lowered = js.lower()
    # The professional disclaimer wording must be present in the view.
    assert "not legal advice" in lowered, "assessment report must render a legal disclaimer"


def test_print_styles_present():
    css = _css()
    assert "@media print" in css, "print stylesheet rules missing"
