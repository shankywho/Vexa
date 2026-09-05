"""Pydantic schemas for API responses/requests.

Phase 1 covers the foundation endpoints only (companies, health, audit).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import (
    AgentRunStatus,
    AutonomyLevel,
    CloseRunStatus,
    CloseTaskStatus,
    CloseTaskType,
    ExceptionSeverity,
    ExceptionStatus,
    ExceptionType,
    Role,
)


class CompanyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    legal_name: str | None = None
    tax_id: str | None = None
    base_currency: str = "USD"
    fiscal_year_end: str | None = None


class CompanyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    legal_name: str | None
    tax_id: str | None
    base_currency: str
    fiscal_year_end: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    email: str
    full_name: str | None
    role: Role
    is_active: bool


class AuditEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID | None
    close_run_id: uuid.UUID | None
    event_type: str
    actor: str | None
    actor_type: str | None
    agent_name: str | None
    agent_prompt_version_id: str | None
    policy_version_id: str | None
    exception_id: uuid.UUID | None
    decision: str | None
    reason: str | None
    financial_impact: Decimal | None
    currency: str | None
    confidence: Decimal | None
    calibrated_confidence: Decimal | None
    created_at: datetime


class HealthRead(BaseModel):
    status: str
    environment: str
    database: str
    version: str


class FxRateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    base_currency: str
    quote_currency: str
    rate: Decimal
    effective_date: date
    source: str | None


class FxConversionResult(BaseModel):
    """Result of a deterministic FX conversion (spec sections 6.1, 8, 16)."""

    original_amount: Decimal
    from_currency: str
    to_currency: str
    effective_date: date
    rate: Decimal
    converted_amount: Decimal
    is_inverse: bool = False
    is_identity: bool = False
    source: str | None = None
    status: str = "MATCHED"  # MATCHED or MISSING per spec section 8


class CloseRunCreate(BaseModel):
    """Request schema for creating a close run."""

    period_start: date
    period_end: date


class CloseRunRead(BaseModel):
    """Response schema for a close run."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    period_start: date
    period_end: date
    status: CloseRunStatus
    version: int
    started_at: datetime | None = None
    completed_at: datetime | None = None
    close_summary: str | None = None
    created_at: datetime
    updated_at: datetime


class CloseTaskRead(BaseModel):
    """Response schema for a close task."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    close_run_id: uuid.UUID
    task_type: CloseTaskType
    status: CloseTaskStatus
    assigned_to: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result_summary: str | None = None
    created_at: datetime


class ExceptionEvidenceItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    evidence_type: str
    evidence_ref_id: uuid.UUID
    description: str | None = None


class ExceptionRead(BaseModel):
    """Response schema for a financial exception."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    close_run_id: uuid.UUID | None = None
    type: ExceptionType
    severity: ExceptionSeverity
    status: ExceptionStatus
    financial_impact: Decimal
    currency: str
    confidence: Decimal | None = None
    calibrated_confidence: Decimal | None = None
    root_cause: str | None = None
    recommended_action: str | None = None
    autonomy_level: AutonomyLevel
    assigned_to: str | None = None
    resolved_at: datetime | None = None
    source_invoice_id: uuid.UUID | None = None
    source_po_id: uuid.UUID | None = None
    source_receipt_id: uuid.UUID | None = None
    source_payment_id: uuid.UUID | None = None
    source_bank_txn_id: uuid.UUID | None = None
    source_journal_entry_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime


class ExceptionEvidenceRead(BaseModel):
    """Response schema for exception evidence dossier and citations."""

    exception_id: uuid.UUID
    evidence_ids: list[str]
    dossier: dict[str, Any]
    nodes: list[dict[str, Any]]
    citations: list[dict[str, Any]]


class HumanReviewRequest(BaseModel):
    """Request schema for human review decisions."""

    actor: str = "controller"
    notes: str | None = None


class EscalateRequest(BaseModel):
    """Request schema for escalating an exception to senior leadership."""

    target_role: str = "CFO"
    reason: str | None = None
    actor: str = "controller"


class ReverseActionRequest(BaseModel):
    """Request schema for reversing an action (spec section 13.2 rollback path)."""

    action_id: uuid.UUID | None = None
    reason: str = "User requested reversal/rollback"
    reversed_by: str = "controller"


class ActionResponse(BaseModel):
    """Response schema for action execution/approval/rejection/reversal."""

    action_id: uuid.UUID | None = None
    exception_id: uuid.UUID | None = None
    action_type: str | None = None
    status: str
    message: str | None = None
    payload: dict[str, Any] | None = None
    actor: str | None = None
    executed_at: datetime | None = None


class AgentStepRead(BaseModel):
    """Response schema for an agent execution step."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agent_run_id: uuid.UUID
    step_number: int
    step_type: str
    tool_name: str | None = None
    input_json: str | None = None
    output_json: str | None = None
    status: str
    latency_ms: int | None = None
    citations_valid: bool | None = None
    error_message: str | None = None
    created_at: datetime


class AgentRunRead(BaseModel):
    """Response schema for an autonomous agent run."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    close_run_id: uuid.UUID | None = None
    exception_id: uuid.UUID | None = None
    agent_name: str
    status: AgentRunStatus
    prompt_version_id: str | None = None
    model: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    latency_ms: int | None = None
    total_tokens: int | None = None
    cost_usd: Decimal | None = None
    finding_json: str | None = None
    error_message: str | None = None
    created_at: datetime
    steps: list[AgentStepRead] = Field(default_factory=list)


class ClosePackageRead(BaseModel):
    """Response schema for structured close package."""

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


class DemoModeToggleRequest(BaseModel):
    """Request schema for toggling demo execution mode."""

    mode: str = Field(description="Execution mode: LIVE or REPLAY")
    close_run_id: uuid.UUID | None = Field(default=None, description="Optional target close run ID")


class DemoModeRead(BaseModel):
    """Response schema for current demo execution mode."""

    mode: str
    close_run_id: uuid.UUID | None = None


class DemoTraceRead(BaseModel):
    """Response schema for a captured or golden demo trace."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    scenario_key: str
    title: str
    description: str | None = None
    events: list[dict[str, Any]] = Field(default_factory=list)
    total_steps: int
    total_duration_ms: int
    is_golden: bool
    created_at: datetime


class DemoRecordRequest(BaseModel):
    """Request schema for recording a close run into a demo trace."""

    close_run_id: uuid.UUID
    scenario_key: str
    title: str
    description: str | None = None
    is_golden: bool = False
