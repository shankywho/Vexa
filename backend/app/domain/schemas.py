"""Pydantic schemas for API responses/requests.

Phase 1 covers the foundation endpoints only (companies, health, audit).
"""

from __future__ import annotations

import uuid
from datetime import datetime
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
