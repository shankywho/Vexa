"""Close-run endpoints (spec sections 14, 15, 17, 34, 35)."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import TenantContext, get_tenant_context
from app.audit.service import AuditService
from app.close_workflow.controller import CloseWorkflowController
from app.close_workflow.state_machine import CloseRunError
from app.db.models.agent import AgentRun, AgentStep
from app.db.models.close_run import CloseRun, CloseTask
from app.db.models.demo import DemoTrace
from app.db.models.exception import ExceptionRecord
from app.db.repository import (
    CloseRunRepository,
    CloseTaskRepository,
    ExceptionRepository,
)
from app.db.session import get_session
from app.demo.mode import DemoMode, demo_mode_manager
from app.demo.trace_player import TracePlayer
from app.demo.trace_recorder import seed_golden_traces
from app.domain.enums import CloseRunStatus
from app.domain.schemas import (
    AuditEventRead,
    ClosePackageRead,
    CloseRunCreate,
    CloseRunRead,
    CloseTaskRead,
    ExceptionRead,
)
from app.streaming.bus import agent_event_bus, format_sse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/close-runs", tags=["close-runs"])


@router.post("", response_model=CloseRunRead, status_code=status.HTTP_201_CREATED)
async def create_close_run(
    payload: CloseRunCreate,
    session: AsyncSession = Depends(get_session),
    tenant: TenantContext = Depends(get_tenant_context),
) -> CloseRun:
    """Create a new month-end close run or retrieve an existing open one for the period."""
    controller = CloseWorkflowController(session, company_id=tenant.company_id)
    try:
        close_run = await controller.create_or_get_close_run(
            period_start=payload.period_start,
            period_end=payload.period_end,
        )
        return close_run
    except CloseRunError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)) from err


@router.get("", response_model=list[CloseRunRead])
async def list_close_runs(
    limit: int = Query(default=100, le=1000),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
    tenant: TenantContext = Depends(get_tenant_context),
) -> list[CloseRun]:
    """List close runs for the current tenant."""
    repo = CloseRunRepository(session, company_id=tenant.company_id)
    runs = await repo.list_close_runs(limit=limit, offset=offset)
    return list(runs)


@router.get("/{id}", response_model=CloseRunRead)
async def get_close_run(
    id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    tenant: TenantContext = Depends(get_tenant_context),
) -> CloseRun:
    """Get close run details and status."""
    repo = CloseRunRepository(session, company_id=tenant.company_id)
    close_run = await repo.get(id)
    if close_run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Close run not found")
    return close_run


@router.post("/{id}/start", response_model=CloseRunRead)
async def start_close_run(
    id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    tenant: TenantContext = Depends(get_tenant_context),
) -> CloseRun:
    """Trigger month-end close workflow tasks in dependency order."""
    repo = CloseRunRepository(session, company_id=tenant.company_id)
    close_run = await repo.get(id)
    if close_run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Close run not found")

    controller = CloseWorkflowController(session, company_id=tenant.company_id)
    try:
        updated_run = await controller.execute_workflow(id)
        return updated_run
    except CloseRunError as err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(err)) from err


@router.get("/{id}/tasks", response_model=list[CloseTaskRead])
async def list_close_tasks(
    id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    tenant: TenantContext = Depends(get_tenant_context),
) -> list[CloseTask]:
    """Retrieve all tasks and execution summaries for a close run."""
    run_repo = CloseRunRepository(session, company_id=tenant.company_id)
    close_run = await run_repo.get(id)
    if close_run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Close run not found")

    task_repo = CloseTaskRepository(session, company_id=tenant.company_id)
    tasks = await task_repo.list_by_close_run(id)
    return list(tasks)


@router.get("/{id}/exceptions", response_model=list[ExceptionRead])
async def list_close_exceptions(
    id: uuid.UUID,
    limit: int = Query(default=500, le=1000),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
    tenant: TenantContext = Depends(get_tenant_context),
) -> list[ExceptionRecord]:
    """Retrieve all exceptions detected during a close run."""
    run_repo = CloseRunRepository(session, company_id=tenant.company_id)
    close_run = await run_repo.get(id)
    if close_run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Close run not found")

    exc_repo = ExceptionRepository(session, company_id=tenant.company_id)
    exceptions = await exc_repo.list_by_close_run(id, limit=limit, offset=offset)
    return list(exceptions)


@router.get("/{id}/package", response_model=ClosePackageRead)
async def get_close_package(
    id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    tenant: TenantContext = Depends(get_tenant_context),
) -> dict[str, Any]:
    """Retrieve or generate the structured close package for a close run."""
    run_repo = CloseRunRepository(session, company_id=tenant.company_id)
    close_run = await run_repo.get(id)
    if close_run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Close run not found")

    controller = CloseWorkflowController(session, company_id=tenant.company_id)
    try:
        package = await controller.generate_close_package(id)
        return package.to_dict()
    except Exception as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)) from err


@router.get("/{id}/audit", response_model=list[AuditEventRead])
async def get_close_run_audit(
    id: uuid.UUID,
    limit: int = Query(default=200, le=1000),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
    tenant: TenantContext = Depends(get_tenant_context),
) -> list[AuditEventRead]:
    """Retrieve audit events for this specific close run."""
    run_repo = CloseRunRepository(session, company_id=tenant.company_id)
    close_run = await run_repo.get(id)
    if close_run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Close run not found")

    audit_service = AuditService(session, company_id=tenant.company_id)
    events = await audit_service.list(close_run_id=id, limit=limit, offset=offset)
    return [AuditEventRead.model_validate(e, from_attributes=True) for e in events]


@router.get("/{id}/stream")
async def stream_close_run(
    id: uuid.UUID,
    trace_id: uuid.UUID | None = Query(default=None, description="Explicit trace ID to replay"),
    playback_speed: float = Query(
        default=1.0, ge=0.1, le=100.0, description="Replay speed multiplier"
    ),
    simulate_delay: bool = Query(
        default=True, description="Whether to simulate delays during replay"
    ),
    session: AsyncSession = Depends(get_session),
    tenant: TenantContext = Depends(get_tenant_context),
) -> StreamingResponse:
    """Stream real-time agent activity, tool executions, and step updates via SSE.

    Automatically switches to REPLAY mode if toggled via demo safety net or if trace_id is specified.
    """
    run_repo = CloseRunRepository(session, company_id=tenant.company_id)
    close_run = await run_repo.get(id)
    if close_run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Close run not found")

    # Check demo replay mode (spec section 37)
    mode = demo_mode_manager.get_mode(id)
    if mode == DemoMode.REPLAY or trace_id is not None:
        trace: DemoTrace | None = None
        if trace_id is not None:
            trace = await session.get(DemoTrace, trace_id)
        if trace is None:
            golden_traces = await seed_golden_traces(session)
            trace = golden_traces[0] if golden_traces else None

        if trace is not None:
            player = TracePlayer(playback_speed=playback_speed, simulate_delay=simulate_delay)
            return StreamingResponse(
                player.play_trace(trace, close_run_id=str(id)),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )

    async def event_generator():
        # 1. Emit initial connection event
        yield format_sse(
            {"type": "connected", "close_run_id": str(id), "status": close_run.status.value},
            event="connected",
        )

        # 2. Yield historical agent steps already recorded for this close run
        stmt = (
            select(AgentStep)
            .join(AgentRun, AgentStep.agent_run_id == AgentRun.id)
            .where(AgentRun.close_run_id == id, AgentRun.company_id == tenant.company_id)
            .order_by(AgentStep.created_at.asc(), AgentStep.step_number.asc())
        )
        historical_steps = (await session.scalars(stmt)).all()
        for step in historical_steps:
            output = None
            if step.output_json:
                try:
                    output = json.loads(step.output_json)
                except Exception:
                    output = step.output_json
            yield format_sse(
                {
                    "type": "agent_step",
                    "step_id": str(step.id),
                    "agent_run_id": str(step.agent_run_id),
                    "step_number": step.step_number,
                    "step_type": step.step_type,
                    "tool_name": step.tool_name,
                    "status": step.status,
                    "latency_ms": step.latency_ms,
                    "citations_valid": step.citations_valid,
                    "output": output,
                },
                event="agent_step",
            )

        # 3. If close run is terminal, end stream
        if close_run.status in (CloseRunStatus.CLOSED, CloseRunStatus.READY_TO_CLOSE):
            yield format_sse(
                {"type": "completed", "close_run_id": str(id), "status": close_run.status.value},
                event="completed",
            )
            return

        # 4. Subscribe to live events
        async with agent_event_bus.subscribe(id) as queue:
            while True:
                try:
                    event_data = await asyncio.wait_for(queue.get(), timeout=15.0)
                    evt_type = event_data.get("event", "message")
                    yield format_sse(event_data, event=evt_type)

                    if evt_type in ("completed", "close_run_closed"):
                        break
                except asyncio.TimeoutError:
                    # Heartbeat / ping comment to keep SSE connection open
                    yield ": ping\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
