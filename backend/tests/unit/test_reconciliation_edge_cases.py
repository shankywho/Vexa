"""Unit tests for reconciliation tolerances and edge cases."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

from app.db.models.procurement import Invoice, PurchaseOrder, PurchaseOrderLine
from app.domain.enums import ReconciliationStatus
from app.reconciliation.config import ReconciliationConfig
from app.reconciliation.rules import match_invoice_to_po


@pytest.mark.asyncio
async def test_penny_roundoff_within_tolerance():
    cid = uuid.uuid4()
    pol_id = uuid.uuid4()
    po = PurchaseOrder(
        id=uuid.uuid4(),
        company_id=cid,
        po_number="PO-ROUND-1",
        currency="USD",
        total=Decimal("10000.00"),
    )
    po.lines = [
        PurchaseOrderLine(
            id=pol_id,
            purchase_order_id=po.id,
            quantity=Decimal("1.0000"),
            unit_price=Decimal("10000.0000"),
            amount=Decimal("10000.00"),
        )
    ]
    # Invoice has 3 cents penny rounding difference
    inv = Invoice(
        id=uuid.uuid4(),
        company_id=cid,
        po_id=po.id,
        invoice_number="INV-ROUND-1",
        currency="USD",
        total=Decimal("10000.03"),
    )
    # Configure tolerance: 0.05 abs tolerance
    cfg = ReconciliationConfig(amount_abs_tolerance=Decimal("0.05"))
    res = await match_invoice_to_po(inv, po, None, cfg)
    assert res.status == ReconciliationStatus.MATCHED
    assert res.financial_impact == Decimal("0.00")


@pytest.mark.asyncio
async def test_roundoff_exceeding_tolerance():
    cid = uuid.uuid4()
    pol_id = uuid.uuid4()
    po = PurchaseOrder(
        id=uuid.uuid4(),
        company_id=cid,
        po_number="PO-ROUND-2",
        currency="USD",
        total=Decimal("10000.00"),
    )
    po.lines = [
        PurchaseOrderLine(
            id=pol_id,
            purchase_order_id=po.id,
            quantity=Decimal("1.0000"),
            unit_price=Decimal("10000.0000"),
            amount=Decimal("10000.00"),
        )
    ]
    # Invoice has 25 cents difference (> 0.05 tolerance)
    inv = Invoice(
        id=uuid.uuid4(),
        company_id=cid,
        po_id=po.id,
        invoice_number="INV-ROUND-2",
        currency="USD",
        total=Decimal("10000.25"),
    )
    cfg = ReconciliationConfig(
        amount_abs_tolerance=Decimal("0.05"), amount_pct_tolerance=Decimal("0.00001")
    )
    res = await match_invoice_to_po(inv, po, None, cfg)
    assert res.status == ReconciliationStatus.MISMATCH
    assert res.financial_impact == Decimal("0.25")
