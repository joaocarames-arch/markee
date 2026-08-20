"""Team and TeamMember models (multi-user / agency accounts)."""
from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin
from app.models.schemas import SCHEMA_APP


class Team(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """A group of users sharing watchlists and client portfolios."""

    __tablename__ = "teams"
    __table_args__ = {"schema": SCHEMA_APP}

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app.users.id")
    )


class TeamMember(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Association between a :class:`User` and a :class:`Team`."""

    __tablename__ = "team_members"
    __table_args__ = (
        UniqueConstraint("team_id", "user_id", name="uq_team_members_team_user"),
        {"schema": SCHEMA_APP},
    )

    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app.teams.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app.users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="member")
