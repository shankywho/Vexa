"""Integration test for Verification -> Action -> Approval -> Reversal end-to-end lifecycle."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.action.service import ActionService
from app.action.types import ActionType
from app.audit.service import AuditService
from app.close_workflow.controller import CloseWorkflowController
from app.data.generator import seed_financial_transactions
from app.data.seed import seed_company
from app.db.models.agent import AgentRun
from app.db.models.exception import ExceptionAction, ExceptionRecord, ReversalAction
from app.db.models.tenancy import Company
from app.db.repository import (
    AgentRunRepository,
    ExceptionActionRepository,
    ExceptionRepository,
    ReversalActionRepository,
)
from app.domain.enums import (
    AgentRunStatus,
    AuditEventType,
    AutonomyLevel,
    ExceptionStatus,
)
from app.investigation.service import InvestigationService
from app.reconciliation.engine import DeterministicReconciliationEngine
from app.verification.service import VerificationService


@pytest.mark.asyncio
async def test_verification_action_reversal_complete_lifecycle(db: AsyncSession):
    # 1. Seed company & transactions
    company = await seed_company(db, seed=42, include_transactions=False)
    await seed_financial_transactions(db, company, seed=42)

    # 2. Run reconciliation to produce exceptions
    engine = DeterministicReconciliationEngine(db, company.id)
    await engine.run_full_reconciliation(persist=True)

    exc_repo = ExceptionRepository(db, company.id)
    exceptions = await exc_repo.list_by_status(ExceptionStatus.OPEN)
    assert len(exceptions) > 0, "Expected open exceptions"

    target_exc = exceptions[0]

    # 3. Autonomous CFO Investigation
    inv_service = InvestigationService(db, company.id)
    finding = await inv_service.investigate_exception(target_exc.id)
    assert finding.all_citations_valid is True

    # 4. Independent Verification Agent
    ver_service = VerificationService(db, company.id)
    verification = await ver_service.verify_exception(
        exception_id=target_exc.id,
        finding=finding,
    )
    assert verification is not None
    assert verification.confidence >= Decimal("0.8000")
    assert verification.reproduction_valid is True
    assert verification.evidence_complete is True

    # Check Verification AgentRun tracking
    agent_repo = AgentRunRepository(db, company.id)
    ver_runs = await agent_repo.list_by_exception(target_exc.id)
    ver_run = next(r for r in ver_runs if r.agent_name == "verification_agent")
    assert ver_run.status == AgentRunStatus.COMPLETED
    assert len(ver_run.steps) == 5

    # 5. Autonomous Action Execution
    action_service = ActionService(db, company.id)
    actions = await action_service.execute_for_verification(
        exception_id=target_exc.id,
        finding=finding,
        verification=verification,
    )
    assert len(actions) >= 1
    primary_action = actions[0]

    # Check Action AgentRun tracking
    act_runs = await agent_repo.list_by_exception(target_exc.id)
    act_run = next(r for r in act_runs if r.agent_name == "action_agent")
    assert act_run.status == AgentRunStatus.COMPLETED
    assert len(act_run.steps) == 2

    # 6. Human Review Approval
    approval_result = await action_service.approve_exception(
        exception_id=target_exc.id,
        actor="controller_sarah",
        notes="Verified evidence and accepted corrective posture",
    )
    assert approval_result.status == "EXECUTED"
    await db.refresh(target_exc)
    assert target_exc.status == ExceptionStatus.RESOLVED
    assert target_exc.resolved_at is not None

    # Verify APPROVAL audit event
    audit_service = AuditService(db, company.id)
    audit_events = await audit_service.list()
    event_types = [e.event_type for e in audit_events]
    assert AuditEventType.APPROVAL in event_types

    # 7. Human Review Reversal (Spec Section 13.2 Rollback Path)
    reversal_result = await action_service.reverse_action(
        action_id=approval_result.action_id,
        reason="Customer updated statement post-close, rollback resolution",
        reversed_by="cfo_alex",
    )
    assert reversal_result.reopened_exception is True
    assert reversal_result.reversed_by == "cfo_alex"

    # Verify exception is now REOPENED and resolved_at is cleared
    await db.refresh(target_exc)
    assert target_exc.status == ExceptionStatus.REOPENED
    assert target_exc.resolved_at is None

    # Verify original action row is marked REVERSED (immutable rollback trail)
    action_repo = ExceptionActionRepository(db, company.id)
    action_db = await action_repo.get_by_id(approval_result.action_id)
    assert action_db.status == "REVERSED"

    # Verify ReversalAction row exists
    reversal_repo = ReversalActionRepository(db, company.id)
    reversals = await reversal_repo.list_by_exception(target_exc.id)
    assert len(reversals) >= 1
    assert reversals[0].reason == "Customer updated statement post-close, rollback resolution"

    # Verify dual audit events (REVERSAL and EXCEPTION_REOPENED)
    updated_audit = await audit_service.list()
    updated_types = [e.event_type for e in updated_audit]
    assert AuditEventType.REVERSAL in updated_types
    assert AuditEventType.EXCEPTION_REOPENED in updated_types
