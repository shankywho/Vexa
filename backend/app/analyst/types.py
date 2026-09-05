"""Domain types and schemas for the Financial Analyst Agent (spec section 10)."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class VarianceItem(BaseModel):
    """Variance analysis item for a General Ledger account."""

    account_code: str
    account_name: str
    account_type: str
    prior_balance: Decimal
    current_balance: Decimal
    variance_amount: Decimal
    variance_percentage: Decimal | None = None
    is_material: bool = False
    explanation: str = ""


class CashImpactSummary(BaseModel):
    """Cash flow and cash burn analysis."""

    opening_cash_balance: Decimal = Decimal("0.00")
    closing_cash_balance: Decimal = Decimal("0.00")
    net_cash_flow: Decimal = Decimal("0.00")
    operating_inflows: Decimal = Decimal("0.00")
    operating_outflows: Decimal = Decimal("0.00")
    monthly_burn_rate: Decimal = Decimal("0.00")
    runway_months: Decimal | None = None
    high_risk_cash_outflows: Decimal = Decimal("0.00")
    risk_items: list[str] = Field(default_factory=list)


class AccrualCandidate(BaseModel):
    """Accrual candidate (e.g. unbilled goods receipt or open purchase order)."""

    record_id: str
    record_type: str
    reference_number: str
    vendor_name: str | None = None
    amount: Decimal
    currency: str = "USD"
    receipt_date: str | None = None
    reason: str
    suggested_gl_account: str = "2100"  # Accrued Expenses / GRNI


class MaterialityFinding(BaseModel):
    """Materiality threshold finding."""

    category: str
    reference: str
    amount: Decimal
    threshold: Decimal
    requires_cfo_attention: bool
    notes: str


class FinancialAnalysisReport(BaseModel):
    """Structured report produced by the Financial Analyst Agent."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    company_id: uuid.UUID
    period_start: str
    period_end: str
    variance_items: list[VarianceItem] = Field(default_factory=list)
    cash_summary: CashImpactSummary = Field(default_factory=CashImpactSummary)
    accrual_candidates: list[AccrualCandidate] = Field(default_factory=list)
    materiality_findings: list[MaterialityFinding] = Field(default_factory=list)
    total_accrual_exposure: Decimal = Decimal("0.00")
    net_burn_rate: Decimal = Decimal("0.00")
    period_over_period_summary: str = ""
    executive_close_summary: str = ""
    agent_run_id: uuid.UUID | None = None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
