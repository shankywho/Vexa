"""Database session / engine management.

Uses SQLAlchemy 2.0 async engine with ``asyncpg`` for PostgreSQL. In tests
we swap to ``aiosqlite`` (see ``tests/conftest.py``).

Tenant enforcement (spec section 30) is applied in the repository/service
layer — see ``app/db/repository.py`` and ``app/api/dependencies.py``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def create_engine_and_sessionmaker(
    db_url: str | None = None, *, echo: bool | None = None
) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """Create an async engine + sessionmaker.

    ``db_url`` and ``echo`` fall back to application settings.
    """
    global _engine, _sessionmaker

    settings = get_settings()
    url = db_url or settings.db_url
    engine = create_async_engine(
        url,
        echo=settings.db_echo if echo is None else echo,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
    )
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    if db_url is None:
        _engine = engine
        _sessionmaker = maker
    return engine, maker


def get_engine() -> AsyncEngine:
    """Return the process-wide engine (created lazily)."""
    if _engine is None:
        create_engine_and_sessionmaker()
    assert _engine is not None
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Return the process-wide sessionmaker (created lazily)."""
    if _sessionmaker is None:
        create_engine_and_sessionmaker()
    assert _sessionmaker is not None
    return _sessionmaker


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: yield a database session.

    Commit on success, rollback on error.
    """
    maker = get_sessionmaker()
    async with maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def dispose_engine() -> None:
    """Dispose the global engine (used in tests/shutdown)."""
    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _sessionmaker = None
