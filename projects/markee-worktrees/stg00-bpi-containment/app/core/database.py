"""SQLAlchemy 2.0 async engine, session factory and declarative base.

This module is the single source of truth for database wiring. Both the
application (``app.models.database``) and the Alembic environment import the
:class:`Base` and :data:`engine` defined here.
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    """Declarative base class shared by every ORM model."""


engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session for use as a FastAPI dependency.

    The session is closed automatically when the request finishes. On an
    unhandled exception the transaction is rolled back before re-raising.

    Yields:
        An active :class:`~sqlalchemy.ext.asyncio.AsyncSession`.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
