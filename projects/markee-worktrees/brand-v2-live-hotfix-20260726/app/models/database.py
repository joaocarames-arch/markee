"""Backwards-compatible database re-exports.

The canonical database wiring lives in :mod:`app.core.database`. This module
re-exports the same objects so existing imports (models, tasks, tests) keep
working through the ``app.models.database`` path.
"""
from __future__ import annotations

from app.core.database import (
    AsyncSessionLocal,
    Base,
    engine,
    get_db,
)

__all__ = ["AsyncSessionLocal", "Base", "engine", "get_db"]
