"""Unit tests for the email templates (PT-PT, text+HTML, accessible)."""
from __future__ import annotations

import re

from app.services.email_templates import (
    render_verification_email,
    verification_url,
)


def test_render_verification_email_returns_text_and_html() -> None:
    text, html = render_verification_email(
        verification_url="https://markee.pt/verify?token=abc",
        ttl_minutes=60,
    )
    assert isinstance(text, str)
    assert isinstance(html, str)
    assert len(text) > 0
    assert len(html) > 0


def test_html_template_is_pt_pt_and_accessible() -> None:
    _, html = render_verification_email(
        verification_url="https://markee.pt/verify?token=abc",
        ttl_minutes=60,
    )
    assert re.search(r'<html\b[^>]*lang="pt-PT"', html) is not None
    assert "charset" in html.lower()
    assert "verifica" in html.lower() or "verificar" in html.lower()
    # No superlative claims.
    forbidden = ["melhor", "garantimos", "100%", "imediato", "instantâneo"]
    for word in forbidden:
        assert word.lower() not in html.lower()


def test_text_template_contains_verification_link() -> None:
    text, _ = render_verification_email(
        verification_url="https://markee.pt/verify?token=abc",
        ttl_minutes=60,
    )
    assert "https://markee.pt/verify?token=abc" in text


def test_verification_url_blocks_unknown_base() -> None:
    try:
        verification_url(
            base_url="https://attacker.example/verify",
            token="abc",
            allowed_bases=["https://markee.pt"],
        )
    except ValueError:
        return
    raise AssertionError("expected ValueError for unknown base")


def test_verification_url_accepts_allowed_base() -> None:
    url = verification_url(
        base_url="https://markee.pt",
        token="abc",
        allowed_bases=["https://markee.pt"],
    )
    assert url.startswith("https://markee.pt/")
    assert "abc" in url
