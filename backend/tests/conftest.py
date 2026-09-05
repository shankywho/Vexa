"""Shared pytest fixtures.

Tests run against a real PostgreSQL database (``vexa_test``) to exercise the
same dialect as production. Schema is created once per session via
``Base.metadata.create_all``; each test gets an isolated transaction that is
rolled back at teardown (fast, deterministic isolation).
"""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.models import Base
from app.db.session import get_session
from app.main import app

TEST_DB_URL = os.environ.get("VEXA_TEST_DB_URL", "postgresql+asyncpg://localhost:5432/vexa_test")


@pytest_asyncio.fixture(scope="session")
async def engine() -> AsyncIterator[AsyncEngine]:
    """Session-scoped async engine for the test database."""
    eng = create_async_engine(TEST_DB_URL, pool_size=5, max_overflow=10)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture
async def sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Function-scoped sessionmaker bound to the test engine."""
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def db(sessionmaker: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncSession]:
    """Isolated transaction per test — rolled back at teardown."""
    session = sessionmaker()
    try:
        yield session
    finally:
        await session.rollback()
        await session.close()


@pytest_asyncio.fixture
async def client(engine: AsyncEngine) -> AsyncIterator[AsyncClient]:
    """FastAPI test client with a transaction-per-test database session.

    All requests in a test share a single session bound to one transaction,
    which is rolled back at teardown — API writes never leak across tests.
    """
    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)

    async def override_get_session() -> AsyncIterator[AsyncSession]:
        yield session  # no commit: the test owns the transaction

    app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
    await transaction.rollback()
    await connection.close()


@pytest.fixture
def company_id() -> uuid.UUID:
    """A stable UUID for tests that do not need a real company row."""
    return uuid.uuid4()
