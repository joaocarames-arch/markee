"""Celery task: recalculate lifecycle deadlines for all monitored marks."""
from __future__ import annotations

from typing import Any

from sqlalchemy import delete, select

from app.models.database import AsyncSessionLocal
from app.models.lifecycle import Deadline, LifecycleEvent
from app.models.trademark import Trademark
from app.services.lifecycle_engine import LifecycleEngine
from app.tasks import celery_app, run_async


@celery_app.task(name="app.tasks.calculate_deadlines.recalculate_all")
def recalculate_all() -> dict[str, Any]:
    """Recompute renewal, grace-period and opposition deadlines for every mark.

    Existing pending deadlines are replaced so the table always reflects the
    latest computation.

    Returns:
        A summary dict with the number of deadlines written.
    """
    engine = LifecycleEngine()

    async def _run() -> dict[str, Any]:
        async with AsyncSessionLocal() as db:
            trademarks = (await db.execute(select(Trademark))).scalars().all()
            count = 0

            for trademark in trademarks:
                if not trademark.registration_date:
                    continue

                # Replace existing pending renewal/grace deadlines.
                await db.execute(
                    delete(Deadline).where(
                        Deadline.trademark_id == trademark.id,
                        Deadline.status == "pending",
                        Deadline.deadline_type.in_(["renewal", "grace_period"]),
                    )
                )
                for rule in engine.calculate_renewal_deadlines(
                    trademark.registration_date
                ):
                    db.add(
                        Deadline(
                            trademark_id=trademark.id,
                            deadline_type=rule.rule_type,
                            due_date=rule.due_date,
                            description=rule.description,
                            alert_dates=rule.alert_dates,
                            status="pending",
                        )
                    )
                    count += 1

                # Add an opposition deadline from the latest publication event.
                publication = (
                    await db.execute(
                        select(LifecycleEvent)
                        .where(
                            LifecycleEvent.trademark_id == trademark.id,
                            LifecycleEvent.event_type == "publication",
                        )
                        .order_by(LifecycleEvent.event_date.desc())
                        .limit(1)
                    )
                ).scalar_one_or_none()

                if publication is not None:
                    await db.execute(
                        delete(Deadline).where(
                            Deadline.trademark_id == trademark.id,
                            Deadline.deadline_type == "opposition",
                            Deadline.status == "pending",
                        )
                    )
                    opposition = engine.calculate_opposition_deadline(
                        publication.event_date, trademark.jurisdiction
                    )
                    db.add(
                        Deadline(
                            trademark_id=trademark.id,
                            deadline_type=opposition.rule_type,
                            due_date=opposition.due_date,
                            description=opposition.description,
                            alert_dates=opposition.alert_dates,
                            status="pending",
                        )
                    )
                    count += 1

            await db.commit()
            return {"status": "ok", "count": count}

    return run_async(_run())
