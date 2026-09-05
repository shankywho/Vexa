"""Unit tests for close workflow state machine and CAS (spec sections 14, 15)."""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import AuditService
from app.close_workflow.state_machine import (
    CloseRunError,
    CloseTaskError,
    CloseWorkflowStateMachine,
)
from app.db.models.close_run import CloseRun, CloseTask
from app.db.models.tenancy import Company
from app.domain.enums import (
    AuditEventType,
    CloseRunStatus,
    CloseTaskStatus,
    CloseTaskType,
)


async def _create_test_env(
    db: AsyncSession, company_name: str = "SM Test Co"
) -> tuple[Company, CloseRun, CloseWorkflowStateMachine]:
    company = Company(name=company_name, base_currency="USD", is_active=True)
    db.add(company)
    await db.flush()

    close_run = CloseRun(
        company_id=company.id,
        period_start=date(2026, 3, 1),
        period_end=date(2026, 3, 31),
        status=CloseRunStatus.CREATED,
        version=1,
    )
    db.add(close_run)
    await db.flush()

    sm = CloseWorkflowStateMachine(db, company.id)
    return company, close_run, sm


async def test_valid_close_run_transitions(db: AsyncSession) -> None:
    _, run, sm = await _create_test_env(db, "Valid Transitions Co")

    # CREATED -> INGESTING -> RECONCILING -> INVESTIGATING -> VERIFYING
    # -> FINAL_VERIFICATION -> READY_TO_CLOSE -> CLOSED
    run = await sm.transition_close_run(run.id, CloseRunStatus.INGESTING)
    assert run.status == CloseRunStatus.INGESTING
    assert run.version == 2
    assert run.started_at is not None

    run = await sm.transition_close_run(run.id, CloseRunStatus.RECONCILING)
    assert run.status == CloseRunStatus.RECONCILING
    assert run.version == 3

    run = await sm.transition_close_run(run.id, CloseRunStatus.INVESTIGATING)
    assert run.status == CloseRunStatus.INVESTIGATING
    assert run.version == 4

    run = await sm.transition_close_run(run.id, CloseRunStatus.VERIFYING)
    assert run.status == CloseRunStatus.VERIFYING
    assert run.version == 5

    run = await sm.transition_close_run(run.id, CloseRunStatus.FINAL_VERIFICATION)
    assert run.status == CloseRunStatus.FINAL_VERIFICATION
    assert run.version == 6

    run = await sm.transition_close_run(run.id, CloseRunStatus.READY_TO_CLOSE)
    assert run.status == CloseRunStatus.READY_TO_CLOSE
    assert run.version == 7

    run = await sm.transition_close_run(run.id, CloseRunStatus.CLOSED)
    assert run.status == CloseRunStatus.CLOSED
    assert run.version == 8
    assert run.completed_at is not None


async def test_invalid_close_run_transitions_rejected(db: AsyncSession) -> None:
    _, run, sm = await _create_test_env(db, "Invalid Transitions Co")

    # CREATED cannot jump directly to CLOSED
    with pytest.raises(CloseRunError, match="Invalid transition"):
        await sm.transition_close_run(run.id, CloseRunStatus.CLOSED)

    # CREATED cannot jump directly to READY_TO_CLOSE
    with pytest.raises(CloseRunError, match="Invalid transition"):
        await sm.transition_close_run(run.id, CloseRunStatus.READY_TO_CLOSE)

    # CREATED -> INGESTING
    run = await sm.transition_close_run(run.id, CloseRunStatus.INGESTING)

    # INGESTING cannot jump to CLOSED
    with pytest.raises(CloseRunError, match="Invalid transition"):
        await sm.transition_close_run(run.id, CloseRunStatus.CLOSED)


async def test_cas_concurrency_failure_on_stale_version(db: AsyncSession) -> None:
    from sqlalchemy import text

    _, run, sm = await _create_test_env(db, "CAS Concurrency Co")

    # Another process updates the version in DB directly behind sm's back
    await db.execute(
        text("UPDATE close_runs SET version = version + 1 WHERE id = :id"),
        {"id": run.id},
    )
    with pytest.raises(CloseRunError, match="Concurrent modification"):
        await sm.transition_close_run(run.id, CloseRunStatus.INGESTING)


async def test_tenant_isolation_on_close_run(db: AsyncSession) -> None:
    _, run_a, _ = await _create_test_env(db, "Tenant A")

    company_b = Company(name="Tenant B", base_currency="USD", is_active=True)
    db.add(company_b)
    await db.flush()

    sm_b = CloseWorkflowStateMachine(db, company_b.id)
    with pytest.raises(CloseRunError, match="not in this tenant"):
        await sm_b.transition_close_run(run_a.id, CloseRunStatus.INGESTING)


async def test_close_task_lifecycle_transitions(db: AsyncSession) -> None:
    _, run, sm = await _create_test_env(db, "Task Lifecycle Co")

    task = CloseTask(
        close_run_id=run.id,
        task_type=CloseTaskType.INVOICE_VALIDATION,
        status=CloseTaskStatus.PENDING,
    )
    db.add(task)
    await db.flush()

    # PENDING -> IN_PROGRESS
    task = await sm.transition_task(task.id, CloseTaskStatus.IN_PROGRESS)
    assert task.status == CloseTaskStatus.IN_PROGRESS
    assert task.started_at is not None

    # IN_PROGRESS -> COMPLETED with summary and metrics
    metrics = {"items_validated": 45, "mismatches": 2}
    task = await sm.transition_task(
        task.id,
        CloseTaskStatus.COMPLETED,
        summary="Invoice validation finished cleanly",
        metrics=metrics,
    )
    assert task.status == CloseTaskStatus.COMPLETED
    assert task.completed_at is not None
    assert "items_validated" in task.result_summary

    # Invalid: COMPLETED cannot jump directly to IN_PROGRESS (must be reset to PENDING first)
    with pytest.raises(CloseTaskError, match="Invalid task transition"):
        await sm.transition_task(task.id, CloseTaskStatus.IN_PROGRESS)

    # Valid: COMPLETED -> PENDING (reset)
    task = await sm.transition_task(task.id, CloseTaskStatus.PENDING, summary="Task reset")
    assert task.status == CloseTaskStatus.PENDING


async def test_audit_events_recorded_on_state_transitions(db: AsyncSession) -> None:
    company, run, sm = await _create_test_env(db, "Audit SM Co")
    audit_service = AuditService(db, company.id)

    await sm.transition_close_run(run.id, CloseRunStatus.INGESTING, reason="Testing audit emission")

    events = await audit_service.list(
        close_run_id=run.id, event_type=AuditEventType.CLOSE_RUN_STATE_CHANGE
    )
    assert len(events) >= 1
    latest = events[0]
    assert latest.decision == CloseRunStatus.INGESTING.value
    assert "Testing audit emission" in (latest.reason or "")
