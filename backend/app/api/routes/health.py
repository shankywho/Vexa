"""Health endpoint — liveness + DB connectivity."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import get_session
from app.domain.schemas import HealthRead

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])

APP_VERSION = "0.1.0"


@router.get("/health", response_model=HealthRead)
async def health(session: AsyncSession = Depends(get_session)) -> HealthRead:
    """Liveness probe. Verifies the database is reachable."""
    database = "ok"
    error_detail: str | None = None
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - health endpoint must not 500 on DB down
        logger.warning("Health check database probe failed: %s", exc)
        database = "unavailable"
        error_detail = str(exc)

    settings = get_settings()
    return HealthRead(
        status="ok" if database == "ok" else "degraded",
        environment=settings.environment,
        database=database,
        version=APP_VERSION,
        error=error_detail,
    )
