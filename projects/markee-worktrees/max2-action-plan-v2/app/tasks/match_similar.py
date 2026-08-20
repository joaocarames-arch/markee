"""Celery task: run similarity matching for all active watchlists."""
from __future__ import annotations

from typing import Any

from sqlalchemy import select

from app.models.database import AsyncSessionLocal
from app.models.watchlist import Watchlist, WatchlistItem
from app.services.alerts import AlertService
from app.services.similarity_engine import SimilarityEngine
from app.tasks import celery_app, run_async


@celery_app.task(name="app.tasks.match_similar.run_similarity_matching")
def run_similarity_matching() -> dict[str, Any]:
    """Compare watched marks against stored trademarks and raise alerts.

    Duplicate alerts (same user/type/trademark within the dedup window) are
    suppressed.

    Returns:
        A summary dict with the number of alerts generated.
    """

    async def _run() -> dict[str, Any]:
        async with AsyncSessionLocal() as db:
            watchlists = (
                await db.execute(
                    select(Watchlist).where(Watchlist.is_active.is_(True))
                )
            ).scalars().all()

            engine = SimilarityEngine(db)
            alert_service = AlertService(db)
            total_alerts = 0

            for watchlist in watchlists:
                items = (
                    await db.execute(
                        select(WatchlistItem).where(
                            WatchlistItem.watchlist_id == watchlist.id
                        )
                    )
                ).scalars().all()

                for item in items:
                    matches = await engine.find_similar_marks(
                        query=item.mark_text,
                        nice_classes=item.nice_classes or [],
                        threshold=watchlist.similarity_threshold,
                        limit=20,
                    )
                    for match in matches:
                        trademark_id = str(match.get("id"))
                        if await alert_service.deduplicate(
                            user_id=str(watchlist.user_id),
                            alert_type="similar_filing",
                            trademark_id=trademark_id,
                        ):
                            continue
                        await alert_service.generate_similarity_alert(
                            user_id=str(watchlist.user_id),
                            watchlist_id=str(watchlist.id),
                            watchlist_item_id=str(item.id),
                            trademark_id=trademark_id,
                            similarity_score=match.get("similarity_score", 0.0),
                            phonetic_score=match.get("phonetic_score", 0.0),
                            class_overlap_score=match.get("class_overlap_score", 0.0),
                        )
                        total_alerts += 1

            return {"status": "ok", "alerts_generated": total_alerts}

    return run_async(_run())
