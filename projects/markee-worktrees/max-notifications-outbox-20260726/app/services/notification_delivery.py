"""Deliver claimed alert notification rows through the typed email gateway."""
from __future__ import annotations

import logging
import re
from datetime import UTC, datetime

from app.models.notification import NotificationOutbox
from app.services.email import EmailBackend, EmailEnvelope
from app.services.notification_templates import render_alert_email
from app.services.notifications import NotificationOutboxService

logger = logging.getLogger(__name__)
_ERROR_CODE_RE = re.compile(r"^[a-z0-9_]{1,64}$")


class DeliveryError(RuntimeError):
    """Classified provider failure with a redacted machine code."""

    def __init__(self, *, code: str, retryable: bool) -> None:
        if not _ERROR_CODE_RE.fullmatch(code):
            raise ValueError("delivery error code must be a redacted identifier")
        super().__init__(code)
        self.code = code
        self.retryable = retryable


class AlertNotificationDeliveryService:
    """Render and deliver one owned outbox lease without transaction commits."""

    def __init__(
        self,
        *,
        outbox: NotificationOutboxService,
        gateway: EmailBackend,
        sender: str,
    ) -> None:
        self.outbox = outbox
        self.gateway = gateway
        self.sender = sender

    async def deliver(
        self,
        row: NotificationOutbox,
        *,
        worker_id: str,
        now: datetime | None = None,
    ) -> NotificationOutbox:
        """Deliver a claimed item and persist sent/retry/dead via its live lease."""
        now = now or datetime.now(UTC)
        owned = await self.outbox.assert_live_lease(row.id, worker_id, now)
        rendered = render_alert_email(
            owned.template_key,
            owned.template_version,
            owned.payload,
        )
        envelope = EmailEnvelope(
            sender=self.sender,
            recipients=[owned.recipient],
            subject=rendered.subject,
            text_body=rendered.text_body,
            html_body=rendered.html_body,
            headers={
                "X-Markee-Event-Type": owned.event_type,
                "X-Markee-Template": (
                    f"{owned.template_key}/{owned.template_version}"
                ),
                "X-Markee-Dedupe-Key": owned.dedupe_key,
            },
        )
        try:
            provider_message_id = await self.gateway.send(envelope)
        except DeliveryError as exc:
            failed = await self.outbox.mark_failure(
                owned.id,
                exc.code,
                worker_id,
                retryable=exc.retryable,
                now=now,
            )
            logger.warning(
                "notification delivery failed id=%s event_type=%s attempts=%s "
                "status=%s error_code=%s",
                owned.id,
                owned.event_type,
                owned.attempts,
                failed.status,
                exc.code,
            )
            return failed
        except Exception as exc:  # noqa: BLE001 - unclassified gateway errors retry
            failed = await self.outbox.mark_failure(
                owned.id,
                "gateway_error",
                worker_id,
                retryable=True,
                now=now,
            )
            logger.warning(
                "notification delivery failed id=%s event_type=%s attempts=%s "
                "status=%s error_code=gateway_error exception_type=%s",
                owned.id,
                owned.event_type,
                owned.attempts,
                failed.status,
                type(exc).__name__,
            )
            return failed

        sent = await self.outbox.mark_sent(
            owned.id,
            provider_message_id,
            worker_id,
            now=now,
        )
        logger.info(
            "notification delivered id=%s event_type=%s attempts=%s status=%s "
            "provider_message_id=%s",
            owned.id,
            owned.event_type,
            owned.attempts,
            sent.status,
            _safe_provider_id(provider_message_id),
        )
        return sent


def _safe_provider_id(value: str) -> str:
    """Return a short opaque provider id representation suitable for logs."""
    return value[:32] if re.fullmatch(r"[A-Za-z0-9._-]+", value) else "redacted"
