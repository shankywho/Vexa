"""FastAPI application factory for the ClosePilot backend."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import (
    agent_runs,
    audit,
    benchmarks,
    close_runs,
    companies,
    demo,
    exceptions,
    health,
)
from app.config import get_settings
from app.db.session import dispose_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — currently only cleanup; engine is lazy."""
    yield
    await dispose_engine()


TAGS_METADATA = [
    {"name": "health", "description": "Service health checks and readiness probes."},
    {"name": "companies", "description": "Company tenant management and financial entity configuration."},
    {"name": "close-runs", "description": "Month-end close workflow orchestration, DAG task execution, and sign-offs."},
    {"name": "exceptions", "description": "Reconciliation exception registry, bounded forensic evidence dossiers, and human approvals."},
    {"name": "agent-runs", "description": "Autonomous financial agent execution runs and step-level telemetry."},
    {"name": "audit", "description": "Immutable SOX 404 audit ledger, control mappings, and tamper-evident event trails."},
    {"name": "benchmarks", "description": "CFO-Bench 35-scenario ground truth benchmark evaluation and confidence calibration reports."},
    {"name": "demo", "description": "Demonstration safety net controls, LIVE vs. REPLAY execution mode, and trace recording."},
]


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description=(
            "Autonomous Office of the CFO — Month-End Close Operating System.\n\n"
            "Features mathematical determinism, graph-based forensic investigation, "
            "cross-model verification independence, and immutable SOX 404 audit logging."
        ),
        version="2.0.0",
        openapi_tags=TAGS_METADATA,
        debug=settings.debug,
        lifespan=lifespan,
    )

    # API Routes (Spec Section 17, 37)
    app.include_router(health.router, prefix=settings.api_prefix)
    app.include_router(companies.router, prefix=settings.api_prefix)
    app.include_router(close_runs.router, prefix=settings.api_prefix)
    app.include_router(exceptions.router, prefix=settings.api_prefix)
    app.include_router(agent_runs.router, prefix=settings.api_prefix)
    app.include_router(audit.router, prefix=settings.api_prefix)
    app.include_router(benchmarks.router, prefix=settings.api_prefix)
    app.include_router(demo.router, prefix=settings.api_prefix)

    return app


app = create_app()
