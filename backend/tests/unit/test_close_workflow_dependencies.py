"""Unit tests for close task dependencies and DAG ordering (spec section 15)."""

from __future__ import annotations

import pytest

from app.close_workflow.dependencies import (
    DEFAULT_TASK_DEPENDENCIES,
    TaskDependencyResolver,
)
from app.domain.enums import CloseTaskStatus, CloseTaskType


def test_default_dependencies_dag_is_valid() -> None:
    resolver = TaskDependencyResolver(DEFAULT_TASK_DEPENDENCIES)
    # validate_dag runs in __init__ and should not raise
    resolver.validate_dag()
    assert len(resolver.dependencies) == 10


def test_cyclic_dependency_rejected() -> None:
    cyclic_deps = {
        CloseTaskType.INVOICE_VALIDATION: [CloseTaskType.PAYMENT_RECONCILIATION],
        CloseTaskType.PAYMENT_RECONCILIATION: [CloseTaskType.INVOICE_VALIDATION],
    }
    with pytest.raises(ValueError, match="Cyclic dependency"):
        TaskDependencyResolver(cyclic_deps)


def test_topological_sort_order() -> None:
    resolver = TaskDependencyResolver()
    order = resolver.get_execution_order()

    assert len(order) == 10
    # INVOICE_VALIDATION must precede PAYMENT_RECONCILIATION
    assert order.index(CloseTaskType.INVOICE_VALIDATION) < order.index(
        CloseTaskType.PAYMENT_RECONCILIATION
    )
    # PAYMENT_RECONCILIATION must precede BANK_RECONCILIATION
    assert order.index(CloseTaskType.PAYMENT_RECONCILIATION) < order.index(
        CloseTaskType.BANK_RECONCILIATION
    )
    # EXCEPTION_REVIEW must precede FINAL_VERIFICATION
    assert order.index(CloseTaskType.EXCEPTION_REVIEW) < order.index(
        CloseTaskType.FINAL_VERIFICATION
    )
    # FINAL_VERIFICATION must precede CLOSE_PACKAGE
    assert order.index(CloseTaskType.FINAL_VERIFICATION) < order.index(CloseTaskType.CLOSE_PACKAGE)


def test_get_ready_tasks_initial_state() -> None:
    resolver = TaskDependencyResolver()
    initial_statuses = {t: CloseTaskStatus.PENDING for t in DEFAULT_TASK_DEPENDENCIES}

    ready = resolver.get_ready_tasks(initial_statuses)
    # Initially, only INVOICE_VALIDATION has zero prerequisites
    assert ready == [CloseTaskType.INVOICE_VALIDATION]


def test_get_ready_tasks_as_prerequisites_complete() -> None:
    resolver = TaskDependencyResolver()
    statuses = {t: CloseTaskStatus.PENDING for t in DEFAULT_TASK_DEPENDENCIES}

    statuses[CloseTaskType.INVOICE_VALIDATION] = CloseTaskStatus.COMPLETED
    ready = resolver.get_ready_tasks(statuses)

    # With INVOICE_VALIDATION complete, PAYMENT_RECONCILIATION is ready
    assert CloseTaskType.PAYMENT_RECONCILIATION in ready

    statuses[CloseTaskType.PAYMENT_RECONCILIATION] = CloseTaskStatus.COMPLETED
    ready = resolver.get_ready_tasks(statuses)

    # Now BANK_RECONCILIATION, AP_RECONCILIATION, and VARIANCE_ANALYSIS become ready
    assert CloseTaskType.BANK_RECONCILIATION in ready
    assert CloseTaskType.AP_RECONCILIATION in ready
    assert CloseTaskType.VARIANCE_ANALYSIS in ready


def test_get_blocked_tasks_when_prerequisite_fails() -> None:
    resolver = TaskDependencyResolver()
    statuses = {t: CloseTaskStatus.PENDING for t in DEFAULT_TASK_DEPENDENCIES}

    statuses[CloseTaskType.INVOICE_VALIDATION] = CloseTaskStatus.FAILED
    blocked = resolver.get_blocked_tasks(statuses)

    # Tasks that directly or indirectly require INVOICE_VALIDATION are blocked
    assert CloseTaskType.PAYMENT_RECONCILIATION in blocked
    assert CloseTaskType.AP_RECONCILIATION in blocked
    assert CloseTaskType.VARIANCE_ANALYSIS in blocked


def test_downstream_dependents() -> None:
    resolver = TaskDependencyResolver()
    dependents = resolver.get_downstream_dependents(CloseTaskType.FINAL_VERIFICATION)
    assert dependents == {CloseTaskType.CLOSE_PACKAGE}

    inv_dependents = resolver.get_downstream_dependents(CloseTaskType.INVOICE_VALIDATION)
    # INVOICE_VALIDATION has downstream impacts across the close
    assert CloseTaskType.PAYMENT_RECONCILIATION in inv_dependents
    assert CloseTaskType.BANK_RECONCILIATION in inv_dependents
    assert CloseTaskType.EXCEPTION_REVIEW in inv_dependents
    assert CloseTaskType.FINAL_VERIFICATION in inv_dependents
    assert CloseTaskType.CLOSE_PACKAGE in inv_dependents
