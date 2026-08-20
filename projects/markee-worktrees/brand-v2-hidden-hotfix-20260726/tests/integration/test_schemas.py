"""Integration tests for the four-schema layout (raw/core/events/app).

Metadata-level assertions always run. Live-database assertions run against a
real PostgreSQL (docker compose ``db`` service, or ``MARKEE_TEST_DATABASE_URL``)
and are skipped when no PostgreSQL is reachable or migrations have not been
applied.
"""
from __future__ import annotations

import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

import app.models  # noqa: F401 - register every table on the metadata
from app.models.database import Base
from app.models.schemas import ALL_SCHEMAS

POSTGRES_URL = os.environ.get(
    "MARKEE_TEST_DATABASE_URL",
    "postgresql+asyncpg://markee:markee_dev@localhost:5432/markee",
)

# The authoritative table→schema layout (see docs/SCHEMA_DESIGN.md).
EXPECTED_TABLES: dict[str, set[str]] = {
    "raw": {"api_responses"},
    "core": {
        "trademarks",
        "trademark_versions",
        "sources",
        "source_runs",
        "holders",
        "representatives",
        "trademark_holders",
        "trademark_representatives",
        "nice_classes",
        "goods_services",
        "documents",
    },
    "events": {"lifecycle_events"},
    "app": {
        "users",
        "subscriptions",
        "teams",
        "team_members",
        "client_portfolios",
        "watchlists",
        "watchlist_items",
        "alerts",
        "alert_deliveries",
        "prospection_opportunities",
        "deadlines",
        "review_queue",
    },
}


class TestMetadataSchemas:
    """Model-level checks that hold on any backend."""

    def test_every_table_lives_in_a_named_schema(self):
        for table in Base.metadata.tables.values():
            assert table.schema in ALL_SCHEMAS, (
                f"table {table.name!r} has schema {table.schema!r}; "
                f"expected one of {ALL_SCHEMAS}"
            )

    def test_expected_tables_are_mapped(self):
        mapped = set(Base.metadata.tables)
        for schema, tables in EXPECTED_TABLES.items():
            for table in tables:
                assert f"{schema}.{table}" in mapped, f"{schema}.{table} is not mapped"

    def test_trademarks_confidence_and_provenance_columns(self):
        trademarks = Base.metadata.tables["core.trademarks"]
        for column in ("confidence_score", "update_date", "ingest_source_id"):
            assert column in trademarks.c

    def test_lifecycle_events_provenance_columns(self):
        events = Base.metadata.tables["events.lifecycle_events"]
        for column in (
            "deadline_date",
            "source_reference",
            "page_number",
            "source_excerpt",
            "confidence_score",
        ):
            assert column in events.c

    def test_raw_api_responses_is_partition_ready(self):
        raw = Base.metadata.tables["raw.api_responses"]
        # Partitioned tables must embed the partition key in the primary key.
        pk_columns = {column.name for column in raw.primary_key.columns}
        assert pk_columns == {"id", "created_at"}
        assert raw.kwargs.get("postgresql_partition_by") == "RANGE (created_at)"


async def _connect_or_skip():
    """Return a connected engine to the live PostgreSQL, or skip the test."""
    engine = create_async_engine(POSTGRES_URL, pool_pre_ping=True)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        await engine.dispose()
        pytest.skip("PostgreSQL is not reachable; skipping live schema checks")
    return engine


class TestLivePostgresSchemas:
    """Checks against the migrated docker-compose database."""

    @pytest.mark.asyncio
    async def test_all_four_schemas_exist(self):
        engine = await _connect_or_skip()
        try:
            async with engine.connect() as conn:
                rows = await conn.execute(
                    text(
                        "SELECT schema_name FROM information_schema.schemata "
                        "WHERE schema_name IN ('raw', 'core', 'events', 'app')"
                    )
                )
                found = {row[0] for row in rows}
            if not found:
                pytest.skip("Schemas not present; migration 002 not applied yet")
            assert found == set(ALL_SCHEMAS)
        finally:
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_each_schema_has_expected_tables(self):
        engine = await _connect_or_skip()
        try:
            async with engine.connect() as conn:
                rows = await conn.execute(
                    text(
                        "SELECT table_schema, table_name FROM information_schema.tables "
                        "WHERE table_schema IN ('raw', 'core', 'events', 'app')"
                    )
                )
                found: dict[str, set[str]] = {}
                for schema, table in rows:
                    found.setdefault(schema, set()).add(table)
            if not found:
                pytest.skip("Schemas not present; migration 002 not applied yet")
            for schema, expected in EXPECTED_TABLES.items():
                missing = expected - found.get(schema, set())
                assert not missing, f"missing tables in {schema}: {sorted(missing)}"
        finally:
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_raw_api_responses_is_partitioned(self):
        engine = await _connect_or_skip()
        try:
            async with engine.connect() as conn:
                partitioned = (
                    await conn.execute(
                        text(
                            "SELECT COUNT(*) FROM pg_partitioned_table pt "
                            "JOIN pg_class c ON c.oid = pt.partrelid "
                            "JOIN pg_namespace n ON n.oid = c.relnamespace "
                            "WHERE n.nspname = 'raw' AND c.relname = 'api_responses'"
                        )
                    )
                ).scalar_one()
                partitions = (
                    await conn.execute(
                        text(
                            "SELECT COUNT(*) FROM pg_inherits i "
                            "JOIN pg_class p ON p.oid = i.inhparent "
                            "JOIN pg_namespace n ON n.oid = p.relnamespace "
                            "WHERE n.nspname = 'raw' AND p.relname = 'api_responses'"
                        )
                    )
                ).scalar_one()
            if partitioned == 0:
                pytest.skip("raw.api_responses not present; migration 002 not applied yet")
            assert partitioned == 1
            if partitions == 0:
                # Monthly partitions are created on demand by
                # app.services.raw_responses.ensure_month_partition; a freshly
                # migrated database has none until the first ingestion runs.
                pytest.skip("no monthly partitions yet; created on demand at first ingest")
        finally:
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_trigram_indexes_exist(self):
        engine = await _connect_or_skip()
        try:
            async with engine.connect() as conn:
                rows = await conn.execute(
                    text(
                        "SELECT indexname FROM pg_indexes "
                        "WHERE schemaname = 'core' "
                        "AND indexname IN ('idx_holders_name_trgm', 'idx_reps_name_trgm')"
                    )
                )
                found = {row[0] for row in rows}
            if not found:
                pytest.skip("Indexes not present; migration 002 not applied yet")
            assert found == {"idx_holders_name_trgm", "idx_reps_name_trgm"}
        finally:
            await engine.dispose()
