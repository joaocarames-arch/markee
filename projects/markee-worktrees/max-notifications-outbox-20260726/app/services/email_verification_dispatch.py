"""Dispatch verification emails through the configured gateway.

Keeps the email envelope construction (URL allowlist, templates) out of the
HTTP router so the same flow can be triggered from Celery or admin scripts.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from app.core.config import Settings
from app.models.email_verification import EmailDeliveryRecord
from app.services.email import send_envelope
from app.services.email_templates import render_verification_email, verification_url
from app.services.email_verification import PURPOSE_REGISTER, TokenService

logger = logging.getLogger(__name__)


async def issue_and_send_verification(
    db,
    settings: Settings,
    *,
    user_id: uuid.UUID,
    email: str,
    purpose: str = PURPOSE_REGISTER,
) -> str | None:
    """Mint a new token, persist it, render the email, send it via the gateway.

    Returns:
        The plaintext token for the caller's delivery flow. Production callers
        must not persist or log this value; it is only rendered into the email.
    """
    service = TokenService(db, settings)
    plaintext = await service.issue(user_id, email, purpose=purpose)

    url = verification_url(
        base_url=settings.EMAIL_VERIFICATION_URL_BASE,
        token=plaintext,
        allowed_bases=settings.VERIFICATION_URL_ALLOWED_BASES,
    )
    text_body, html_body = render_verification_email(
        verification_url=url,
        ttl_minutes=settings.EMAIL_VERIFY_TTL_MINUTES,
    )

    # Persist the delivery attempt before dispatching so an audit row exists
    # even if the SMTP call crashes.
    record = EmailDeliveryRecord(
        recipient=email,
        subject="Verificação de email — markee",
        status="pending",
    )
    db.add(record)
    await db.flush()

    sender = settings.SMTP_FROM or "no-reply@markee.pt"
    try:
        await send_envelope(
            settings,
            sender=sender,
            recipients=[email],
            subject="Verificação de email — markee",
            text_body=text_body,
            html_body=html_body,
        )
        record.status = "sent"
        record.sent_at = datetime.now(timezone.utc)
    except Exception as exc:  # noqa: BLE001 - record failure without token data
        record.status = "failed"
        record.error_message = type(exc).__name__
        logger.warning("verification email dispatch failed for %s", email)

    await db.commit()
    return plaintext
