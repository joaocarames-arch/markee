"""Data infrastructure: raw/core/events/app schemas + normalised entities.

- Creates the four PostgreSQL schemas (see docs/adr/0001-use-postgresql-schemas.md).
- Moves existing tables into their schema (users→app, trademarks→core,
  lifecycle_events→events, ...).
- Creates the new core tables (sources, source_runs, trademark_versions,
  holders, representatives, N:M links, nice_classes, goods_services,
  documents), the partitioned raw.api_responses and app.review_queue.
- Adds confidence/provenance columns to trademarks and lifecycle_events.

Revision ID: 002
Revises: 001
Create Date: 2026-07-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Existing tables and their destination schemas.
_APP_TABLES = (
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
    "api_keys",
    "deadlines",
)
_CORE_TABLES = ("trademarks",)
_EVENTS_TABLES = ("lifecycle_events",)


def upgrade() -> None:
    # 1. Schemas + extensions.
    for schema in ("raw", "core", "events", "app"):
        op.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    # pgvector is optional (postgres:15-alpine ships without it); reserved for
    # future embedding search, so its absence must not block the migration.
    op.execute(
        """
        DO $$
        BEGIN
            CREATE EXTENSION IF NOT EXISTS vector;
        EXCEPTION WHEN OTHERS THEN
            RAISE NOTICE 'pgvector extension not available; skipping';
        END $$;
        """
    )

    # 2. Move existing tables into their schemas (indexes/FKs move along).
    for table in _APP_TABLES:
        op.execute(f"ALTER TABLE public.{table} SET SCHEMA app")
    for table in _CORE_TABLES:
        op.execute(f"ALTER TABLE public.{table} SET SCHEMA core")
    for table in _EVENTS_TABLES:
        op.execute(f"ALTER TABLE public.{table} SET SCHEMA events")

    # 3. core.sources + core.source_runs (before trademarks gains its FK).
    op.create_table(
        "sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(64), nullable=False, unique=True),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("base_url", sa.Text),
        sa.Column("auth_method", sa.String(32)),
        sa.Column("is_enabled", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("priority", sa.Integer, nullable=False, server_default=sa.text("1")),
        sa.Column("config_snapshot", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.CheckConstraint("priority >= 1", name="ck_sources_priority"),
        schema="core",
    )

    op.create_table(
        "source_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("core.sources.id"), nullable=False),
        sa.Column("run_type", sa.String(32), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("items_processed", sa.Integer, server_default=sa.text("0")),
        sa.Column("items_new", sa.Integer, server_default=sa.text("0")),
        sa.Column("items_updated", sa.Integer, server_default=sa.text("0")),
        sa.Column("items_failed", sa.Integer, server_default=sa.text("0")),
        sa.Column("error_message", sa.Text),
        sa.Column("cursor_value", sa.String(128)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        schema="core",
    )
    op.create_index("idx_runs_source_id", "source_runs", ["source_id"], schema="core")
    op.create_index("idx_runs_status", "source_runs", ["status"], schema="core")

    # 4. New provenance/confidence columns on moved tables.
    op.add_column("trademarks", sa.Column("update_date", sa.DateTime(timezone=True)), schema="core")
    op.add_column("trademarks", sa.Column("confidence_score", sa.Float), schema="core")
    op.add_column(
        "trademarks",
        sa.Column(
            "ingest_source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("core.sources.id", ondelete="SET NULL"),
        ),
        schema="core",
    )
    op.create_index("idx_trademarks_update_date", "trademarks", ["update_date"], schema="core")

    op.add_column("lifecycle_events", sa.Column("deadline_date", sa.Date), schema="events")
    op.add_column("lifecycle_events", sa.Column("source_reference", sa.String(128)), schema="events")
    op.add_column("lifecycle_events", sa.Column("page_number", sa.Integer), schema="events")
    op.add_column("lifecycle_events", sa.Column("source_excerpt", sa.Text), schema="events")
    op.add_column("lifecycle_events", sa.Column("confidence_score", sa.Float), schema="events")
    op.create_index("idx_events_deadline_date", "lifecycle_events", ["deadline_date"], schema="events")
    op.create_index("idx_events_event_type", "lifecycle_events", ["event_type"], schema="events")
    op.create_index(
        "idx_events_trademark_type", "lifecycle_events", ["trademark_id", "event_type"], schema="events"
    )

    # 5. Version history (ADR 0002: never delete, always append).
    op.create_table(
        "trademark_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("trademark_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("core.trademarks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_number", sa.Integer, nullable=False),
        sa.Column("snapshot", postgresql.JSONB, nullable=False),
        sa.Column("diff_from_previous", postgresql.JSONB),
        sa.Column("change_source", sa.String(64), nullable=False),
        sa.Column("change_type", sa.String(32), nullable=False),
        sa.Column("raw_response_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("trademark_id", "version_number", name="uq_versions_trademark_version"),
        schema="core",
    )
    op.create_index("idx_versions_trademark_id", "trademark_versions", ["trademark_id"], schema="core")

    # 6. Holders / representatives + N:M links.
    op.create_table(
        "holders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("source_id", sa.String(64), nullable=False),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("address", sa.Text),
        sa.Column("country", sa.String(2)),
        sa.Column("type", sa.String(32)),
        sa.Column("raw_data", postgresql.JSONB),
        sa.Column("confidence_score", sa.Float),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.CheckConstraint("type IN ('natural', 'legal')", name="ck_holders_type"),
        schema="core",
    )
    op.create_index("idx_holders_source_id", "holders", ["source_id"], schema="core")
    op.execute(
        "CREATE INDEX idx_holders_name_trgm ON core.holders USING GIN (name gin_trgm_ops)"
    )

    op.create_table(
        "representatives",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("source_id", sa.String(64), nullable=False),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("address", sa.Text),
        sa.Column("country", sa.String(2)),
        sa.Column("type", sa.String(32)),
        sa.Column("raw_data", postgresql.JSONB),
        sa.Column("confidence_score", sa.Float),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.CheckConstraint("type IN ('natural', 'legal', 'association')", name="ck_representatives_type"),
        schema="core",
    )
    op.create_index("idx_reps_source_id", "representatives", ["source_id"], schema="core")
    op.execute(
        "CREATE INDEX idx_reps_name_trgm ON core.representatives USING GIN (name gin_trgm_ops)"
    )

    op.create_table(
        "trademark_holders",
        sa.Column("trademark_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("core.trademarks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("holder_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("core.holders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(32), nullable=False, server_default=sa.text("'applicant'")),
        sa.Column("since_date", sa.Date),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.PrimaryKeyConstraint("trademark_id", "holder_id", "role"),
        schema="core",
    )

    op.create_table(
        "trademark_representatives",
        sa.Column("trademark_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("core.trademarks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("representative_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("core.representatives.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(32), nullable=False, server_default=sa.text("'representative'")),
        sa.Column("since_date", sa.Date),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.PrimaryKeyConstraint("trademark_id", "representative_id"),
        schema="core",
    )

    # 7. Nice classes + goods/services.
    op.create_table(
        "nice_classes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("class_number", sa.Integer, nullable=False, unique=True),
        sa.Column("description_pt", sa.Text),
        sa.Column("description_en", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.CheckConstraint("class_number >= 1 AND class_number <= 45", name="ck_nice_class_number"),
        schema="core",
    )

    op.create_table(
        "goods_services",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("trademark_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("core.trademarks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("nice_class_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("core.nice_classes.id"), nullable=False),
        sa.Column("term", sa.Text, nullable=False),
        sa.Column("language", sa.String(8), nullable=False, server_default=sa.text("'pt'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        schema="core",
    )
    op.create_index("idx_gs_trademark_id", "goods_services", ["trademark_id"], schema="core")

    # 8. Documents.
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("trademark_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("core.trademarks.id")),
        sa.Column("document_type", sa.String(64), nullable=False),
        sa.Column("source_url", sa.Text),
        sa.Column("storage_path", sa.Text),
        sa.Column("file_hash", sa.String(64)),
        sa.Column("publication_date", sa.Date),
        sa.Column("language", sa.String(8), server_default=sa.text("'pt'")),
        sa.Column("metadata", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        schema="core",
    )
    op.create_index("idx_docs_trademark_id", "documents", ["trademark_id"], schema="core")
    op.create_index("idx_docs_file_hash", "documents", ["file_hash"], schema="core")

    # 9. raw.api_responses — partitioned by month on created_at. PostgreSQL
    # requires the partition key inside the PK, hence (id, created_at).
    op.execute(
        """
        CREATE TABLE raw.api_responses (
            id                  UUID NOT NULL DEFAULT gen_random_uuid(),
            source_id           UUID NOT NULL,
            source_run_id       UUID,
            endpoint            TEXT NOT NULL,
            request_params      JSONB,
            response_status     INTEGER,
            response_headers    JSONB,
            response_body       JSONB,
            response_size_bytes INTEGER,
            duration_ms         INTEGER,
            error_message       TEXT,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (id, created_at)
        ) PARTITION BY RANGE (created_at)
        """
    )
    op.execute(
        "CREATE TABLE raw.api_responses_2026_07 PARTITION OF raw.api_responses "
        "FOR VALUES FROM ('2026-07-01') TO ('2026-08-01')"
    )
    op.execute(
        "CREATE TABLE raw.api_responses_2026_08 PARTITION OF raw.api_responses "
        "FOR VALUES FROM ('2026-08-01') TO ('2026-09-01')"
    )
    op.execute(
        "CREATE INDEX idx_raw_source_created ON raw.api_responses (source_id, created_at DESC)"
    )

    # 10. app.review_queue — uncertain extraction results awaiting review.
    op.create_table(
        "review_queue",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("item_type", sa.String(64), nullable=False),
        sa.Column("payload", postgresql.JSONB, nullable=False),
        sa.Column("reason", sa.Text),
        sa.Column("confidence_score", sa.Float),
        sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("trademark_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("core.trademarks.id", ondelete="SET NULL")),
        sa.Column("document_id", postgresql.UUID(as_uuid=True)),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("resolved_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("app.users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        schema="app",
    )
    op.create_index(
        "idx_review_queue_status", "review_queue", ["status", "created_at"], schema="app"
    )


def downgrade() -> None:
    op.drop_table("review_queue", schema="app")
    op.execute("DROP TABLE raw.api_responses")
    op.drop_table("documents", schema="core")
    op.drop_table("goods_services", schema="core")
    op.drop_table("nice_classes", schema="core")
    op.drop_table("trademark_representatives", schema="core")
    op.drop_table("trademark_holders", schema="core")
    op.drop_table("representatives", schema="core")
    op.drop_table("holders", schema="core")
    op.drop_table("trademark_versions", schema="core")

    op.drop_index("idx_events_trademark_type", table_name="lifecycle_events", schema="events")
    op.drop_index("idx_events_event_type", table_name="lifecycle_events", schema="events")
    op.drop_index("idx_events_deadline_date", table_name="lifecycle_events", schema="events")
    op.drop_column("lifecycle_events", "confidence_score", schema="events")
    op.drop_column("lifecycle_events", "source_excerpt", schema="events")
    op.drop_column("lifecycle_events", "page_number", schema="events")
    op.drop_column("lifecycle_events", "source_reference", schema="events")
    op.drop_column("lifecycle_events", "deadline_date", schema="events")

    op.drop_index("idx_trademarks_update_date", table_name="trademarks", schema="core")
    op.drop_column("trademarks", "ingest_source_id", schema="core")
    op.drop_column("trademarks", "confidence_score", schema="core")
    op.drop_column("trademarks", "update_date", schema="core")

    op.drop_table("source_runs", schema="core")
    op.drop_table("sources", schema="core")

    for table in _EVENTS_TABLES:
        op.execute(f"ALTER TABLE events.{table} SET SCHEMA public")
    for table in _CORE_TABLES:
        op.execute(f"ALTER TABLE core.{table} SET SCHEMA public")
    for table in _APP_TABLES:
        op.execute(f"ALTER TABLE app.{table} SET SCHEMA public")

    for schema in ("raw", "core", "events", "app"):
        op.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
