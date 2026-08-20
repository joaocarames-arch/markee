"""Transactional notification outbox.

Revision ID: 004
Revises: 003
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "004"
down_revision: str | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "notification_outbox",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("dedupe_key", sa.String(512), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("event_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("aggregate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recipient", sa.String(320), nullable=False),
        sa.Column("channel", sa.String(16), nullable=False, server_default="email"),
        sa.Column("template_key", sa.String(100), nullable=False),
        sa.Column("template_version", sa.String(32), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True)),
        sa.Column("lease_owner", sa.String(128)),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
        sa.Column("provider_message_id", sa.String(255)),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("failed_at", sa.DateTime(timezone=True)),
        sa.Column("last_error_code", sa.String(64)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint("dedupe_key", name="uq_notification_outbox_dedupe"),
        sa.CheckConstraint(
            "channel IN ('email')",
            name="ck_notification_outbox_channel_valid",
        ),
        sa.CheckConstraint(
            "event_version > 0",
            name="ck_notification_outbox_event_version_positive",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'sending', 'sent', 'dead')",
            name="ck_notification_outbox_status_valid",
        ),
        sa.CheckConstraint(
            "attempts >= 0",
            name="ck_notification_outbox_attempts_nonneg",
        ),
        sa.CheckConstraint(
            "(status = 'sending' AND lease_owner IS NOT NULL"
            " AND lease_expires_at IS NOT NULL)"
            " OR (status != 'sending' AND lease_owner IS NULL"
            " AND lease_expires_at IS NULL)",
            name="ck_notification_outbox_lease_coherent",
        ),
        sa.CheckConstraint(
            "(status = 'sent' AND sent_at IS NOT NULL)"
            " OR (status != 'sent' AND sent_at IS NULL)",
            name="ck_notification_outbox_sent_at_coherent",
        ),
        sa.CheckConstraint(
            "status != 'dead' OR failed_at IS NOT NULL",
            name="ck_notification_outbox_dead_failed_at",
        ),
        sa.CheckConstraint(
            "status NOT IN ('sent', 'dead') OR next_attempt_at IS NULL",
            name="ck_notification_outbox_terminal_no_retry",
        ),
        schema="app",
    )
    op.create_index(
        "idx_notification_outbox_claim",
        "notification_outbox",
        ["status", "next_attempt_at", "lease_expires_at"],
        schema="app",
    )


def downgrade() -> None:
    op.drop_index(
        "idx_notification_outbox_claim",
        table_name="notification_outbox",
        schema="app",
    )
    op.drop_table("notification_outbox", schema="app")
