"""Vexa Autonomous Close Workflow package (Phase 5).

Coordinates month-end close using the financial data layer, deterministic reconciliation
engine, evidence graph, and controlled autonomy routing.
"""

from app.close_workflow.controller import CloseWorkflowController
from app.close_workflow.dependencies import (
    DEFAULT_TASK_DEPENDENCIES,
    TaskDependencyResolver,
)
from app.close_workflow.executor import (
    CloseTaskExecutor,
    TaskExecutionContext,
    TaskExecutorRegistry,
    default_executor_registry,
)
from app.close_workflow.readiness import CloseReadinessService
from app.close_workflow.routing import EvidencePackRouter, ExceptionRouter
from app.close_workflow.state_machine import (
    ALLOWED_CLOSE_RUN_TRANSITIONS,
    ALLOWED_TASK_TRANSITIONS,
    CloseRunError,
    CloseTaskError,
    CloseWorkflowStateMachine,
)
from app.close_workflow.types import (
    ClosePackage,
    ClosePolicy,
    CloseReadiness,
    ExceptionRoutingDecision,
    TaskExecutionResult,
    WorkflowEvent,
)

__all__ = [
    "ALLOWED_CLOSE_RUN_TRANSITIONS",
    "ALLOWED_TASK_TRANSITIONS",
    "ClosePackage",
    "ClosePolicy",
    "CloseReadiness",
    "CloseReadinessService",
    "CloseRunError",
    "CloseTaskError",
    "CloseTaskExecutor",
    "CloseWorkflowController",
    "CloseWorkflowStateMachine",
    "DEFAULT_TASK_DEPENDENCIES",
    "EvidencePackRouter",
    "ExceptionRouter",
    "ExceptionRoutingDecision",
    "TaskDependencyResolver",
    "TaskExecutionContext",
    "TaskExecutionResult",
    "TaskExecutorRegistry",
    "WorkflowEvent",
    "default_executor_registry",
]
