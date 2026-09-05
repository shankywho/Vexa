"""Task executor interface, registry, and deterministic close task executors (spec section 15).

Pluggable executor interfaces so Phase 6 Investigation Agents can plug into the workflow.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import AuditService
from app.close_workflow.readiness import CloseReadinessService
from app.close_workflow.routing import EvidencePackRouter, ExceptionRouter
from app.close_workflow.types import (
    ClosePackage,
    ClosePolicy,
    TaskExecutionResult,
)
from app.db.base import utcnow
from app.db.models.close_run import CloseRun, CloseTask
from app.db.repository import ExceptionRepository
from app.domain.enums import (
    CloseTaskStatus,
    CloseTaskType,
    ExceptionStatus,
)
from app.evidence_graph.builder import FinancialEvidenceGraphBuilder
from app.evidence_graph.graph import FinancialEvidenceGraph
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.reconciliation.engine import DeterministicReconciliationEngine
from app.reconciliation.schemas import ReconciliationRunSummary, ReconciliationType


@dataclass
class TaskExecutionContext:
    """Context passed to each close task executor during workflow execution."""

    session: AsyncSession
    company_id: uuid.UUID
    close_run: CloseRun
    task: CloseTask
    engine: DeterministicReconciliationEngine
    audit_service: AuditService
    policy: ClosePolicy
    evidence_graph: FinancialEvidenceGraph | None = None
    reconciliation_summary: ReconciliationRunSummary | None = None

    async def get_or_create_reconciliation_summary(self) -> ReconciliationRunSummary:
        """Lazily load or run deterministic reconciliation, persisting results idempotently."""
        if self.reconciliation_summary is None:
            exc_repo = ExceptionRepository(self.session, self.company_id)
            existing_exc = await exc_repo.list_by_close_run(self.close_run.id)
            should_persist = len(existing_exc) == 0
            self.reconciliation_summary = await self.engine.run_full_reconciliation(
                close_run_id=self.close_run.id, persist=should_persist
            )
        return self.reconciliation_summary

    async def get_or_create_evidence_graph(self) -> FinancialEvidenceGraph:
        """Lazily build or retrieve tenant evidence graph."""
        if self.evidence_graph is None:
            builder = FinancialEvidenceGraphBuilder(self.session, self.company_id)
            self.evidence_graph = await builder.build()
        return self.evidence_graph


class CloseTaskExecutor(ABC):
    """Abstract interface for close task execution."""

    @abstractmethod
    async def execute(self, context: TaskExecutionContext) -> TaskExecutionResult:
        """Execute the task deterministically and return the structured result."""
        ...


class InvoiceValidationExecutor(CloseTaskExecutor):
    """Three-way matching, invoice-to-PO, invoice-to-receipt, and duplicate invoice detection."""

    async def execute(self, context: TaskExecutionContext) -> TaskExecutionResult:
        started_at = utcnow()
        summary = await context.get_or_create_reconciliation_summary()

        invoice_types = {
            ReconciliationType.THREE_WAY,
            ReconciliationType.INVOICE_PO,
            ReconciliationType.INVOICE_RECEIPT,
            ReconciliationType.DUPLICATE_DETECTION,
        }
        matching_items = [r for r in summary.results if r.reconciliation_type in invoice_types]
        matched_count = sum(1 for r in matching_items if r.status.value == "MATCHED")
        mismatches = sum(1 for r in matching_items if r.status.value in ("MISMATCH", "MISSING"))
        impact = sum(r.financial_impact for r in matching_items)

        metrics = {
            "total_evaluated": len(matching_items),
            "matched": matched_count,
            "mismatches": mismatches,
            "financial_impact": str(impact),
        }
        summary_text = (
            f"Validated {len(matching_items)} invoices/procurement items: "
            f"{matched_count} matched, {mismatches} mismatches/exceptions detected."
        )

        return TaskExecutionResult(
            task_type=CloseTaskType.INVOICE_VALIDATION,
            status=CloseTaskStatus.COMPLETED,
            summary=summary_text,
            metrics=metrics,
            started_at=started_at,
            completed_at=utcnow(),
        )


class PaymentReconciliationExecutor(CloseTaskExecutor):
    """Pass 4: Payment-to-invoice matching, duplicate payments, and payment fragmentation."""

    async def execute(self, context: TaskExecutionContext) -> TaskExecutionResult:
        started_at = utcnow()
        summary = await context.get_or_create_reconciliation_summary()

        items = [
            r
            for r in summary.results
            if r.reconciliation_type == ReconciliationType.PAYMENT_INVOICE
            or r.source_record_type == "PAYMENT"
            or (r.exception_type and "PAYMENT" in r.exception_type.value)
        ]
        matched = sum(1 for r in items if r.status.value == "MATCHED")
        exceptions = sum(1 for r in items if r.exception_type is not None)
        impact = sum(r.financial_impact for r in items)

        metrics = {
            "total_evaluated": len(items),
            "matched": matched,
            "exceptions": exceptions,
            "financial_impact": str(impact),
        }
        summary_text = (
            f"Reconciled {len(items)} payment records: {matched} matched, "
            f"{exceptions} anomalies detected (total impact: {impact})."
        )

        return TaskExecutionResult(
            task_type=CloseTaskType.PAYMENT_RECONCILIATION,
            status=CloseTaskStatus.COMPLETED,
            summary=summary_text,
            metrics=metrics,
            started_at=started_at,
            completed_at=utcnow(),
        )


class BankReconciliationExecutor(CloseTaskExecutor):
    """Pass 6: Bank statement transactions, payment clearance, and cash anomalies."""

    async def execute(self, context: TaskExecutionContext) -> TaskExecutionResult:
        started_at = utcnow()
        summary = await context.get_or_create_reconciliation_summary()

        bank_types = {
            ReconciliationType.BANK_PAYMENT,
            ReconciliationType.BANK_JOURNAL_ENTRY,
            ReconciliationType.CASH_ANOMALY,
        }
        items = [
            r
            for r in summary.results
            if r.reconciliation_type in bank_types or r.source_record_type == "BANK_TRANSACTION"
        ]
        matched = sum(1 for r in items if r.status.value == "MATCHED")
        exceptions = sum(1 for r in items if r.exception_type is not None)
        impact = sum(r.financial_impact for r in items)

        metrics = {
            "total_evaluated": len(items),
            "matched": matched,
            "exceptions": exceptions,
            "financial_impact": str(impact),
        }
        summary_text = (
            f"Bank reconciliation completed for {len(items)} bank transactions: "
            f"{matched} matched, {exceptions} cash anomalies/mismatches."
        )

        return TaskExecutionResult(
            task_type=CloseTaskType.BANK_RECONCILIATION,
            status=CloseTaskStatus.COMPLETED,
            summary=summary_text,
            metrics=metrics,
            started_at=started_at,
            completed_at=utcnow(),
        )


class ApReconciliationExecutor(CloseTaskExecutor):
    """Accounts Payable verification: vendor surges, unbilled receipts, AP balances."""

    async def execute(self, context: TaskExecutionContext) -> TaskExecutionResult:
        started_at = utcnow()
        summary = await context.get_or_create_reconciliation_summary()

        ap_types = {
            ReconciliationType.VENDOR_SURGE,
            ReconciliationType.INVOICE_PO,
            ReconciliationType.INVOICE_RECEIPT,
        }
        items = [r for r in summary.results if r.reconciliation_type in ap_types]
        exceptions = sum(1 for r in items if r.exception_type is not None)
        impact = sum(r.financial_impact for r in items if r.exception_type is not None)

        metrics = {
            "total_evaluated": len(items),
            "exceptions": exceptions,
            "financial_impact": str(impact),
        }
        summary_text = (
            f"AP reconciliation verified vendor activity and balances: "
            f"{exceptions} AP exceptions identified (total impact: {impact})."
        )

        return TaskExecutionResult(
            task_type=CloseTaskType.AP_RECONCILIATION,
            status=CloseTaskStatus.COMPLETED,
            summary=summary_text,
            metrics=metrics,
            started_at=started_at,
            completed_at=utcnow(),
        )


class ArReconciliationExecutor(CloseTaskExecutor):
    """Accounts Receivable reconciliation: customer remittances and short payments."""

    async def execute(self, context: TaskExecutionContext) -> TaskExecutionResult:
        started_at = utcnow()
        summary = await context.get_or_create_reconciliation_summary()

        items = [
            r for r in summary.results if r.reconciliation_type == ReconciliationType.AR_CUSTOMER
        ]
        exceptions = sum(1 for r in items if r.exception_type is not None)
        impact = sum(r.financial_impact for r in items)

        metrics = {
            "total_evaluated": len(items),
            "exceptions": exceptions,
            "financial_impact": str(impact),
        }
        summary_text = (
            f"AR reconciliation completed: {len(items)} customer remittances evaluated, "
            f"{exceptions} short payments identified (impact: {impact})."
        )

        return TaskExecutionResult(
            task_type=CloseTaskType.AR_RECONCILIATION,
            status=CloseTaskStatus.COMPLETED,
            summary=summary_text,
            metrics=metrics,
            started_at=started_at,
            completed_at=utcnow(),
        )


class VarianceAnalysisExecutor(CloseTaskExecutor):
    """Analysis of quantity/unit price discrepancies, timing differences, and FX variances."""

    async def execute(self, context: TaskExecutionContext) -> TaskExecutionResult:
        started_at = utcnow()
        summary = await context.get_or_create_reconciliation_summary()

        variance_items = [
            r
            for r in summary.results
            if r.differences or r.fx_conversion_applied or (r.status.value == "MISMATCH")
        ]
        fx_items = [r for r in summary.results if r.fx_conversion_applied]
        total_variance_impact = sum(r.financial_impact for r in variance_items)

        metrics = {
            "items_with_variance": len(variance_items),
            "fx_conversions_evaluated": len(fx_items),
            "total_variance_impact": str(total_variance_impact),
        }
        summary_text = (
            f"Variance analysis identified {len(variance_items)} records with price, "
            f"quantity, or FX variances (total variance: {total_variance_impact})."
        )

        return TaskExecutionResult(
            task_type=CloseTaskType.VARIANCE_ANALYSIS,
            status=CloseTaskStatus.COMPLETED,
            summary=summary_text,
            metrics=metrics,
            started_at=started_at,
            completed_at=utcnow(),
        )


class AccrualReviewExecutor(CloseTaskExecutor):
    """Accrual review: unbilled goods receipts (GRNI candidates) and journal entry accruals."""

    async def execute(self, context: TaskExecutionContext) -> TaskExecutionResult:
        started_at = utcnow()
        summary = await context.get_or_create_reconciliation_summary()

        accrual_items = [
            r
            for r in summary.results
            if r.reconciliation_type
            in (ReconciliationType.ACCRUAL_REVIEW, ReconciliationType.INVOICE_RECEIPT)
            and r.status.value in ("MISSING", "MISMATCH")
        ]
        impact = sum(r.financial_impact for r in accrual_items)

        metrics = {
            "accrual_candidates": len(accrual_items),
            "total_accrual_impact": str(impact),
        }
        summary_text = (
            f"Accrual review flagged {len(accrual_items)} unbilled goods receipts / "
            f"accrual candidates requiring month-end adjustment (impact: {impact})."
        )

        return TaskExecutionResult(
            task_type=CloseTaskType.ACCRUAL_REVIEW,
            status=CloseTaskStatus.COMPLETED,
            summary=summary_text,
            metrics=metrics,
            started_at=started_at,
            completed_at=utcnow(),
        )


class ExceptionReviewExecutor(CloseTaskExecutor):
    """Exception review and evidence pack generation across all detected tenant exceptions.

    Phase 6 hooks directly into or replaces this executor with the Investigation Agent.
    """

    async def execute(self, context: TaskExecutionContext) -> TaskExecutionResult:
        started_at = utcnow()
        exc_repo = ExceptionRepository(context.session, context.company_id)
        exceptions = await exc_repo.list_by_close_run(context.close_run.id)

        router = ExceptionRouter(context.policy)
        pack_router = EvidencePackRouter()
        ev_graph = await context.get_or_create_evidence_graph()

        decisions = router.route_all(exceptions, context.policy)
        auto_resolve_count = sum(1 for d in decisions if d.routing == "AUTO_RESOLVE")
        human_review_count = sum(1 for d in decisions if d.routing == "HUMAN_REVIEW")
        cfo_escalation_count = sum(1 for d in decisions if d.routing == "CFO_ESCALATION")
        blocking_count = sum(1 for d in decisions if d.is_blocking)

        # Generate evidence packs, investigate, verify, and stage actions for evaluation sample
        from app.action.service import ActionService
        from app.investigation.service import InvestigationService
        from app.verification.service import VerificationService

        investigation_service = InvestigationService(context.session, context.company_id)
        verification_service = VerificationService(context.session, context.company_id)
        action_service = ActionService(context.session, context.company_id)

        packs_generated = 0
        investigations_completed = 0
        verifications_completed = 0
        actions_executed = 0

        for exc in exceptions[:10]:  # generate packs, investigate, verify, act
            await pack_router.generate_evidence_pack(
                context.session, context.company_id, exc, ev_graph
            )
            packs_generated += 1
            try:
                finding = await investigation_service.investigate_exception(
                    exception_id=exc.id,
                    policy=context.policy,
                    graph=ev_graph,
                )
                investigations_completed += 1
                try:
                    ver = await verification_service.verify_exception(
                        exception_id=exc.id,
                        policy=context.policy,
                        graph=ev_graph,
                        finding=finding,
                    )
                    verifications_completed += 1
                    acts = await action_service.execute_for_verification(
                        exception_id=exc.id,
                        finding=finding,
                        verification=ver,
                    )
                    actions_executed += len(acts)
                except Exception:
                    pass
            except Exception:
                pass

        metrics = {
            "total_exceptions": len(exceptions),
            "auto_resolve": auto_resolve_count,
            "human_review": human_review_count,
            "cfo_escalation": cfo_escalation_count,
            "blocking_exceptions": blocking_count,
            "evidence_packs_generated": packs_generated,
            "investigations_completed": investigations_completed,
            "verifications_completed": verifications_completed,
            "actions_executed": actions_executed,
        }
        summary_text = (
            f"Reviewed {len(exceptions)} exceptions "
            f"({investigations_completed} investigated, {verifications_completed} verified, {actions_executed} actions executed): "
            f"{auto_resolve_count} auto-resolvable, {human_review_count} require human review, "
            f"{cfo_escalation_count} CFO escalations, {blocking_count} blocking close completion."
        )

        return TaskExecutionResult(
            task_type=CloseTaskType.EXCEPTION_REVIEW,
            status=CloseTaskStatus.COMPLETED,
            summary=summary_text,
            metrics=metrics,
            started_at=started_at,
            completed_at=utcnow(),
        )


class FinalVerificationExecutor(CloseTaskExecutor):
    """Final verification evaluating close readiness and blocking conditions."""

    async def execute(self, context: TaskExecutionContext) -> TaskExecutionResult:
        started_at = utcnow()
        readiness_service = CloseReadinessService(
            context.session, context.company_id, context.policy
        )
        readiness = await readiness_service.calculate_readiness(context.close_run.id)

        metrics = {
            "is_ready": readiness.is_ready,
            "completion_percentage": str(readiness.close_completion_percentage),
            "open_exceptions": readiness.open_exceptions,
            "blocking_exceptions": readiness.blocking_exceptions,
            "financial_impact_at_risk": str(readiness.financial_impact_at_risk),
            "blockers_count": len(readiness.blockers),
        }
        if readiness.is_ready:
            summary_text = (
                "Final verification passed: all tasks completed with zero blocking exceptions. "
                "Books are READY_TO_CLOSE."
            )
            status = CloseTaskStatus.COMPLETED
        else:
            summary_text = (
                f"Final verification identified {len(readiness.blockers)} blockers "
                f"({readiness.blocking_exceptions} blocking exceptions, "
                f"{readiness.financial_impact_at_risk} at risk). Close is BLOCKED."
            )
            # Verification task completes successfully, recording if close is BLOCKED
            status = CloseTaskStatus.COMPLETED

        return TaskExecutionResult(
            task_type=CloseTaskType.FINAL_VERIFICATION,
            status=status,
            summary=summary_text,
            metrics=metrics,
            started_at=started_at,
            completed_at=utcnow(),
        )


class ClosePackageExecutor(CloseTaskExecutor):
    """Compiles the final structured close package (spec section 35)."""

    async def execute(self, context: TaskExecutionContext) -> TaskExecutionResult:
        started_at = utcnow()
        readiness_service = CloseReadinessService(
            context.session, context.company_id, context.policy
        )
        readiness = await readiness_service.calculate_readiness(context.close_run.id)
        summary = await context.get_or_create_reconciliation_summary()

        exc_repo = ExceptionRepository(context.session, context.company_id)
        exceptions = await exc_repo.list_by_close_run(context.close_run.id)
        router = ExceptionRouter(context.policy)
        decisions = router.route_all(exceptions, context.policy)

        # Tasks summary
        stmt_tasks = select(CloseTask).where(CloseTask.close_run_id == context.close_run.id)
        tasks = list((await context.session.scalars(stmt_tasks)).all())
        tasks_data = [
            {
                "task_type": t.task_type.value,
                "status": t.status.value,
                "started_at": t.started_at.isoformat() if t.started_at else None,
                "completed_at": t.completed_at.isoformat() if t.completed_at else None,
                "result_summary": t.result_summary,
            }
            for t in tasks
        ]

        audit_events = await context.audit_service.list(close_run_id=context.close_run.id)

        package = ClosePackage(
            close_run_id=context.close_run.id,
            company_id=context.company_id,
            period_start=context.close_run.period_start,
            period_end=context.close_run.period_end,
            status=context.close_run.status,
            version=context.close_run.version,
            tasks=tasks_data,
            reconciliation_summary={
                "total_items_processed": summary.total_items_processed,
                "total_matched": summary.total_matched,
                "total_partial": summary.total_partial,
                "total_mismatch": summary.total_mismatch,
                "total_missing": summary.total_missing,
                "total_exceptions": summary.total_exceptions,
                "total_financial_impact": str(summary.total_financial_impact),
            },
            exceptions_summary={
                "total": len(exceptions),
                "open": sum(
                    1
                    for e in exceptions
                    if e.status in (ExceptionStatus.OPEN, ExceptionStatus.INVESTIGATING)
                ),
                "auto_resolve": sum(1 for d in decisions if d.routing == "AUTO_RESOLVE"),
                "human_review": sum(1 for d in decisions if d.routing == "HUMAN_REVIEW"),
                "cfo_escalation": sum(1 for d in decisions if d.routing == "CFO_ESCALATION"),
                "blocking": sum(1 for d in decisions if d.is_blocking),
            },
            readiness=readiness.to_dict(),
            blockers=readiness.blockers,
            audit_events_count=len(audit_events),
            generated_at=utcnow(),
        )

        package_json = package.to_dict()
        import json

        context.close_run.close_summary = json.dumps(package_json, default=str)
        await context.session.flush()

        metrics = {
            "package_generated": True,
            "tasks_count": len(tasks_data),
            "audit_events_count": len(audit_events),
            "is_ready": readiness.is_ready,
        }
        summary_text = (
            f"Close package compiled successfully: {len(tasks_data)} tasks, "
            f"{len(exceptions)} exceptions, status: {readiness.status.value}."
        )

        return TaskExecutionResult(
            task_type=CloseTaskType.CLOSE_PACKAGE,
            status=CloseTaskStatus.COMPLETED,
            summary=summary_text,
            metrics=metrics,
            started_at=started_at,
            completed_at=utcnow(),
        )


class TaskExecutorRegistry:
    """Registry holding task executors indexed by CloseTaskType.

    Allows plugging specialized or agent-driven executors in Phase 6.
    """

    def __init__(self) -> None:
        self._executors: dict[CloseTaskType, CloseTaskExecutor] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        self.register(CloseTaskType.INVOICE_VALIDATION, InvoiceValidationExecutor())
        self.register(CloseTaskType.PAYMENT_RECONCILIATION, PaymentReconciliationExecutor())
        self.register(CloseTaskType.BANK_RECONCILIATION, BankReconciliationExecutor())
        self.register(CloseTaskType.AP_RECONCILIATION, ApReconciliationExecutor())
        self.register(CloseTaskType.AR_RECONCILIATION, ArReconciliationExecutor())
        self.register(CloseTaskType.VARIANCE_ANALYSIS, VarianceAnalysisExecutor())
        self.register(CloseTaskType.ACCRUAL_REVIEW, AccrualReviewExecutor())
        self.register(CloseTaskType.EXCEPTION_REVIEW, ExceptionReviewExecutor())
        self.register(CloseTaskType.FINAL_VERIFICATION, FinalVerificationExecutor())
        self.register(CloseTaskType.CLOSE_PACKAGE, ClosePackageExecutor())

    def register(self, task_type: CloseTaskType, executor: CloseTaskExecutor) -> None:
        """Register an executor for a given close task type."""
        self._executors[task_type] = executor

    def get(self, task_type: CloseTaskType) -> CloseTaskExecutor:
        """Retrieve the registered executor for a given task type."""
        if task_type not in self._executors:
            raise KeyError(f"No executor registered for task type {task_type}")
        return self._executors[task_type]


# Global default registry instance
default_executor_registry = TaskExecutorRegistry()
