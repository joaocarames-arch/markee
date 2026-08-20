"""Alert generation and multi-channel notification dispatch (email + Telegram)."""
from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timedelta, timezone
from email.message import EmailMessage

import aiosmtplib
import httpx
from jinja2 import Template
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.source_policy import get_source_policy
from app.models.alert import Alert, Notification
from app.models.source import Source
from app.models.trademark import Trademark
from app.models.user import User
from app.models.watchlist import WatchlistItem

logger = logging.getLogger(__name__)

EMAIL_TEMPLATE_HTML = """
<!DOCTYPE html>
<html lang="pt-PT">
<head><meta charset="UTF-8"><title>{{ title }}</title></head>
<body style="font-family: Arial, sans-serif; background:#08090a; color:#e8e8e8; padding:20px;">
  <div style="max-width:600px; margin:auto; background:#111214; border-radius:10px; padding:24px;">
    <h2 style="color:#35d0e0;">{{ title }}</h2>
    <p>{{ body }}</p>
    <hr style="border-color:#35d0e0; margin:20px 0;">
    <p style="font-size:12px; color:#8a8d93;">Enviado por markee — Monitorização de marcas</p>
  </div>
</body>
</html>
"""

TELEGRAM_TEMPLATE = "🔍 *{{ title }}*\n\n{{ body }}\n\n_Enviado por markee_"


async def send_telegram_alert(chat_id: str, message: str) -> None:
    """Send a one-off Telegram message via the Bot API.

    Args:
        chat_id: The recipient Telegram chat id.
        message: The Markdown-formatted message body.
    """
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        logger.warning("Telegram token not configured; skipping message to %s", chat_id)
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()


class AlertService:
    """Generate, deduplicate and dispatch alerts to users."""

    def __init__(
        self,
        db_session: AsyncSession,
        smtp_host: str = "",
        smtp_port: int = 587,
        smtp_user: str = "",
        smtp_password: str = "",
        telegram_token: str = "",
    ) -> None:
        """Initialise the service.

        Args:
            db_session: Async database session.
            smtp_host: SMTP server host (empty disables email).
            smtp_port: SMTP server port.
            smtp_user: SMTP username / from address.
            smtp_password: SMTP password.
            telegram_token: Telegram bot token (empty disables Telegram).
        """
        self.db = db_session
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.telegram_token = telegram_token

    @staticmethod
    def _normalize_uuid(
        value: str | uuid.UUID | None,
        *,
        field_name: str,
        required: bool = True,
    ) -> uuid.UUID | None:
        """Normalize a public string/UUID identifier at the service boundary."""
        if value is None:
            if required:
                raise ValueError(f"{field_name} is required")
            return None
        if isinstance(value, uuid.UUID):
            return value
        try:
            return uuid.UUID(value)
        except (AttributeError, TypeError, ValueError) as exc:
            raise ValueError(f"{field_name} must be a valid UUID") from exc

    async def is_trademark_source_denied(self, trademark_id: str | uuid.UUID | None) -> bool:
        """Return whether a trademark is rooted in a policy-denied source.

        A trademark is BPI-rooted when the source that ingested it
        (``core.sources``) is on the central deny list.

        Args:
            trademark_id: The trademark id (string or UUID), if any.

        Returns:
            ``True`` when alerts for this trademark must be suppressed.
        """
        if trademark_id is None:
            return False
        normalized_trademark_id = self._normalize_uuid(
            trademark_id, field_name="trademark_id"
        )
        assert normalized_trademark_id is not None
        source_name = (
            await self.db.execute(
                select(Source.name)
                .join(Trademark, Trademark.ingest_source_id == Source.id)
                .where(Trademark.id == normalized_trademark_id)
            )
        ).scalar_one_or_none()
        return get_source_policy().is_source_denied(source_name)

    async def generate_similarity_alert(
        self,
        user_id: str | uuid.UUID,
        watchlist_id: str | uuid.UUID | None,
        watchlist_item_id: str | uuid.UUID | None,
        trademark_id: str | uuid.UUID,
        similarity_score: float,
        phonetic_score: float,
        class_overlap_score: float,
    ) -> Alert | None:
        """Create and persist an alert for a detected similar mark.

        Args:
            user_id: Owner of the alert.
            watchlist_id: Related watchlist id, if any.
            watchlist_item_id: Related watched item id, if any.
            trademark_id: The similar trademark that triggered the alert.
            similarity_score: Textual similarity (0–100).
            phonetic_score: Phonetic similarity (0–100).
            class_overlap_score: Nice class overlap (0–100).

        Returns:
            The persisted :class:`Alert`, or ``None`` when the trademark's
            source is denied by the containment policy.
        """
        normalized_user_id = self._normalize_uuid(user_id, field_name="user_id")
        normalized_watchlist_id = self._normalize_uuid(
            watchlist_id, field_name="watchlist_id", required=False
        )
        normalized_watchlist_item_id = self._normalize_uuid(
            watchlist_item_id, field_name="watchlist_item_id", required=False
        )
        normalized_trademark_id = self._normalize_uuid(
            trademark_id, field_name="trademark_id"
        )
        assert normalized_user_id is not None
        assert normalized_trademark_id is not None

        if await self.is_trademark_source_denied(normalized_trademark_id):
            logger.warning(
                "Similarity alert suppressed for denied-source trademark %s",
                normalized_trademark_id,
            )
            return None
        trademark = await self.db.get(Trademark, normalized_trademark_id)
        item = (
            await self.db.get(WatchlistItem, normalized_watchlist_item_id)
            if normalized_watchlist_item_id
            else None
        )

        mark_text = trademark.word_mark if trademark else "Nova marca"
        watched_text = item.mark_text if item else "a sua marca"

        title = f"Marca semelhante detetada: {mark_text}"
        body = (
            f"Detetámos uma nova marca semelhante a '{watched_text}': '{mark_text}'.\n"
            f"Similaridade textual: {similarity_score:.1f} | "
            f"Fonética: {phonetic_score:.1f} | "
            f"Sobreposição de classes: {class_overlap_score:.1f}"
        )

        alert = Alert(
            user_id=normalized_user_id,
            watchlist_id=normalized_watchlist_id,
            watchlist_item_id=normalized_watchlist_item_id,
            trademark_id=normalized_trademark_id,
            alert_type="similar_filing",
            similarity_score=similarity_score,
            phonetic_score=phonetic_score,
            class_overlap_score=class_overlap_score,
            title=title,
            body=body,
        )
        self.db.add(alert)
        await self.db.commit()
        await self.db.refresh(alert)
        return alert

    async def generate_deadline_alert(
        self,
        user_id: str | uuid.UUID,
        trademark_id: str | uuid.UUID,
        deadline_type: str,
        due_date: date,
        days_remaining: int,
    ) -> Alert | None:
        """Create and persist an alert for an approaching deadline.

        Args:
            user_id: Owner of the alert.
            trademark_id: The trademark the deadline belongs to.
            deadline_type: The deadline category (e.g. ``"renewal"``).
            due_date: The deadline date.
            days_remaining: Days remaining until the deadline.

        Returns:
            The persisted :class:`Alert`, or ``None`` when the trademark's
            source is denied by the containment policy.
        """
        normalized_user_id = self._normalize_uuid(user_id, field_name="user_id")
        normalized_trademark_id = self._normalize_uuid(
            trademark_id, field_name="trademark_id"
        )
        assert normalized_user_id is not None
        assert normalized_trademark_id is not None

        if await self.is_trademark_source_denied(normalized_trademark_id):
            logger.warning(
                "Deadline alert suppressed for denied-source trademark %s",
                normalized_trademark_id,
            )
            return None
        trademark = await self.db.get(Trademark, normalized_trademark_id)
        mark_text = trademark.word_mark if trademark else "a sua marca"

        type_labels = {
            "renewal": "Renovação em breve",
            "opposition": "Prazo de oposição",
            "response_refusal": "Prazo para resposta a recusa",
            "grace_period": "Período de graça a terminar",
        }
        title = type_labels.get(deadline_type, "Prazo importante")
        body = (
            f"A marca '{mark_text}' tem um prazo importante dentro de {days_remaining} "
            f"dias ({due_date.isoformat()}). Tipo: {title}."
        )

        alert = Alert(
            user_id=normalized_user_id,
            trademark_id=normalized_trademark_id,
            alert_type=deadline_type,
            title=title,
            body=body,
        )
        self.db.add(alert)
        await self.db.commit()
        await self.db.refresh(alert)
        return alert

    async def deduplicate(
        self,
        user_id: str | uuid.UUID,
        alert_type: str,
        trademark_id: str | uuid.UUID,
        hours: int = 24,
        watchlist_id: str | uuid.UUID | None = None,
        watchlist_item_id: str | uuid.UUID | None = None,
    ) -> bool:
        """Return whether a matching alert already exists within a time window.

        Args:
            user_id: Owner of the alert.
            alert_type: The alert category.
            trademark_id: The related trademark id.
            hours: Look-back window in hours.
            watchlist_id: Related watchlist id, when deduplicating that scope.
            watchlist_item_id: Related watched item id, when deduplicating that scope.

        Returns:
            ``True`` if a duplicate already exists, ``False`` otherwise.
        """
        normalized_user_id = self._normalize_uuid(user_id, field_name="user_id")
        normalized_trademark_id = self._normalize_uuid(
            trademark_id, field_name="trademark_id"
        )
        normalized_watchlist_id = self._normalize_uuid(
            watchlist_id, field_name="watchlist_id", required=False
        )
        normalized_watchlist_item_id = self._normalize_uuid(
            watchlist_item_id, field_name="watchlist_item_id", required=False
        )
        assert normalized_user_id is not None
        assert normalized_trademark_id is not None

        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        predicates = [
            Alert.user_id == normalized_user_id,
            Alert.alert_type == alert_type,
            Alert.trademark_id == normalized_trademark_id,
            Alert.created_at >= since,
        ]
        if normalized_watchlist_id is not None:
            predicates.append(Alert.watchlist_id == normalized_watchlist_id)
        if normalized_watchlist_item_id is not None:
            predicates.append(Alert.watchlist_item_id == normalized_watchlist_item_id)

        result = await self.db.execute(select(Alert).where(and_(*predicates)))
        return result.scalars().first() is not None

    async def send_email(self, to: str, subject: str, html_body: str) -> Notification:
        """Send an HTML email and record the delivery attempt.

        Args:
            to: Recipient email address.
            subject: Email subject.
            html_body: HTML body content.

        Returns:
            The :class:`Notification` delivery record.
        """
        notification = Notification(channel="email", recipient=to, status="pending")
        self.db.add(notification)
        await self.db.commit()

        if not all([self.smtp_host, self.smtp_user, self.smtp_password]):
            logger.warning("SMTP not configured; skipping email to %s", to)
            notification.status = "skipped"
            await self.db.commit()
            return notification

        try:
            message = EmailMessage()
            message["From"] = settings.SMTP_FROM or self.smtp_user
            message["To"] = to
            message["Subject"] = subject
            message.set_content("Este alerta requer um cliente compatível com HTML.")
            message.add_alternative(html_body, subtype="html")

            await aiosmtplib.send(
                message,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.smtp_user,
                password=self.smtp_password,
                start_tls=True,
            )
            notification.status = "sent"
            notification.sent_at = datetime.now(timezone.utc)
            logger.info("Email sent to %s: %s", to, subject)
        except Exception as exc:  # noqa: BLE001 - record and continue
            notification.status = "failed"
            notification.error_message = str(exc)
            logger.exception("Failed to send email to %s", to)

        await self.db.commit()
        return notification

    async def send_telegram(self, chat_id: str, message: str) -> Notification:
        """Send a Telegram message and record the delivery attempt.

        Args:
            chat_id: Recipient Telegram chat id.
            message: Markdown-formatted message.

        Returns:
            The :class:`Notification` delivery record.
        """
        notification = Notification(channel="telegram", recipient=chat_id, status="pending")
        self.db.add(notification)
        await self.db.commit()

        if not self.telegram_token:
            logger.warning("Telegram token not configured; skipping message to %s", chat_id)
            notification.status = "skipped"
            await self.db.commit()
            return notification

        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
            notification.status = "sent"
            notification.sent_at = datetime.now(timezone.utc)
            logger.info("Telegram sent to %s", chat_id)
        except Exception as exc:  # noqa: BLE001 - record and continue
            notification.status = "failed"
            notification.error_message = str(exc)
            logger.exception("Failed to send Telegram to %s", chat_id)

        await self.db.commit()
        return notification

    async def block_alert(self, alert: Alert) -> None:
        """Drop a denied-source alert from the pending queue without sending.

        The alert is dismissed (never ``sent_at``) so the dispatcher does not
        reprocess it; no notification record is produced.

        Args:
            alert: The alert to block.
        """
        alert.is_dismissed = True
        await self.db.commit()
        logger.warning("Alert %s blocked: denied-source trademark", alert.id)

    async def dispatch_alert(self, alert: Alert) -> list[Notification]:
        """Send an alert to a user across every configured channel.

        Alerts rooted in a policy-denied source are never delivered: no
        adapter is invoked, no notification row is written and ``sent_at``
        stays unset.

        Args:
            alert: The alert to dispatch.

        Returns:
            The list of :class:`Notification` records produced.
        """
        notifications: list[Notification] = []

        if await self.is_trademark_source_denied(alert.trademark_id):
            logger.warning(
                "Dispatch refused for alert %s: denied-source trademark", alert.id
            )
            return notifications

        user = await self.db.get(User, alert.user_id)
        if not user or not user.email:
            return notifications

        html = Template(EMAIL_TEMPLATE_HTML).render(title=alert.title, body=alert.body or "")
        email_notif = await self.send_email(user.email, alert.title, html)
        email_notif.alert_id = alert.id
        notifications.append(email_notif)

        telegram_chat_id = getattr(user, "telegram_chat_id", None)
        if self.telegram_token and telegram_chat_id:
            message = Template(TELEGRAM_TEMPLATE).render(
                title=alert.title, body=alert.body or ""
            )
            tg_notif = await self.send_telegram(telegram_chat_id, message)
            tg_notif.alert_id = alert.id
            notifications.append(tg_notif)

        alert.sent_at = datetime.now(timezone.utc)
        await self.db.commit()
        return notifications

    async def get_pending_alerts(self, limit: int = 100) -> list[Alert]:
        """Fetch alerts that have not yet been dispatched.

        Args:
            limit: Maximum number of alerts to return.

        Returns:
            Undismissed, unsent alerts ordered by creation time (newest first).
        """
        result = await self.db.execute(
            select(Alert)
            .where(and_(Alert.is_dismissed.is_(False), Alert.sent_at.is_(None)))
            .order_by(Alert.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
