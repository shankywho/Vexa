"""End-to-end test of autonomous close workflow (spec sections 14, 15, 34).

Demonstrates:
1. Seeding NovaScale AI company and financial transactions
2. Orchestrating month-end close run and task lifecycle
3. Deterministic reconciliation and exception generation
4. Exception routing and evidence pack availability
5. Human-review checkpoint blocking close completion (WAITING_FOR_HUMAN)
6. Submitting human approval to resolve blocking exceptions
7. Advancing through FINAL_VERIFICATION to READY_TO_CLOSE
8. Structured close package compilation and versioned audit trail verification
"""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.audit.service import AuditService
from app.close_workflow.controller import CloseWorkflowController
from app.close_workflow.routing import EvidencePackRouter, ExceptionRouter
from app.close_workflow.types import ClosePolicy
from app.data.generator import seed_financial_transactions
from app.data.seed import seed_company
from app.db.models.exception import ExceptionRecord
from app.domain.enums import (
    AuditEventType,
    CloseRunStatus,
    CloseTaskStatus,
    CloseTaskType,
    ExceptionType,
)


async def test_full_autonomous_close_workflow_e2e(db: AsyncSession) -> None:
    # 1. Seed NovaScale company and multi-currency transactions
    company = await seed_company(db, name="NovaScale AI Close")
    await seed_financial_transactions(db, company, save_ground_truth=False)

    policy = ClosePolicy(
        max_auto_resolution_amount=Decimal("50000.00"),
        materiality_threshold=Decimal("100000.00"),
        min_confidence=Decimal("0.95"),
    )
    controller = CloseWorkflowController(db, company.id, policy=policy)
    audit_service = AuditService(db, company.id)

    # 2. Create Close Run (idempotent for month-end period)
    close_run = await controller.create_or_get_close_run(
        period_start=date(2026, 3, 1), period_end=date(2026, 3, 31)
    )
    assert close_run.status == CloseRunStatus.CREATED
    assert close_run.version == 1

    # Verify all 10 tasks are initially PENDING
    tasks_dict = await controller.state_machine.get_tasks(close_run.id)
    assert len(tasks_dict) == 10
    assert all(t.status == CloseTaskStatus.PENDING for t in tasks_dict.values())

    # 3. Execute workflow -> Orchestrates tasks in DAG dependency order
    # Reaches EXCEPTION_REVIEW and stops at WAITING_FOR_HUMAN checkpoint
    close_run = await controller.execute_workflow(close_run.id, stop_at_human_review=True)

    tasks_dict = await controller.state_machine.get_tasks(close_run.id)
    for t_type, t in tasks_dict.items():
        if t.status == CloseTaskStatus.FAILED:
            print(f"FAILED TASK {t_type}: {t.result_summary}")

    assert close_run.status == CloseRunStatus.WAITING_FOR_HUMAN
    assert close_run.version > 1

    # Verify reconciliation tasks completed
    tasks_dict = await controller.state_machine.get_tasks(close_run.id)
    assert tasks_dict[CloseTaskType.INVOICE_VALIDATION].status == CloseTaskStatus.COMPLETED
    assert tasks_dict[CloseTaskType.PAYMENT_RECONCILIATION].status == CloseTaskStatus.COMPLETED
    assert tasks_dict[CloseTaskType.BANK_RECONCILIATION].status == CloseTaskStatus.COMPLETED
    assert tasks_dict[CloseTaskType.AP_RECONCILIATION].status == CloseTaskStatus.COMPLETED
    assert tasks_dict[CloseTaskType.AR_RECONCILIATION].status == CloseTaskStatus.COMPLETED
    assert tasks_dict[CloseTaskType.VARIANCE_ANALYSIS].status == CloseTaskStatus.COMPLETED
    assert tasks_dict[CloseTaskType.ACCRUAL_REVIEW].status == CloseTaskStatus.COMPLETED
    assert tasks_dict[CloseTaskType.EXCEPTION_REVIEW].status == CloseTaskStatus.COMPLETED

    # 4. Inspect routed exceptions and evidence pack generation
    stmt_exc = (
        select(ExceptionRecord)
        .options(selectinload(ExceptionRecord.evidence))
        .where(
            ExceptionRecord.company_id == company.id,
            ExceptionRecord.close_run_id == close_run.id,
        )
    )
    exceptions = list((await db.scalars(stmt_exc)).all())
    assert len(exceptions) > 0

    router = ExceptionRouter(policy)
    decisions = router.route_all(exceptions, policy)

    # Validate routing tiers
    cfo_escalations = [d for d in decisions if d.routing == "CFO_ESCALATION"]
    human_reviews = [d for d in decisions if d.routing == "HUMAN_REVIEW"]
    auto_resolves = [d for d in decisions if d.routing == "AUTO_RESOLVE"]

    assert len(cfo_escalations) > 0, "Expected CFO escalation cases (e.g. payment fragmentation)"
    assert len(human_reviews) > 0, "Expected human review cases (e.g. quantity mismatches)"
    assert len(auto_resolves) > 0, "Expected auto-resolve routine cases"

    # Find the payment fragmentation exception (Demo Scenario 1)
    frag_exc = next((e for e in exceptions if e.type == ExceptionType.PAYMENT_FRAGMENTATION), None)
    assert frag_exc is not None
    assert frag_exc.financial_impact in (Decimal("1450000.00"), Decimal("500000.00"))

    # Generate evidence pack for payment fragmentation
    pack_router = EvidencePackRouter()
    pack = await pack_router.generate_evidence_pack(db, company.id, frag_exc)
    assert pack["exception_id"] == str(frag_exc.id)
    assert pack["ranked_nodes_count"] > 0
    assert "### FINANCIAL EVIDENCE DOSSIER" in pack["markdown_dossier"]
    assert "PAYMENT_FRAGMENTATION" in pack["markdown_dossier"]

    # 5. Check Close Readiness before human review (Must be BLOCKED)
    readiness_before = await controller.evaluate_readiness(close_run.id)
    assert readiness_before.is_ready is False
    assert readiness_before.blocking_exceptions > 0
    assert readiness_before.financial_impact_at_risk > Decimal("0.00")
    assert len(readiness_before.blockers) > 0

    # 6. Human Review Checkpoint: CFO reviews and approves all blocking open exceptions
    blocking_open_exceptions = [
        e for e in exceptions if any(d.exception_id == e.id and d.is_blocking for d in decisions)
    ]
    for b_exc in blocking_open_exceptions:
        await controller.submit_human_review(
            close_run_id=close_run.id,
            exception_id=b_exc.id,
            decision="APPROVED",
            actor="cfo@novascale.ai",
            notes="Reviewed evidence dossier and approved variance resolution.",
        )

    # Refresh close run
    await db.refresh(close_run)

    # 7. Verify close run transitions and completes
    # Once human reviews were submitted, the controller unblocks and resumes workflow
    assert close_run.status in (CloseRunStatus.FINAL_VERIFICATION, CloseRunStatus.READY_TO_CLOSE)

    # If in FINAL_VERIFICATION, execute to produce final package
    if close_run.status != CloseRunStatus.READY_TO_CLOSE:
        close_run = await controller.execute_workflow(close_run.id, stop_at_human_review=False)

    assert close_run.status == CloseRunStatus.READY_TO_CLOSE

    # 8. Verify structured close package in close_run.close_summary
    assert close_run.close_summary is not None
    package_data = json.loads(close_run.close_summary)
    assert package_data["status"] == CloseRunStatus.READY_TO_CLOSE.value
    assert package_data["readiness"]["is_ready"] is True
    assert package_data["readiness"]["blocking_exceptions"] == 0
    assert len(package_data["tasks"]) == 10

    # 9. Verify versioned audit trail has recorded key milestones
    events = await audit_service.list(close_run_id=close_run.id, limit=200)
    assert len(events) >= 15
    event_types = {e.event_type for e in events}
    assert AuditEventType.CLOSE_RUN_STATE_CHANGE in event_types
    assert AuditEventType.CLOSE_TASK_STATE_CHANGE in event_types
    assert AuditEventType.APPROVAL in event_types
