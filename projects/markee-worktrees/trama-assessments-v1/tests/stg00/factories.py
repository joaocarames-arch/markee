"""Row factories shared by the STG00 BPI containment tests."""
from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lifecycle import LifecycleEvent
from app.models.trademark import Trademark
from app.models.user import User
from app.services.ingestion import get_or_create_source


async def make_trademark(
    session: AsyncSession,
    *,
    application_number: str = "N-100001",
    source_name: str | None = None,
    registration_date: date | None = None,
    jurisdiction: str = "PT",
    word_mark: str = "MARCA TESTE",
) -> Trademark:
    """Create a trademark, optionally linked to a named ingest source."""
    ingest_source_id = None
    if source_name is not None:
        source = await get_or_create_source(session, source_name)
        ingest_source_id = source.id
    trademark = Trademark(
        source_id=f"{jurisdiction}-{application_number}-{uuid.uuid4().hex[:8]}",
        application_number=application_number,
        word_mark=word_mark,
        jurisdiction=jurisdiction,
        registration_date=registration_date,
        ingest_source_id=ingest_source_id,
    )
    session.add(trademark)
    await session.flush()
    return trademark


async def make_publication_event(
    session: AsyncSession,
    trademark: Trademark,
    *,
    source: str = "BPI",
    event_date: date = date(2026, 7, 1),
) -> LifecycleEvent:
    """Create a publication lifecycle event for a trademark."""
    event = LifecycleEvent(
        trademark_id=trademark.id,
        event_type="publication",
        event_date=event_date,
        source=source,
        description="Publicação do pedido",
    )
    session.add(event)
    await session.flush()
    return event


async def make_user(session: AsyncSession, *, email: str | None = None) -> User:
    """Create an active user."""
    user = User(
        email=email or f"user-{uuid.uuid4().hex[:8]}@example.com",
        hashed_password="x",
        full_name="Utilizador Teste",
        is_active=True,
    )
    session.add(user)
    await session.flush()
    return user
