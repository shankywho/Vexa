"""Pydantic schemas for the deterministic reconciliation engine (spec section 8).

Strict Decimal precision, zero LLM dependencies, structured explainable outputs.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import ExceptionType, ReconciliationStatus


class ReconciliationType(StrEnum):
    """Reconciliation workflow domains."""

    INVOICE_PO = "INVOICE_PO"
    INVOICE_RECEIPT = "INVOICE_RECEIPT"
    PO_RECEIPT = "PO_RECEIPT"
    THREE_WAY = "THREE_WAY"
    PAYMENT_INVOICE = "PAYMENT_INVOICE"
    BANK_PAYMENT = "BANK_PAYMENT"
    BANK_JOURNAL_ENTRY = "BANK_JOURNAL_ENTRY"
    LEDGER_DOUBLE_ENTRY = "LEDGER_DOUBLE_ENTRY"
    GL_MAPPING = "GL_MAPPING"
    ACCRUAL_REVIEW = "ACCRUAL_REVIEW"
    AR_CUSTOMER = "AR_CUSTOMER"
    CASH_ANOMALY = "CASH_ANOMALY"
    DUPLICATE_DETECTION = "DUPLICATE_DETECTION"
    MISSING_DOCUMENT = "MISSING_DOCUMENT"
    VENDOR_SURGE = "VENDOR_SURGE"
    VENDOR_BANK_CHANGE = "VENDOR_BANK_CHANGE"
    DATA_INGESTION_GAP = "DATA_INGESTION_GAP"
    BANK_DUPLICATE = "BANK_DUPLICATE"


class MatchedRecordReference(BaseModel):
    """A reference to an entity participating in a reconciliation event."""

    model_config = ConfigDict(from_attributes=True)

    record_type: str
    record_id: uuid.UUID
    record_number: str | None = None
    role: str = "MATCHED"  # PRIMARY | MATCHED | RELATED


class ReconciliationItemResult(BaseModel):
    """Structured result for an individual reconciliation event (spec section 8).

    Every result is fully explainable from structured inputs alone.
    """

    model_config = ConfigDict(from_attributes=True)

    company_id: uuid.UUID
    reconciliation_type: str
    status: ReconciliationStatus
    confidence: Decimal = Field(default=Decimal("1.0000"))
    financial_impact: Decimal = Field(default=Decimal("0.00"))
    source_record_type: str
    source_record_id: uuid.UUID
    source_record_number: str | None = None
    matched_records: list[MatchedRecordReference] = Field(default_factory=list)
    amounts: dict[str, Decimal] = Field(default_factory=dict)
    currencies: dict[str, str] = Field(default_factory=dict)
    fx_conversion_applied: bool = False
    fx_details: dict[str, Any] | None = None
    differences: dict[str, Any] = Field(default_factory=dict)
    tolerances_applied: dict[str, Any] = Field(default_factory=dict)
    deterministic_reason: str
    exception_type: ExceptionType | None = None
    evidence_ids: list[uuid.UUID] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ReconciliationRunSummary(BaseModel):
    """Aggregated summary of a reconciliation pass."""

    model_config = ConfigDict(from_attributes=True)

    company_id: uuid.UUID
    close_run_id: uuid.UUID | None = None
    total_items_processed: int = 0
    total_matched: int = 0
    total_partial: int = 0
    total_mismatch: int = 0
    total_missing: int = 0
    total_exceptions: int = 0
    total_financial_impact: Decimal = Field(default=Decimal("0.00"))
    results: list[ReconciliationItemResult] = Field(default_factory=list)
    detected_exception_types: dict[str, int] = Field(default_factory=dict)
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EvaluationReport(BaseModel):
    """Ground-truth evaluation report against injected scenarios and clean demos."""

    model_config = ConfigDict(from_attributes=True)

    total_scenarios: int
    detected_scenarios: int
    clean_scenarios_verified: int
    exception_scenarios_detected: int
    precision: Decimal
    recall: Decimal
    f1_score: Decimal
    scenario_details: list[dict[str, Any]] = Field(default_factory=list)
