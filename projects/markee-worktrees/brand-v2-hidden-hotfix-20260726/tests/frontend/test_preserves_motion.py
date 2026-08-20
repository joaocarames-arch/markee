"""Tests that the brand integration preserves the motion stack.

The brief mandates preserving GSAP, Lenis, Three.js / WebGL and the
existing interactive layers (magnetic buttons, tilt cards, custom
cursor, scroll reveals, preloader fade). Removing any of these in the
name of a brand cleanup would be a destructive redesign.

These tests assert the production source still wires each subsystem.
"""
from __future__ import annotations

import re

import pytest

from . import _helpers as H


# ---------------------------------------------------------------------------
# Landing motion wiring (HTML + script.js)
# ---------------------------------------------------------------------------


def test_landing_html_loads_motion_dependencies():
    """The landing must keep its CDN imports for GSAP, ScrollTrigger,
    Lenis and Three.js.
    """
    body = H.read_text(H.LANDING_HTML)
    assert "gsap@3.12.5" in body, "GSAP CDN removed"
    assert "ScrollTrigger" in body, "ScrollTrigger CDN removed"
    assert "lenis@1.1.14" in body, "Lenis CDN removed"
    assert "three@0.160.0" in body, "Three.js import-map removed"


def test_landing_html_has_preloader_and_cursor():
    """The preloader veil and the custom cursor elements must remain in
    the HTML so the corresponding script.js code keeps working.
    """
    body = H.read_text(H.LANDING_HTML)
    assert 'id="preloader"' in body, "preloader container removed"
    assert 'id="cursorDot"' in body, "cursor-dot removed"
    assert 'id="cursorRing"' in body, "cursor-ring removed"
    assert 'id="webglCanvas"' in body, "WebGL canvas removed"


def test_landing_js_keeps_motion_initializers():
    """script.js must still import the Lenis / GSAP / WebGL helpers."""
    body = H.read_text(H.LANDING_JS)
    assert "function initLenis" in body, "initLenis removed"
    assert "function initMagnetic" in body, "initMagnetic removed"
    assert "function initTiltCards" in body, "initTiltCards removed"
    assert "function initCursor" in body, "initCursor removed"
    assert "function initWebGL" in body, "initWebGL removed"
    assert "function initScrollAnimations" in body, "initScrollAnimations removed"
    assert "function initPreloader" in body, "initPreloader removed"
    assert "VERTEX_SHADER" in body, "WebGL shaders removed"
    assert "FRAGMENT_SHADER" in body, "WebGL shaders removed"
    assert "import('three')" in body, "Three.js dynamic import removed"
    assert "gsap.registerPlugin" in body, "GSAP plugin registration removed"
    assert "ScrollTrigger" in body, "ScrollTrigger references removed"
    assert "new Lenis" in body, "Lenis instantiation removed"


def test_landing_js_keeps_reduced_motion_fallback():
    """The reduced-motion / no-JS fallback paths must remain so the
    page degrades cleanly when motion is suppressed.
    """
    body = H.read_text(H.LANDING_JS)
    assert "prefers-reduced-motion" in body, "reduced-motion guard removed"
    assert "pointer: fine" in body, "fine-pointer guard removed"
    assert "min-width: 1024px" in body, "desktop guard removed"


def test_landing_engine_tabs_preserved():
    """The accessibility-driven engine showcase tabs (Panel A/B/C) are
    part of the rich motion experience.
    """
    body = H.read_text(H.LANDING_JS)
    assert "initEngineTabs" in body, "engine tabs initializer removed"
    assert "data-engine-tab" in body, "engine tabs markup dependency removed"
    assert "animateMeters" in body, "similarity meter animation removed"


def test_landing_css_keeps_motion_layer():
    """CSS must keep the class hooks the motion code depends on."""
    body = H.read_text(H.LANDING_CSS)
    assert ".preloader" in body, "preloader CSS removed"
    assert ".cursor-dot" in body, "cursor-dot CSS removed"
    assert ".cursor-ring" in body, "cursor-ring CSS removed"
    assert ".hero__canvas" in body, "WebGL canvas CSS removed"
    assert ".has-webgl" in body, "has-webgl class hook removed"
    assert ".tilt-card" in body, "tilt-card class hook removed"
    assert ".magnetic" in body, "magnetic class hook removed"


# ---------------------------------------------------------------------------
# Dashboard motion (hash router, modal focus, scroll reveal)
# ---------------------------------------------------------------------------


def test_dashboard_js_keeps_hash_router():
    """The dashboard SPA relies on hash-based routing. The router code
    must still be present.
    """
    body = H.read_text(H.DASHBOARD_JS)
    assert "hashchange" in body, "hashchange listener removed"
    assert "currentPath" in body, "currentPath() removed"
    assert "VIEW_RENDERERS" in body, "VIEW_RENDERERS map removed"
    assert "renderAuth" in body, "renderAuth removed"
    assert "renderShell" in body, "renderShell removed"
    assert "renderDashboard" in body, "renderDashboard removed"
    assert "renderSearch" in body, "renderSearch removed"
    assert "renderWatchlists" in body, "renderWatchlists removed"
    assert "renderAlerts" in body, "renderAlerts removed"
    assert "renderDeadlines" in body, "renderDeadlines removed"
    assert "renderSettings" in body, "renderSettings removed"
    assert "openWatchlistModal" in body, "watchlist modal removed"


def test_dashboard_js_keeps_glassmorphism_classes():
    """Glass cards / motion classes are referenced in templates."""
    css = H.read_text(H.DASHBOARD_CSS)
    assert ".glass-card" in css, "glass-card class removed"
    assert "backdrop-filter" in css, "backdrop-filter declaration removed"
    assert ".skeleton" in css, "skeleton placeholder removed"
    assert "@keyframes shimmer" in css, "skeleton shimmer removed"
    assert "@keyframes spin" in css, "spinner keyframes removed"


def test_dashboard_html_keeps_root_mount():
    body = H.read_text(H.DASHBOARD_HTML)
    assert 'id="root"' in body
    assert 'id="toast-container"' in body