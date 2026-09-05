"""Financial exceptions endpoints (spec sections 9, 11, 13.2, 17)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.action.correction_service import HumanCorrectionService
from app.action.service import ActionService
from app.api.dependencies import TenantContext, get_tenant_context
from app.db.models.exception import ExceptionRecord
from app.db.repository import ExceptionRepository
from app.db.session import get_session
from app.domain.schemas import (
    ActionResponse,
    EscalateRequest,
    ExceptionEvidenceRead,
    ExceptionRead,
    HumanCorrectionStatsRead,
    HumanReviewRequest,
    ReverseActionRequest,
)
from app.investigation.dossier_builder import EvidenceDossierBuilder

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/exceptions", tags=["exceptions"])


@router.get("/corrections/stats", response_model=HumanCorrectionStatsRead)
async def get_correction_stats(
    session: AsyncSession = Depends(get_session),
    tenant: TenantContext = Depends(get_tenant_context),
) -> HumanCorrectionStatsRead:
    """Retrieve human correction and override statistics for policy tuning."""
    service = HumanCorrectionService(session, company_id=tenant.company_id)
    return await service.get_override_statistics()


@router.get("/{id}", response_model=ExceptionRead)
async def get_exception(
    id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    tenant: TenantContext = Depends(get_tenant_context),
) -> ExceptionRecord:
    """Retrieve details for a specific financial exception."""
    repo = ExceptionRepository(session, company_id=tenant.company_id)
    exc = await repo.get(id)
    if exc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exception not found")
    return exc


@router.get("/{id}/evidence", response_model=ExceptionEvidenceRead)
async def get_exception_evidence(
    id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    tenant: TenantContext = Depends(get_tenant_context),
) -> dict[str, Any]:
    """Retrieve bounded evidence dossier, graph nodes, and citations for an exception."""
    repo = ExceptionRepository(session, company_id=tenant.company_id)
    exc = await repo.get(id)
    if exc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exception not found")

    dossier_builder = EvidenceDossierBuilder(session, company_id=tenant.company_id)
    try:
        dossier = await dossier_builder.build_dossier(id)
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to build evidence dossier: {str(err)}",
        ) from err

    dossier_dict = dossier.to_dict()
    evidence_ids = list(dossier.valid_evidence_ids)
    nodes = dossier_dict.get("ranked_nodes", [])
    citations = [
        {"claim": claim, "sources": sources}
        for claim, sources in dossier_dict.get("citations", {}).items()
    ]

    return {
        "exception_id": id,
        "evidence_ids": evidence_ids,
        "dossier": dossier_dict,
        "nodes": nodes,
        "citations": citations,
    }


@router.post("/{id}/approve", response_model=ActionResponse)
async def approve_exception(
    id: uuid.UUID,
    payload: HumanReviewRequest = HumanReviewRequest(),
    session: AsyncSession = Depends(get_session),
    tenant: TenantContext = Depends(get_tenant_context),
) -> ActionResponse:
    """Human approver approves exception and executes staged actions."""
    service = ActionService(session, company_id=tenant.company_id)
    try:
        result = await service.approve_exception(
            exception_id=id,
            actor=payload.actor,
            notes=payload.notes,
        )
        return ActionResponse(
            action_id=result.action_id,
            exception_id=result.exception_id,
            action_type=result.action_type.value,
            status=result.status,
            message=result.message,
            payload=result.payload,
            actor=result.actor,
            executed_at=result.executed_at,
        )
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err)) from err


@router.post("/{id}/reject", response_model=ActionResponse)
async def reject_exception(
    id: uuid.UUID,
    payload: HumanReviewRequest = HumanReviewRequest(),
    session: AsyncSession = Depends(get_session),
    tenant: TenantContext = Depends(get_tenant_context),
) -> ActionResponse:
    """Human reviewer rejects staged actions; returns exception to OPEN."""
    service = ActionService(session, company_id=tenant.company_id)
    try:
        result = await service.reject_exception(
            exception_id=id,
            actor=payload.actor,
            notes=payload.notes,
        )
        return ActionResponse(
            action_id=result.action_id,
            exception_id=result.exception_id,
            action_type=result.action_type.value,
            status=result.status,
            message=result.message,
            payload=result.payload,
            actor=result.actor,
            executed_at=result.executed_at,
        )
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err)) from err


@router.post("/{id}/escalate", response_model=ActionResponse)
async def escalate_exception(
    id: uuid.UUID,
    payload: EscalateRequest = EscalateRequest(),
    session: AsyncSession = Depends(get_session),
    tenant: TenantContext = Depends(get_tenant_context),
) -> ActionResponse:
    """Escalate exception to senior leadership / CFO."""
    service = ActionService(session, company_id=tenant.company_id)
    try:
        result = await service.escalate_exception(
            exception_id=id,
            target_role=payload.target_role,
            reason=payload.reason,
            actor=payload.actor,
        )
        return ActionResponse(
            action_id=result.action_id,
            exception_id=result.exception_id,
            action_type=result.action_type.value,
            status=result.status,
            message=result.message,
            payload=result.payload,
            actor=result.actor,
            executed_at=result.executed_at,
        )
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err)) from err


@router.post("/{id}/resolve", response_model=ActionResponse)
async def resolve_exception(
    id: uuid.UUID,
    payload: HumanReviewRequest = HumanReviewRequest(),
    session: AsyncSession = Depends(get_session),
    tenant: TenantContext = Depends(get_tenant_context),
) -> ActionResponse:
    """Manually resolve an exception with notes."""
    service = ActionService(session, company_id=tenant.company_id)
    try:
        result = await service.tools.mark_exception_resolved(
            exception_id=id,
            resolution_note=payload.notes or "Resolved manually by user",
            actor=payload.actor,
            auto_resolved=False,
        )
        return ActionResponse(
            action_id=result.action_id,
            exception_id=result.exception_id,
            action_type=result.action_type.value,
            status=result.status,
            message=result.message,
            payload=result.payload,
            actor=result.actor,
            executed_at=result.executed_at,
        )
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err)) from err


@router.post("/{id}/reverse", response_model=ActionResponse)
async def reverse_exception_action(
    id: uuid.UUID,
    payload: ReverseActionRequest = ReverseActionRequest(),
    session: AsyncSession = Depends(get_session),
    tenant: TenantContext = Depends(get_tenant_context),
) -> ActionResponse:
    """Rollback/reversal path for an exception action (spec section 13.2)."""
    service = ActionService(session, company_id=tenant.company_id)

    target_action_id = payload.action_id
    if target_action_id is None:
        actions = await service.list_actions_for_exception(id)
        # Find latest non-reversed action
        active_actions = [a for a in actions if a.status in ("EXECUTED", "STAGED")]
        if not active_actions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active or executed action found to reverse for this exception",
            )
        target_action_id = active_actions[-1].id

    try:
        reversal = await service.reverse_action(
            action_id=target_action_id,
            reason=payload.reason,
            reversed_by=payload.reversed_by,
        )
        return ActionResponse(
            action_id=reversal.reversal_id,
            exception_id=reversal.exception_id,
            action_type="REVERSAL",
            status="REVERSED",
            message=reversal.message,
            payload=reversal.model_dump(mode="json"),
            actor=payload.reversed_by,
            executed_at=reversal.reversed_at,
        )
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)) from err
