"""Unit tests for multi-currency reconciliation using deterministic FX conversion."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock

from app.db.models.banking import Payment
from app.db.models.procurement import Invoice, PurchaseOrder
from app.domain.enums import DocumentStatus, ReconciliationStatus
from app.domain.schemas import FxConversionResult
from app.reconciliation.config import ReconciliationConfig
from app.reconciliation.rules import match_invoice_to_po, match_payments_to_invoice
from app.services.fx_service import FxService


async def test_multi_currency_invoice_po_matching():
    cid = uuid.uuid4()
    # PO is in USD: 1,000 USD
    po = PurchaseOrder(
        id=uuid.uuid4(),
        company_id=cid,
        po_number="PO-USD-01",
        order_date=date(2026, 1, 10),
        currency="USD",
        total=Decimal("1000.00"),
        status=DocumentStatus.OPEN,
    )
    # Invoice billed in INR: 86,000 INR (at rate 1 USD = 86 INR)
    inv = Invoice(
        id=uuid.uuid4(),
        company_id=cid,
        po_id=po.id,
        invoice_number="INV-INR-01",
        invoice_date=date(2026, 1, 15),
        currency="INR",
        total=Decimal("86000.00"),
        status=DocumentStatus.OPEN,
    )

    fx_service = FxService(session=AsyncMock())
    fx_service.try_convert_amount = AsyncMock(
        return_value=FxConversionResult(
            original_amount=Decimal("1000.00"),
            from_currency="USD",
            to_currency="INR",
            effective_date=date(2026, 1, 15),
            rate=Decimal("86.0000"),
            converted_amount=Decimal("86000.00"),
            status="MATCHED",
        )
    )

    res = await match_invoice_to_po(inv, po, fx_service, ReconciliationConfig())
    assert res.status == ReconciliationStatus.MATCHED
    assert res.fx_conversion_applied is True
    assert res.financial_impact == Decimal("0.00")


async def test_multi_currency_payment_invoice_matching():
    cid = uuid.uuid4()
    # Invoice in USD: 500 USD
    inv = Invoice(
        id=uuid.uuid4(),
        company_id=cid,
        invoice_number="INV-USD-500",
        currency="USD",
        total=Decimal("500.00"),
    )
    # Paid in INR: 43,000 INR
    p = Payment(
        id=uuid.uuid4(),
        company_id=cid,
        invoice_id=inv.id,
        amount=Decimal("43000.00"),
        currency="INR",
        payment_date=date(2026, 1, 20),
    )

    fx_service = FxService(session=AsyncMock())
    # 43,000 INR converted to USD @ 1/86 = 500.00 USD
    fx_service.try_convert_amount = AsyncMock(
        return_value=FxConversionResult(
            original_amount=Decimal("43000.00"),
            from_currency="INR",
            to_currency="USD",
            effective_date=date(2026, 1, 20),
            rate=Decimal("0.0116279"),
            converted_amount=Decimal("500.00"),
            status="MATCHED",
        )
    )

    res = await match_payments_to_invoice(inv, [p], fx_service, ReconciliationConfig())
    assert res.status == ReconciliationStatus.MATCHED
    assert res.fx_conversion_applied is True
    assert res.financial_impact == Decimal("0.00")
