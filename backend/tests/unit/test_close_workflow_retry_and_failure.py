"""Unit tests for close workflow retry, idempotency, and failure isolation (spec 31, 32)."""

from __future__ import annotations

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.close_workflow.controller import CloseWorkflowController
from app.close_workflow.executor import (
    CloseTaskExecutor,
    TaskExecutionContext,
    TaskExecutorRegistry,
)
from app.close_workflow.types import TaskExecutionResult
from app.db.models.close_run import CloseRun, CloseTask
from app.db.models.tenancy import Company
from app.domain.enums import (
    CloseRunStatus,
    CloseTaskStatus,
    CloseTaskType,
)


class FailingTaskExecutor(CloseTaskExecutor):
    """Test executor that deliberately simulates a tool timeout or database error."""

    async def execute(self, context: TaskExecutionContext) -> TaskExecutionResult:
        raise RuntimeError("Simulated transient connection timeout during reconciliation")


async def test_idempotent_close_run_creation(db: AsyncSession) -> None:
    company = Company(name="Idempotency Co", base_currency="USD", is_active=True)
    db.add(company)
    await db.flush()

    controller = CloseWorkflowController(db, company.id)
    run_1 = await controller.create_or_get_close_run(
        period_start=date(2026, 4, 1), period_end=date(2026, 4, 30)
    )
    run_2 = await controller.create_or_get_close_run(
        period_start=date(2026, 4, 1), period_end=date(2026, 4, 30)
    )

    assert run_1.id == run_2.id
    assert run_1.version == run_2.version


async def test_workflow_no_op_on_closed_run(db: AsyncSession) -> None:
    company = Company(name="Closed Run Co", base_currency="USD", is_active=True)
    db.add(company)
    await db.flush()

    close_run = CloseRun(
        company_id=company.id,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 1, 31),
        status=CloseRunStatus.CLOSED,
        version=10,
    )
    db.add(close_run)
    await db.flush()

    controller = CloseWorkflowController(db, company.id)
    result = await controller.execute_workflow(close_run.id)

    assert result.status == CloseRunStatus.CLOSED
    assert result.version == 10  # Untouched


async def test_task_failure_marks_task_failed_and_closes_failed(
    db: AsyncSession,
) -> None:
    company = Company(name="Failure Handling Co", base_currency="USD", is_active=True)
    db.add(company)
    await db.flush()

    # Custom registry with a failing executor for INVOICE_VALIDATION
    registry = TaskExecutorRegistry()
    registry.register(CloseTaskType.INVOICE_VALIDATION, FailingTaskExecutor())

    controller = CloseWorkflowController(db, company.id, registry=registry)
    run = await controller.create_or_get_close_run(
        period_start=date(2026, 5, 1), period_end=date(2026, 5, 31)
    )

    result_run = await controller.execute_workflow(run.id)

    # Close run should transition to FAILED
    assert result_run.status == CloseRunStatus.FAILED

    tasks_dict = await controller.state_machine.get_tasks(run.id)
    inv_task = tasks_dict[CloseTaskType.INVOICE_VALIDATION]
    assert inv_task.status == CloseTaskStatus.FAILED
    assert "Simulated transient connection timeout" in (inv_task.result_summary or "")


async def test_retry_task_resets_downstream_dependents(db: AsyncSession) -> None:
    company = Company(name="Retry Co", base_currency="USD", is_active=True)
    db.add(company)
    await db.flush()

    close_run = CloseRun(
        company_id=company.id,
        period_start=date(2026, 6, 1),
        period_end=date(2026, 6, 30),
        status=CloseRunStatus.FAILED,
        version=4,
    )
    db.add(close_run)
    await db.flush()

    # Create tasks: INVOICE_VALIDATION failed, downstream tasks blocked/pending
    task_inv = CloseTask(
        close_run_id=close_run.id,
        task_type=CloseTaskType.INVOICE_VALIDATION,
        status=CloseTaskStatus.FAILED,
    )
    task_pmt = CloseTask(
        close_run_id=close_run.id,
        task_type=CloseTaskType.PAYMENT_RECONCILIATION,
        status=CloseTaskStatus.BLOCKED,
    )
    task_final = CloseTask(
        close_run_id=close_run.id,
        task_type=CloseTaskType.FINAL_VERIFICATION,
        status=CloseTaskStatus.BLOCKED,
    )
    db.add_all([task_inv, task_pmt, task_final])
    await db.flush()

    controller = CloseWorkflowController(db, company.id)

    # Verify downstream dependents
    downstream = controller.resolver.get_downstream_dependents(CloseTaskType.INVOICE_VALIDATION)
    assert CloseTaskType.PAYMENT_RECONCILIATION in downstream
    assert CloseTaskType.FINAL_VERIFICATION in downstream
