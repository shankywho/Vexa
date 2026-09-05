"""Integration tests for CFO Investigation Agent end-to-end execution flow."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import AuditService
from app.data.generator import seed_financial_transactions
from app.data.seed import seed_company
from app.db.models.exception import ExceptionRecord
from app.db.models.tenancy import Company
from app.db.repository import AgentRunRepository, ExceptionRepository
from app.domain.enums import (
    AgentRunStatus,
    AuditEventType,
    ExceptionSeverity,
    ExceptionStatus,
    ExceptionType,
)
from app.investigation.prompt import PROMPT_VERSION_ID
from app.investigation.service import InvestigationService
from app.investigation.types import AutonomyAction, FindingStatus
from app.reconciliation.engine import DeterministicReconciliationEngine


@pytest.mark.asyncio
async def test_investigation_agent_end_to_end_flow(db: AsyncSession):
    # 1. Seed tenant and transactions
    company = await seed_company(db, seed=42, include_transactions=False)
    await seed_financial_transactions(db, company, seed=42)

    # 2. Run deterministic reconciliation to populate DB exceptions
    engine = DeterministicReconciliationEngine(db, company.id)
    await engine.run_full_reconciliation(persist=True)

    exc_repo = ExceptionRepository(db, company.id)
    exceptions = await exc_repo.list_by_status(ExceptionStatus.OPEN)
    assert len(exceptions) > 0, "Expected reconciliation to produce exceptions"

    target_exc = exceptions[0]

    # 3. Execute autonomous investigation
    service = InvestigationService(db, company.id)
    finding = await service.investigate_exception(target_exc.id)

    # 4. Verify structured finding contracts
    assert finding is not None
    assert finding.exception_id == target_exc.id
    assert finding.all_citations_valid is True
    assert len(finding.hallucinated_citations) == 0
    assert len(finding.facts) > 0
    assert finding.root_cause_analysis.likely_cause != ""
    assert finding.recommendation.action in (
        AutonomyAction.AUTO_RESOLVE,
        AutonomyAction.STAGE,
        AutonomyAction.ESCALATE,
        AutonomyAction.REFUSE,
    )
    assert finding.calibrated_confidence > Decimal("0.0000")

    # 5. Verify all 8 standard CFO questions answered
    assert len(finding.answers_to_questions) == 8
    for question, answer in finding.answers_to_questions.items():
        assert len(answer) > 0, f"Empty answer for: {question}"

    # 6. Verify PostgreSQL AgentRun and AgentSteps persisted
    agent_repo = AgentRunRepository(db, company.id)
    runs = await agent_repo.list_by_exception(target_exc.id)
    assert len(runs) >= 1

    run = runs[0]
    assert run.status == AgentRunStatus.COMPLETED
    assert run.prompt_version_id == PROMPT_VERSION_ID
    assert run.latency_ms is not None and run.latency_ms >= 0
    assert len(run.steps) == 5

    step_types = [s.step_type for s in run.steps]
    assert "dossier_inspection" in step_types
    assert "reasoning_generation" in step_types
    assert "citation_validation" in step_types
    assert "confidence_calibration" in step_types
    assert "governance_policy_check" in step_types

    # 7. Verify Exception record in DB was updated
    await db.refresh(target_exc)
    assert target_exc.root_cause == finding.root_cause_analysis.likely_cause
    assert target_exc.recommended_action == finding.recommendation.recommended_action

    # 8. Verify AuditEvents emitted
    audit_service = AuditService(db, company.id)
    audit_events = await audit_service.list()
    event_types = [e.event_type for e in audit_events]
    assert AuditEventType.AGENT_RUN_STARTED in event_types
    assert AuditEventType.AGENT_RUN_COMPLETED in event_types


@pytest.mark.asyncio
async def test_investigation_agent_tenant_isolation(db: AsyncSession):
    company_a = Company(name="Tenant Alpha Flow", base_currency="USD", is_active=True)
    company_b = Company(name="Tenant Beta Flow", base_currency="USD", is_active=True)
    db.add_all([company_a, company_b])
    await db.flush()

    # Create exception under Company A
    exc_a = ExceptionRecord(
        company_id=company_a.id,
        type=ExceptionType.PO_MISMATCH,
        severity=ExceptionSeverity.HIGH,
        financial_impact=Decimal("12000.00"),
        currency="USD",
        status=ExceptionStatus.OPEN,
    )
    db.add(exc_a)
    await db.flush()
    await db.refresh(exc_a)

    # Attempt to investigate Company A exception using Company B service
    service_b = InvestigationService(db, company_b.id)
    with pytest.raises(ValueError, match="not found for company"):
        await service_b.investigate_exception(exc_a.id)


@pytest.mark.asyncio
async def test_investigation_agent_insufficient_evidence(db: AsyncSession):
    company = Company(name="Tenant Gamma Flow", base_currency="USD", is_active=True)
    db.add(company)
    await db.flush()

    # Create orphan exception without any linked primary or related records
    orphan_exc = ExceptionRecord(
        company_id=company.id,
        type=ExceptionType.PO_MISMATCH,
        severity=ExceptionSeverity.MEDIUM,
        financial_impact=Decimal("5000.00"),
        currency="USD",
        status=ExceptionStatus.OPEN,
    )
    db.add(orphan_exc)
    await db.flush()
    await db.refresh(orphan_exc)

    service = InvestigationService(db, company.id)
    finding = await service.investigate_exception(orphan_exc.id)

    assert finding.finding_status == FindingStatus.INSUFFICIENT_EVIDENCE
    assert finding.recommendation.action == AutonomyAction.REFUSE
    assert len(finding.missing_evidence) > 0
    assert "insufficient" in finding.executive_summary.lower()
