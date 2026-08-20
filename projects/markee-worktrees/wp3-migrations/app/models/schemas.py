"""PostgreSQL schema names used across the data layer.

Four schemas separate concerns (see docs/adr/0001-use-postgresql-schemas.md):

- ``raw``    — immutable API responses, partitioned, purgeable.
- ``core``   — normalised domain entities (trademarks, holders, ...).
- ``events`` — legal lifecycle events.
- ``app``    — application data (users, watchlists, alerts, ...).

Tests running on SQLite map every schema to ``None`` via a
``schema_translate_map`` on the engine, so the same models work everywhere.
"""
from __future__ import annotations

SCHEMA_RAW = "raw"
SCHEMA_CORE = "core"
SCHEMA_EVENTS = "events"
SCHEMA_APP = "app"

ALL_SCHEMAS: tuple[str, ...] = (SCHEMA_RAW, SCHEMA_CORE, SCHEMA_EVENTS, SCHEMA_APP)

# Translate map that collapses every schema into the default namespace.
# Used by SQLite test engines, which have no schema support.
SQLITE_SCHEMA_TRANSLATE_MAP: dict[str | None, str | None] = {
    SCHEMA_RAW: None,
    SCHEMA_CORE: None,
    SCHEMA_EVENTS: None,
    SCHEMA_APP: None,
}
