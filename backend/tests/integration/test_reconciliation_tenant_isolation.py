"""Integration tests for tenant isolation in the reconciliation engine."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.counterparty import Vendor
from app.db.models.procurement import Invoice, PurchaseOrder, PurchaseOrderLine
from app.db.models.tenancy import Company
from app.reconciliation.engine import DeterministicReconciliationEngine


@pytest.mark.asyncio
async def test_reconciliation_engine_tenant_isolation(db: AsyncSession):
    # Company A
    comp_a = Company(
        id=uuid.uuid4(),
        name="Company Alpha",
        base_currency="USD",
        is_active=True,
    )
    # Company B
    comp_b = Company(
        id=uuid.uuid4(),
        name="Company Beta",
        base_currency="USD",
        is_active=True,
    )
    db.add_all([comp_a, comp_b])
    await db.flush()

    # Vendor in Company A
    vendor_a = Vendor(company_id=comp_a.id, name="Vendor Alpha Supplies")
    vendor_b = Vendor(company_id=comp_b.id, name="Vendor Beta Supplies")
    db.add_all([vendor_a, vendor_b])
    await db.flush()

    # PO and Invoice in Company A
    po_a = PurchaseOrder(
        company_id=comp_a.id,
        vendor_id=vendor_a.id,
        po_number="PO-ALPHA-01",
        order_date=date(2026, 1, 10),
        currency="USD",
        total=Decimal("5000.00"),
    )
    po_a.lines = [
        PurchaseOrderLine(
            quantity=Decimal("10.0000"),
            unit_price=Decimal("500.0000"),
            amount=Decimal("5000.00"),
        )
    ]
    inv_a = Invoice(
        company_id=comp_a.id,
        vendor_id=vendor_a.id,
        po_id=po_a.id,
        invoice_number="INV-ALPHA-01",
        invoice_date=date(2026, 1, 15),
        currency="USD",
        total=Decimal("5000.00"),
    )
    db.add_all([po_a, inv_a])

    # Invoice in Company B
    inv_b = Invoice(
        company_id=comp_b.id,
        vendor_id=vendor_b.id,
        invoice_number="INV-BETA-01",
        invoice_date=date(2026, 1, 15),
        currency="USD",
        total=Decimal("9999.00"),
    )
    db.add(inv_b)
    await db.flush()

    # Run engine for Company A
    engine_a = DeterministicReconciliationEngine(db, comp_a.id)
    summary_a = await engine_a.run_full_reconciliation(persist=True)

    assert summary_a.company_id == comp_a.id
    # Ensure all results belong to Company A
    for res in summary_a.results:
        assert res.company_id == comp_a.id
        assert res.source_record_id != inv_b.id
        assert res.source_record_number != "INV-BETA-01"

    # Verify repository queries for Company A
    repo_a = engine_a.rec_repo
    stored_a = await repo_a.list()
    assert len(stored_a) > 0
    for r in stored_a:
        assert r.company_id == comp_a.id
