"""Mobile button layout regressions for the landing page."""
from __future__ import annotations

from . import _helpers as H


def test_landing_uses_border_box_sizing_to_keep_buttons_inside_cards():
    css = H.read_text(H.LANDING_CSS)

    assert "box-sizing: border-box" in css
    assert "*::before" in css
    assert "*::after" in css


def test_pricing_ctas_are_constrained_inside_cards_on_mobile():
    css = H.read_text(H.LANDING_CSS)

    assert ".price-card .btn" in css
    assert "max-width: 100%" in css
    assert "align-self: stretch" in css
