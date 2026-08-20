"""Shared test fixtures for async database sessions.

``db_session`` prefers a real PostgreSQL test database: it creates a dedicated
``markee_test`` database on the docker-compose server (never touching the live
``markee`` database), recreates the four schemas (raw/core/events/app) with all
tables before each test, and drops them afterwards. This exercises the real
PostgreSQL features the models rely on (JSONB, arrays, partitioning).

When PostgreSQL is unreachable, the fixture falls back to in-memory SQLite via
aiosqlite. SQLite has no schemas, so the engine collapses raw/core/events/app
into the default namespace with a schema_translate_map; a StaticPool keeps the
single in-memory database alive across the connections of one test.
"""
import os

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool, StaticPool

import app.models  # noqa: F401 - register every table on the metadata
from app.models.database import Base, get_db  # noqa: F401 - re-exported for tests
from app.models.schemas import ALL_SCHEMAS, SQLITE_SCHEMA_TRANSLATE_MAP

# Server hosting the docker-compose ``db`` service. The fixture derives the
# dedicated test database URL from it by swapping the database name.
POSTGRES_SERVER_URL = os.environ.get(
    "MARKEE_TEST_SERVER_URL",
    "postgresql+asyncpg://markee:markee_dev@localhost:5432/markee",
)
TEST_DB_NAME = os.environ.get("MARKEE_TEST_DB_NAME", "markee_test")

# None = not probed yet; cached so a down server is only probed once per run.
_postgres_available: bool | None = None


def _test_db_url() -> str:
    """Return the server URL pointed at the dedicated test database."""
    return POSTGRES_SERVER_URL.rsplit("/", 1)[0] + "/" + TEST_DB_NAME


async def _ensure_test_database() -> bool:
    """Create the test database if missing; return False when PG is down."""
    global _postgres_available
    if _postgres_available is not None:
        return _postgres_available
    admin = create_async_engine(
        POSTGRES_SERVER_URL, poolclass=NullPool, isolation_level="AUTOCOMMIT"
    )
    try:
        async with admin.connect() as conn:
            exists = (
                await conn.execute(
                    text("SELECT 1 FROM pg_database WHERE datname = :name"),
                    {"name": TEST_DB_NAME},
                )
            ).scalar()
            if not exists:
                await conn.execute(text(f'CREATE DATABASE "{TEST_DB_NAME}"'))
        _postgres_available = True
    except Exception:
        _postgres_available = False
    finally:
        await admin.dispose()
    return _postgres_available


async def _postgres_session():
    """Yield a session on a freshly built markee_test schema set."""
    engine = create_async_engine(_test_db_url(), poolclass=NullPool)
    try:
        async with engine.begin() as conn:
            for schema in ALL_SCHEMAS:
                await conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
            for schema in ALL_SCHEMAS:
                await conn.execute(text(f'CREATE SCHEMA "{schema}"'))
            await conn.run_sync(Base.metadata.create_all)
            # The partitioned parent rejects inserts until a partition exists;
            # a DEFAULT partition catches rows for any month.
            await conn.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS raw.api_responses_default "
                    "PARTITION OF raw.api_responses DEFAULT"
                )
            )
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            yield session
            await session.rollback()
        async with engine.begin() as conn:
            for schema in ALL_SCHEMAS:
                await conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
    finally:
        await engine.dispose()


async def _sqlite_session():
    """Yield a session on an in-memory SQLite database (schemas collapsed)."""
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        execution_options={"schema_translate_map": SQLITE_SCHEMA_TRANSLATE_MAP},
    )
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            yield session
            await session.rollback()
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def db_session():
    if await _ensure_test_database():
        async for session in _postgres_session():
            yield session
    else:
        async for session in _sqlite_session():
            yield session


@pytest.fixture
def override_get_db(db_session):
    async def _get_db():
        yield db_session
    return _get_db
