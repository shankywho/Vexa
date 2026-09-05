"""Integration tests for deterministic financial seed & ground truth (spec 20-24)."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.generator import seed_company
from app.db.models.ledger import JournalEntry, JournalEntryLine
from app.db.models.procurement import (
    Invoice,
)
from app.domain.enums import ExceptionType
from app.services.fx_service import FxService


async def _count(db: AsyncSession, table: str, company_id: str | None = None) -> int:
    if company_id:
        query = text(f"SELECT count(*) FROM {table} WHERE company_id = '{company_id}'")
    else:
        query = text(f"SELECT count(*) FROM {table}")
    return int((await db.execute(query)).scalar_one())


async def test_full_financial_seed_targets_and_relationships(db: AsyncSession) -> None:
    """Full financial seed generates the exact target numbers from spec section 20."""
    company = await seed_company(db, seed=42, include_transactions=True)
    cid = str(company.id)

    # Master Data targets (spec section 20)
    assert await _count(db, "companies") >= 1
    assert await _count(db, "vendors", cid) == 42
    assert await _count(db, "customers", cid) == 18
    assert await _count(db, "bank_accounts", cid) == 3
    assert await _count(db, "ledger_accounts", cid) == 60
    assert await _count(db, "users", cid) == 12
    assert await _count(db, "role_assignments", cid) == 12
    assert await _count(db, "contracts", cid) == 15

    # Transaction targets (spec section 20)
    assert await _count(db, "invoices", cid) == 450
    assert await _count(db, "purchase_orders", cid) == 410
    assert await _count(db, "goods_receipts", cid) == 390
    assert await _count(db, "bank_transactions", cid) == 1500
    assert await _count(db, "journal_entries", cid) == 600
    assert await _count(db, "expense_reports", cid) == 80

    # Market data (spec section 20)
    assert await _count(db, "fx_rates") == 273  # 3 pairs x 91 days


async def test_every_seeded_journal_entry_is_balanced(db: AsyncSession) -> None:
    """Every journal entry must strictly obey double-entry equation: sum(debit) == sum(credit)."""
    company = await seed_company(db, seed=42, include_transactions=True)

    entries = (
        await db.scalars(select(JournalEntry).where(JournalEntry.company_id == company.id))
    ).all()

    assert len(entries) == 600

    total_debit_all = Decimal("0")
    total_credit_all = Decimal("0")

    for je in entries:
        # Load lines
        lines = (
            await db.scalars(
                select(JournalEntryLine).where(JournalEntryLine.journal_entry_id == je.id)
            )
        ).all()
        assert len(lines) >= 2, f"Entry {je.reference} must have at least 2 lines"
        debit_sum = sum((line.debit for line in lines), Decimal("0"))
        credit_sum = sum((line.credit for line in lines), Decimal("0"))
        assert debit_sum == credit_sum, (
            f"Entry {je.reference} unbalanced: {debit_sum} != {credit_sum}"
        )
        total_debit_all += debit_sum
        total_credit_all += credit_sum

    assert total_debit_all == total_credit_all
    assert total_debit_all > Decimal("0")


async def test_ground_truth_scenarios_injected(db: AsyncSession) -> None:
    """Validate that the private ground truth mapping file exists and has all 34 scenarios."""
    company = await seed_company(db, seed=42, include_transactions=True)
    cid = company.id

    gt_file = Path(__file__).resolve().parent.parent.parent / "app" / "data" / "ground_truth.json"
    assert gt_file.exists(), "ground_truth.json must be generated"

    with open(gt_file, "r") as f:
        ground_truth = json.load(f)

    assert len(ground_truth) == 35, "Expected 35 ground truth scenarios"

    by_id = {sc["scenario_id"]: sc for sc in ground_truth}

    # Demo 1: Payment Fragmentation (spec section 22)
    demo1 = by_id["SCENARIO-001"]
    assert demo1["scenario_type"] == ExceptionType.PAYMENT_FRAGMENTATION.value
    assert demo1["financial_impact"] == "1450000.00"
    assert demo1["expected_action"] == "ESCALATE"
    assert demo1["human_review_required"] is True
    assert len(demo1["related_record_ids"]) == 14  # 14 payments of 1,00,000

    # Demo 2: Quantity Mismatch (spec section 23)
    demo2 = by_id["SCENARIO-002"]
    assert demo2["scenario_type"] == ExceptionType.PO_MISMATCH.value
    assert demo2["financial_impact"] == "384000.00"
    assert demo2["expected_action"] == "STAGE"

    # Demo 3: Clean Transaction (spec section 24)
    demo3 = by_id["SCENARIO-003"]
    assert demo3["scenario_type"] == "CLEAN_TRANSACTION"
    assert demo3["financial_impact"] == "0.00"
    assert demo3["expected_action"] == "AUTO_RESOLVE"
    assert demo3["human_review_required"] is False

    # 5 Duplicate Invoices
    dup_invs = [
        sc for sc in ground_truth if sc["scenario_type"] == ExceptionType.DUPLICATE_INVOICE.value
    ]
    assert len(dup_invs) == 5

    # 4 Duplicate Payments
    dup_pmts = [
        sc for sc in ground_truth if sc["scenario_type"] == ExceptionType.DUPLICATE_PAYMENT.value
    ]
    assert len(dup_pmts) == 4

    # Verify primary record exists in DB
    inv_demo1 = await db.scalar(select(Invoice).where(Invoice.id == demo1["primary_record_id"]))
    assert inv_demo1 is not None
    assert inv_demo1.total == Decimal("1450000.00")
    assert inv_demo1.company_id == cid


async def test_multi_currency_and_fx_conversion(db: AsyncSession) -> None:
    """Validate that multi-currency transactions exist and can be converted via FxService."""
    company = await seed_company(db, seed=42, include_transactions=True)

    # Find USD invoices
    usd_invoices = (
        await db.scalars(
            select(Invoice).where(Invoice.company_id == company.id, Invoice.currency == "USD")
        )
    ).all()
    assert len(usd_invoices) > 0, "USD invoices must be present in synthetic dataset"

    usd_inv = usd_invoices[0]
    assert usd_inv.currency == "USD"
    assert usd_inv.total > Decimal("0")

    # Convert USD invoice to company base currency (INR)
    fx = FxService(db)
    converted = await fx.convert_amount(
        amount=usd_inv.total,
        from_currency="USD",
        to_currency=company.base_currency,
        effective_date=usd_inv.invoice_date,
    )

    assert converted.from_currency == "USD"
    assert converted.to_currency == "INR"
    assert converted.status == "MATCHED"
    assert converted.converted_amount > Decimal("0")


async def test_financial_seed_is_idempotent(db: AsyncSession) -> None:
    """Calling seed_company multiple times does not crash or duplicate transactions."""
    company1 = await seed_company(db, seed=42, include_transactions=True)
    inv_count1 = await _count(db, "invoices", str(company1.id))

    # Second call returns existing company and skips re-seeding
    company2 = await seed_company(db, seed=42, include_transactions=True)
    assert company1.id == company2.id

    inv_count2 = await _count(db, "invoices", str(company1.id))
    assert inv_count1 == inv_count2 == 450
