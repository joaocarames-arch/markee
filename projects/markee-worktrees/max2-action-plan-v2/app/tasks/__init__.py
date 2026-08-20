"""Celery application and task registration for markee.

Also exposes :func:`run_async`, a small helper that lets the synchronous Celery
task bodies drive the project's async services and database sessions.
"""
from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any, TypeVar

from celery import Celery
from celery.signals import worker_ready

from app.core.config import settings

celery_app = Celery(
    "markee",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.poll_euipo",
        "app.tasks.parse_bpi",
        "app.tasks.calculate_deadlines",
        "app.tasks.match_similar",
        "app.tasks.send_alerts",
        "app.tasks.check_expiry",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Lisbon",
    enable_utc=True,
    beat_schedule={
        "poll-euipo-6h": {
            "task": "app.tasks.poll_euipo.poll_recent_changes",
            "schedule": 21600.0,  # every 6 hours
        },
        "parse-bpi-daily": {
            "task": "app.tasks.parse_bpi.download_and_parse",
            "schedule": 86400.0,  # daily
        },
        "calculate-deadlines-hourly": {
            "task": "app.tasks.calculate_deadlines.recalculate_all",
            "schedule": 3600.0,  # hourly
        },
        "match-similar-hourly": {
            "task": "app.tasks.match_similar.run_similarity_matching",
            "schedule": 3600.0,  # hourly
        },
        "send-alerts-every-15min": {
            "task": "app.tasks.send_alerts.dispatch_pending_alerts",
            "schedule": 900.0,  # every 15 minutes
        },
        "check-expiry-weekly": {
            "task": "app.tasks.check_expiry.check_all_expiring",
            "schedule": 604800.0,  # weekly
        },
    },
)

_T = TypeVar("_T")


def run_async(coro: Coroutine[Any, Any, _T]) -> _T:
    """Run an async coroutine to completion from a synchronous Celery task.

    A dedicated event loop is created and torn down for each invocation, which
    keeps asyncpg connections bound to a single, well-defined loop.

    Args:
        coro: The coroutine to execute.

    Returns:
        The coroutine's result.
    """
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        loop.close()
        asyncio.set_event_loop(None)


@worker_ready.connect
def on_worker_ready(sender: Any, **kwargs: Any) -> None:
    """Log a message once the Celery worker is ready."""
    print("markee Celery worker ready")
