"""Celery task: dispatch pending alerts via email and Telegram."""
from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.database import AsyncSessionLocal
from app.services.alerts import AlertService
from app.tasks import celery_app, run_async


async def dispatch_pending(db: AsyncSession, batch_size: int = 100) -> dict[str, Any]:
    """Deliver undispatched alerts, blocking denied-source (BPI-rooted) ones.

    Blocked alerts are dismissed without invoking any delivery adapter so
    they leave the pending queue with no external effect.

    Args:
        db: An active async session; the caller owns the connection.
        batch_size: Maximum number of alerts to process in one run.

    Returns:
        A summary dict with sent/failed/blocked/total counts.
    """
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
    blocked = 0
    for alert in alerts:
        try:
            if await service.is_trademark_source_denied(alert.trademark_id):
                await service.block_alert(alert)
                blocked += 1
                continue
            await service.dispatch_alert(alert)
            sent += 1
        except Exception:  # noqa: BLE001 - one failure must not stop the batch
            failed += 1
    return {
        "status": "ok",
        "sent": sent,
        "failed": failed,
        "blocked": blocked,
        "total": len(alerts),
    }


@celery_app.task(name="app.tasks.send_alerts.dispatch_pending_alerts")
def dispatch_pending_alerts(batch_size: int = 100) -> dict[str, Any]:
    """Run :func:`dispatch_pending` on a fresh session.

    Args:
        batch_size: Maximum number of alerts to process in one run.

    Returns:
        A summary dict with sent/failed/blocked/total counts.
    """

    async def _run() -> dict[str, Any]:
        async with AsyncSessionLocal() as db:
            return await dispatch_pending(db, batch_size=batch_size)

    return run_async(_run())
