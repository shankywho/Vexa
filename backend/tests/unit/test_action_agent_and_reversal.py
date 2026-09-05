"""Unit tests for Action Agent and Rollback/Reversal Engine (spec section 10, 11, 13.2)."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.action.agent import ActionAgent
from app.action.reversal import ReversalEngine
from app.action.tools import ActionTools
from app.action.types import ActionType
from app.audit.service import AuditService
from app.db.models.agent import AgentRun
from app.db.models.exception import ExceptionAction, ExceptionRecord, ReversalAction
from app.db.models.tenancy import Company
from app.domain.enums import (
    AgentRunStatus,
    AuditEventType,
    AutonomyLevel,
    ExceptionSeverity,
    ExceptionStatus,
    ExceptionType,
    Role,
)
from app.investigation.types import (
    AutonomyAction,
    FindingStatus,
    InvestigationFinding,
    InvestigationRecommendation,
    RootCauseAnalysis,
)
from app.verification.types import VerificationResult


@pytest.fixture
async def company(db: AsyncSession) -> Company:
    comp = Company(name="Acme Operations", base_currency="USD", is_active=True)
    db.add(comp)
    await db.flush()
    await db.refresh(comp)
    return comp


@pytest.fixture
async def open_exception(db: AsyncSession, company: Company) -> ExceptionRecord:
    exc = ExceptionRecord(
        company_id=company.id,
        type=ExceptionType.PO_MISMATCH,
        severity=ExceptionSeverity.HIGH,
        financial_impact=Decimal("15000.00"),
        currency="USD",
        status=ExceptionStatus.OPEN,
    )
    db.add(exc)
    await db.flush()
    await db.refresh(exc)
    return exc


@pytest.mark.asyncio
async def test_action_tools_idempotency(db: AsyncSession, company: Company, open_exception: ExceptionRecord):
    tools = ActionTools(db, company.id)

    # 1. Create review task
    r1 = await tools.create_review_task(
        exception_id=open_exception.id,
        title="Review PO Mismatch",
        description="Discrepancy of 15,000 between Invoice and PO",
        assigned_to=Role.CONTROLLER,
    )
    assert r1.status == "EXECUTED"

    # 2. Call again with same inputs -> must be idempotent
    r2 = await tools.create_review_task(
        exception_id=open_exception.id,
        title="Review PO Mismatch",
        description="Discrepancy of 15,000 between Invoice and PO",
        assigned_to=Role.CONTROLLER,
    )
    assert r1.action_id == r2.action_id
    assert "idempotent" in r2.message.lower()

    # 3. Stage vendor draft
    d1 = await tools.draft_vendor_email(
        exception_id=open_exception.id,
        vendor_name="Acme Supplier",
        subject="Notice of Discrepancy",
        body="Please review invoice discrepancy",
    )
    assert d1.status == "STAGED"

    # Second draft call returns existing staged action
    d2 = await tools.draft_vendor_email(
        exception_id=open_exception.id,
        vendor_name="Acme Supplier",
        subject="Notice of Discrepancy",
        body="Please review invoice discrepancy",
    )
    assert d1.action_id == d2.action_id


@pytest.mark.asyncio
async def test_reversal_engine_rollback_trail(
    db: AsyncSession, company: Company, open_exception: ExceptionRecord
):
    tools = ActionTools(db, company.id)
    reversal_engine = ReversalEngine(db, company.id)
    audit_service = AuditService(db, company.id)

    # 1. Take a staged action (staging adjusting journal entry)
    act = await tools.stage_journal_entry(
        exception_id=open_exception.id,
        memo="Accrual adjustment",
        lines=[{"debit": "15000.00", "credit": "15000.00"}],
    )
    assert act.status == "STAGED"

    # Resolve exception initially
    resolve_act = await tools.mark_exception_resolved(
        exception_id=open_exception.id,
        resolution_note="Staged resolution approved",
        actor="human_reviewer",
    )
    await db.refresh(open_exception)
    assert open_exception.status == ExceptionStatus.RESOLVED
    assert open_exception.resolved_at is not None

    # 2. Controller reverses the resolution action after finding an error
    reversal_result = await reversal_engine.reverse_action(
        action_id=resolve_act.action_id,
        reason="Vendor corrected bill directly, no entry needed",
        reversed_by="controller_jane",
    )

    # 3. Verify Spec Section 13.2 requirements:
    # A. ReversalAction record created
    assert reversal_result.reversal_id is not None
    assert reversal_result.exception_action_id == resolve_act.action_id
    assert reversal_result.reversed_by == "controller_jane"

    # B. Original ExceptionAction is kept immutable (status changed to REVERSED, row not deleted)
    action_in_db = await tools.action_repo.get_by_id(resolve_act.action_id)
    assert action_in_db is not None
    assert action_in_db.status == "REVERSED"

    # C. Exception is re-opened (status -> REOPENED, resolved_at cleared)
    await db.refresh(open_exception)
    assert open_exception.status == ExceptionStatus.REOPENED
    assert open_exception.resolved_at is None

    # D. Dual audit events recorded (REVERSAL and EXCEPTION_REOPENED)
    events = await audit_service.list()
    event_types = [e.event_type for e in events]
    assert AuditEventType.REVERSAL in event_types
    assert AuditEventType.EXCEPTION_REOPENED in event_types

    # E. Cannot reverse the same action twice
    with pytest.raises(ValueError, match="already been reversed"):
        await reversal_engine.reverse_action(
            action_id=resolve_act.action_id,
            reason="Double reversal attempt",
        )


@pytest.mark.asyncio
async def test_reversal_engine_tenant_isolation(
    db: AsyncSession, company: Company, open_exception: ExceptionRecord
):
    other_comp = Company(name="Other Tenant", base_currency="USD", is_active=True)
    db.add(other_comp)
    await db.flush()

    tools = ActionTools(db, company.id)
    act = await tools.mark_exception_resolved(
        exception_id=open_exception.id,
        resolution_note="Company A resolution",
    )

    # Attempt reversal from company B
    rogue_engine = ReversalEngine(db, other_comp.id)
    with pytest.raises(ValueError, match="not found for company"):
        await rogue_engine.reverse_action(act.action_id, reason="cross tenant")


@pytest.mark.asyncio
async def test_action_agent_governed_execution(
    db: AsyncSession, company: Company, open_exception: ExceptionRecord
):
    agent = ActionAgent(db, company.id)

    finding = InvestigationFinding(
        exception_id=open_exception.id,
        exception_type=open_exception.type,
        finding_status=FindingStatus.COMPLETED,
        root_cause_analysis=RootCauseAnalysis(
            primary_category="PO_PRICE_VARIANCE",
            summary="Vendor price mismatch",
            likely_cause="Vendor billed above PO price",
            is_genuine_discrepancy=True,
            is_timing_or_operational=False,
        ),
        recommendation=InvestigationRecommendation(
            action=AutonomyAction.STAGE,
            target_role=Role.CONTROLLER,
            recommended_action="Request vendor price correction",
            should_block_close=True,
            should_escalate_to_cfo=False,
        ),
        raw_confidence=Decimal("0.9800"),
        calibrated_confidence=Decimal("0.9500"),
        all_citations_valid=True,
        cited_record_ids=["inv-1"],
    )

    verification = VerificationResult(
        exception_id=open_exception.id,
        verified=True,
        confidence=Decimal("0.9800"),
        calibrated_confidence=Decimal("0.9500"),
        missing_evidence=[],
        calculation_errors=[],
        policy_violations=[],
        recommended_autonomy=AutonomyLevel.STAGE,
    )

    actions = await agent.execute_for_verification(open_exception.id, finding, verification)
    assert len(actions) >= 1

    action_types = [a.action_type for a in actions]
    assert ActionType.CREATE_REVIEW_TASK in action_types

    # Verify AgentRun and steps persisted
    from app.db.repository import AgentRunRepository

    run_repo = AgentRunRepository(db, company.id)
    runs = await run_repo.list_by_exception(open_exception.id)
    action_runs = [r for r in runs if r.agent_name == "action_agent"]
    assert len(action_runs) >= 1
    run = action_runs[0]
    assert run.status == AgentRunStatus.COMPLETED
    assert len(run.steps) == 2
