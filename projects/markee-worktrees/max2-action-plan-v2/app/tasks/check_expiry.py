"""Celery task: raise alerts for trademarks with approaching deadlines."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy import and_, select

from app.core.config import settings
from app.models.database import AsyncSessionLocal
from app.models.lifecycle import Deadline
from app.models.trademark import Trademark
from app.models.watchlist import Watchlist, WatchlistItem
from app.services.alerts import AlertService
from app.tasks import celery_app, run_async


@celery_app.task(name="app.tasks.check_expiry.check_all_expiring")
def check_all_expiring(days_ahead: int = 30) -> dict[str, Any]:
    """Find deadlines within ``days_ahead`` days and raise deadline alerts.

    Each deadline is matched to a watched mark (by text) to determine the
    owning user; duplicate alerts are suppressed.

    Args:
        days_ahead: The look-ahead window in days.

    Returns:
        A summary dict with the number of deadlines checked and alerts raised.
    """

    async def _run() -> dict[str, Any]:
        async with AsyncSessionLocal() as db:
            today = date.today()
            horizon = today + timedelta(days=days_ahead)
            deadlines = (
                await db.execute(
                    select(Deadline).where(
                        and_(
                            Deadline.due_date <= horizon,
                            Deadline.due_date >= today,
                            Deadline.status == "pending",
                        )
                    )
                )
            ).scalars().all()

            service = AlertService(
                db,
                smtp_host=settings.SMTP_HOST,
                smtp_port=settings.SMTP_PORT,
                smtp_user=settings.SMTP_USER,
                smtp_password=settings.SMTP_PASSWORD,
            )

            alerts_generated = 0
            for deadline in deadlines:
                trademark = await db.get(Trademark, deadline.trademark_id)
                if trademark is None or not trademark.word_mark:
                    continue

                # Find a watched item (and its owning watchlist) for this mark.
                row = (
                    await db.execute(
                        select(WatchlistItem, Watchlist)
                        .join(Watchlist, WatchlistItem.watchlist_id == Watchlist.id)
                        .where(WatchlistItem.mark_text.ilike(f"%{trademark.word_mark}%"))
                        .limit(1)
                    )
                ).first()
                if row is None:
                    continue
                _item, watchlist = row

                if await service.deduplicate(
                    user_id=str(watchlist.user_id),
                    alert_type=deadline.deadline_type,
                    trademark_id=str(trademark.id),
                ):
                    continue

                await service.generate_deadline_alert(
                    user_id=str(watchlist.user_id),
                    trademark_id=str(trademark.id),
                    deadline_type=deadline.deadline_type,
                    due_date=deadline.due_date,
                    days_remaining=(deadline.due_date - today).days,
                )
                alerts_generated += 1

            return {
                "status": "ok",
                "deadlines_checked": len(deadlines),
                "alerts_generated": alerts_generated,
            }

    return run_async(_run())
