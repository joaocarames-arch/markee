"""Typed email gateway.

Only this module talks to the SMTP server. The rest of the codebase builds
:class:`EmailEnvelope` objects and hands them to ``send_envelope``. Backends are
swappable (in-memory for tests, SMTP for prod) and capped by an allowlist
parsed from settings.
"""
from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from email.message import EmailMessage
from typing import Protocol

import aiosmtplib

from app.core.config import Settings

logger = logging.getLogger(__name__)


# ── Envelope ───────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class EmailEnvelope:
    """A single outgoing message.

    Attributes:
        sender: Bare address or ``"Name <addr@host>"``.
        recipients: One or more bare addresses.
        subject: Plaintext subject; CRLF is rejected.
        text_body: Plaintext body.
        html_body: HTML body.
    """

    sender: str
    recipients: list[str]
    subject: str
    text_body: str
    html_body: str
    headers: dict[str, str] = field(default_factory=dict)


# ── Protocol ───────────────────────────────────────────────────────────────


class EmailBackend(Protocol):
    """Backend contract for the email gateway.

    ``send`` is a coroutine on every backend so call sites always ``await`` it.
    """

    async def send(self, envelope: EmailEnvelope) -> None:
        """Dispatch an envelope. Raises on permanent failures."""

    @property
    def sent(self) -> list[EmailEnvelope]:
        """Return every envelope the backend has accepted (test introspection)."""
        ...


# ── In-memory backend ──────────────────────────────────────────────────────


class InMemoryEmailGateway:
    """Collects envelopes in process. Intended for tests and dev."""

    def __init__(self) -> None:
        self._sent: list[EmailEnvelope] = []

    @property
    def sent(self) -> list[EmailEnvelope]:
        return list(self._sent)

    async def send(self, envelope: EmailEnvelope) -> None:
        self._sent.append(envelope)
        logger.info("in-memory email queued to %s", envelope.recipients)


_IN_MEMORY_SINGLETON: InMemoryEmailGateway | None = None


def get_in_memory_gateway() -> InMemoryEmailGateway:
    """Return the process-wide in-memory backend (idempotent)."""
    global _IN_MEMORY_SINGLETON
    if _IN_MEMORY_SINGLETON is None:
        _IN_MEMORY_SINGLETON = InMemoryEmailGateway()
    return _IN_MEMORY_SINGLETON


def reset_in_memory_gateway() -> None:
    """Drop the singleton — used by tests between cases."""
    global _IN_MEMORY_SINGLETON
    _IN_MEMORY_SINGLETON = None


# ── Helpers ────────────────────────────────────────────────────────────────


_NAME_RE = re.compile(r"^(?P<name>[^<>]+)\s*<(?P<addr>[^<>]+)>$")
_CONTROL_RE = re.compile(r"[\r\n\t\0]")


def _extract_bare_address(value: str) -> str:
    """Return a bare ``addr@host`` from either ``"Name <addr@host>"`` or ``"addr@host"``."""
    value = value.strip()
    match = _NAME_RE.match(value)
    if match:
        return match.group("addr").strip().lower()
    return value.strip().lower()


def _ensure_no_control_chars(*values: str) -> None:
    """Reject CRLF / TAB / NUL anywhere a header could be set."""
    for value in values:
        if _CONTROL_RE.search(value):
            raise ValueError(f"control characters not allowed in header: {value!r}")


def _ensure_valid_recipients(recipients: list[str]) -> None:
    """Reject empty or malformed recipient addresses before any backend call."""
    for recipient in recipients:
        _ensure_no_control_chars(recipient)
        bare = _extract_bare_address(recipient)
        if not re.fullmatch(r"[^@\s<>]+@[^@\s<>]+", bare):
            raise ValueError("invalid recipient address")


def _ensure_valid_sender(sender: str) -> None:
    """Reject an empty or malformed sender before constructing a message."""
    _ensure_no_control_chars(sender)
    if not re.fullmatch(r"[^@\s<>]+@[^@\s<>]+", _extract_bare_address(sender)):
        raise ValueError("invalid sender address")


def _normalised_allowlist(values: list[str]) -> set[str]:
    return {_extract_bare_address(item) for item in values if item}


# ── SMTP backend ───────────────────────────────────────────────────────────


class SMTPEmailGateway:
    """aiosmtplib-backed SMTP gateway.

    The backend enforces:
      * allowlist membership for the configured sender,
      * CRLF rejection in subject/recipient headers,
      * a hard timeout (``SMTP_TIMEOUT``),
      * optional STARTTLS (``SMTP_USE_TLS``),
      * redaction of the failing envelope before the error is raised.
    """

    def __init__(self, settings: Settings, sender: str) -> None:
        self._settings = settings
        self._sender = sender
        self._allowed = _normalised_allowlist(settings.ALLOWED_FROM_ADDRESSES)
        if _extract_bare_address(sender) not in self._allowed:
            raise ValueError(
                f"sender {sender!r} is not in ALLOWED_FROM_ADDRESSES allowlist"
            )

    @property
    def sent(self) -> list[EmailEnvelope]:
        return []

    @staticmethod
    def _build_message(envelope: EmailEnvelope) -> EmailMessage:
        _ensure_no_control_chars(envelope.subject, envelope.sender, *envelope.recipients)
        _ensure_valid_sender(envelope.sender)
        _ensure_valid_recipients(envelope.recipients)
        msg = EmailMessage()
        msg["From"] = envelope.sender
        msg["To"] = ", ".join(envelope.recipients)
        msg["Subject"] = envelope.subject
        for key, value in envelope.headers.items():
            _ensure_no_control_chars(key, value)
            msg[key] = value
        msg.set_content(envelope.text_body)
        msg.add_alternative(envelope.html_body, subtype="html")
        return msg

    async def send(self, envelope: EmailEnvelope) -> None:
        message = self._build_message(envelope)
        smtp = aiosmtplib.SMTP(
            hostname=self._settings.SMTP_HOST,
            port=self._settings.SMTP_PORT,
            use_tls=False,
        )
        try:
            async def _send() -> None:
                await smtp.connect()
                if self._settings.SMTP_USE_TLS:
                    await smtp.starttls()
                await smtp.login(self._settings.SMTP_USER, self._settings.SMTP_PASSWORD)
                await smtp.send_message(message)

            await asyncio.wait_for(_send(), timeout=self._settings.SMTP_TIMEOUT)
        except Exception as exc:  # noqa: BLE001 - re-raised with redacted context
            raise RuntimeError(
                f"smtp send failed (recipient={envelope.recipients!r}, "
                f"reason={type(exc).__name__})"
            ) from exc
        finally:
            try:
                await smtp.quit()
            except Exception:  # noqa: BLE001
                pass


# ── Factory ────────────────────────────────────────────────────────────────


def create_email_backend(settings: Settings, sender: str) -> EmailBackend:
    """Return the backend configured by ``settings.EMAIL_PROVIDER``.

    Production must supply credentials and a populated allowlist; the function
    raises ``RuntimeError`` otherwise (fail-closed).
    """
    provider = settings.EMAIL_PROVIDER.lower()
    if settings.ENVIRONMENT not in {"development", "test"} and provider != "smtp":
        raise RuntimeError("production email provider must be smtp")
    if provider == "memory":
        return get_in_memory_gateway()
    if provider == "smtp":
        if settings.ENVIRONMENT not in {"development", "test"}:
            if not settings.ALLOWED_FROM_ADDRESSES:
                raise RuntimeError(
                    "ALLOWED_FROM_ADDRESSES must be populated outside development/test"
                )
            if not (
                settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD
            ):
                raise RuntimeError("SMTP credentials required outside development/test")
        return SMTPEmailGateway(settings, sender=sender)
    raise ValueError(f"unknown EMAIL_PROVIDER: {settings.EMAIL_PROVIDER!r}")


async def send_envelope(
    settings: Settings,
    *,
    sender: str,
    recipients: list[str],
    subject: str,
    text_body: str,
    html_body: str,
    headers: dict[str, str] | None = None,
) -> EmailBackend:
    """Convenience helper: build an envelope, dispatch it, return the backend."""
    envelope = EmailEnvelope(
        sender=sender,
        recipients=list(recipients),
        subject=subject,
        text_body=text_body,
        html_body=html_body,
        headers=dict(headers or {}),
    )
    _ensure_no_control_chars(
        sender,
        subject,
        *recipients,
        *(headers or {}).keys(),
        *(headers or {}).values(),
    )
    _ensure_valid_sender(sender)
    _ensure_valid_recipients(list(recipients))
    backend = create_email_backend(settings, sender=sender)
    await backend.send(envelope)
    return backend
