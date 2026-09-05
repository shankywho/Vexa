"""Vocabulary sanity: the spec's enums exist and match expected values."""

from __future__ import annotations

from app.domain.enums import (
    AutonomyLevel,
    CloseRunStatus,
    CloseTaskType,
    ExceptionStatus,
    ExceptionType,
    ReconciliationStatus,
    Role,
)


def test_close_run_state_machine_enum() -> None:
    states = [s.value for s in CloseRunStatus]
    for expected in (
        "CREATED",
        "INGESTING",
        "RECONCILING",
        "INVESTIGATING",
        "VERIFYING",
        "WAITING_FOR_HUMAN",
        "RESOLVING",
        "FINAL_VERIFICATION",
        "READY_TO_CLOSE",
        "CLOSED",
        "FAILED",
        "BLOCKED",
    ):
        assert expected in states


def test_close_task_catalogue() -> None:
    tasks = [t.value for t in CloseTaskType]
    for expected in (
        "BANK_RECONCILIATION",
        "AP_RECONCILIATION",
        "AR_RECONCILIATION",
        "INVOICE_VALIDATION",
        "PAYMENT_RECONCILIATION",
        "VARIANCE_ANALYSIS",
        "ACCRUAL_REVIEW",
        "EXCEPTION_REVIEW",
        "FINAL_VERIFICATION",
        "CLOSE_PACKAGE",
    ):
        assert expected in tasks


def test_exception_catalogue() -> None:
    types = [t.value for t in ExceptionType]
    for expected in (
        "DUPLICATE_INVOICE",
        "PO_MISMATCH",
        "RECEIPT_MISMATCH",
        "PAYMENT_MISMATCH",
        "BANK_GL_MISMATCH",
        "MISSING_DOCUMENT",
        "DUPLICATE_PAYMENT",
        "UNUSUAL_VENDOR_ACTIVITY",
        "PAYMENT_FRAGMENTATION",
        "AR_MISMATCH",
        "ACCRUAL_ANOMALY",
        "GL_MAPPING_ERROR",
        "CASH_ANOMALY",
        "OTHER",
    ):
        assert expected in types


def test_exception_status_enum() -> None:
    assert ExceptionStatus.REOPENED.value == "REOPENED"
    assert ExceptionStatus.AUTO_RESOLVED.value == "AUTO_RESOLVED"


def test_autonomy_levels() -> None:
    assert [a.value for a in AutonomyLevel] == ["OBSERVE", "RECOMMEND", "STAGE", "EXECUTE"]


def test_roles() -> None:
    assert [r.value for r in Role] == ["VIEWER", "ACCOUNTANT", "CONTROLLER", "CFO", "ADMIN"]


def test_reconciliation_statuses() -> None:
    assert [s.value for s in ReconciliationStatus] == [
        "MATCHED",
        "PARTIAL",
        "MISMATCH",
        "MISSING",
    ]
