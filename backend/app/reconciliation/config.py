"""Configuration and tolerances for the deterministic reconciliation engine.

All financial amounts and tolerances use Decimal precision.
Floats are strictly forbidden.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field


class ReconciliationConfig(BaseModel):
    """Configurable tolerances and thresholds for deterministic reconciliation (spec section 8)."""

    # Absolute amount tolerance (e.g. penny rounding differences)
    amount_abs_tolerance: Decimal = Field(default=Decimal("0.05"))

    # Percentage amount tolerance (0.005 = 0.5%)
    amount_pct_tolerance: Decimal = Field(default=Decimal("0.005"))

    # Quantity tolerance for unit matching
    quantity_tolerance: Decimal = Field(default=Decimal("0.0001"))

    # Unit price tolerance
    unit_price_tolerance: Decimal = Field(default=Decimal("0.01"))

    # Date lag tolerance in days (acceptable clearing/processing window)
    date_tolerance_days: int = Field(default=7)

    # FX rate variance tolerance (2% allowance for settlement timing)
    fx_tolerance_pct: Decimal = Field(default=Decimal("0.02"))

    # Maximum standard bank wire fee (amounts within this range are recognized as fee deductions)
    bank_fee_max: Decimal = Field(default=Decimal("150.00"))

    # Minimum payment count threshold to flag payment fragmentation
    fragmentation_count_threshold: int = Field(default=5)

    # High-value transaction threshold where fragmentation or cash anomalies are elevated
    high_value_threshold: Decimal = Field(default=Decimal("100000.00"))

    # Volume surge multiplier threshold for unusual vendor activity (e.g. 3.0 = 300% surge)
    unusual_vendor_surge_factor: Decimal = Field(default=Decimal("3.0"))

    # Materiality threshold for single uncontracted invoices
    uncontracted_invoice_threshold: Decimal = Field(default=Decimal("500000.00"))

    # Material accrual variance percentage threshold (25% variance vs actual)
    accrual_variance_pct_threshold: Decimal = Field(default=Decimal("0.25"))

    # Vendor bank account change detection window in days
    vendor_bank_change_window_days: int = Field(default=7)

    # Threshold above which a vendor bank change anomaly is elevated to CRITICAL
    vendor_bank_change_large_threshold: Decimal = Field(default=Decimal("10000.00"))
