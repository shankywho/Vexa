"""Unit tests for deterministic FxService (spec sections 6.1, 16)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.fx import FxRate
from app.services.fx_service import FxRateNotFoundError, FxService


@pytest.fixture
async def fx_service(db: AsyncSession) -> FxService:
    service = FxService(db)
    # Seed known test rates
    rates = [
        FxRate(
            base_currency="INR",
            quote_currency="USD",
            rate=Decimal("0.01200000"),
            effective_date=date(2026, 2, 1),
            source="TEST_RBI",
        ),
        FxRate(
            base_currency="USD",
            quote_currency="EUR",
            rate=Decimal("0.92000000"),
            effective_date=date(2026, 2, 1),
            source="TEST_ECB",
        ),
    ]
    for r in rates:
        db.add(r)
    await db.flush()
    return service


async def test_identity_conversion(fx_service: FxService) -> None:
    """Converting to the same currency requires no FX rate and returns identical amount."""
    res = await fx_service.convert_amount(
        amount=Decimal("1500.75"),
        from_currency="INR",
        to_currency="INR",
        effective_date=date(2026, 2, 1),
    )
    assert res.is_identity is True
    assert res.is_inverse is False
    assert res.rate == Decimal("1.0")
    assert res.converted_amount == Decimal("1500.75")
    assert res.status == "MATCHED"


async def test_direct_rate_conversion(fx_service: FxService) -> None:
    """Direct conversion uses the stored rate."""
    res = await fx_service.convert_amount(
        amount=Decimal("10000.00"),
        from_currency="INR",
        to_currency="USD",
        effective_date=date(2026, 2, 1),
    )
    assert res.is_identity is False
    assert res.is_inverse is False
    assert res.rate == Decimal("0.01200000")
    assert res.converted_amount == Decimal("120.00")
    assert res.source == "TEST_RBI"
    assert res.status == "MATCHED"


async def test_inverse_rate_conversion(fx_service: FxService) -> None:
    """Inverse rate is computed as 1 / rate when only the reverse pair is stored."""
    # We have USD -> EUR = 0.92. Converting EUR -> USD uses 1 / 0.92
    res = await fx_service.convert_amount(
        amount=Decimal("92.00"),
        from_currency="EUR",
        to_currency="USD",
        effective_date=date(2026, 2, 1),
    )
    assert res.is_inverse is True
    # 92.00 * (1 / 0.92000000) = 100.00
    assert res.converted_amount == Decimal("100.00")
    assert res.source == "TEST_ECB"


async def test_missing_rate_raises_error(fx_service: FxService) -> None:
    """Exact date match required: different date raises FxRateNotFoundError."""
    with pytest.raises(FxRateNotFoundError):
        await fx_service.convert_amount(
            amount=Decimal("1000.00"),
            from_currency="INR",
            to_currency="USD",
            effective_date=date(2026, 2, 2),  # Not seeded
        )


async def test_try_convert_missing_returns_missing_status(fx_service: FxService) -> None:
    """try_convert_amount returns status='MISSING' when rate is missing without guessing."""
    res = await fx_service.try_convert_amount(
        amount=Decimal("1000.00"),
        from_currency="INR",
        to_currency="GBP",
        effective_date=date(2026, 2, 1),
    )
    assert res.status == "MISSING"
    assert res.rate == Decimal("0")
    assert res.converted_amount == Decimal("0")


def test_float_rejection(fx_service: FxService) -> None:
    """Floats are strictly rejected to prevent floating-point accounting drift."""
    with pytest.raises(TypeError, match="Floating-point financial amounts are strictly forbidden"):
        fx_service._validate_decimal(100.5)
