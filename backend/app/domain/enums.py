"""Domain enums.

Single source of truth for the vocabulary defined in
``CLOSEPILOT_BACKEND_CONTEXT_V2.md`` (close-run states, exception types,
autonomy levels, roles, close tasks, reconciliation statuses, etc.).
"""

from __future__ import annotations

from enum import StrEnum


class CloseRunStatus(StrEnum):
    """Close run state machine (spec section 14)."""

    CREATED = "CREATED"
    INGESTING = "INGESTING"
    RECONCILING = "RECONCILING"
    INVESTIGATING = "INVESTIGATING"
    VERIFYING = "VERIFYING"
    WAITING_FOR_HUMAN = "WAITING_FOR_HUMAN"
    RESOLVING = "RESOLVING"
    FINAL_VERIFICATION = "FINAL_VERIFICATION"
    READY_TO_CLOSE = "READY_TO_CLOSE"
    CLOSED = "CLOSED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


class CloseTaskType(StrEnum):
    """Close task catalogue (spec section 15)."""

    BANK_RECONCILIATION = "BANK_RECONCILIATION"
    AP_RECONCILIATION = "AP_RECONCILIATION"
    AR_RECONCILIATION = "AR_RECONCILIATION"
    INVOICE_VALIDATION = "INVOICE_VALIDATION"
    PAYMENT_RECONCILIATION = "PAYMENT_RECONCILIATION"
    VARIANCE_ANALYSIS = "VARIANCE_ANALYSIS"
    ACCRUAL_REVIEW = "ACCRUAL_REVIEW"
    EXCEPTION_REVIEW = "EXCEPTION_REVIEW"
    FINAL_VERIFICATION = "FINAL_VERIFICATION"
    CLOSE_PACKAGE = "CLOSE_PACKAGE"


class CloseTaskStatus(StrEnum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


class ExceptionType(StrEnum):
    """Exception catalogue (spec section 9)."""

    DUPLICATE_INVOICE = "DUPLICATE_INVOICE"
    PO_MISMATCH = "PO_MISMATCH"
    RECEIPT_MISMATCH = "RECEIPT_MISMATCH"
    PAYMENT_MISMATCH = "PAYMENT_MISMATCH"
    BANK_GL_MISMATCH = "BANK_GL_MISMATCH"
    MISSING_DOCUMENT = "MISSING_DOCUMENT"
    DUPLICATE_PAYMENT = "DUPLICATE_PAYMENT"
    UNUSUAL_VENDOR_ACTIVITY = "UNUSUAL_VENDOR_ACTIVITY"
    PAYMENT_FRAGMENTATION = "PAYMENT_FRAGMENTATION"
    AR_MISMATCH = "AR_MISMATCH"
    ACCRUAL_ANOMALY = "ACCRUAL_ANOMALY"
    GL_MAPPING_ERROR = "GL_MAPPING_ERROR"
    CASH_ANOMALY = "CASH_ANOMALY"
    OTHER = "OTHER"


class ExceptionSeverity(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ExceptionStatus(StrEnum):
    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"
    REOPENED = "REOPENED"
    AUTO_RESOLVED = "AUTO_RESOLVED"


class AgentRunStatus(StrEnum):
    """Execution status for an autonomous agent run (spec section 5.3)."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"


class AutonomyLevel(StrEnum):
    """Controlled autonomy levels (spec section 11)."""

    OBSERVE = "OBSERVE"  # Level 0
    RECOMMEND = "RECOMMEND"  # Level 1
    STAGE = "STAGE"  # Level 2
    EXECUTE = "EXECUTE"  # Level 3


class Role(StrEnum):
    """RBAC roles (spec section 29)."""

    VIEWER = "VIEWER"
    ACCOUNTANT = "ACCOUNTANT"
    CONTROLLER = "CONTROLLER"
    CFO = "CFO"
    ADMIN = "ADMIN"


class ReconciliationStatus(StrEnum):
    """Reconciliation engine output contract (spec section 8)."""

    MATCHED = "MATCHED"
    PARTIAL = "PARTIAL"
    MISMATCH = "MISMATCH"
    MISSING = "MISSING"


class DocumentStatus(StrEnum):
    DRAFT = "DRAFT"
    OPEN = "OPEN"
    APPROVED = "APPROVED"
    PAID = "PAID"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    POSTED = "POSTED"
    VOID = "VOID"
    CLOSED = "CLOSED"


class BankTransactionDirection(StrEnum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"


class Currency(StrEnum):
    """Currencies used in the synthetic dataset (spec section 20/24)."""

    USD = "USD"
    INR = "INR"
    EUR = "EUR"
    GBP = "GBP"


class AuditEventType(StrEnum):
    """High-level audit event categories (spec section 13)."""

    EXCEPTION_DECISION = "EXCEPTION_DECISION"
    EXCEPTION_CREATED = "EXCEPTION_CREATED"
    EXCEPTION_RESOLVED = "EXCEPTION_RESOLVED"
    EXCEPTION_ESCALATED = "EXCEPTION_ESCALATED"
    EXCEPTION_REOPENED = "EXCEPTION_REOPENED"
    APPROVAL = "APPROVAL"
    REVERSAL = "REVERSAL"
    CLOSE_RUN_STATE_CHANGE = "CLOSE_RUN_STATE_CHANGE"
    CLOSE_TASK_STATE_CHANGE = "CLOSE_TASK_STATE_CHANGE"
    ACTION_EXECUTED = "ACTION_EXECUTED"
    AGENT_RUN_STARTED = "AGENT_RUN_STARTED"
    AGENT_RUN_COMPLETED = "AGENT_RUN_COMPLETED"
    SYSTEM = "SYSTEM"
    SEED = "SEED"


class EvidenceType(StrEnum):
    INVOICE = "INVOICE"
    PURCHASE_ORDER = "PURCHASE_ORDER"
    GOODS_RECEIPT = "GOODS_RECEIPT"
    PAYMENT = "PAYMENT"
    BANK_TRANSACTION = "BANK_TRANSACTION"
    JOURNAL_ENTRY = "JOURNAL_ENTRY"
    CONTRACT = "CONTRACT"
    EXPENSE_REPORT = "EXPENSE_REPORT"
