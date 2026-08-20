"""Unit tests for the transactional email gateway.

The gateway is the only outward-facing mail boundary. Tests focus on the
behavioural contract: typed envelope, allowed from-addresses, header-injection
rejection, fail-closed outside development/test, and an in-memory backend that
collection in tests can inspect without touching SMTP.
"""
from __future__ import annotations

import asyncio
from typing import Any

import pytest

from app.core.config import Settings
from app.services.email import (
    EmailBackend,
    EmailEnvelope,
    InMemoryEmailGateway,
    SMTPEmailGateway,
    create_email_backend,
    send_envelope,
)


# ── In-memory backend ──────────────────────────────────────────────────────


def test_in_memory_backend_records_envelope() -> None:
    backend = InMemoryEmailGateway()
    envelope = EmailEnvelope(
        sender="no-reply@markee.pt",
        recipients=["user@example.com"],
        subject="Olá",
        text_body="texto",
        html_body="<p>html</p>",
    )
    asyncio.run(backend.send(envelope))
    assert len(backend.sent) == 1
    assert backend.sent[0].subject == "Olá"
    assert backend.sent[0].recipients == ["user@example.com"]


def test_send_envelope_helper_returns_in_memory_backend() -> None:
    settings = Settings(ENVIRONMENT="development", EMAIL_PROVIDER="memory")
    backend = asyncio.run(
        send_envelope(
            settings,
            sender="no-reply@markee.pt",
            recipients=["a@example.com"],
            subject="Assunto",
            text_body="t",
            html_body="<p>h</p>",
        )
    )
    assert isinstance(backend, InMemoryEmailGateway)
    assert backend.sent[-1].subject == "Assunto"


# ── Allowed from-addresses ─────────────────────────────────────────────────


def test_create_email_backend_rejects_sender_outside_allowlist_development() -> None:
    settings = Settings(
        ENVIRONMENT="development",
        EMAIL_PROVIDER="smtp",
        SMTP_HOST="smtp.example.com",
        SMTP_PORT=587,
        SMTP_USER="user",
        SMTP_PASSWORD="pw",
        ALLOWED_FROM_ADDRESSES=["no-reply@markee.pt"],
    )
    with pytest.raises(ValueError, match="allowlist"):
        create_email_backend(settings, sender="evil@example.com")


def test_create_email_backend_accepts_allowlisted_sender() -> None:
    settings = Settings(
        ENVIRONMENT="development",
        EMAIL_PROVIDER="smtp",
        SMTP_HOST="smtp.example.com",
        SMTP_PORT=587,
        SMTP_USER="user",
        SMTP_PASSWORD="pw",
        ALLOWED_FROM_ADDRESSES=["no-reply@markee.pt"],
    )
    backend = create_email_backend(settings, sender="no-reply@markee.pt")
    assert isinstance(backend, SMTPEmailGateway)


# ── Fail-closed behaviour ──────────────────────────────────────────────────


def test_smtp_backend_fails_closed_outside_development_without_allowlist() -> None:
    """Production must refuse to start without an explicit allowlist."""
    settings = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="x" * 64,
        CORS_ORIGINS=["https://markee.pt"],
        EMAIL_PROVIDER="smtp",
        SMTP_HOST="smtp.example.com",
        SMTP_PORT=587,
        SMTP_USER="user",
        SMTP_PASSWORD="pw",
        ALLOWED_FROM_ADDRESSES=[],
    )
    with pytest.raises(RuntimeError):
        create_email_backend(settings, sender="no-reply@markee.pt")


def test_smtp_backend_fails_closed_outside_development_without_credentials() -> None:
    settings = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="x" * 64,
        CORS_ORIGINS=["https://markee.pt"],
        EMAIL_PROVIDER="smtp",
        SMTP_HOST="",
        SMTP_PORT=587,
        SMTP_USER="",
        SMTP_PASSWORD="",
        ALLOWED_FROM_ADDRESSES=["no-reply@markee.pt"],
    )
    with pytest.raises(RuntimeError):
        create_email_backend(settings, sender="no-reply@markee.pt")


# ── Header-injection protection ────────────────────────────────────────────


def test_smtp_builder_rejects_crlf_in_subject() -> None:
    settings = Settings(
        ENVIRONMENT="development",
        EMAIL_PROVIDER="smtp",
        SMTP_HOST="smtp.example.com",
        SMTP_PORT=587,
        SMTP_USER="user",
        SMTP_PASSWORD="pw",
        ALLOWED_FROM_ADDRESSES=["no-reply@markee.pt"],
        SMTP_USE_TLS=True,
        SMTP_TIMEOUT=10,
    )
    backend = SMTPEmailGateway(settings, sender="no-reply@markee.pt")
    bad = EmailEnvelope(
        sender="no-reply@markee.pt",
        recipients=["a@example.com"],
        subject="ok\r\nBcc: attacker@example.com",
        text_body="t",
        html_body="<p>h</p>",
    )
    with pytest.raises(ValueError, match="control"):
        asyncio.run(backend.send(bad))


def test_smtp_builder_rejects_crlf_in_recipient() -> None:
    settings = Settings(
        ENVIRONMENT="development",
        EMAIL_PROVIDER="smtp",
        SMTP_HOST="smtp.example.com",
        SMTP_PORT=587,
        SMTP_USER="user",
        SMTP_PASSWORD="pw",
        ALLOWED_FROM_ADDRESSES=["no-reply@markee.pt"],
        SMTP_USE_TLS=True,
        SMTP_TIMEOUT=10,
    )
    backend = SMTPEmailGateway(settings, sender="no-reply@markee.pt")
    bad = EmailEnvelope(
        sender="no-reply@markee.pt",
        recipients=["a@example.com\nBcc: attacker@example.com"],
        subject="ok",
        text_body="t",
        html_body="<p>h</p>",
    )
    with pytest.raises(ValueError, match="control"):
        asyncio.run(backend.send(bad))


def test_smtp_builder_constructs_message_with_headers() -> None:
    settings = Settings(
        ENVIRONMENT="development",
        EMAIL_PROVIDER="smtp",
        SMTP_HOST="smtp.example.com",
        SMTP_PORT=587,
        SMTP_USER="user",
        SMTP_PASSWORD="pw",
        ALLOWED_FROM_ADDRESSES=["no-reply@markee.pt"],
        SMTP_USE_TLS=True,
        SMTP_TIMEOUT=10,
    )
    backend = SMTPEmailGateway(settings, sender="no-reply@markee.pt")
    msg = backend._build_message(  # type: ignore[attr-defined]
        EmailEnvelope(
            sender="no-reply@markee.pt",
            recipients=["a@example.com"],
            subject="Olá",
            text_body="t",
            html_body="<p>h</p>",
        )
    )
    assert msg["From"] == "no-reply@markee.pt"
    assert msg["To"] == "a@example.com"
    assert msg["Subject"] == "Olá"
    # Both parts present.
    payload = msg.as_string()
    assert "text/plain" in payload
    assert "text/html" in payload


def test_smtp_send_records_error_and_redacts_token() -> None:
    """If SMTP fails, the error message must not leak the verification token."""

    class _ExplodingSMTP:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        async def connect(self) -> "_ExplodingSMTP":
            return self

        async def starttls(self) -> None:
            return None

        async def login(self, *args: Any, **kwargs: Any) -> None:
            return None

        async def send_message(self, *args: Any, **kwargs: Any) -> None:
            raise OSError("550 user unknown")

        async def quit(self) -> None:
            return None

    # monkeypatch aiosmtplib.SMTP inside the gateway module
    import app.services.email as email_mod

    monkey = pytest.MonkeyPatch()
    monkey.setattr(email_mod.aiosmtplib, "SMTP", _ExplodingSMTP)
    try:
        settings = Settings(
            ENVIRONMENT="development",
            EMAIL_PROVIDER="smtp",
            SMTP_HOST="smtp.example.com",
            SMTP_PORT=587,
            SMTP_USER="user",
            SMTP_PASSWORD="pw",
            ALLOWED_FROM_ADDRESSES=["no-reply@markee.pt"],
            SMTP_USE_TLS=True,
            SMTP_TIMEOUT=10,
        )
        backend = SMTPEmailGateway(settings, sender="no-reply@markee.pt")
        env = EmailEnvelope(
            sender="no-reply@markee.pt",
            recipients=["a@example.com"],
            subject="Verify",
            text_body="secret-token-MUST-NOT-LEAK-1234567890",
            html_body="<p>secret-token-MUST-NOT-LEAK-1234567890</p>",
        )
        with pytest.raises(RuntimeError) as exc:
            asyncio.run(backend.send(env))
        msg = str(exc.value)
        assert "secret-token-MUST-NOT-LEAK-1234567890" not in msg
    finally:
        monkey.undo()


# ── Backend protocol ──────────────────────────────────────────────────────


def test_backend_protocol_is_typed() -> None:
    backend: EmailBackend = InMemoryEmailGateway()
    assert hasattr(backend, "send")
    assert hasattr(backend, "sent")
