"""Demo safety net REST endpoints for LIVE/REPLAY mode and trace player (spec section 37)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import TenantContext, get_session, get_tenant_context
from app.db.models.close_run import CloseRun
from app.db.models.demo import DemoTrace
from app.demo.mode import DemoMode, demo_mode_manager
from app.demo.trace_player import TracePlayer
from app.demo.trace_recorder import TraceRecorder, seed_golden_traces
from app.domain.schemas import (
    DemoModeRead,
    DemoModeToggleRequest,
    DemoRecordRequest,
    DemoTraceRead,
)

router = APIRouter(prefix="/demo", tags=["demo"])


@router.get("/mode", response_model=DemoModeRead)
async def get_demo_mode(
    close_run_id: uuid.UUID | None = Query(
        default=None, description="Optional close run ID to check"
    ),
) -> DemoModeRead:
    """Get the current demo execution mode (LIVE or REPLAY), globally or for a specific run."""
    mode = demo_mode_manager.get_mode(close_run_id)
    return DemoModeRead(mode=mode.value, close_run_id=close_run_id)


@router.post("/mode", response_model=DemoModeRead)
async def set_demo_mode(
    payload: DemoModeToggleRequest,
) -> DemoModeRead:
    """Set demo execution mode to LIVE or REPLAY globally or per close run."""
    try:
        mode_enum = DemoMode(payload.mode.upper())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid mode '{payload.mode}'. Must be 'LIVE' or 'REPLAY'.",
        )

    demo_mode_manager.set_mode(mode_enum, close_run_id=payload.close_run_id)
    return DemoModeRead(mode=mode_enum.value, close_run_id=payload.close_run_id)


@router.get("/traces", response_model=list[DemoTraceRead])
async def list_demo_traces(
    scenario_key: str | None = Query(default=None, description="Filter by scenario key"),
    is_golden: bool | None = Query(default=None, description="Filter by golden status"),
    session: AsyncSession = Depends(get_session),
    tenant: TenantContext = Depends(get_tenant_context),
) -> list[DemoTraceRead]:
    """List all available demo traces. Automatically seeds golden demo traces if empty."""
    # Ensure golden traces exist
    await seed_golden_traces(session)

    stmt = select(DemoTrace).where(
        or_(DemoTrace.company_id == tenant.company_id, DemoTrace.company_id.is_(None))
    )
    if scenario_key:
        stmt = stmt.where(DemoTrace.scenario_key == scenario_key)
    if is_golden is not None:
        stmt = stmt.where(DemoTrace.is_golden == is_golden)
    stmt = stmt.order_by(DemoTrace.created_at.asc())

    traces = (await session.scalars(stmt)).all()
    return [DemoTraceRead.model_validate(t, from_attributes=True) for t in traces]


@router.get("/traces/{id}", response_model=DemoTraceRead)
async def get_demo_trace(
    id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    tenant: TenantContext = Depends(get_tenant_context),
) -> DemoTraceRead:
    """Get a demo trace by ID including full event list."""
    stmt = select(DemoTrace).where(
        DemoTrace.id == id,
        or_(DemoTrace.company_id == tenant.company_id, DemoTrace.company_id.is_(None)),
    )
    trace = await session.scalar(stmt)
    if trace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demo trace not found")
    return DemoTraceRead.model_validate(trace, from_attributes=True)


@router.post("/record", response_model=DemoTraceRead, status_code=status.HTTP_201_CREATED)
async def record_demo_trace(
    payload: DemoRecordRequest,
    session: AsyncSession = Depends(get_session),
    tenant: TenantContext = Depends(get_tenant_context),
) -> DemoTraceRead:
    """Record a completed or in-progress close run into a replayable demo trace."""
    # Verify close run exists and belongs to tenant
    run = await session.get(CloseRun, payload.close_run_id)
    if run is None or run.company_id != tenant.company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Close run not found")

    recorder = TraceRecorder(session)
    try:
        trace = await recorder.record_from_close_run(
            close_run_id=payload.close_run_id,
            scenario_key=payload.scenario_key,
            title=payload.title,
            description=payload.description,
            is_golden=payload.is_golden,
        )
        await session.commit()
    except Exception as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record trace: {str(exc)}",
        )

    return DemoTraceRead.model_validate(trace, from_attributes=True)


@router.post("/traces/seed", response_model=list[DemoTraceRead])
async def seed_traces_endpoint(
    session: AsyncSession = Depends(get_session),
    tenant: TenantContext = Depends(get_tenant_context),
) -> list[DemoTraceRead]:
    """Explicitly seed or update golden demo traces."""
    traces = await seed_golden_traces(session)
    await session.commit()
    return [DemoTraceRead.model_validate(t, from_attributes=True) for t in traces]


@router.get("/traces/{id}/stream")
async def stream_demo_trace(
    id: uuid.UUID,
    playback_speed: float = Query(default=1.0, ge=0.1, le=100.0, description="Speed multiplier"),
    simulate_delay: bool = Query(
        default=True, description="Whether to simulate delay between events"
    ),
    session: AsyncSession = Depends(get_session),
    tenant: TenantContext = Depends(get_tenant_context),
) -> StreamingResponse:
    """Stream a captured demo trace directly as SSE."""
    stmt = select(DemoTrace).where(
        DemoTrace.id == id,
        or_(DemoTrace.company_id == tenant.company_id, DemoTrace.company_id.is_(None)),
    )
    trace = await session.scalar(stmt)
    if trace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demo trace not found")

    player = TracePlayer(playback_speed=playback_speed, simulate_delay=simulate_delay)

    return StreamingResponse(
        player.play_trace(trace),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
