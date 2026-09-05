"""Types, schemas, and policies for the autonomous close workflow (spec sections 12, 14, 34)."""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from app.domain.enums import (
    AutonomyLevel,
    CloseRunStatus,
    CloseTaskStatus,
    CloseTaskType,
    ExceptionSeverity,
    ExceptionType,
)

# Default close-task catalogue created with every close run (spec section 15).
DEFAULT_CLOSE_TASKS: list[CloseTaskType] = [
    CloseTaskType.BANK_RECONCILIATION,
    CloseTaskType.AP_RECONCILIATION,
    CloseTaskType.AR_RECONCILIATION,
    CloseTaskType.INVOICE_VALIDATION,
    CloseTaskType.PAYMENT_RECONCILIATION,
    CloseTaskType.VARIANCE_ANALYSIS,
    CloseTaskType.ACCRUAL_REVIEW,
    CloseTaskType.EXCEPTION_REVIEW,
    CloseTaskType.FINAL_VERIFICATION,
    CloseTaskType.CLOSE_PACKAGE,
]


@dataclass
class ClosePolicy:
    """Configurable close policy and autonomy thresholds (spec section 12)."""

    max_auto_resolution_amount: Decimal = Decimal("50000.00")
    min_confidence: Decimal = Decimal("0.95")
    high_impact_requires_human: bool = True
    materiality_threshold: Decimal = Decimal("100000.00")
    blocking_exception_types: set[ExceptionType] = field(
        default_factory=lambda: {
            ExceptionType.PAYMENT_FRAGMENTATION,
            ExceptionType.UNUSUAL_VENDOR_ACTIVITY,
            ExceptionType.DUPLICATE_PAYMENT,
            ExceptionType.CASH_ANOMALY,
            ExceptionType.BANK_GL_MISMATCH,
        }
    )
    policy_version_id: str = "policy-v1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_auto_resolution_amount": str(self.max_auto_resolution_amount),
            "min_confidence": str(self.min_confidence),
            "high_impact_requires_human": self.high_impact_requires_human,
            "materiality_threshold": str(self.materiality_threshold),
            "blocking_exception_types": [t.value for t in self.blocking_exception_types],
            "policy_version_id": self.policy_version_id,
        }


@dataclass
class TaskExecutionResult:
    """Output contract of a close task execution."""

    task_type: CloseTaskType
    status: CloseTaskStatus
    summary: str
    metrics: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_type": self.task_type.value,
            "status": self.status.value,
            "summary": self.summary,
            "metrics": self.metrics,
            "error_message": self.error_message,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass
class ExceptionRoutingDecision:
    """Routing and autonomy classification for an exception (spec section 11)."""

    exception_id: uuid.UUID
    exception_type: ExceptionType
    severity: ExceptionSeverity
    financial_impact: Decimal
    routing: str  # AUTO_RESOLVE | HUMAN_REVIEW | CFO_ESCALATION
    autonomy_level: AutonomyLevel
    is_blocking: bool
    reason: str
    evidence_ids: list[str] = field(default_factory=list)
    evidence_summary: str | None = None
    evidence_pack: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "exception_id": str(self.exception_id),
            "exception_type": self.exception_type.value,
            "severity": self.severity.value,
            "financial_impact": str(self.financial_impact),
            "routing": self.routing,
            "autonomy_level": self.autonomy_level.value,
            "is_blocking": self.is_blocking,
            "reason": self.reason,
            "evidence_ids": self.evidence_ids,
            "evidence_summary": self.evidence_summary,
            "evidence_pack": self.evidence_pack,
        }


@dataclass
class CloseReadiness:
    """Close readiness metrics and blocking status calculation (spec section 34)."""

    is_ready: bool
    status: CloseRunStatus
    close_completion_percentage: Decimal
    total_tasks: int
    completed_tasks: int
    pending_tasks: int
    failed_tasks: int
    blocked_tasks: int
    total_exceptions: int
    open_exceptions: int
    blocking_exceptions: int
    unreviewed_material_items: int
    pending_approvals: int
    financial_impact_at_risk: Decimal
    blockers: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_ready": self.is_ready,
            "status": self.status.value,
            "close_completion_percentage": str(self.close_completion_percentage),
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "pending_tasks": self.pending_tasks,
            "failed_tasks": self.failed_tasks,
            "blocked_tasks": self.blocked_tasks,
            "total_exceptions": self.total_exceptions,
            "open_exceptions": self.open_exceptions,
            "blocking_exceptions": self.blocking_exceptions,
            "unreviewed_material_items": self.unreviewed_material_items,
            "pending_approvals": self.pending_approvals,
            "financial_impact_at_risk": str(self.financial_impact_at_risk),
            "blockers": self.blockers,
            "details": self.details,
        }


@dataclass
class ClosePackage:
    """Structured month-end close package (spec section 35)."""

    close_run_id: uuid.UUID
    company_id: uuid.UUID
    period_start: date
    period_end: date
    status: CloseRunStatus
    version: int
    tasks: list[dict[str, Any]]
    reconciliation_summary: dict[str, Any]
    exceptions_summary: dict[str, Any]
    readiness: dict[str, Any]
    blockers: list[str]
    audit_events_count: int
    generated_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "close_run_id": str(self.close_run_id),
            "company_id": str(self.company_id),
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "status": self.status.value,
            "version": self.version,
            "tasks": self.tasks,
            "reconciliation_summary": self.reconciliation_summary,
            "exceptions_summary": self.exceptions_summary,
            "readiness": self.readiness,
            "blockers": self.blockers,
            "audit_events_count": self.audit_events_count,
            "generated_at": self.generated_at.isoformat(),
        }


@dataclass
class WorkflowEvent:
    """Structured workflow event for observability and audit trail."""

    event_type: str
    close_run_id: uuid.UUID
    company_id: uuid.UUID
    timestamp: datetime
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
