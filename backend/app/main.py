"""FastAPI application factory for the ClosePilot backend."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import agent_runs, audit, close_runs, companies, exceptions, health
from app.config import get_settings
from app.db.session import dispose_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — currently only cleanup; engine is lazy."""
    yield
    await dispose_engine()


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        debug=settings.debug,
        lifespan=lifespan,
    )

    # API Routes (Spec Section 17)
    app.include_router(health.router, prefix=settings.api_prefix)
    app.include_router(companies.router, prefix=settings.api_prefix)
    app.include_router(close_runs.router, prefix=settings.api_prefix)
    app.include_router(exceptions.router, prefix=settings.api_prefix)
    app.include_router(agent_runs.router, prefix=settings.api_prefix)
    app.include_router(audit.router, prefix=settings.api_prefix)

    return app


app = create_app()
