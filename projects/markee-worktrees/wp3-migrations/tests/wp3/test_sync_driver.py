"""No-DB tests for the synchronous PostgreSQL driver used by WP3 tooling.

``scripts.drift_inventory`` converts the asyncpg DSN to a plain
``postgresql://`` URL (``_sync_dsn``) and builds a synchronous SQLAlchemy
engine for catalog inspection. SQLAlchemy resolves that scheme to the
``psycopg2`` dialect, so the driver must be importable in the tooling
environment even though the application itself is async-only (asyncpg).

These tests prove driver availability without opening any connection:
``create_engine`` imports the DBAPI module eagerly but connects lazily.
"""
from __future__ import annotations

import importlib.util

from sqlalchemy import create_engine

from scripts.drift_inventory import _sync_dsn
from scripts.target_guard import disposable_database_url


def test_psycopg2_is_importable():
    """The sync driver declared for dev tooling must be installed."""
    assert importlib.util.find_spec("psycopg2") is not None, (
        "psycopg2 (psycopg2-binary) is not installed in this environment; "
        "the drift-inventory sync engine cannot load its DBAPI"
    )


def test_sync_engine_dialect_loads_without_connecting():
    """``create_engine`` on the converted DSN must resolve the psycopg2 DBAPI.

    No connection is attempted: SQLAlchemy engines connect lazily, so this
    only exercises dialect + driver import, which is exactly what fails when
    the driver is absent.
    """
    engine = create_engine(_sync_dsn(disposable_database_url()), future=True)
    try:
        assert engine.dialect.name == "postgresql"
        assert engine.dialect.driver == "psycopg2"
    finally:
        engine.dispose()
