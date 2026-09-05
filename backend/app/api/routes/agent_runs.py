"""Agent run and step inspection endpoints (spec sections 5.3, 17, 27)."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import TenantContext, get_tenant_context
from app.db.models.agent import AgentRun, AgentStep
from app.db.repository import AgentRunRepository
from app.db.session import get_session
from app.domain.schemas import AgentRunRead, AgentStepRead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent-runs", tags=["agent-runs"])


@router.get("/{id}", response_model=AgentRunRead)
async def get_agent_run(
    id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    tenant: TenantContext = Depends(get_tenant_context),
) -> AgentRun:
    """Retrieve an agent run with all its execution steps."""
    repo = AgentRunRepository(session, company_id=tenant.company_id)
    run = await repo.get_with_steps(id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent run not found")
    return run


@router.get("/{id}/steps", response_model=list[AgentStepRead])
async def list_agent_steps(
    id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    tenant: TenantContext = Depends(get_tenant_context),
) -> list[AgentStep]:
    """Retrieve discrete execution steps for an agent run."""
    repo = AgentRunRepository(session, company_id=tenant.company_id)
    run = await repo.get_with_steps(id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent run not found")
    return list(run.steps)
