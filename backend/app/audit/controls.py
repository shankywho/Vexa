"""SOX control registry and deterministic control ID mapping (spec section 13).

Provides deterministic mapping from financial exception types, close tasks,
and audit events to recognized internal accounting control IDs.
Zero LLM dependencies.
"""

from __future__ import annotations

from enum import StrEnum

from app.domain.enums import AuditEventType, CloseTaskType, ExceptionType


class SoxControl(StrEnum):
    """Catalog of deterministic SOX accounting control identifiers."""

    AP_03 = "AP-03"  # Duplicate Payment Control
    AP_07 = "AP-07"  # Vendor Bank Account Change Control
    PROC_04 = "PROC-04"  # PO / Receipt Mismatch Control
    GL_02 = "GL-02"  # General Ledger Reconciliation Control
    BANK_01 = "BANK-01"  # Bank Reconciliation Control
    CLOSE_01 = "CLOSE-01"  # Close Completeness & Ingestion Control
    REV_01 = "REV-01"  # Accounts Receivable & Revenue Matching Control
    EXP_01 = "EXP-01"  # Accrual & Expense Recognition Control


CONTROL_DESCRIPTIONS: dict[str, str] = {
    SoxControl.AP_03: "Duplicate Payment Prevention & Detection Control",
    SoxControl.AP_07: "Vendor Master Bank Account Modification Control",
    SoxControl.PROC_04: "Purchase Order to Goods Receipt 3-Way Matching Control",
    SoxControl.GL_02: "General Ledger Mapping & Journal Entry Balance Control",
    SoxControl.BANK_01: "Bank Account to General Ledger Reconciliation Control",
    SoxControl.CLOSE_01: "Period-End Close Completeness & Data Ingestion Control",
    SoxControl.REV_01: "Accounts Receivable Customer Remittance Matching Control",
    SoxControl.EXP_01: "Accrued Liabilities & Expense Anomaly Review Control",
}

# Deterministic mapping from ExceptionType to SoxControl
EXCEPTION_CONTROL_MAP: dict[ExceptionType | str, str] = {
    ExceptionType.DUPLICATE_PAYMENT: SoxControl.AP_03,
    ExceptionType.DUPLICATE_INVOICE: SoxControl.AP_03,
    ExceptionType.PAYMENT_FRAGMENTATION: SoxControl.AP_03,
    ExceptionType.VENDOR_BANK_CHANGE_ANOMALY: SoxControl.AP_07,
    ExceptionType.PO_MISMATCH: SoxControl.PROC_04,
    ExceptionType.RECEIPT_MISMATCH: SoxControl.PROC_04,
    ExceptionType.MISSING_DOCUMENT: SoxControl.PROC_04,
    ExceptionType.GL_MAPPING_ERROR: SoxControl.GL_02,
    ExceptionType.BANK_GL_MISMATCH: SoxControl.BANK_01,
    ExceptionType.CASH_ANOMALY: SoxControl.BANK_01,
    ExceptionType.PAYMENT_MISMATCH: SoxControl.BANK_01,
    ExceptionType.DATA_INGESTION_GAP: SoxControl.CLOSE_01,
    ExceptionType.AR_MISMATCH: SoxControl.REV_01,
    ExceptionType.ACCRUAL_ANOMALY: SoxControl.EXP_01,
    ExceptionType.UNUSUAL_VENDOR_ACTIVITY: SoxControl.AP_07,
    ExceptionType.BANK_DUPLICATE: SoxControl.BANK_01,
}

# Deterministic mapping from CloseTaskType to SoxControl
TASK_CONTROL_MAP: dict[CloseTaskType | str, str] = {
    CloseTaskType.BANK_RECONCILIATION: SoxControl.BANK_01,
    CloseTaskType.AP_RECONCILIATION: SoxControl.AP_03,
    CloseTaskType.AR_RECONCILIATION: SoxControl.REV_01,
    CloseTaskType.INVOICE_VALIDATION: SoxControl.PROC_04,
    CloseTaskType.PAYMENT_RECONCILIATION: SoxControl.AP_03,
    CloseTaskType.VARIANCE_ANALYSIS: SoxControl.EXP_01,
    CloseTaskType.ACCRUAL_REVIEW: SoxControl.EXP_01,
    CloseTaskType.EXCEPTION_REVIEW: SoxControl.CLOSE_01,
    CloseTaskType.FINAL_VERIFICATION: SoxControl.CLOSE_01,
    CloseTaskType.CLOSE_PACKAGE: SoxControl.CLOSE_01,
}


def map_to_control_id(
    exception_type: ExceptionType | str | None = None,
    task_type: CloseTaskType | str | None = None,
    event_type: AuditEventType | str | None = None,
) -> str | None:
    """Deterministically map exception types, close tasks, or events to a SOX control ID."""
    if exception_type:
        val = exception_type.value if hasattr(exception_type, "value") else str(exception_type)
        if val in EXCEPTION_CONTROL_MAP:
            return EXCEPTION_CONTROL_MAP[val]

    if task_type:
        val = task_type.value if hasattr(task_type, "value") else str(task_type)
        if val in TASK_CONTROL_MAP:
            return TASK_CONTROL_MAP[val]

    if event_type:
        val = event_type.value if hasattr(event_type, "value") else str(event_type)
        if val in ("CLOSE_RUN_FINALIZED", "CLOSE_PACKAGE_GENERATED"):
            return SoxControl.CLOSE_01

    return None
