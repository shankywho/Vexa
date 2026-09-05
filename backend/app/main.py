"""FastAPI application factory for the ClosePilot backend."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import audit, companies, health
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

    # Foundation routers (Phase 1). Additional routes (close-runs,
    # exceptions, agents, benchmarks, demo) arrive in later phases.
    app.include_router(health.router, prefix=settings.api_prefix)
    app.include_router(companies.router, prefix=settings.api_prefix)
    app.include_router(audit.router, prefix=settings.api_prefix)

    return app


app = create_app()
