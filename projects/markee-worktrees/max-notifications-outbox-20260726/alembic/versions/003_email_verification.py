"""Email verification: add columns to ``app.users`` and create the supporting
tables (``app.email_verification_tokens`` and ``app.email_deliveries``).

Revision ID: 003
Revises: 002
Create Date: 2026-07-26

Reversible: ``downgrade`` drops the new tables and columns in the inverse order
so a ``002 → 003 → 002`` round-trip leaves the database in the same state.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Augment ``app.users`` so we can gate login on verified email.
    op.add_column(
        "users",
        sa.Column(
            "is_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        schema="app",
    )
    op.add_column(
        "users",
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        schema="app",
    )
    op.add_column(
        "users",
        sa.Column("pending_email", sa.String(255), nullable=True),
        schema="app",
    )

    # 2. Token table. ``token_hash`` is unique; the plaintext is never
    # persisted and only lives in the email body.
    op.create_table(
        "email_verification_tokens",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("app.users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("purpose", sa.String(32), nullable=False),
        sa.Column("token_hash", sa.String(128), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        schema="app",
    )
    op.create_index(
        "idx_email_verification_user",
        "email_verification_tokens",
        ["user_id"],
        schema="app",
    )
    op.create_index(
        "idx_email_verification_purpose",
        "email_verification_tokens",
        ["purpose"],
        schema="app",
    )

    # 3. Delivery audit trail.
    op.create_table(
        "email_deliveries",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("recipient", sa.String(320), nullable=False),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        schema="app",
    )
    op.create_index(
        "idx_email_deliveries_recipient",
        "email_deliveries",
        ["recipient"],
        schema="app",
    )


def downgrade() -> None:
    op.drop_index(
        "idx_email_deliveries_recipient",
        table_name="email_deliveries",
        schema="app",
    )
    op.drop_table("email_deliveries", schema="app")

    op.drop_index(
        "idx_email_verification_purpose",
        table_name="email_verification_tokens",
        schema="app",
    )
    op.drop_index(
        "idx_email_verification_user",
        table_name="email_verification_tokens",
        schema="app",
    )
    op.drop_table("email_verification_tokens", schema="app")

    op.drop_column("users", "pending_email", schema="app")
    op.drop_column("users", "verified_at", schema="app")
    op.drop_column("users", "is_verified", schema="app")
