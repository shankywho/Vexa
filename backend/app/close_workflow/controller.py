"""Close workflow controller orchestrating month-end close (spec sections 14, 15, 34)."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import AuditService
from app.close_workflow.dependencies import TaskDependencyResolver
from app.close_workflow.executor import (
    ClosePackageExecutor,
    TaskExecutionContext,
    TaskExecutorRegistry,
    default_executor_registry,
)
from app.close_workflow.readiness import CloseReadinessService
from app.close_workflow.routing import ExceptionRouter
from app.close_workflow.state_machine import (
    CloseRunError,
    CloseWorkflowStateMachine,
)
from app.close_workflow.types import (
    DEFAULT_CLOSE_TASKS,
    ClosePackage,
    ClosePolicy,
    CloseReadiness,
    TaskExecutionResult,
)
from app.db.base import utcnow
from app.db.models.close_run import CloseRun, CloseTask
from app.db.models.exception import ExceptionRecord
from app.db.models.tenancy import Company
from app.db.repository import ExceptionRepository
from app.domain.enums import (
    AuditEventType,
    CloseRunStatus,
    CloseTaskStatus,
    CloseTaskType,
    ExceptionStatus,
)
from app.evidence_graph.graph import FinancialEvidenceGraph
from app.reconciliation.schemas import ReconciliationRunSummary

logger = logging.getLogger(__name__)


class CloseWorkflowController:
    """Orchestrates month-end close workflows, deterministic tasks, and human checkpoints."""

    def __init__(
        self,
        session: AsyncSession,
        company_id: uuid.UUID,
        policy: ClosePolicy | None = None,
        registry: TaskExecutorRegistry | None = None,
        audit_service: AuditService | None = None,
    ) -> None:
        from app.reconciliation.engine import DeterministicReconciliationEngine

        self.session = session
        self.company_id = company_id
        self.policy = policy or ClosePolicy()
        self.registry = registry or default_executor_registry
        self.audit_service = audit_service or AuditService(session, company_id)
        self.state_machine = CloseWorkflowStateMachine(
            session, company_id, self.audit_service, self.policy.policy_version_id
        )
        self.resolver = TaskDependencyResolver()
        self.readiness_service = CloseReadinessService(session, company_id, self.policy)
        self.engine = DeterministicReconciliationEngine(session, company_id)
        self._reconciliation_summary: ReconciliationRunSummary | None = None
        self._evidence_graph: FinancialEvidenceGraph | None = None

    async def _require_company(self) -> None:
        exists = await self.session.scalar(select(Company.id).where(Company.id == self.company_id))
        if exists is None:
            raise CloseRunError(f"Company {self.company_id} does not exist")

    async def create_or_get_close_run(self, *, period_start: date, period_end: date) -> CloseRun:
        """Create a close run idempotently for the period, seeding default tasks."""
        await self._require_company()
        existing = await self.session.scalar(
            select(CloseRun).where(
                CloseRun.company_id == self.company_id,
                CloseRun.period_start == period_start,
                CloseRun.period_end == period_end,
                CloseRun.status != CloseRunStatus.CLOSED,
            )
        )
        if existing is not None:
            return existing

        close_run = CloseRun(
            company_id=self.company_id,
            period_start=period_start,
            period_end=period_end,
            status=CloseRunStatus.CREATED,
            version=1,
        )
        self.session.add(close_run)
        await self.session.flush()

        for task_type in DEFAULT_CLOSE_TASKS:
            self.session.add(
                CloseTask(
                    close_run_id=close_run.id,
                    task_type=task_type,
                    status=CloseTaskStatus.PENDING,
                )
            )
        await self.session.flush()

        await self.audit_service.record(
            event_type=AuditEventType.CLOSE_RUN_STATE_CHANGE,
            actor="controller",
            actor_type="CONTROLLER",
            agent_name="close_controller",
            policy_version_id=self.policy.policy_version_id,
            close_run_id=close_run.id,
            decision=CloseRunStatus.CREATED.value,
            reason=f"Created close run for period {period_start} to {period_end}",
        )

        return close_run

    async def execute_workflow(
        self,
        close_run_id: uuid.UUID,
        *,
        max_steps: int = 30,
        stop_at_human_review: bool = True,
    ) -> CloseRun:
        """Execute close workflow tasks in dependency order until completion or human checkpoint."""
        close_run = await self.session.get(CloseRun, close_run_id)
        if close_run is None:
            raise CloseRunError(f"Close run {close_run_id} does not exist")
        if close_run.company_id != self.company_id:
            raise CloseRunError("Close run is not in this tenant")

        if close_run.status == CloseRunStatus.CLOSED:
            return close_run

        # Start close run if currently CREATED
        if close_run.status == CloseRunStatus.CREATED:
            close_run = await self.state_machine.transition_close_run(
                close_run.id,
                CloseRunStatus.INGESTING,
                reason="Starting month-end close workflow ingestion",
            )
            close_run = await self.state_machine.transition_close_run(
                close_run.id,
                CloseRunStatus.RECONCILING,
                reason="Beginning deterministic reconciliation tasks",
            )

        # Context shared across execution passes
        evidence_graph = self._evidence_graph
        reconciliation_summary = self._reconciliation_summary

        steps_taken = 0
        while steps_taken < max_steps:
            steps_taken += 1

            # Fetch tasks and check dependencies
            tasks_dict = await self.state_machine.get_tasks(close_run.id)
            task_statuses = {t_type: task.status for t_type, task in tasks_dict.items()}

            ready_task_types = self.resolver.get_ready_tasks(task_statuses)
            blocked_task_types = self.resolver.get_blocked_tasks(task_statuses)

            # Mark blocked tasks
            for b_type in blocked_task_types:
                b_task = tasks_dict[b_type]
                if b_task.status == CloseTaskStatus.PENDING:
                    await self.state_machine.transition_task(
                        b_task.id,
                        CloseTaskStatus.BLOCKED,
                        error_message="Blocked by failed or blocked prerequisite task",
                    )

            if not ready_task_types:
                # No more ready tasks. Check if all tasks are complete
                break

            # Advance close run status based on current tasks
            if CloseTaskType.EXCEPTION_REVIEW in ready_task_types:
                if close_run.status == CloseRunStatus.RECONCILING:
                    close_run = await self.state_machine.transition_close_run(
                        close_run.id,
                        CloseRunStatus.INVESTIGATING,
                        reason="Reconciliation completed; analyzing exceptions",
                    )
            elif CloseTaskType.FINAL_VERIFICATION in ready_task_types:
                if close_run.status in (CloseRunStatus.INVESTIGATING, CloseRunStatus.RESOLVING):
                    close_run = await self.state_machine.transition_close_run(
                        close_run.id,
                        CloseRunStatus.FINAL_VERIFICATION,
                        reason="Verifying close completeness and readiness",
                    )

            # Execute the next ready task
            task_type_to_run = ready_task_types[0]
            task_to_run = tasks_dict[task_type_to_run]

            # Mark task IN_PROGRESS
            await self.state_machine.transition_task(task_to_run.id, CloseTaskStatus.IN_PROGRESS)

            context = TaskExecutionContext(
                session=self.session,
                company_id=self.company_id,
                close_run=close_run,
                task=task_to_run,
                engine=self.engine,
                audit_service=self.audit_service,
                policy=self.policy,
                evidence_graph=evidence_graph,
                reconciliation_summary=reconciliation_summary,
            )

            executor = self.registry.get(task_type_to_run)
            try:
                result = await executor.execute(context)
                # Cache shared summary and graph
                if context.reconciliation_summary:
                    reconciliation_summary = context.reconciliation_summary
                    self._reconciliation_summary = context.reconciliation_summary
                if context.evidence_graph:
                    evidence_graph = context.evidence_graph
                    self._evidence_graph = context.evidence_graph

                await self.state_machine.transition_task(
                    task_to_run.id,
                    result.status,
                    summary=result.summary,
                    metrics=result.metrics,
                    error_message=result.error_message,
                )
            except Exception as exc:
                logger.exception("Task %s execution failed: %s", task_type_to_run.value, exc)
                await self.state_machine.transition_task(
                    task_to_run.id,
                    CloseTaskStatus.FAILED,
                    summary=f"Task execution failed: {str(exc)}",
                    error_message=str(exc),
                )
                close_run = await self.state_machine.transition_close_run(
                    close_run.id,
                    CloseRunStatus.FAILED,
                    reason=f"Task {task_type_to_run.value} execution failed: {str(exc)}",
                )
                return close_run

            # Checkpoint: After EXCEPTION_REVIEW, evaluate if human review is required
            if task_type_to_run == CloseTaskType.EXCEPTION_REVIEW and stop_at_human_review:
                exc_repo = ExceptionRepository(self.session, self.company_id)
                exceptions = list(await exc_repo.list_by_close_run(close_run.id))
                router = ExceptionRouter(self.policy)
                decisions = router.route_all(exceptions, self.policy)
                human_needed = any(
                    d.routing in ("HUMAN_REVIEW", "CFO_ESCALATION")
                    and exc.status in (ExceptionStatus.OPEN, ExceptionStatus.INVESTIGATING)
                    for d, exc in zip(decisions, exceptions, strict=False)
                )

                if human_needed:
                    close_run = await self.state_machine.transition_close_run(
                        close_run.id,
                        CloseRunStatus.WAITING_FOR_HUMAN,
                        reason="Material exceptions require human approval before closing books",
                    )
                    return close_run

        # Evaluate readiness after tasks are processed
        readiness = await self.readiness_service.calculate_readiness(close_run.id)
        if readiness.is_ready:
            if close_run.status in (
                CloseRunStatus.FINAL_VERIFICATION,
                CloseRunStatus.RESOLVING,
                CloseRunStatus.WAITING_FOR_HUMAN,
                CloseRunStatus.BLOCKED,
            ):
                close_run = await self.state_machine.transition_close_run(
                    close_run.id,
                    CloseRunStatus.READY_TO_CLOSE,
                    reason="All tasks completed and zero blocking exceptions remain",
                )
                await self.generate_close_package(close_run.id)
        else:
            if close_run.status not in (
                CloseRunStatus.BLOCKED,
                CloseRunStatus.WAITING_FOR_HUMAN,
                CloseRunStatus.FAILED,
            ):
                close_run = await self.state_machine.transition_close_run(
                    close_run.id,
                    CloseRunStatus.BLOCKED,
                    reason=f"Close blocked: {len(readiness.blockers)} blocking condition(s)",
                )

        return close_run

    async def retry_task(
        self, close_run_id: uuid.UUID, task_type: CloseTaskType
    ) -> TaskExecutionResult:
        """Retry a failed or blocked task and reset any downstream dependent tasks to PENDING."""
        close_run = await self.session.get(CloseRun, close_run_id)
        if close_run is None:
            raise CloseRunError(f"Close run {close_run_id} does not exist")

        tasks_dict = await self.state_machine.get_tasks(close_run.id)
        if task_type not in tasks_dict:
            raise CloseRunError(f"Task {task_type} does not exist in close run")

        target_task = tasks_dict[task_type]

        # Reset downstream tasks
        downstream = self.resolver.get_downstream_dependents(task_type)
        for d_type in downstream:
            d_task = tasks_dict.get(d_type)
            if d_task and d_task.status != CloseTaskStatus.PENDING:
                await self.state_machine.transition_task(
                    d_task.id, CloseTaskStatus.PENDING, summary="Reset due to upstream task retry"
                )

        # Reset target task to PENDING
        await self.state_machine.transition_task(
            target_task.id, CloseTaskStatus.PENDING, summary="Retrying task"
        )

        # If close run was FAILED or BLOCKED, reset status to RECONCILING
        if close_run.status in (CloseRunStatus.FAILED, CloseRunStatus.BLOCKED):
            await self.state_machine.transition_close_run(
                close_run.id,
                CloseRunStatus.RECONCILING,
                reason=f"Resuming workflow after task {task_type.value} retry",
            )

        # Re-execute workflow
        await self.execute_workflow(close_run.id)
        await self.session.refresh(target_task)

        metrics = {}
        if target_task.result_summary:
            try:
                metrics = json.loads(target_task.result_summary).get("metrics", {})
            except Exception:
                pass

        return TaskExecutionResult(
            task_type=target_task.task_type,
            status=target_task.status,
            summary=target_task.result_summary or "Retried",
            metrics=metrics,
            started_at=target_task.started_at,
            completed_at=target_task.completed_at,
        )

    async def submit_human_review(
        self,
        close_run_id: uuid.UUID,
        exception_id: uuid.UUID,
        decision: str,  # RESOLVED | ESCALATED | REJECTED
        actor: str,
        notes: str | None = None,
    ) -> ExceptionRecord:
        """Submit a human decision for an exception (spec sections 11, 13.2)."""
        close_run = await self.session.get(CloseRun, close_run_id)
        if close_run is None:
            raise CloseRunError(f"Close run {close_run_id} does not exist")

        exception = await self.session.get(ExceptionRecord, exception_id)
        if exception is None or exception.company_id != self.company_id:
            raise CloseRunError(f"Exception {exception_id} does not exist in this tenant")

        old_status = exception.status
        if decision.upper() in ("APPROVED", "RESOLVED"):
            new_status = ExceptionStatus.RESOLVED
            exception.resolved_at = utcnow()
        elif decision.upper() == "ESCALATED":
            new_status = ExceptionStatus.ESCALATED
        else:
            new_status = ExceptionStatus.OPEN

        exception.status = new_status
        exception.assigned_to = actor
        await self.session.flush()

        # Audit event
        await self.audit_service.record(
            event_type=AuditEventType.APPROVAL,
            actor=actor,
            actor_type="USER",
            agent_name="human_reviewer",
            policy_version_id=self.policy.policy_version_id,
            close_run_id=close_run_id,
            exception_id=exception_id,
            decision=decision.upper(),
            reason=notes or f"Human review decision: {decision.upper()}",
            financial_impact=exception.financial_impact,
            currency=exception.currency,
            confidence=Decimal("1.0000"),
            metadata_={
                "previous_status": old_status.value,
                "new_status": new_status.value,
                "notes": notes,
            },
        )

        # Check if all blockers for the close run are now resolved
        readiness = await self.readiness_service.calculate_readiness(close_run_id)
        if readiness.blocking_exceptions == 0:
            if close_run.status in (CloseRunStatus.WAITING_FOR_HUMAN, CloseRunStatus.BLOCKED):
                await self.state_machine.transition_close_run(
                    close_run.id,
                    CloseRunStatus.RESOLVING,
                    reason="All human review blockers resolved",
                )
                await self.state_machine.transition_close_run(
                    close_run.id,
                    CloseRunStatus.FINAL_VERIFICATION,
                    reason="Proceeding to final verification after human approvals",
                )
                # Resume execution to complete remaining tasks
                await self.execute_workflow(close_run.id, stop_at_human_review=False)

        return exception

    async def evaluate_readiness(self, close_run_id: uuid.UUID) -> CloseReadiness:
        """Evaluate and return close readiness metrics."""
        return await self.readiness_service.calculate_readiness(close_run_id)

    async def generate_close_package(self, close_run_id: uuid.UUID) -> ClosePackage:
        """Compile and persist the structured close package."""
        executor = ClosePackageExecutor()
        close_run = await self.session.get(CloseRun, close_run_id)
        if close_run is None:
            raise CloseRunError(f"Close run {close_run_id} does not exist")

        tasks_dict = await self.state_machine.get_tasks(close_run_id)
        context = TaskExecutionContext(
            session=self.session,
            company_id=self.company_id,
            close_run=close_run,
            task=tasks_dict.get(CloseTaskType.CLOSE_PACKAGE)
            or CloseTask(
                close_run_id=close_run_id,
                task_type=CloseTaskType.CLOSE_PACKAGE,
                status=CloseTaskStatus.IN_PROGRESS,
            ),
            engine=self.engine,
            audit_service=self.audit_service,
            policy=self.policy,
            evidence_graph=self._evidence_graph,
            reconciliation_summary=self._reconciliation_summary,
        )
        await executor.execute(context)
        await self.session.refresh(close_run)

        package_dict = json.loads(close_run.close_summary or "{}")
        return ClosePackage(
            close_run_id=uuid.UUID(package_dict["close_run_id"]),
            company_id=uuid.UUID(package_dict["company_id"]),
            period_start=date.fromisoformat(package_dict["period_start"]),
            period_end=date.fromisoformat(package_dict["period_end"]),
            status=CloseRunStatus(package_dict["status"]),
            version=package_dict["version"],
            tasks=package_dict["tasks"],
            reconciliation_summary=package_dict["reconciliation_summary"],
            exceptions_summary=package_dict["exceptions_summary"],
            readiness=package_dict["readiness"],
            blockers=package_dict["blockers"],
            audit_events_count=package_dict["audit_events_count"],
            generated_at=datetime.fromisoformat(package_dict["generated_at"]),
        )

    async def investigate_exception(
        self,
        exception_id: uuid.UUID,
        *,
        provider: Any | None = None,
    ) -> Any:
        """Investigate a specific exception using the CFO Investigation Agent."""
        from app.investigation.service import InvestigationService

        await self._require_company()
        service = InvestigationService(self.session, self.company_id)
        return await service.investigate_exception(
            exception_id=exception_id,
            policy=self.policy,
            provider=provider,
            graph=self._evidence_graph,
        )

    async def verify_exception(
        self,
        exception_id: uuid.UUID,
        *,
        finding: Any | None = None,
    ) -> Any:
        """Independently verify an exception using the Verification Agent."""
        from app.verification.service import VerificationService

        await self._require_company()
        service = VerificationService(self.session, self.company_id)
        return await service.verify_exception(
            exception_id=exception_id,
            policy=self.policy,
            graph=self._evidence_graph,
            finding=finding,
        )

    async def execute_actions_for_exception(
        self,
        exception_id: uuid.UUID,
        *,
        finding: Any | None = None,
        verification: Any | None = None,
    ) -> Any:
        """Execute autonomous actions for an exception via Action Agent."""
        from app.action.service import ActionService
        from app.investigation.service import InvestigationService
        from app.verification.service import VerificationService

        await self._require_company()
        if finding is None:
            inv_service = InvestigationService(self.session, self.company_id)
            finding = await inv_service.investigate_exception(
                exception_id=exception_id, policy=self.policy, graph=self._evidence_graph
            )
        if verification is None:
            ver_service = VerificationService(self.session, self.company_id)
            verification = await ver_service.verify_exception(
                exception_id=exception_id,
                policy=self.policy,
                graph=self._evidence_graph,
                finding=finding,
            )

        act_service = ActionService(self.session, self.company_id)
        return await act_service.execute_for_verification(
            exception_id=exception_id, finding=finding, verification=verification
        )

    async def approve_exception(
        self,
        exception_id: uuid.UUID,
        *,
        actor: str = "controller",
        notes: str | None = None,
    ) -> Any:
        """Human approval of an exception resolution."""
        from app.action.service import ActionService

        await self._require_company()
        service = ActionService(self.session, self.company_id)
        return await service.approve_exception(exception_id=exception_id, actor=actor, notes=notes)

    async def reject_exception(
        self,
        exception_id: uuid.UUID,
        *,
        actor: str = "controller",
        notes: str | None = None,
    ) -> Any:
        """Human rejection of an exception resolution."""
        from app.action.service import ActionService

        await self._require_company()
        service = ActionService(self.session, self.company_id)
        return await service.reject_exception(exception_id=exception_id, actor=actor, notes=notes)

    async def escalate_exception(
        self,
        exception_id: uuid.UUID,
        *,
        target_role: str = "CFO",
        reason: str | None = None,
        actor: str = "controller",
    ) -> Any:
        """Escalate an exception to senior role."""
        from app.action.service import ActionService

        await self._require_company()
        service = ActionService(self.session, self.company_id)
        return await service.escalate_exception(
            exception_id=exception_id, target_role=target_role, reason=reason, actor=actor
        )

    async def reverse_action(
        self,
        action_id: uuid.UUID,
        *,
        reason: str,
        reversed_by: str = "controller",
    ) -> Any:
        """Roll back an executed or staged action (spec section 13.2)."""
        from app.action.service import ActionService

        await self._require_company()
        service = ActionService(self.session, self.company_id)
        return await service.reverse_action(
            action_id=action_id, reason=reason, reversed_by=reversed_by
        )
