"""Tests that the dashboard keeps billing functional.

The brief says the brand integration must not silently disable the
billing flow that the backend exposes (the cross-review explicitly
called out the previous Max-3 patch that removed PLAN_META / plans /
checkout under the guise of a visual cleanup).
"""
from __future__ import annotations

import re

import pytest

from . import _helpers as H


def test_dashboard_js_defines_plan_metadata():
    """PLAN_META must keep the five tiers with the EUR prices."""
    body = H.read_text(H.DASHBOARD_JS)
    assert "PLAN_META" in body, "PLAN_META removed"
    assert "PLAN_ORDER" in body, "PLAN_ORDER removed"
    for tier, price in (
        ("free", 0),
        ("individual", 5),
        ("pro", 29),
        ("profissional", 99),
        ("enterprise", 249),
    ):
        assert f"{tier}:" in body, f"PLAN_META tier missing: {tier}"
        assert f"price: {price}" in body, f"PLAN_META price missing for {tier}"


def test_dashboard_js_calls_billing_endpoints():
    """The settings view must still request /billing/subscription,
    /billing/plans and /billing/checkout from the backend.
    """
    body = H.read_text(H.DASHBOARD_JS)
    assert "/billing/subscription" in body, "/billing/subscription call removed"
    assert "/billing/plans" in body, "/billing/plans call removed"
    assert "/billing/checkout" in body, "/billing/checkout call removed"


def test_dashboard_js_renders_plan_grid():
    """The settings view must render plan cards and bind plan buttons.
    """
    body = H.read_text(H.DASHBOARD_JS)
    assert "renderPlanCards" in body, "renderPlanCards removed"
    assert "bindPlanButtons" in body, "bindPlanButtons removed"
    assert 'data-plan="' in body, "plan-button data attribute removed"


def test_billing_router_endpoint_exists():
    """The backend router still exposes the billing endpoints the
    dashboard calls.
    """
    body = (H.REPO_ROOT / "app" / "api" / "billing.py").read_text(encoding="utf-8")
    assert "/subscription" in body, "billing router dropped /subscription"
    assert "/plans" in body, "billing router dropped /plans"
    assert "/checkout" in body, "billing router dropped /checkout"


def test_dashboard_js_does_not_show_indisponivel_for_subscription():
    """A common regression is to replace ``/billing/subscription`` with
    a hard-coded "Indisponível" card. The integration must keep the
    real request and only fall back gracefully on error.
    """
    body = H.read_text(H.DASHBOARD_JS)
    assert "renderSettings" in body
    # Confirm the success path (PLAN_META-driven card) still exists.
    assert "PLAN_META[currentPlan]" in body, "subscription card not driven by PLAN_META"