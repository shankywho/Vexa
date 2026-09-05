"""Unit tests for financial repositories and tenant boundary enforcement (spec section 30)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.banking import BankAccount, BankTransaction, Payment
from app.db.models.counterparty import Customer, Vendor
from app.db.models.ledger import JournalEntry, JournalEntryLine, LedgerAccount
from app.db.models.procurement import (
    Contract,
    ExpenseReport,
    GoodsReceipt,
    GoodsReceiptLine,
    Invoice,
    InvoiceLine,
    PurchaseOrder,
    PurchaseOrderLine,
)
from app.db.models.tenancy import Company
from app.db.repository import (
    BankAccountRepository,
    BankTransactionRepository,
    ContractRepository,
    CustomerRepository,
    ExpenseReportRepository,
    GoodsReceiptRepository,
    InvoiceRepository,
    JournalEntryRepository,
    LedgerAccountRepository,
    PaymentRepository,
    PurchaseOrderRepository,
    VendorRepository,
)
from app.domain.enums import BankTransactionDirection, DocumentStatus


@pytest.fixture
async def companies(db: AsyncSession) -> tuple[Company, Company]:
    comp_a = Company(name="Tenant Alpha", base_currency="INR", is_active=True)
    comp_b = Company(name="Tenant Beta", base_currency="USD", is_active=True)
    db.add_all([comp_a, comp_b])
    await db.flush()
    return comp_a, comp_b


async def test_vendor_and_customer_repository_tenant_isolation(
    db: AsyncSession, companies: tuple[Company, Company]
) -> None:
    comp_a, comp_b = companies
    repo_v_a = VendorRepository(db, comp_a.id)
    repo_v_b = VendorRepository(db, comp_b.id)

    v_a = Vendor(name="Supplier Alpha", tax_id="TAX-A1")
    await repo_v_a.add(v_a)

    # Tenant B cannot see Tenant A's vendor
    assert await repo_v_b.get(v_a.id) is None
    assert await repo_v_b.get_by_name("Supplier Alpha") is None
    assert await repo_v_b.get_by_tax_id("TAX-A1") is None

    # Tenant A sees it
    assert await repo_v_a.get(v_a.id) is not None
    assert await repo_v_a.get_by_name("Supplier Alpha") is not None

    repo_c_a = CustomerRepository(db, comp_a.id)
    repo_c_b = CustomerRepository(db, comp_b.id)
    c_a = Customer(name="Client Alpha")
    await repo_c_a.add(c_a)

    assert await repo_c_b.get(c_a.id) is None
    assert await repo_c_a.get_by_name("Client Alpha") is not None


async def test_invoice_and_po_repository_with_lines(
    db: AsyncSession, companies: tuple[Company, Company]
) -> None:
    comp_a, comp_b = companies
    repo_v_a = VendorRepository(db, comp_a.id)
    v_a = await repo_v_a.add(Vendor(name="Vendor One"))

    repo_po_a = PurchaseOrderRepository(db, comp_a.id)
    repo_po_b = PurchaseOrderRepository(db, comp_b.id)

    po = PurchaseOrder(
        vendor_id=v_a.id,
        po_number="PO-TEST-100",
        order_date=date(2026, 2, 1),
        currency="INR",
        total=Decimal("50000.00"),
    )
    await repo_po_a.add(po)

    pol = PurchaseOrderLine(
        purchase_order_id=po.id,
        description="Parts",
        quantity=Decimal("10.0000"),
        unit_price=Decimal("5000.0000"),
        amount=Decimal("50000.00"),
    )
    db.add(pol)
    await db.flush()

    # Tenant B isolation
    assert await repo_po_b.get(po.id) is None
    assert await repo_po_b.get_by_number("PO-TEST-100") is None

    # Tenant A fetch with lines
    fetched_po = await repo_po_a.get_with_lines(po.id)
    assert fetched_po is not None
    assert len(fetched_po.lines) == 1
    assert fetched_po.lines[0].description == "Parts"

    # Invoices
    repo_inv_a = InvoiceRepository(db, comp_a.id)
    repo_inv_b = InvoiceRepository(db, comp_b.id)

    inv = Invoice(
        vendor_id=v_a.id,
        po_id=po.id,
        invoice_number="INV-TEST-100",
        invoice_date=date(2026, 2, 5),
        currency="INR",
        subtotal=Decimal("50000.00"),
        total=Decimal("50000.00"),
    )
    await repo_inv_a.add(inv)

    invl = InvoiceLine(
        invoice_id=inv.id,
        po_line_id=pol.id,
        description="Parts",
        quantity=Decimal("10.0000"),
        unit_price=Decimal("5000.0000"),
        amount=Decimal("50000.00"),
    )
    db.add(invl)
    await db.flush()

    # Tenant B cannot see Tenant A's invoice
    assert await repo_inv_b.get(inv.id) is None
    assert len(await repo_inv_b.get_by_number("INV-TEST-100")) == 0

    fetched_inv = await repo_inv_a.get_with_lines(inv.id)
    assert fetched_inv is not None
    assert len(fetched_inv.lines) == 1
    assert fetched_inv.lines[0].amount == Decimal("50000.00")


async def test_goods_receipt_repository(
    db: AsyncSession, companies: tuple[Company, Company]
) -> None:
    comp_a, comp_b = companies
    repo_v = VendorRepository(db, comp_a.id)
    v = await repo_v.add(Vendor(name="Vendor GR"))
    repo_po = PurchaseOrderRepository(db, comp_a.id)
    po = await repo_po.add(
        PurchaseOrder(
            vendor_id=v.id,
            po_number="PO-GR-01",
            order_date=date(2026, 2, 1),
            total=Decimal("1000.00"),
        )
    )

    repo_gr_a = GoodsReceiptRepository(db, comp_a.id)
    repo_gr_b = GoodsReceiptRepository(db, comp_b.id)

    gr = await repo_gr_a.add(
        GoodsReceipt(
            po_id=po.id,
            receipt_number="GR-TEST-001",
            receipt_date=date(2026, 2, 4),
        )
    )
    grl = GoodsReceiptLine(
        goods_receipt_id=gr.id,
        quantity_received=Decimal("5.0000"),
    )
    db.add(grl)
    await db.flush()

    assert await repo_gr_b.get(gr.id) is None
    fetched = await repo_gr_a.get_with_lines(gr.id)
    assert fetched is not None
    assert len(fetched.lines) == 1
    assert fetched.lines[0].quantity_received == Decimal("5.0000")


async def test_banking_and_payment_repositories(
    db: AsyncSession, companies: tuple[Company, Company]
) -> None:
    comp_a, comp_b = companies
    repo_bank_a = BankAccountRepository(db, comp_a.id)
    repo_bank_b = BankAccountRepository(db, comp_b.id)

    acc_a = await repo_bank_a.add(
        BankAccount(account_name="Ops A", account_number="ACT-A-01", currency="INR")
    )
    assert await repo_bank_b.get(acc_a.id) is None
    assert await repo_bank_b.get_by_number("ACT-A-01") is None

    repo_bt_a = BankTransactionRepository(db, comp_a.id)
    repo_bt_b = BankTransactionRepository(db, comp_b.id)

    bt = await repo_bt_a.add(
        BankTransaction(
            bank_account_id=acc_a.id,
            transaction_date=date(2026, 2, 10),
            amount=Decimal("15000.00"),
            currency="INR",
            direction=BankTransactionDirection.DEBIT,
            reference="TXN-A-01",
        )
    )

    assert await repo_bt_b.get(bt.id) is None
    txs_a = await repo_bt_a.list_by_account(acc_a.id)
    assert len(txs_a) == 1
    assert txs_a[0].reference == "TXN-A-01"

    # Payment repository
    repo_pmt_a = PaymentRepository(db, comp_a.id)
    repo_pmt_b = PaymentRepository(db, comp_b.id)

    pmt = await repo_pmt_a.add(
        Payment(
            bank_account_id=acc_a.id,
            amount=Decimal("15000.00"),
            currency="INR",
            payment_date=date(2026, 2, 10),
            beneficiary_reference="REF-PMT-A1",
        )
    )
    assert await repo_pmt_b.get(pmt.id) is None
    assert len(await repo_pmt_a.list_by_bank_account(acc_a.id)) == 1


async def test_ledger_repository_and_double_entry_balance(
    db: AsyncSession, companies: tuple[Company, Company]
) -> None:
    comp_a, comp_b = companies
    repo_acc_a = LedgerAccountRepository(db, comp_a.id)
    repo_acc_b = LedgerAccountRepository(db, comp_b.id)

    cash = await repo_acc_a.add(
        LedgerAccount(account_code="1000", name="Cash", account_type="ASSET", currency="INR")
    )
    exp = await repo_acc_a.add(
        LedgerAccount(account_code="5000", name="COGS", account_type="EXPENSE", currency="INR")
    )

    assert await repo_acc_b.get_by_code("1000") is None
    assert await repo_acc_a.get_by_code("1000") is not None

    repo_je_a = JournalEntryRepository(db, comp_a.id)
    repo_je_b = JournalEntryRepository(db, comp_b.id)

    je = await repo_je_a.add(
        JournalEntry(
            entry_date=date(2026, 2, 15),
            description="Expense purchase",
            reference="JE-TEST-001",
            status=DocumentStatus.POSTED,
        )
    )

    db.add(
        JournalEntryLine(
            journal_entry_id=je.id,
            ledger_account_id=exp.id,
            debit=Decimal("12500.00"),
            credit=Decimal("0.00"),
        )
    )
    db.add(
        JournalEntryLine(
            journal_entry_id=je.id,
            ledger_account_id=cash.id,
            debit=Decimal("0.00"),
            credit=Decimal("12500.00"),
        )
    )
    await db.flush()

    assert await repo_je_b.get(je.id) is None
    fetched_je = await repo_je_a.get_with_lines(je.id)
    assert fetched_je is not None
    assert fetched_je.total_debit == Decimal("12500.00")
    assert fetched_je.total_credit == Decimal("12500.00")
    assert fetched_je.is_balanced is True


async def test_contract_and_expense_report_repositories(
    db: AsyncSession, companies: tuple[Company, Company]
) -> None:
    comp_a, comp_b = companies
    repo_ctr_a = ContractRepository(db, comp_a.id)
    repo_ctr_b = ContractRepository(db, comp_b.id)

    ctr = await repo_ctr_a.add(
        Contract(
            contract_number="CTR-TEST-01",
            start_date=date(2026, 1, 1),
            value=Decimal("500000.00"),
        )
    )
    assert await repo_ctr_b.get(ctr.id) is None
    assert await repo_ctr_a.get_by_number("CTR-TEST-01") is not None

    repo_exp_a = ExpenseReportRepository(db, comp_a.id)
    repo_exp_b = ExpenseReportRepository(db, comp_b.id)

    expr = await repo_exp_a.add(
        ExpenseReport(
            report_number="EXP-TEST-01",
            expense_date=date(2026, 1, 20),
            total=Decimal("1250.00"),
        )
    )
    assert await repo_exp_b.get(expr.id) is None
    assert await repo_exp_a.get_by_number("EXP-TEST-01") is not None
