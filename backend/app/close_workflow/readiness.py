"""Close readiness service calculating completion metrics and blocking status (spec 34)."""

from __future__ import annotations

import uuid
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.close_workflow.routing import ExceptionRouter
from app.close_workflow.types import ClosePolicy, CloseReadiness
from app.db.models.close_run import CloseRun, CloseTask
from app.db.models.exception import ExceptionRecord
from app.domain.enums import (
    CloseRunStatus,
    CloseTaskStatus,
    CloseTaskType,
    ExceptionStatus,
)


class CloseReadinessService:
    """Calculates close completion, open exceptions, and readiness criteria (spec section 34)."""

    def __init__(
        self,
        session: AsyncSession,
        company_id: uuid.UUID,
        policy: ClosePolicy | None = None,
    ) -> None:
        self.session = session
        self.company_id = company_id
        self.policy = policy or ClosePolicy()
        self.router = ExceptionRouter(self.policy)

    async def calculate_readiness(self, close_run_id: uuid.UUID) -> CloseReadiness:
        """Evaluate close tasks and exceptions to determine if the close run is READY_TO_CLOSE."""
        # 1. Fetch close run
        close_run = await self.session.get(CloseRun, close_run_id)
        if close_run is None:
            raise ValueError(f"Close run {close_run_id} does not exist")
        if close_run.company_id != self.company_id:
            raise ValueError("Close run is not in this tenant")

        # 2. Fetch tasks
        stmt_tasks = select(CloseTask).where(CloseTask.close_run_id == close_run_id)
        tasks = list((await self.session.scalars(stmt_tasks)).all())

        total_tasks = len(tasks)
        completed_tasks = sum(
            1
            for t in tasks
            if t.status == CloseTaskStatus.COMPLETED
            or (
                t.task_type == CloseTaskType.CLOSE_PACKAGE
                and t.status == CloseTaskStatus.IN_PROGRESS
            )
        )
        failed_tasks = sum(1 for t in tasks if t.status == CloseTaskStatus.FAILED)
        blocked_tasks = sum(1 for t in tasks if t.status == CloseTaskStatus.BLOCKED)
        pending_tasks = sum(
            1
            for t in tasks
            if t.status in (CloseTaskStatus.PENDING, CloseTaskStatus.IN_PROGRESS)
            and not (
                t.task_type == CloseTaskType.CLOSE_PACKAGE
                and t.status == CloseTaskStatus.IN_PROGRESS
            )
        )

        if total_tasks > 0:
            pct = (Decimal(completed_tasks) / Decimal(total_tasks)) * Decimal("100.00")
            completion_percentage = pct.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        else:
            completion_percentage = Decimal("0.00")

        # 3. Fetch exceptions for close run
        stmt_exc = (
            select(ExceptionRecord)
            .options(selectinload(ExceptionRecord.evidence))
            .where(
                ExceptionRecord.company_id == self.company_id,
                ExceptionRecord.close_run_id == close_run_id,
            )
        )
        exceptions = list((await self.session.scalars(stmt_exc)).all())

        total_exceptions = len(exceptions)
        open_exceptions = sum(
            1
            for e in exceptions
            if e.status
            in (ExceptionStatus.OPEN, ExceptionStatus.INVESTIGATING, ExceptionStatus.REOPENED)
        )

        blocking_exceptions = 0
        unreviewed_material_items = 0
        pending_approvals = 0
        financial_impact_at_risk = Decimal("0.00")
        blockers: list[str] = []

        # 4. Route and evaluate exceptions
        for exc in exceptions:
            decision = self.router.route_exception(exc, self.policy)

            # Check if blocking
            if decision.is_blocking:
                blocking_exceptions += 1
                financial_impact_at_risk += decision.financial_impact
                blockers.append(
                    f"Blocking exception [{exc.type.value}] ({exc.id}): {decision.reason}"
                )

            # Check human review and approvals
            if decision.routing in ("HUMAN_REVIEW", "CFO_ESCALATION"):
                if exc.status in (ExceptionStatus.OPEN, ExceptionStatus.INVESTIGATING):
                    unreviewed_material_items += 1
                if exc.status not in (ExceptionStatus.RESOLVED, ExceptionStatus.AUTO_RESOLVED):
                    pending_approvals += 1

        # 5. Check task-level blockers
        if failed_tasks > 0:
            blockers.append(f"{failed_tasks} task(s) failed during execution.")
        if blocked_tasks > 0:
            blockers.append(f"{blocked_tasks} task(s) are blocked by dependencies.")
        if completed_tasks < total_tasks:
            incomplete = total_tasks - completed_tasks
            blockers.append(f"{incomplete} task(s) remain incomplete.")

        # 6. Readiness decision
        is_ready = (
            (completed_tasks == total_tasks)
            and (failed_tasks == 0)
            and (blocked_tasks == 0)
            and (blocking_exceptions == 0)
        )

        status = CloseRunStatus.READY_TO_CLOSE if is_ready else CloseRunStatus.BLOCKED

        details: dict[str, Any] = {
            "close_run_id": str(close_run_id),
            "company_id": str(self.company_id),
            "current_status": close_run.status.value,
            "tasks_summary": {t.task_type.value: t.status.value for t in tasks},
        }

        return CloseReadiness(
            is_ready=is_ready,
            status=status,
            close_completion_percentage=completion_percentage,
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
            pending_tasks=pending_tasks,
            failed_tasks=failed_tasks,
            blocked_tasks=blocked_tasks,
            total_exceptions=total_exceptions,
            open_exceptions=open_exceptions,
            blocking_exceptions=blocking_exceptions,
            unreviewed_material_items=unreviewed_material_items,
            pending_approvals=pending_approvals,
            financial_impact_at_risk=financial_impact_at_risk,
            blockers=blockers,
            details=details,
        )
