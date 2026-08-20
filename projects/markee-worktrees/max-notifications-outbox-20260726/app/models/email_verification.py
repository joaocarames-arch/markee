"""Email verification tokens and delivery audit records.

The token model stores only the cryptographic hash of the random secret — the
plaintext lives in the email body and never touches the database. A token has
one of two purposes (``register`` / ``email_change``); older outstanding
tokens for the same purpose are revoked when a new one is issued.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin
from app.models.schemas import SCHEMA_APP


class EmailVerificationToken(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """A single-use, hashed token that confirms an email address."""

    __tablename__ = "email_verification_tokens"
    __table_args__ = {"schema": SCHEMA_APP}

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("app.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # The address the token is meant to confirm. For ``register`` this equals
    # the account's current email; for ``email_change`` it is the new one.
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    purpose: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    # SHA-256 hex of the plaintext token.
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class EmailDeliveryRecord(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Audit trail for every send attempted by the email gateway."""

    __tablename__ = "email_deliveries"
    __table_args__ = {"schema": SCHEMA_APP}

    recipient: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
