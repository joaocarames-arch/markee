"""Initial migration: create all tables + pg_trgm extension + indexes.

Revision ID: 001
Revises: 
Create Date: 2026-07-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Extension pg_trgm (fuzzy search)
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # 2. Users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255)),
        sa.Column("company_name", sa.String(255)),
        sa.Column("telegram_chat_id", sa.String(64)),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("is_superuser", sa.Boolean, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    # 3. Subscriptions
    op.create_table(
        "subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stripe_customer_id", sa.String(255)),
        sa.Column("stripe_subscription_id", sa.String(255)),
        sa.Column("plan_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, default="active"),
        sa.Column("current_period_start", sa.DateTime(timezone=True)),
        sa.Column("current_period_end", sa.DateTime(timezone=True)),
        sa.Column("max_marks", sa.Integer, nullable=False, default=1),
        sa.Column("max_users", sa.Integer, nullable=False, default=1),
        sa.Column("max_clients", sa.Integer, default=0),
        sa.Column("features", postgresql.JSONB, default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    # 4. Teams
    op.create_table(
        "teams",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    # 5. Team members
    op.create_table(
        "team_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(50), nullable=False, default="member"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.UniqueConstraint("team_id", "user_id", name="uq_team_members_team_user"),
    )

    # 6. Client portfolios
    op.create_table(
        "client_portfolios",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_name", sa.String(255), nullable=False),
        sa.Column("client_email", sa.String(255)),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    # 7. Trademarks
    op.create_table(
        "trademarks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("source_id", sa.String(100), unique=True, nullable=False),
        sa.Column("application_number", sa.String(100)),
        sa.Column("application_date", sa.Date),
        sa.Column("registration_number", sa.String(100)),
        sa.Column("registration_date", sa.Date),
        sa.Column("word_mark", sa.String(500)),
        sa.Column("figurative_mark_url", sa.String(500)),
        sa.Column("status", sa.String(100)),
        sa.Column("renewal_status", sa.String(100)),
        sa.Column("nice_classes", sa.ARRAY(sa.Integer)),
        sa.Column("applicants", postgresql.JSONB),
        sa.Column("representatives", postgresql.JSONB),
        sa.Column("goods_services", sa.Text),
        sa.Column("jurisdiction", sa.String(50), nullable=False),
        sa.Column("raw_data", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    # 8. Lifecycle events
    op.create_table(
        "lifecycle_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("trademark_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("trademarks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("event_date", sa.Date, nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("raw_data", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    # 9. Deadlines
    op.create_table(
        "deadlines",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("trademark_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("trademarks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("deadline_type", sa.String(100), nullable=False),
        sa.Column("due_date", sa.Date, nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("status", sa.String(50), nullable=False, default="pending"),
        sa.Column("alert_dates", sa.ARRAY(sa.Date)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    # 10. Watchlists
    op.create_table(
        "watchlists",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("teams.id", ondelete="SET NULL")),
        sa.Column("client_portfolio_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("client_portfolios.id", ondelete="SET NULL")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("similarity_threshold", sa.Integer, nullable=False, default=80),
        sa.Column("phonetic_weight", sa.Float, default=0.3),
        sa.Column("class_weight", sa.Float, default=0.2),
        sa.Column("nice_classes_filter", sa.ARRAY(sa.Integer)),
        sa.Column("jurisdictions", sa.ARRAY(sa.String), default=["EUIPO", "INPI"]),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    # 11. Watchlist items
    op.create_table(
        "watchlist_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("watchlist_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("watchlists.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mark_text", sa.String(500), nullable=False),
        sa.Column("nice_classes", sa.ARRAY(sa.Integer)),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    # 12. Alerts
    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("watchlist_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("watchlists.id", ondelete="SET NULL")),
        sa.Column("watchlist_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("watchlist_items.id", ondelete="SET NULL")),
        sa.Column("trademark_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("trademarks.id", ondelete="SET NULL")),
        sa.Column("alert_type", sa.String(50), nullable=False),
        sa.Column("similarity_score", sa.Float),
        sa.Column("phonetic_score", sa.Float),
        sa.Column("class_overlap_score", sa.Float),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("body", sa.Text),
        sa.Column("is_read", sa.Boolean, default=False),
        sa.Column("is_dismissed", sa.Boolean, default=False),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    # 13. Alert deliveries
    op.create_table(
        "alert_deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("alert_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("alerts.id", ondelete="CASCADE"), nullable=True),
        sa.Column("channel", sa.String(50), nullable=False),
        sa.Column("recipient", sa.Text, nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("error_message", sa.Text),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    # 14. Prospection opportunities
    op.create_table(
        "prospection_opportunities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("trademark_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("trademarks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("opportunity_type", sa.String(50), nullable=False),
        sa.Column("holder_name", sa.String(500)),
        sa.Column("holder_type", sa.String(50)),
        sa.Column("holder_district", sa.String(100)),
        sa.Column("holder_cae", sa.String(50)),
        sa.Column("nice_classes", sa.ARRAY(sa.Integer)),
        sa.Column("expiry_date", sa.Date),
        sa.Column("score", sa.Float),
        sa.Column("is_exported", sa.Boolean, default=False),
        sa.Column("exported_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    # 15. API keys (Pro+)
    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("key_hash", sa.String(255), unique=True, nullable=False),
        sa.Column("name", sa.String(255)),
        sa.Column("scopes", sa.ARRAY(sa.String(100))),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    # Indexes
    op.execute("CREATE INDEX idx_trademarks_wordmark ON trademarks USING gin (word_mark gin_trgm_ops)")
    op.create_index("idx_trademarks_jurisdiction", "trademarks", ["jurisdiction"])
    op.create_index("idx_lifecycle_events_trademark", "lifecycle_events", ["trademark_id", "event_date"])
    op.create_index("idx_deadlines_due_date", "deadlines", ["due_date", "status"])
    op.create_index("idx_alerts_user_unread", "alerts", ["user_id", "is_dismissed", "created_at"])
    op.create_index("idx_alerts_composite_score", "alerts", ["watchlist_id", "similarity_score"])
    op.create_index("idx_prospection_score", "prospection_opportunities", ["opportunity_type", "score"])


def downgrade() -> None:
    op.drop_table("api_keys")
    op.drop_table("prospection_opportunities")
    op.drop_table("alert_deliveries")
    op.drop_table("alerts")
    op.drop_table("watchlist_items")
    op.drop_table("watchlists")
    op.drop_table("deadlines")
    op.drop_table("lifecycle_events")
    op.drop_table("trademarks")
    op.drop_table("client_portfolios")
    op.drop_table("team_members")
    op.drop_table("teams")
    op.drop_table("subscriptions")
    op.drop_table("users")
