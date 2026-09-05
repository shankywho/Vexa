"""Pydantic schemas for API responses/requests.

Phase 1 covers the foundation endpoints only (companies, health, audit).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import Role


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
