"""Celery task: dispatch pending alerts via email and Telegram."""
from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.models.database import AsyncSessionLocal
from app.services.alerts import AlertService
from app.tasks import celery_app, run_async


@celery_app.task(name="app.tasks.send_alerts.dispatch_pending_alerts")
def dispatch_pending_alerts(batch_size: int = 100) -> dict[str, Any]:
    """Fetch undispatched alerts and deliver them over configured channels.

    Args:
        batch_size: Maximum number of alerts to process in one run.

    Returns:
        A summary dict with sent/failed/total counts.
    """

    async def _run() -> dict[str, Any]:
        async with AsyncSessionLocal() as db:
            service = AlertService(
                db,
                smtp_host=settings.SMTP_HOST,
                smtp_port=settings.SMTP_PORT,
                smtp_user=settings.SMTP_USER,
                smtp_password=settings.SMTP_PASSWORD,
                telegram_token=settings.TELEGRAM_BOT_TOKEN,
            )
            alerts = await service.get_pending_alerts(limit=batch_size)
            sent = 0
            failed = 0
            for alert in alerts:
                try:
                    await service.dispatch_alert(alert)
                    sent += 1
                except Exception:  # noqa: BLE001 - one failure must not stop the batch
                    failed += 1
            return {"status": "ok", "sent": sent, "failed": failed, "total": len(alerts)}

    return run_async(_run())
