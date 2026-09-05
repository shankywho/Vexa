"""Health endpoint — liveness + DB connectivity."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import get_session
from app.domain.schemas import HealthRead

router = APIRouter(tags=["health"])

APP_VERSION = "0.1.0"


@router.get("/health", response_model=HealthRead)
async def health(session: AsyncSession = Depends(get_session)) -> HealthRead:
    """Liveness probe. Verifies the database is reachable."""
    database = "ok"
    try:
        await session.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001 - health endpoint must not 500 on DB down
        database = "unavailable"

    settings = get_settings()
    return HealthRead(
        status="ok" if database == "ok" else "degraded",
        environment=settings.environment,
        database=database,
        version=APP_VERSION,
    )
