"""Deterministic seed foundation (spec sections 20, 21, 22, 23, 24).

Provides the NovaScale AI synthetic company profile and deterministic,
seeded data generators for both master data and multi-month financial transactions.

Target profile (spec section 20):
- 3 bank accounts
- 42 vendors
- 18 customers
- 12 employees (users with RBAC roles)
- 1,500 bank transactions
- 450 invoices
- 410 purchase orders
- 390 goods receipts
- 600 ledger entries (balanced double-entry lines)
- 80 expense reports
- 15 vendor contracts
- 91-day FX rates across 3 currency pairs (INR/USD, INR/EUR, USD/EUR)

Injected exceptions (~30-35 known scenarios, spec sections 21-24):
- Demo 1: Payment fragmentation (1 invoice of ₹14,50,000 with 14x ₹1,00,000 payments)
- Demo 2: Quantity mismatch (1,000 units invoiced vs 800 PO vs 760 receipt, diff ₹3,84,000)
- Demo 3: Clean transaction (full 6-way match auto-resolvable)
- 5 duplicate invoices
- 4 PO mismatches
- 3 receipt mismatches
- 4 duplicate payments
- 3 unusual vendor activity
- 1 additional payment fragmentation (total 2)
- 3 missing documents
- 3 incorrect GL mappings
- 2 incorrect accruals
- 2 AR mismatches
- 2 cash anomalies

Every generator is seeded from a global ``random.Random`` instance so runs
are byte-for-byte reproducible.
"""

from __future__ import annotations

import json
import random
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.banking import BankAccount, BankTransaction, Payment
from app.db.models.counterparty import Customer, Vendor
from app.db.models.fx import FxRate
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
from app.db.models.tenancy import Company, RoleAssignment, User
from app.domain.enums import (
    BankTransactionDirection,
    Currency,
    DocumentStatus,
    ExceptionType,
    Role,
)

# NovaScale AI profile (spec section 20).
NOVASCALE_PROFILE = {
    "name": "NovaScale AI",
    "legal_name": "NovaScale AI Technologies Pvt. Ltd.",
    "base_currency": Currency.INR.value,
    "fiscal_year_end": "03-31",
    "targets": {
        "vendors": 42,
        "customers": 18,
        "employees": 12,
        "bank_accounts": 3,
        "ledger_accounts": 60,
    },
}

NOVASCALE_TRANSACTION_TARGETS = {
    "invoices": 450,
    "purchase_orders": 410,
    "goods_receipts": 390,
    "bank_transactions": 1500,
    "ledger_entries": 600,
    "expense_reports": 80,
}

# Deterministic currency pairs used to exercise fx_rates (spec sections 20/24).
FX_PAIRS: list[tuple[str, str, str]] = [
    (Currency.INR.value, Currency.USD.value, "RBI"),
    (Currency.INR.value, Currency.EUR.value, "RBI"),
    (Currency.USD.value, Currency.EUR.value, "ECB"),
]

VENDOR_NAME_PREFIXES = ["Acme", "Vertex", "Blue", "Swift", "Nova", "Prime", "Orion", "Delta"]
VENDOR_NAME_SUFFIXES = ["Supplies", "Industries", "Logistics", "Systems", "Partners", "Tech"]

CUSTOMER_NAME_PREFIXES = ["Stellar", "Quantum", "Bright", "Fusion", "Apex", "Core"]
CUSTOMER_NAME_SUFFIXES = ["Labs", "Group", "Solutions", "Digital", "Ventures"]

EMPLOYEES_DATA: list[tuple[str, str, Role]] = [
    ("Anita Sharma", "anita.sharma@novascale.ai", Role.CFO),
    ("Rajesh Verma", "rajesh.verma@novascale.ai", Role.CONTROLLER),
    ("Priya Nair", "priya.nair@novascale.ai", Role.ACCOUNTANT),
    ("Amit Patel", "amit.patel@novascale.ai", Role.ACCOUNTANT),
    ("Vikram Rao", "vikram.rao@novascale.ai", Role.VIEWER),
    ("Sneha Reddy", "sneha.reddy@novascale.ai", Role.VIEWER),
    ("Rohan Gupta", "rohan.gupta@novascale.ai", Role.VIEWER),
    ("Ananya Iyer", "ananya.iyer@novascale.ai", Role.VIEWER),
    ("Karthik Menon", "karthik.menon@novascale.ai", Role.VIEWER),
    ("Pooja Joshi", "pooja.joshi@novascale.ai", Role.VIEWER),
    ("Sunita Deshmukh", "sunita.deshmukh@novascale.ai", Role.VIEWER),
    ("Manoj Kumar", "manoj.kumar@novascale.ai", Role.VIEWER),
]

LEDGER_ACCOUNT_TYPES = {
    "1000": "ASSET",
    "1100": "ASSET",
    "1200": "ASSET",
    "1300": "ASSET",
    "1400": "ASSET",
    "1500": "ASSET",
    "1600": "ASSET",
    "1700": "ASSET",
    "1800": "ASSET",
    "2000": "LIABILITY",
    "2100": "LIABILITY",
    "2200": "LIABILITY",
    "2300": "LIABILITY",
    "2400": "LIABILITY",
    "2500": "LIABILITY",
    "2600": "LIABILITY",
    "3000": "EQUITY",
    "3100": "EQUITY",
    "3200": "EQUITY",
    "4000": "REVENUE",
    "4100": "REVENUE",
    "4200": "REVENUE",
    "4300": "REVENUE",
    "5000": "EXPENSE",
    "5100": "EXPENSE",
    "5200": "EXPENSE",
    "5300": "EXPENSE",
    "5400": "EXPENSE",
    "5500": "EXPENSE",
    "5600": "EXPENSE",
    "5700": "EXPENSE",
    "5800": "EXPENSE",
    "5900": "EXPENSE",
    "6000": "EXPENSE",
}

LEDGER_ACCOUNT_LABELS: dict[str, str] = {
    "1000": "Cash and Cash Equivalents",
    "1100": "Accounts Receivable",
    "1200": "Inventory",
    "1300": "Prepaid Expenses",
    "1400": "Fixed Assets",
    "1500": "Accumulated Depreciation",
    "1600": "Intangible Assets",
    "1700": "Security Deposits",
    "1800": "Deferred Tax Assets",
    "2000": "Accounts Payable",
    "2100": "Accrued Liabilities",
    "2200": "Short-Term Debt",
    "2300": "Deferred Revenue",
    "2400": "Tax Payable",
    "2500": "Other Current Liabilities",
    "2600": "Long-Term Debt",
    "3000": "Common Stock",
    "3100": "Additional Paid-In Capital",
    "3200": "Retained Earnings",
    "4000": "Product Revenue",
    "4100": "Service Revenue",
    "4200": "Interest Income",
    "4300": "Other Income",
    "5000": "Cost of Goods Sold",
    "5100": "Salaries and Wages",
    "5200": "Rent and Utilities",
    "5300": "Marketing and Sales",
    "5400": "IT and Software",
    "5500": "Professional Fees",
    "5600": "Travel and Entertainment",
    "5700": "Depreciation Expense",
    "5800": "Office Supplies",
    "5900": "Insurance",
    "6000": "Miscellaneous Expense",
}


class DeterministicSeed:
    """Deterministic data generator for a single company (tenant)."""

    def __init__(self, seed: int = 42) -> None:
        self.rng = random.Random(seed)

    # --- name generation -------------------------------------------------
    def _pick(self, prefixes: list[str], suffixes: list[str]) -> str:
        return f"{self.rng.choice(prefixes)} {self.rng.choice(suffixes)}"

    def vendor_name(self) -> str:
        return self._pick(VENDOR_NAME_PREFIXES, VENDOR_NAME_SUFFIXES)

    def customer_name(self) -> str:
        return self._pick(CUSTOMER_NAME_PREFIXES, CUSTOMER_NAME_SUFFIXES)

    # --- accounts --------------------------------------------------------
    def ledger_accounts(self, target: int = 60) -> list[tuple[str, str, str]]:
        """Deterministic chart of accounts: (code, name, account_type)."""
        accounts: list[tuple[str, str, str]] = []
        for code, label in LEDGER_ACCOUNT_LABELS.items():
            kind = LEDGER_ACCOUNT_TYPES[code]
            accounts.append((code, label, kind))
        family_codes = sorted(LEDGER_ACCOUNT_TYPES)
        while len(accounts) < target:
            code_family = self.rng.choice(family_codes)
            base_code = int(code_family)
            suffix = self.rng.randint(1, 99)
            code = f"{base_code + suffix // 100}.{suffix:02d}"
            if any(existing[0] == code for existing in accounts):
                continue
            kind = LEDGER_ACCOUNT_TYPES[code_family]
            label = f"{kind.title()} Account {code}"
            accounts.append((code, label, kind))
        return accounts[:target]

    def fx_rates(
        self, start: date, end: date, base_currency: str = Currency.INR.value
    ) -> list[tuple[str, str, Decimal, date, str]]:
        """Deterministic FX rates per pair per day within [start, end]."""
        rows: list[tuple[str, str, Decimal, date, str]] = []
        day = start
        while day <= end:
            for pair_base, pair_quote, source in FX_PAIRS:
                mid = {
                    (Currency.INR.value, Currency.USD.value): Decimal("0.012"),
                    (Currency.INR.value, Currency.EUR.value): Decimal("0.011"),
                    (Currency.USD.value, Currency.EUR.value): Decimal("0.92"),
                }[(pair_base, pair_quote)]
                wiggle = Decimal(str(self.rng.uniform(0.98, 1.02)))
                rate = (mid * wiggle).quantize(Decimal("0.00000001"))
                rows.append((pair_base, pair_quote, rate, day, source))
            day += timedelta(days=1)
        return rows


async def seed_company(
    session: AsyncSession,
    *,
    seed: int = 42,
    name: str | None = None,
    months: int = 3,
    fx_start: date | None = None,
    include_transactions: bool = False,
) -> Company:
    """Deterministically create NovaScale AI master data (and transactions if requested).

    Returns the created company. Safe to call multiple times (idempotent by name lookup).
    """
    profile = NOVASCALE_PROFILE
    company_name = name or profile["name"]

    company_obj = await session.scalar(select(Company).where(Company.name == company_name))
    if company_obj is not None:
        if include_transactions:
            await seed_financial_transactions(
                session, company_obj, seed=seed, months=months, fx_start=fx_start
            )
        return company_obj

    company = Company(
        name=company_name,
        legal_name=profile["legal_name"],
        base_currency=profile["base_currency"],
        fiscal_year_end=profile["fiscal_year_end"],
        is_active=True,
    )
    session.add(company)
    await session.flush()

    gen = DeterministicSeed(seed=seed)

    # FX rates for the default 3-month window (deterministic).
    if fx_start is None:
        fx_start = date(2026, 1, 1)
    fx_end = fx_start + timedelta(days=months * 30)
    for base, quote, rate, eff_date, source in gen.fx_rates(fx_start, fx_end):
        session.add(
            FxRate(
                base_currency=base,
                quote_currency=quote,
                rate=rate,
                effective_date=eff_date,
                source=source,
            )
        )

    # Ledger accounts (spec: 60).
    for code, label, kind in gen.ledger_accounts():
        session.add(
            LedgerAccount(
                company_id=company.id,
                account_code=code,
                name=label,
                account_type=kind,
                currency=profile["base_currency"],
            )
        )

    # Bank accounts (spec: 3 accounts).
    bank_currencies = [Currency.INR.value, Currency.INR.value, Currency.USD.value]
    for i, cur in enumerate(bank_currencies, start=1):
        session.add(
            BankAccount(
                company_id=company.id,
                account_name=f"NovaScale Operating Account {i}",
                account_number=f"NB{i:04d}{gen.rng.randint(1000, 9999)}",
                currency=cur,
                is_active=True,
            )
        )

    # Vendors (spec: 42).
    used_names: set[str] = set()
    for _ in range(profile["targets"]["vendors"]):
        vname = gen.vendor_name()
        while vname in used_names:
            vname = gen.vendor_name()
        used_names.add(vname)
        session.add(
            Vendor(
                company_id=company.id,
                name=vname,
                tax_id=f"TAX{gen.rng.randint(100000, 999999)}",
                status=DocumentStatus.OPEN,
            )
        )

    # Customers (spec: 18).
    used_names = set()
    for _ in range(profile["targets"]["customers"]):
        cname = gen.customer_name()
        while cname in used_names:
            cname = gen.customer_name()
        used_names.add(cname)
        session.add(Customer(company_id=company.id, name=cname, status=DocumentStatus.OPEN))

    await session.flush()

    if include_transactions:
        await seed_financial_transactions(
            session, company, seed=seed, months=months, fx_start=fx_start
        )

    return company


async def seed_financial_transactions(
    session: AsyncSession,
    company: Company,
    *,
    seed: int = 42,
    months: int = 3,
    fx_start: date | None = None,
    save_ground_truth: bool = False,
) -> dict:
    """Seed the full multi-month financial transactions and ground truth exceptions.

    Generates:
    - 12 Employees (Users + RoleAssignments)
    - 15 Contracts
    - 410 Purchase Orders with Lines
    - 390 Goods Receipts with Lines
    - 450 Invoices with Lines (including USD multi-currency)
    - Payments (linked to invoices, bank accounts, and bank txns)
    - 1,500 Bank Transactions
    - 600 Journal Entries (all balanced double-entry lines)
    - 80 Expense Reports
    - 34 Ground Truth scenarios (33 injected exceptions + clean demo)
    """
    rng = random.Random(seed)
    start_date = fx_start or date(2026, 1, 1)

    # Check if transactions already exist
    existing_inv = await session.scalar(
        select(Invoice.id).where(Invoice.company_id == company.id).limit(1)
    )
    if existing_inv is not None:
        return {"status": "already_seeded", "company_id": str(company.id)}

    # Fetch master rows
    vendors = (
        await session.scalars(
            select(Vendor).where(Vendor.company_id == company.id).order_by(Vendor.name)
        )
    ).all()
    customers = (
        await session.scalars(
            select(Customer).where(Customer.company_id == company.id).order_by(Customer.name)
        )
    ).all()
    bank_accounts = (
        await session.scalars(
            select(BankAccount)
            .where(BankAccount.company_id == company.id)
            .order_by(BankAccount.account_number)
        )
    ).all()
    ledger_accounts = (
        await session.scalars(
            select(LedgerAccount)
            .where(LedgerAccount.company_id == company.id)
            .order_by(LedgerAccount.account_code)
        )
    ).all()

    account_by_code = {acc.account_code: acc for acc in ledger_accounts}
    cash_acc = account_by_code.get("1000", ledger_accounts[0])
    ar_acc = account_by_code.get("1100", ledger_accounts[1])
    inv_acc = account_by_code.get("1200", ledger_accounts[2])
    ap_acc = account_by_code.get("2000", ledger_accounts[9])
    accrual_acc = account_by_code.get("2100", ledger_accounts[10])
    rev_acc = account_by_code.get("4000", ledger_accounts[19])
    cogs_acc = account_by_code.get("5000", ledger_accounts[23])
    salary_acc = account_by_code.get("5100", ledger_accounts[24])
    rent_acc = account_by_code.get("5200", ledger_accounts[25])
    it_acc = account_by_code.get("5400", ledger_accounts[27])
    travel_acc = account_by_code.get("5600", ledger_accounts[29])
    office_acc = account_by_code.get("5800", ledger_accounts[31])

    inr_bank_acc_1 = bank_accounts[0]
    inr_bank_acc_2 = bank_accounts[1]
    usd_bank_acc = bank_accounts[2]

    ground_truth: list[dict] = []

    # 1. Employees / Users (12 employees)
    users: list[User] = []
    for full_name, email, role in EMPLOYEES_DATA:
        u = User(
            company_id=company.id,
            email=email,
            full_name=full_name,
            is_active=True,
        )
        session.add(u)
        users.append(u)
    await session.flush()

    for u, (_, _, role) in zip(users, EMPLOYEES_DATA):
        session.add(RoleAssignment(user_id=u.id, company_id=company.id, role=role))
    await session.flush()

    # 2. Contracts (15 contracts)
    contracts: list[Contract] = []
    for i in range(15):
        v = vendors[i % len(vendors)]
        c = Contract(
            company_id=company.id,
            counterparty_id=v.id,
            contract_number=f"CTR-2026-{i + 1:03d}",
            start_date=start_date,
            end_date=start_date + timedelta(days=365),
            value=Decimal(str(rng.randint(200000, 2500000))),
            status=DocumentStatus.OPEN,
        )
        session.add(c)
        contracts.append(c)
    await session.flush()

    # 3. Ground Truth Injected Exceptions Preparation
    # Demo 1: Payment Fragmentation (spec section 22)
    demo1_vendor = vendors[0]
    po_demo1 = PurchaseOrder(
        company_id=company.id,
        vendor_id=demo1_vendor.id,
        po_number="PO-DEMO-001",
        order_date=start_date + timedelta(days=14),
        currency="INR",
        total=Decimal("1450000.00"),
        status=DocumentStatus.OPEN,
    )
    session.add(po_demo1)
    await session.flush()

    po_demo1_line = PurchaseOrderLine(
        purchase_order_id=po_demo1.id,
        description="High Performance Compute Blades",
        quantity=Decimal("1450.0000"),
        unit_price=Decimal("1000.0000"),
        amount=Decimal("1450000.00"),
    )
    session.add(po_demo1_line)
    await session.flush()

    gr_demo1 = GoodsReceipt(
        company_id=company.id,
        po_id=po_demo1.id,
        receipt_number="GR-DEMO-001",
        receipt_date=start_date + timedelta(days=18),
        status=DocumentStatus.OPEN,
    )
    session.add(gr_demo1)
    await session.flush()

    gr_demo1_line = GoodsReceiptLine(
        goods_receipt_id=gr_demo1.id,
        po_line_id=po_demo1_line.id,
        description="High Performance Compute Blades",
        quantity_received=Decimal("1450.0000"),
    )
    session.add(gr_demo1_line)
    await session.flush()

    inv_demo1 = Invoice(
        company_id=company.id,
        vendor_id=demo1_vendor.id,
        po_id=po_demo1.id,
        invoice_number="INV-DEMO-001",
        invoice_date=start_date + timedelta(days=20),
        due_date=start_date + timedelta(days=50),
        currency="INR",
        subtotal=Decimal("1450000.00"),
        tax=Decimal("0.00"),
        total=Decimal("1450000.00"),
        status=DocumentStatus.OPEN,
    )
    session.add(inv_demo1)
    await session.flush()

    inv_demo1_line = InvoiceLine(
        invoice_id=inv_demo1.id,
        po_line_id=po_demo1_line.id,
        description="High Performance Compute Blades",
        quantity=Decimal("1450.0000"),
        unit_price=Decimal("1000.0000"),
        amount=Decimal("1450000.00"),
    )
    session.add(inv_demo1_line)
    await session.flush()

    # 14 fragmented payments of 1,00,000
    demo1_payments: list[Payment] = []
    demo1_bank_txs: list[BankTransaction] = []
    for p_idx in range(14):
        pmt_date = start_date + timedelta(days=24 + (p_idx // 4))
        p = Payment(
            company_id=company.id,
            vendor_id=demo1_vendor.id,
            invoice_id=inv_demo1.id,
            bank_account_id=inr_bank_acc_1.id,
            amount=Decimal("100000.00"),
            currency="INR",
            payment_date=pmt_date,
            beneficiary_reference=f"REF-FRAG-DEMO-{p_idx + 1:02d}",
            status=DocumentStatus.POSTED,
        )
        session.add(p)
        demo1_payments.append(p)

        bt = BankTransaction(
            company_id=company.id,
            bank_account_id=inr_bank_acc_1.id,
            transaction_date=pmt_date,
            amount=Decimal("100000.00"),
            currency="INR",
            direction=BankTransactionDirection.DEBIT,
            counterparty=demo1_vendor.name,
            reference=f"REF-FRAG-DEMO-{p_idx + 1:02d}",
            status=DocumentStatus.POSTED,
        )
        session.add(bt)
        demo1_bank_txs.append(bt)

    await session.flush()

    ground_truth.append(
        {
            "scenario_id": "SCENARIO-001",
            "scenario_type": ExceptionType.PAYMENT_FRAGMENTATION.value,
            "title": "Critical Demo: Payment Fragmentation Anomaly",
            "description": (
                "Invoice of 14,50,000 paid via 14 separate payments of 1,00,000 "
                "within same settlement window"
            ),
            "expected_action": "ESCALATE",
            "financial_impact": "1450000.00",
            "human_review_required": True,
            "primary_record_type": "INVOICE",
            "primary_record_id": str(inv_demo1.id),
            "primary_record_number": inv_demo1.invoice_number,
            "related_record_ids": [str(p.id) for p in demo1_payments],
            "expected_root_cause": "payment fragmentation anomaly",
        }
    )

    # Demo 2: Quantity Mismatch (spec section 23)
    # PO: 800 units @ 1600 = 12,80,000; Receipt: 760 units; Invoice: 1,000 units @ 1600 = 16,00,000
    demo2_vendor = vendors[1]
    po_demo2 = PurchaseOrder(
        company_id=company.id,
        vendor_id=demo2_vendor.id,
        po_number="PO-DEMO-002",
        order_date=start_date + timedelta(days=35),
        currency="INR",
        total=Decimal("1280000.00"),
        status=DocumentStatus.OPEN,
    )
    session.add(po_demo2)
    await session.flush()

    po_demo2_line = PurchaseOrderLine(
        purchase_order_id=po_demo2.id,
        description="Optic Transceivers 400G",
        quantity=Decimal("800.0000"),
        unit_price=Decimal("1600.0000"),
        amount=Decimal("1280000.00"),
    )
    session.add(po_demo2_line)
    await session.flush()

    gr_demo2 = GoodsReceipt(
        company_id=company.id,
        po_id=po_demo2.id,
        receipt_number="GR-DEMO-002",
        receipt_date=start_date + timedelta(days=40),
        status=DocumentStatus.OPEN,
    )
    session.add(gr_demo2)
    await session.flush()

    gr_demo2_line = GoodsReceiptLine(
        goods_receipt_id=gr_demo2.id,
        po_line_id=po_demo2_line.id,
        description="Optic Transceivers 400G",
        quantity_received=Decimal("760.0000"),
    )
    session.add(gr_demo2_line)
    await session.flush()

    inv_demo2 = Invoice(
        company_id=company.id,
        vendor_id=demo2_vendor.id,
        po_id=po_demo2.id,
        invoice_number="INV-DEMO-002",
        invoice_date=start_date + timedelta(days=42),
        due_date=start_date + timedelta(days=72),
        currency="INR",
        subtotal=Decimal("1600000.00"),
        tax=Decimal("0.00"),
        total=Decimal("1600000.00"),
        status=DocumentStatus.OPEN,
    )
    session.add(inv_demo2)
    await session.flush()

    inv_demo2_line = InvoiceLine(
        invoice_id=inv_demo2.id,
        po_line_id=po_demo2_line.id,
        description="Optic Transceivers 400G",
        quantity=Decimal("1000.0000"),
        unit_price=Decimal("1600.0000"),
        amount=Decimal("1600000.00"),
    )
    session.add(inv_demo2_line)
    await session.flush()

    ground_truth.append(
        {
            "scenario_id": "SCENARIO-002",
            "scenario_type": ExceptionType.PO_MISMATCH.value,
            "title": "Second Demo: Quantity Mismatch across Invoice, PO, Receipt",
            "description": (
                "Invoice 1,000 units exceeds PO 800 units and Goods Receipt 760 units. "
                "Variance = 240 units x 1,600 = 3,84,000"
            ),
            "expected_action": "STAGE",
            "financial_impact": "384000.00",
            "human_review_required": True,
            "primary_record_type": "INVOICE",
            "primary_record_id": str(inv_demo2.id),
            "primary_record_number": inv_demo2.invoice_number,
            "related_record_ids": [str(po_demo2.id), str(gr_demo2.id)],
            "expected_root_cause": "Invoice quantity exceeds received quantity",
        }
    )

    # Demo 3: Clean Transaction (spec section 24)
    demo3_vendor = vendors[2]
    po_demo3 = PurchaseOrder(
        company_id=company.id,
        vendor_id=demo3_vendor.id,
        po_number="PO-CLEAN-001",
        order_date=start_date + timedelta(days=20),
        currency="INR",
        total=Decimal("250000.00"),
        status=DocumentStatus.POSTED,
    )
    session.add(po_demo3)
    await session.flush()

    po_demo3_line = PurchaseOrderLine(
        purchase_order_id=po_demo3.id,
        description="Industrial Storage Units",
        quantity=Decimal("250.0000"),
        unit_price=Decimal("1000.0000"),
        amount=Decimal("250000.00"),
    )
    session.add(po_demo3_line)
    await session.flush()

    gr_demo3 = GoodsReceipt(
        company_id=company.id,
        po_id=po_demo3.id,
        receipt_number="GR-CLEAN-001",
        receipt_date=start_date + timedelta(days=24),
        status=DocumentStatus.POSTED,
    )
    session.add(gr_demo3)
    await session.flush()

    gr_demo3_line = GoodsReceiptLine(
        goods_receipt_id=gr_demo3.id,
        po_line_id=po_demo3_line.id,
        description="Industrial Storage Units",
        quantity_received=Decimal("250.0000"),
    )
    session.add(gr_demo3_line)
    await session.flush()

    inv_demo3 = Invoice(
        company_id=company.id,
        vendor_id=demo3_vendor.id,
        po_id=po_demo3.id,
        invoice_number="INV-CLEAN-001",
        invoice_date=start_date + timedelta(days=26),
        due_date=start_date + timedelta(days=56),
        currency="INR",
        subtotal=Decimal("250000.00"),
        tax=Decimal("0.00"),
        total=Decimal("250000.00"),
        status=DocumentStatus.PAID,
    )
    session.add(inv_demo3)
    await session.flush()

    inv_demo3_line = InvoiceLine(
        invoice_id=inv_demo3.id,
        po_line_id=po_demo3_line.id,
        description="Industrial Storage Units",
        quantity=Decimal("250.0000"),
        unit_price=Decimal("1000.0000"),
        amount=Decimal("250000.00"),
    )
    session.add(inv_demo3_line)
    await session.flush()

    pmt_demo3 = Payment(
        company_id=company.id,
        vendor_id=demo3_vendor.id,
        invoice_id=inv_demo3.id,
        bank_account_id=inr_bank_acc_1.id,
        amount=Decimal("250000.00"),
        currency="INR",
        payment_date=start_date + timedelta(days=32),
        beneficiary_reference="REF-CLEAN-001",
        status=DocumentStatus.POSTED,
    )
    session.add(pmt_demo3)

    bt_demo3 = BankTransaction(
        company_id=company.id,
        bank_account_id=inr_bank_acc_1.id,
        transaction_date=start_date + timedelta(days=32),
        amount=Decimal("250000.00"),
        currency="INR",
        direction=BankTransactionDirection.DEBIT,
        counterparty=demo3_vendor.name,
        reference="REF-CLEAN-001",
        status=DocumentStatus.POSTED,
    )
    session.add(bt_demo3)
    await session.flush()

    # GL entry for Clean Demo
    je_clean = JournalEntry(
        company_id=company.id,
        entry_date=start_date + timedelta(days=32),
        description=f"Payment for {inv_demo3.invoice_number}",
        reference="JE-CLEAN-001",
        status=DocumentStatus.POSTED,
    )
    session.add(je_clean)
    await session.flush()
    session.add(
        JournalEntryLine(
            journal_entry_id=je_clean.id,
            ledger_account_id=ap_acc.id,
            debit=Decimal("250000.00"),
            credit=Decimal("0.00"),
            description="AP Debit",
        )
    )
    session.add(
        JournalEntryLine(
            journal_entry_id=je_clean.id,
            ledger_account_id=cash_acc.id,
            debit=Decimal("0.00"),
            credit=Decimal("250000.00"),
            description="Cash Credit",
        )
    )
    await session.flush()

    ground_truth.append(
        {
            "scenario_id": "SCENARIO-003",
            "scenario_type": "CLEAN_TRANSACTION",
            "title": "Third Demo: Clean 6-Way Matched Transaction",
            "description": "Invoice, PO, Receipt, Payment, Bank Tx, and GL all perfectly match",
            "expected_action": "AUTO_RESOLVE",
            "financial_impact": "0.00",
            "human_review_required": False,
            "primary_record_type": "INVOICE",
            "primary_record_id": str(inv_demo3.id),
            "primary_record_number": inv_demo3.invoice_number,
            "related_record_ids": [
                str(po_demo3.id),
                str(gr_demo3.id),
                str(pmt_demo3.id),
                str(bt_demo3.id),
                str(je_clean.id),
            ],
            "expected_root_cause": "None (clean transaction)",
        }
    )

    # 4. Injected Exception Sets (Spec Section 21)
    scenario_counter = 4

    # 5 Duplicate Invoices (Scenarios 4-8)
    for dup_idx in range(5):
        v = vendors[3 + dup_idx]
        po = PurchaseOrder(
            company_id=company.id,
            vendor_id=v.id,
            po_number=f"PO-DUP-{dup_idx + 1:03d}",
            order_date=start_date + timedelta(days=10 + dup_idx * 5),
            currency="INR",
            total=Decimal("85000.00"),
            status=DocumentStatus.OPEN,
        )
        session.add(po)
        await session.flush()

        gr = GoodsReceipt(
            company_id=company.id,
            po_id=po.id,
            receipt_number=f"GR-DUP-{dup_idx + 1:03d}",
            receipt_date=start_date + timedelta(days=14 + dup_idx * 5),
            status=DocumentStatus.OPEN,
        )
        session.add(gr)
        await session.flush()

        inv_orig = Invoice(
            company_id=company.id,
            vendor_id=v.id,
            po_id=po.id,
            invoice_number=f"INV-DUP-REF-{dup_idx + 1:03d}",
            invoice_date=start_date + timedelta(days=16 + dup_idx * 5),
            currency="INR",
            subtotal=Decimal("85000.00"),
            total=Decimal("85000.00"),
            status=DocumentStatus.OPEN,
        )
        session.add(inv_orig)
        await session.flush()

        inv_dup = Invoice(
            company_id=company.id,
            vendor_id=v.id,
            po_id=po.id,
            invoice_number=f"INV-DUP-REF-{dup_idx + 1:03d}",
            invoice_date=start_date + timedelta(days=18 + dup_idx * 5),
            currency="INR",
            subtotal=Decimal("85000.00"),
            total=Decimal("85000.00"),
            status=DocumentStatus.OPEN,
        )
        session.add(inv_dup)
        await session.flush()

        ground_truth.append(
            {
                "scenario_id": f"SCENARIO-{scenario_counter:03d}",
                "scenario_type": ExceptionType.DUPLICATE_INVOICE.value,
                "title": f"Duplicate Invoice from {v.name}",
                "description": f"Duplicate invoice {inv_orig.invoice_number} submitted twice",
                "expected_action": "ESCALATE",
                "financial_impact": "85000.00",
                "human_review_required": True,
                "primary_record_type": "INVOICE",
                "primary_record_id": str(inv_dup.id),
                "primary_record_number": inv_dup.invoice_number,
                "related_record_ids": [str(inv_orig.id)],
                "expected_root_cause": "Vendor re-submitted identical invoice",
            }
        )
        scenario_counter += 1

    # 4 PO Mismatches (Scenarios 9-12)
    for po_mismatch_idx in range(4):
        v = vendors[8 + po_mismatch_idx]
        po_price = Decimal(str(500 + po_mismatch_idx * 100))
        inv_price = po_price + Decimal("150.00")
        qty = Decimal("100.0000")
        po_tot = (po_price * qty).quantize(Decimal("0.01"))
        inv_tot = (inv_price * qty).quantize(Decimal("0.01"))
        diff = inv_tot - po_tot

        po = PurchaseOrder(
            company_id=company.id,
            vendor_id=v.id,
            po_number=f"PO-MIS-{po_mismatch_idx + 1:03d}",
            order_date=start_date + timedelta(days=12 + po_mismatch_idx * 8),
            currency="INR",
            total=po_tot,
            status=DocumentStatus.OPEN,
        )
        session.add(po)
        await session.flush()

        pol = PurchaseOrderLine(
            purchase_order_id=po.id,
            description="Hardware Parts",
            quantity=qty,
            unit_price=po_price,
            amount=po_tot,
        )
        session.add(pol)
        await session.flush()

        gr = GoodsReceipt(
            company_id=company.id,
            po_id=po.id,
            receipt_number=f"GR-MIS-{po_mismatch_idx + 1:03d}",
            receipt_date=start_date + timedelta(days=16 + po_mismatch_idx * 8),
            status=DocumentStatus.OPEN,
        )
        session.add(gr)
        await session.flush()

        inv = Invoice(
            company_id=company.id,
            vendor_id=v.id,
            po_id=po.id,
            invoice_number=f"INV-POMIS-{po_mismatch_idx + 1:03d}",
            invoice_date=start_date + timedelta(days=18 + po_mismatch_idx * 8),
            currency="INR",
            subtotal=inv_tot,
            total=inv_tot,
            status=DocumentStatus.OPEN,
        )
        session.add(inv)
        await session.flush()

        invl = InvoiceLine(
            invoice_id=inv.id,
            po_line_id=pol.id,
            description="Hardware Parts",
            quantity=qty,
            unit_price=inv_price,
            amount=inv_tot,
        )
        session.add(invl)
        await session.flush()

        ground_truth.append(
            {
                "scenario_id": f"SCENARIO-{scenario_counter:03d}",
                "scenario_type": ExceptionType.PO_MISMATCH.value,
                "title": f"PO Price Mismatch for {inv.invoice_number}",
                "description": f"Invoice unit price {inv_price} exceeds PO unit price {po_price}",
                "expected_action": "STAGE",
                "financial_impact": str(diff),
                "human_review_required": True,
                "primary_record_type": "INVOICE",
                "primary_record_id": str(inv.id),
                "primary_record_number": inv.invoice_number,
                "related_record_ids": [str(po.id)],
                "expected_root_cause": "Unit price mismatch against approved PO",
            }
        )
        scenario_counter += 1

    # 3 Receipt Mismatches (Scenarios 13-15)
    for rc_idx in range(3):
        v = vendors[12 + rc_idx]
        po = PurchaseOrder(
            company_id=company.id,
            vendor_id=v.id,
            po_number=f"PO-RCMIS-{rc_idx + 1:03d}",
            order_date=start_date + timedelta(days=20 + rc_idx * 10),
            currency="INR",
            total=Decimal("200000.00"),
            status=DocumentStatus.OPEN,
        )
        session.add(po)
        await session.flush()

        pol = PurchaseOrderLine(
            purchase_order_id=po.id,
            description="Server Memory DIMMs",
            quantity=Decimal("200.0000"),
            unit_price=Decimal("1000.0000"),
            amount=Decimal("200000.00"),
        )
        session.add(pol)
        await session.flush()

        gr = GoodsReceipt(
            company_id=company.id,
            po_id=po.id,
            receipt_number=f"GR-RCMIS-{rc_idx + 1:03d}",
            receipt_date=start_date + timedelta(days=25 + rc_idx * 10),
            status=DocumentStatus.OPEN,
        )
        session.add(gr)
        await session.flush()

        grl = GoodsReceiptLine(
            goods_receipt_id=gr.id,
            po_line_id=pol.id,
            description="Server Memory DIMMs",
            quantity_received=Decimal("150.0000"),  # Received 150 only
        )
        session.add(grl)
        await session.flush()

        inv = Invoice(
            company_id=company.id,
            vendor_id=v.id,
            po_id=po.id,
            invoice_number=f"INV-RCMIS-{rc_idx + 1:03d}",
            invoice_date=start_date + timedelta(days=28 + rc_idx * 10),
            currency="INR",
            subtotal=Decimal("200000.00"),
            total=Decimal("200000.00"),  # Billed for 200
            status=DocumentStatus.OPEN,
        )
        session.add(inv)
        await session.flush()

        invl = InvoiceLine(
            invoice_id=inv.id,
            po_line_id=pol.id,
            description="Server Memory DIMMs",
            quantity=Decimal("200.0000"),
            unit_price=Decimal("1000.0000"),
            amount=Decimal("200000.00"),
        )
        session.add(invl)
        await session.flush()

        ground_truth.append(
            {
                "scenario_id": f"SCENARIO-{scenario_counter:03d}",
                "scenario_type": ExceptionType.RECEIPT_MISMATCH.value,
                "title": f"Receipt Quantity Mismatch for {inv.invoice_number}",
                "description": "Invoice billed 200 units but goods receipt confirmed 150 units",
                "expected_action": "STAGE",
                "financial_impact": "50000.00",
                "human_review_required": True,
                "primary_record_type": "INVOICE",
                "primary_record_id": str(inv.id),
                "primary_record_number": inv.invoice_number,
                "related_record_ids": [str(po.id), str(gr.id)],
                "expected_root_cause": "Invoiced quantity exceeds goods receipt quantity",
            }
        )
        scenario_counter += 1

    # 4 Duplicate Payments (Scenarios 16-19)
    for dp_idx in range(4):
        v = vendors[15 + dp_idx]
        po = PurchaseOrder(
            company_id=company.id,
            vendor_id=v.id,
            po_number=f"PO-DUPP-{dp_idx + 1:03d}",
            order_date=start_date + timedelta(days=15 + dp_idx * 10),
            currency="INR",
            total=Decimal("120000.00"),
            status=DocumentStatus.OPEN,
        )
        session.add(po)
        await session.flush()

        gr = GoodsReceipt(
            company_id=company.id,
            po_id=po.id,
            receipt_number=f"GR-DUPP-{dp_idx + 1:03d}",
            receipt_date=start_date + timedelta(days=18 + dp_idx * 10),
            status=DocumentStatus.OPEN,
        )
        session.add(gr)
        await session.flush()

        inv = Invoice(
            company_id=company.id,
            vendor_id=v.id,
            po_id=po.id,
            invoice_number=f"INV-DUPP-{dp_idx + 1:03d}",
            invoice_date=start_date + timedelta(days=20 + dp_idx * 10),
            currency="INR",
            subtotal=Decimal("120000.00"),
            total=Decimal("120000.00"),
            status=DocumentStatus.PAID,
        )
        session.add(inv)
        await session.flush()

        # Duplicate payment 1
        p1 = Payment(
            company_id=company.id,
            vendor_id=v.id,
            invoice_id=inv.id,
            bank_account_id=inr_bank_acc_1.id,
            amount=Decimal("120000.00"),
            currency="INR",
            payment_date=start_date + timedelta(days=25 + dp_idx * 10),
            beneficiary_reference=f"REF-DUPP-{dp_idx + 1}-1",
            status=DocumentStatus.POSTED,
        )
        session.add(p1)

        # Duplicate payment 2 (erroneous duplicate)
        p2 = Payment(
            company_id=company.id,
            vendor_id=v.id,
            invoice_id=inv.id,
            bank_account_id=inr_bank_acc_1.id,
            amount=Decimal("120000.00"),
            currency="INR",
            payment_date=start_date + timedelta(days=26 + dp_idx * 10),
            beneficiary_reference=f"REF-DUPP-{dp_idx + 1}-2",
            status=DocumentStatus.POSTED,
        )
        session.add(p2)

        # 2 corresponding bank debit transactions
        bt1 = BankTransaction(
            company_id=company.id,
            bank_account_id=inr_bank_acc_1.id,
            transaction_date=start_date + timedelta(days=25 + dp_idx * 10),
            amount=Decimal("120000.00"),
            currency="INR",
            direction=BankTransactionDirection.DEBIT,
            counterparty=v.name,
            reference=f"REF-DUPP-{dp_idx + 1}-1",
            status=DocumentStatus.POSTED,
        )
        session.add(bt1)

        bt2 = BankTransaction(
            company_id=company.id,
            bank_account_id=inr_bank_acc_1.id,
            transaction_date=start_date + timedelta(days=26 + dp_idx * 10),
            amount=Decimal("120000.00"),
            currency="INR",
            direction=BankTransactionDirection.DEBIT,
            counterparty=v.name,
            reference=f"REF-DUPP-{dp_idx + 1}-2",
            status=DocumentStatus.POSTED,
        )
        session.add(bt2)
        await session.flush()

        ground_truth.append(
            {
                "scenario_id": f"SCENARIO-{scenario_counter:03d}",
                "scenario_type": ExceptionType.DUPLICATE_PAYMENT.value,
                "title": f"Duplicate Payment for Invoice {inv.invoice_number}",
                "description": "Two identical payments of 1,20,000 executed for single invoice",
                "expected_action": "ESCALATE",
                "financial_impact": "120000.00",
                "human_review_required": True,
                "primary_record_type": "PAYMENT",
                "primary_record_id": str(p2.id),
                "primary_record_number": p2.beneficiary_reference,
                "related_record_ids": [str(inv.id), str(p1.id)],
                "expected_root_cause": "Double payment executed against same invoice",
            }
        )
        scenario_counter += 1

    # 3 Unusual Vendor Activity (Scenarios 20-22)
    for uva_idx in range(3):
        v = vendors[19 + uva_idx]
        surge_amount = Decimal("950000.00")
        po = PurchaseOrder(
            company_id=company.id,
            vendor_id=v.id,
            po_number=f"PO-UVA-{uva_idx + 1:03d}",
            order_date=start_date + timedelta(days=30 + uva_idx * 12),
            currency="INR",
            total=surge_amount,
            status=DocumentStatus.OPEN,
        )
        session.add(po)
        await session.flush()

        inv = Invoice(
            company_id=company.id,
            vendor_id=v.id,
            po_id=po.id,
            invoice_number=f"INV-UVA-{uva_idx + 1:03d}",
            invoice_date=start_date + timedelta(days=34 + uva_idx * 12),
            currency="INR",
            subtotal=surge_amount,
            total=surge_amount,
            status=DocumentStatus.OPEN,
        )
        session.add(inv)
        await session.flush()

        ground_truth.append(
            {
                "scenario_id": f"SCENARIO-{scenario_counter:03d}",
                "scenario_type": ExceptionType.UNUSUAL_VENDOR_ACTIVITY.value,
                "title": f"Unusual Volume Surge from {v.name}",
                "description": f"Invoice of {surge_amount} is 10x higher than historical average",
                "expected_action": "ESCALATE",
                "financial_impact": str(surge_amount),
                "human_review_required": True,
                "primary_record_type": "INVOICE",
                "primary_record_id": str(inv.id),
                "primary_record_number": inv.invoice_number,
                "related_record_ids": [str(po.id)],
                "expected_root_cause": "Material volume surge beyond historical vendor profile",
            }
        )
        scenario_counter += 1

    # 2nd Payment Fragmentation (Scenario 23)
    v_frag2 = vendors[22]
    po_frag2 = PurchaseOrder(
        company_id=company.id,
        vendor_id=v_frag2.id,
        po_number="PO-FRAG2-001",
        order_date=start_date + timedelta(days=40),
        currency="INR",
        total=Decimal("500000.00"),
        status=DocumentStatus.OPEN,
    )
    session.add(po_frag2)
    await session.flush()

    inv_frag2 = Invoice(
        company_id=company.id,
        vendor_id=v_frag2.id,
        po_id=po_frag2.id,
        invoice_number="INV-FRAG2-001",
        invoice_date=start_date + timedelta(days=45),
        currency="INR",
        subtotal=Decimal("500000.00"),
        total=Decimal("500000.00"),
        status=DocumentStatus.OPEN,
    )
    session.add(inv_frag2)
    await session.flush()

    frag2_pmts: list[Payment] = []
    for fp_idx in range(10):
        p_date = start_date + timedelta(days=50 + fp_idx)
        p = Payment(
            company_id=company.id,
            vendor_id=v_frag2.id,
            invoice_id=inv_frag2.id,
            bank_account_id=inr_bank_acc_2.id,
            amount=Decimal("50000.00"),
            currency="INR",
            payment_date=p_date,
            beneficiary_reference=f"REF-FRAG2-{fp_idx + 1:02d}",
            status=DocumentStatus.POSTED,
        )
        session.add(p)
        frag2_pmts.append(p)

        bt = BankTransaction(
            company_id=company.id,
            bank_account_id=inr_bank_acc_2.id,
            transaction_date=p_date,
            amount=Decimal("50000.00"),
            currency="INR",
            direction=BankTransactionDirection.DEBIT,
            counterparty=v_frag2.name,
            reference=f"REF-FRAG2-{fp_idx + 1:02d}",
            status=DocumentStatus.POSTED,
        )
        session.add(bt)
    await session.flush()

    ground_truth.append(
        {
            "scenario_id": f"SCENARIO-{scenario_counter:03d}",
            "scenario_type": ExceptionType.PAYMENT_FRAGMENTATION.value,
            "title": "Payment Fragmentation (5,00,000 in 10 installments)",
            "description": "Invoice of 5,00,000 paid via 10 consecutive daily payments of 50,000",
            "expected_action": "ESCALATE",
            "financial_impact": "500000.00",
            "human_review_required": True,
            "primary_record_type": "INVOICE",
            "primary_record_id": str(inv_frag2.id),
            "primary_record_number": inv_frag2.invoice_number,
            "related_record_ids": [str(p.id) for p in frag2_pmts],
            "expected_root_cause": "Fragmented settlement pattern",
        }
    )
    scenario_counter += 1

    # 3 Missing Documents (Scenarios 24-26)
    # Scenario 24: Invoice with missing PO
    v_miss1 = vendors[23]
    inv_no_po = Invoice(
        company_id=company.id,
        vendor_id=v_miss1.id,
        po_id=None,  # Missing PO
        invoice_number="INV-NO-PO-001",
        invoice_date=start_date + timedelta(days=22),
        currency="INR",
        subtotal=Decimal("175000.00"),
        total=Decimal("175000.00"),
        status=DocumentStatus.OPEN,
    )
    session.add(inv_no_po)
    await session.flush()

    ground_truth.append(
        {
            "scenario_id": f"SCENARIO-{scenario_counter:03d}",
            "scenario_type": ExceptionType.MISSING_DOCUMENT.value,
            "title": "Invoice Missing Approved Purchase Order",
            "description": "Invoice received and entered with no purchase order linkage",
            "expected_action": "STAGE",
            "financial_impact": "175000.00",
            "human_review_required": True,
            "primary_record_type": "INVOICE",
            "primary_record_id": str(inv_no_po.id),
            "primary_record_number": inv_no_po.invoice_number,
            "related_record_ids": [],
            "expected_root_cause": "Missing purchase order authorization",
        }
    )
    scenario_counter += 1

    # Scenario 25: Invoice with PO but Missing Goods Receipt
    v_miss2 = vendors[24]
    po_no_gr = PurchaseOrder(
        company_id=company.id,
        vendor_id=v_miss2.id,
        po_number="PO-NO-GR-001",
        order_date=start_date + timedelta(days=25),
        currency="INR",
        total=Decimal("210000.00"),
        status=DocumentStatus.OPEN,
    )
    session.add(po_no_gr)
    await session.flush()

    inv_no_gr = Invoice(
        company_id=company.id,
        vendor_id=v_miss2.id,
        po_id=po_no_gr.id,
        invoice_number="INV-NO-GR-001",
        invoice_date=start_date + timedelta(days=30),
        currency="INR",
        subtotal=Decimal("210000.00"),
        total=Decimal("210000.00"),
        status=DocumentStatus.OPEN,
    )
    session.add(inv_no_gr)
    await session.flush()

    ground_truth.append(
        {
            "scenario_id": f"SCENARIO-{scenario_counter:03d}",
            "scenario_type": ExceptionType.MISSING_DOCUMENT.value,
            "title": "Invoice Missing Goods Receipt Confirmation",
            "description": "Supplier billed for hardware without warehouse goods receipt",
            "expected_action": "STAGE",
            "financial_impact": "210000.00",
            "human_review_required": True,
            "primary_record_type": "INVOICE",
            "primary_record_id": str(inv_no_gr.id),
            "primary_record_number": inv_no_gr.invoice_number,
            "related_record_ids": [str(po_no_gr.id)],
            "expected_root_cause": "Missing goods receipt delivery confirmation",
        }
    )
    scenario_counter += 1

    # Scenario 26: PO & Goods Receipt with Missing Invoice
    v_miss3 = vendors[25]
    po_no_inv = PurchaseOrder(
        company_id=company.id,
        vendor_id=v_miss3.id,
        po_number="PO-NO-INV-001",
        order_date=start_date + timedelta(days=15),
        currency="INR",
        total=Decimal("320000.00"),
        status=DocumentStatus.OPEN,
    )
    session.add(po_no_inv)
    await session.flush()

    gr_no_inv = GoodsReceipt(
        company_id=company.id,
        po_id=po_no_inv.id,
        receipt_number="GR-NO-INV-001",
        receipt_date=start_date + timedelta(days=20),
        status=DocumentStatus.OPEN,
    )
    session.add(gr_no_inv)
    await session.flush()

    ground_truth.append(
        {
            "scenario_id": f"SCENARIO-{scenario_counter:03d}",
            "scenario_type": ExceptionType.MISSING_DOCUMENT.value,
            "title": "Unbilled Goods Receipt (GRNI Accrual Candidate)",
            "description": "Goods received in January but invoice not received after 60 days",
            "expected_action": "STAGE",
            "financial_impact": "320000.00",
            "human_review_required": True,
            "primary_record_type": "GOODS_RECEIPT",
            "primary_record_id": str(gr_no_inv.id),
            "primary_record_number": gr_no_inv.receipt_number,
            "related_record_ids": [str(po_no_inv.id)],
            "expected_root_cause": "Unbilled receipt requires GRNI accrual",
        }
    )
    scenario_counter += 1

    # 3 Incorrect GL Mappings (Scenarios 27-29)
    # Entry 1: Software Expense misposted to Travel Expense
    je_gl1 = JournalEntry(
        company_id=company.id,
        entry_date=start_date + timedelta(days=35),
        description="AWS Infrastructure Monthly (Mismapped)",
        reference="JE-ERR-GL-001",
        status=DocumentStatus.POSTED,
    )
    session.add(je_gl1)
    await session.flush()
    session.add(
        JournalEntryLine(
            journal_entry_id=je_gl1.id,
            ledger_account_id=travel_acc.id,
            debit=Decimal("185000.00"),
            credit=Decimal("0.00"),
            description="Travel Debit instead of IT/Software",
        )
    )
    session.add(
        JournalEntryLine(
            journal_entry_id=je_gl1.id,
            ledger_account_id=ap_acc.id,
            debit=Decimal("0.00"),
            credit=Decimal("185000.00"),
            description="AP Credit",
        )
    )

    ground_truth.append(
        {
            "scenario_id": f"SCENARIO-{scenario_counter:03d}",
            "scenario_type": ExceptionType.GL_MAPPING_ERROR.value,
            "title": "Software Infrastructure Mapped to Travel Expense",
            "description": "AWS cloud bill debited to 5600 Travel instead of 5400 IT/Software",
            "expected_action": "STAGE",
            "financial_impact": "185000.00",
            "human_review_required": True,
            "primary_record_type": "JOURNAL_ENTRY",
            "primary_record_id": str(je_gl1.id),
            "primary_record_number": je_gl1.reference,
            "related_record_ids": [],
            "expected_root_cause": "Incorrect account classification in posting rule",
        }
    )
    scenario_counter += 1

    # Entry 2: Office Supplies misposted to Fixed Assets
    je_gl2 = JournalEntry(
        company_id=company.id,
        entry_date=start_date + timedelta(days=45),
        description="Stationery and Printer Ink (Mismapped)",
        reference="JE-ERR-GL-002",
        status=DocumentStatus.POSTED,
    )
    session.add(je_gl2)
    await session.flush()
    fa_acc = account_by_code.get("1400", ledger_accounts[4])
    session.add(
        JournalEntryLine(
            journal_entry_id=je_gl2.id,
            ledger_account_id=fa_acc.id,
            debit=Decimal("45000.00"),
            credit=Decimal("0.00"),
            description="Fixed Assets Debit instead of Office Supplies",
        )
    )
    session.add(
        JournalEntryLine(
            journal_entry_id=je_gl2.id,
            ledger_account_id=ap_acc.id,
            debit=Decimal("0.00"),
            credit=Decimal("45000.00"),
            description="AP Credit",
        )
    )

    ground_truth.append(
        {
            "scenario_id": f"SCENARIO-{scenario_counter:03d}",
            "scenario_type": ExceptionType.GL_MAPPING_ERROR.value,
            "title": "Consumable Supplies Capitalized as Fixed Assets",
            "description": "Stationery debited to 1400 Fixed Assets below threshold",
            "expected_action": "STAGE",
            "financial_impact": "45000.00",
            "human_review_required": True,
            "primary_record_type": "JOURNAL_ENTRY",
            "primary_record_id": str(je_gl2.id),
            "primary_record_number": je_gl2.reference,
            "related_record_ids": [],
            "expected_root_cause": "Capitalization policy violation",
        }
    )
    scenario_counter += 1

    # Entry 3: Revenue account debited on credit note
    je_gl3 = JournalEntry(
        company_id=company.id,
        entry_date=start_date + timedelta(days=55),
        description="Supplier Refund (Mismapped to Revenue)",
        reference="JE-ERR-GL-003",
        status=DocumentStatus.POSTED,
    )
    session.add(je_gl3)
    await session.flush()
    session.add(
        JournalEntryLine(
            journal_entry_id=je_gl3.id,
            ledger_account_id=rev_acc.id,
            debit=Decimal("65000.00"),
            credit=Decimal("0.00"),
            description="Revenue Account Debited instead of Expense Reduction",
        )
    )
    session.add(
        JournalEntryLine(
            journal_entry_id=je_gl3.id,
            ledger_account_id=cash_acc.id,
            debit=Decimal("0.00"),
            credit=Decimal("65000.00"),
            description="Cash Credit",
        )
    )

    ground_truth.append(
        {
            "scenario_id": f"SCENARIO-{scenario_counter:03d}",
            "scenario_type": ExceptionType.GL_MAPPING_ERROR.value,
            "title": "Vendor Credit Note Debited to Product Revenue",
            "description": "Rebate booked against 4000 Revenue instead of 5000 COGS",
            "expected_action": "STAGE",
            "financial_impact": "65000.00",
            "human_review_required": True,
            "primary_record_type": "JOURNAL_ENTRY",
            "primary_record_id": str(je_gl3.id),
            "primary_record_number": je_gl3.reference,
            "related_record_ids": [],
            "expected_root_cause": "Revenue account used for vendor transaction",
        }
    )
    scenario_counter += 1

    # 2 Incorrect Accruals (Scenarios 30-31)
    # Accrual 1: Rent/Utilities estimated 2,50,000, actual invoice was 60,000
    je_acc1 = JournalEntry(
        company_id=company.id,
        entry_date=start_date + timedelta(days=31),
        description="Jan Month-End Utilities Accrual Estimate",
        reference="JE-ACCR-001",
        status=DocumentStatus.POSTED,
    )
    session.add(je_acc1)
    await session.flush()
    session.add(
        JournalEntryLine(
            journal_entry_id=je_acc1.id,
            ledger_account_id=rent_acc.id,
            debit=Decimal("250000.00"),
            credit=Decimal("0.00"),
            description="Utilities Expense Accrual",
        )
    )
    session.add(
        JournalEntryLine(
            journal_entry_id=je_acc1.id,
            ledger_account_id=accrual_acc.id,
            debit=Decimal("0.00"),
            credit=Decimal("250000.00"),
            description="Accrued Liabilities",
        )
    )

    ground_truth.append(
        {
            "scenario_id": f"SCENARIO-{scenario_counter:03d}",
            "scenario_type": ExceptionType.ACCRUAL_ANOMALY.value,
            "title": "Substantial Over-Accrual of Utilities Expense",
            "description": "Accrued 2,50,000 for electricity; actual invoice was 60,000",
            "expected_action": "STAGE",
            "financial_impact": "190000.00",
            "human_review_required": True,
            "primary_record_type": "JOURNAL_ENTRY",
            "primary_record_id": str(je_acc1.id),
            "primary_record_number": je_acc1.reference,
            "related_record_ids": [],
            "expected_root_cause": "Accrual estimate variance > 300%",
        }
    )
    scenario_counter += 1

    # Accrual 2: Legal fees accrued 50,000, actual invoice 3,00,000
    je_acc2 = JournalEntry(
        company_id=company.id,
        entry_date=start_date + timedelta(days=59),
        description="Feb Legal Services Accrual Estimate",
        reference="JE-ACCR-002",
        status=DocumentStatus.POSTED,
    )
    session.add(je_acc2)
    await session.flush()
    prof_acc = account_by_code.get("5500", ledger_accounts[28])
    session.add(
        JournalEntryLine(
            journal_entry_id=je_acc2.id,
            ledger_account_id=prof_acc.id,
            debit=Decimal("50000.00"),
            credit=Decimal("0.00"),
            description="Legal Fees Accrual",
        )
    )
    session.add(
        JournalEntryLine(
            journal_entry_id=je_acc2.id,
            ledger_account_id=accrual_acc.id,
            debit=Decimal("0.00"),
            credit=Decimal("50000.00"),
            description="Accrued Liabilities",
        )
    )

    ground_truth.append(
        {
            "scenario_id": f"SCENARIO-{scenario_counter:03d}",
            "scenario_type": ExceptionType.ACCRUAL_ANOMALY.value,
            "title": "Severe Under-Accrual for Patent Litigation Legal Fees",
            "description": "Accrued 50,000; vendor submitted 3,00,000 for dispute counseling",
            "expected_action": "STAGE",
            "financial_impact": "250000.00",
            "human_review_required": True,
            "primary_record_type": "JOURNAL_ENTRY",
            "primary_record_id": str(je_acc2.id),
            "primary_record_number": je_acc2.reference,
            "related_record_ids": [],
            "expected_root_cause": "Under-accrual due to uncommunicated litigation scope",
        }
    )
    scenario_counter += 1

    # 2 AR Mismatches (Scenarios 32-33)
    for ar_idx in range(2):
        cust = customers[ar_idx]
        inv_amt = Decimal("420000.00")
        paid_amt = Decimal("350000.00")
        diff = inv_amt - paid_amt

        # Bank transaction for customer payment
        bt_ar = BankTransaction(
            company_id=company.id,
            bank_account_id=inr_bank_acc_1.id,
            transaction_date=start_date + timedelta(days=40 + ar_idx * 15),
            amount=paid_amt,
            currency="INR",
            direction=BankTransactionDirection.CREDIT,
            counterparty=cust.name,
            reference=f"CUST-REM-SHORT-{ar_idx + 1:02d}",
            status=DocumentStatus.OPEN,
        )
        session.add(bt_ar)
        await session.flush()

        ground_truth.append(
            {
                "scenario_id": f"SCENARIO-{scenario_counter:03d}",
                "scenario_type": ExceptionType.AR_MISMATCH.value,
                "title": f"Short Payment from Customer {cust.name}",
                "description": f"Customer paid {paid_amt} against {inv_amt} (short 70k)",
                "expected_action": "STAGE",
                "financial_impact": str(diff),
                "human_review_required": True,
                "primary_record_type": "BANK_TRANSACTION",
                "primary_record_id": str(bt_ar.id),
                "primary_record_number": bt_ar.reference,
                "related_record_ids": [],
                "expected_root_cause": "Unexplained customer deduction / withholding",
            }
        )
        scenario_counter += 1

    # 2 Cash Anomalies (Scenarios 34-35)
    # Anomaly 1: Unreconciled wire debit on statement
    bt_cash1 = BankTransaction(
        company_id=company.id,
        bank_account_id=inr_bank_acc_1.id,
        transaction_date=start_date + timedelta(days=62),
        amount=Decimal("300000.00"),
        currency="INR",
        direction=BankTransactionDirection.DEBIT,
        counterparty="UNKNOWN / OFFSHORE ESCROW",
        reference="TXN-UNIDENT-WIRE-OUT-001",
        status=DocumentStatus.OPEN,
    )
    session.add(bt_cash1)

    ground_truth.append(
        {
            "scenario_id": f"SCENARIO-{scenario_counter:03d}",
            "scenario_type": ExceptionType.CASH_ANOMALY.value,
            "title": "Unexplained High-Value Wire Withdrawal",
            "description": "Debit of 3,00,000 on statement with no internal payment voucher",
            "expected_action": "ESCALATE",
            "financial_impact": "300000.00",
            "human_review_required": True,
            "primary_record_type": "BANK_TRANSACTION",
            "primary_record_id": str(bt_cash1.id),
            "primary_record_number": bt_cash1.reference,
            "related_record_ids": [],
            "expected_root_cause": "Direct bank debit without authorized payment voucher",
        }
    )
    scenario_counter += 1

    # Anomaly 2: Unexplained credit inflow
    bt_cash2 = BankTransaction(
        company_id=company.id,
        bank_account_id=inr_bank_acc_2.id,
        transaction_date=start_date + timedelta(days=70),
        amount=Decimal("180000.00"),
        currency="INR",
        direction=BankTransactionDirection.CREDIT,
        counterparty="UNIDENTIFIED REMITTER",
        reference="TXN-UNIDENT-INFLOW-002",
        status=DocumentStatus.OPEN,
    )
    session.add(bt_cash2)

    ground_truth.append(
        {
            "scenario_id": f"SCENARIO-{scenario_counter:03d}",
            "scenario_type": ExceptionType.CASH_ANOMALY.value,
            "title": "Unidentified Bank Credit Inflow",
            "description": "Credit of 1,80,000 received with unknown remitter and no AR match",
            "expected_action": "STAGE",
            "financial_impact": "180000.00",
            "human_review_required": True,
            "primary_record_type": "BANK_TRANSACTION",
            "primary_record_id": str(bt_cash2.id),
            "primary_record_number": bt_cash2.reference,
            "related_record_ids": [],
            "expected_root_cause": "Unidentified deposit requiring suspense account allocation",
        }
    )
    scenario_counter += 1

    await session.flush()

    # 5. Populate Clean / Standard Transactions to meet target counts
    # Already created:
    # POs created so far: 25 (anomalies + demo)
    # Target: 410 -> Need 385 regular POs.
    # Receipts created so far: 20
    # Target: 390 -> Need 370 regular Receipts.
    # Invoices created so far: 30
    # Target: 450 -> Need 420 regular Invoices.

    regular_pos: list[PurchaseOrder] = []
    regular_grs: list[GoodsReceipt] = []
    regular_invs: list[Invoice] = []

    # International USD vendors: vendors 35 to 41 (multi-currency)
    usd_vendors = vendors[35:42]

    # Generate 385 regular POs, 370 of which get GoodsReceipts, and 370 of which get Invoices.
    # Then generate 50 additional direct service invoices (to reach 420 regular invoices).
    for i in range(385):
        is_usd = i % 8 == 0
        v = rng.choice(usd_vendors) if is_usd else rng.choice(vendors[:35])
        cur = "USD" if is_usd else "INR"
        po_date = start_date + timedelta(days=rng.randint(1, 80))
        qty = Decimal(str(rng.randint(5, 100)))
        unit_price = (
            Decimal(str(rng.randint(20, 800))) if is_usd else Decimal(str(rng.randint(200, 8000)))
        )
        tot = (qty * unit_price).quantize(Decimal("0.01"))

        po = PurchaseOrder(
            company_id=company.id,
            vendor_id=v.id,
            po_number=f"PO-2026-{i + 1:04d}",
            order_date=po_date,
            currency=cur,
            total=tot,
            status=DocumentStatus.POSTED,
        )
        session.add(po)
        regular_pos.append(po)

    await session.flush()

    for i, po in enumerate(regular_pos):
        pol = PurchaseOrderLine(
            purchase_order_id=po.id,
            description="Goods & Materials",
            quantity=Decimal("10.0000"),
            unit_price=po.total / Decimal("10.0000"),
            amount=po.total,
        )
        session.add(pol)

        # 370 of them get goods receipts
        if i < 370:
            gr = GoodsReceipt(
                company_id=company.id,
                po_id=po.id,
                receipt_number=f"GR-2026-{i + 1:04d}",
                receipt_date=po.order_date + timedelta(days=rng.randint(2, 6)),
                status=DocumentStatus.POSTED,
            )
            session.add(gr)
            regular_grs.append(gr)

    await session.flush()

    for gr in regular_grs:
        session.add(
            GoodsReceiptLine(
                goods_receipt_id=gr.id,
                po_line_id=None,
                description="Goods & Materials",
                quantity_received=Decimal("10.0000"),
            )
        )

    # Invoices for the 370 received POs
    for i, po in enumerate(regular_pos[:370]):
        inv_d = po.order_date + timedelta(days=rng.randint(6, 12))
        inv = Invoice(
            company_id=company.id,
            vendor_id=po.vendor_id,
            po_id=po.id,
            invoice_number=f"INV-2026-{i + 1:04d}",
            invoice_date=inv_d,
            due_date=inv_d + timedelta(days=30),
            currency=po.currency,
            subtotal=po.total,
            tax=Decimal("0.00"),
            total=po.total,
            status=DocumentStatus.PAID if i < 280 else DocumentStatus.OPEN,
        )
        session.add(inv)
        regular_invs.append(inv)

    # 50 direct service/recurring invoices (no PO required, e.g. SaaS subscriptions)
    for i in range(50):
        is_usd = i % 3 == 0
        v = rng.choice(usd_vendors) if is_usd else rng.choice(vendors[:35])
        cur = "USD" if is_usd else "INR"
        inv_d = start_date + timedelta(days=rng.randint(5, 85))
        amt = (
            Decimal(str(rng.randint(15, 350))) if is_usd else Decimal(str(rng.randint(5000, 45000)))
        )

        inv = Invoice(
            company_id=company.id,
            vendor_id=v.id,
            po_id=None,
            invoice_number=f"INV-SRV-2026-{i + 1:04d}",
            invoice_date=inv_d,
            due_date=inv_d + timedelta(days=30),
            currency=cur,
            subtotal=amt,
            tax=Decimal("0.00"),
            total=amt,
            status=DocumentStatus.PAID if i < 35 else DocumentStatus.OPEN,
        )
        session.add(inv)
        regular_invs.append(inv)

    await session.flush()

    # Invoice lines for regular invoices
    for inv in regular_invs:
        session.add(
            InvoiceLine(
                invoice_id=inv.id,
                description="Commercial Services / Supplies",
                quantity=Decimal("1.0000"),
                unit_price=inv.total,
                amount=inv.total,
            )
        )

    # Payments for paid regular invoices (~315 payments)
    regular_pmts: list[Payment] = []
    for i, inv in enumerate(regular_invs):
        if inv.status == DocumentStatus.PAID:
            b_acc = (
                usd_bank_acc
                if inv.currency == "USD"
                else (inr_bank_acc_1 if i % 2 == 0 else inr_bank_acc_2)
            )
            p = Payment(
                company_id=company.id,
                vendor_id=inv.vendor_id,
                invoice_id=inv.id,
                bank_account_id=b_acc.id,
                amount=inv.total,
                currency=inv.currency,
                payment_date=inv.invoice_date + timedelta(days=rng.randint(5, 25)),
                beneficiary_reference=f"PMT-REG-{i + 1:04d}",
                status=DocumentStatus.POSTED,
            )
            session.add(p)
            regular_pmts.append(p)

    await session.flush()

    # 6. Bank Transactions (Target: exactly 1,500)
    # Current bank transactions:
    # Demo 1: 14
    # Demo 3: 1
    # Duplicate payments: 8
    # Frag 2: 10
    # Cash anomalies: 2
    # AR mismatches: 2
    # Regular invoice payments: len(regular_pmts) (~315)
    # Total so far ~ 352.
    # Need 1,500 - 352 = ~1,148 additional bank transactions.

    for p in regular_pmts:
        session.add(
            BankTransaction(
                company_id=company.id,
                bank_account_id=p.bank_account_id or inr_bank_acc_1.id,
                transaction_date=p.payment_date,
                amount=p.amount,
                currency=p.currency,
                direction=BankTransactionDirection.DEBIT,
                counterparty="Supplier Settlement",
                reference=p.beneficiary_reference,
                status=DocumentStatus.POSTED,
            )
        )

    await session.flush()

    current_bt_count = 14 + 1 + 8 + 10 + 2 + 2 + len(regular_pmts)
    remaining_bts = 1500 - current_bt_count

    # Generate customer collection credits (~50% of remaining) and operational debits (~50%)
    for bt_idx in range(remaining_bts):
        t_date = start_date + timedelta(days=rng.randint(1, 89))
        is_credit = bt_idx % 2 == 0
        b_acc = (
            inr_bank_acc_1
            if bt_idx % 3 == 0
            else (inr_bank_acc_2 if bt_idx % 3 == 1 else usd_bank_acc)
        )
        cur = b_acc.currency
        if is_credit:
            c = customers[bt_idx % len(customers)]
            amt = (
                Decimal(str(rng.randint(200, 3500)))
                if cur == "USD"
                else Decimal(str(rng.randint(15000, 450000)))
            )
            session.add(
                BankTransaction(
                    company_id=company.id,
                    bank_account_id=b_acc.id,
                    transaction_date=t_date,
                    amount=amt,
                    currency=cur,
                    direction=BankTransactionDirection.CREDIT,
                    counterparty=c.name,
                    reference=f"CUST-DEP-{bt_idx + 1:04d}",
                    status=DocumentStatus.POSTED,
                )
            )
        else:
            amt = (
                Decimal(str(rng.randint(50, 800)))
                if cur == "USD"
                else Decimal(str(rng.randint(2500, 95000)))
            )
            session.add(
                BankTransaction(
                    company_id=company.id,
                    bank_account_id=b_acc.id,
                    transaction_date=t_date,
                    amount=amt,
                    currency=cur,
                    direction=BankTransactionDirection.DEBIT,
                    counterparty="Operational / Vendor",
                    reference=f"OP-DEBIT-{bt_idx + 1:04d}",
                    status=DocumentStatus.POSTED,
                )
            )

    await session.flush()

    # 7. Journal Entries (Target: exactly 600 balanced entries)
    # Already created:
    # Demo 3: 1
    # GL errors: 3
    # Accruals: 2
    # Total so far = 6.
    # Need 594 more balanced journal entries.
    for je_idx in range(594):
        je_date = start_date + timedelta(days=rng.randint(1, 89))
        je_amt = Decimal(str(rng.randint(10000, 350000)))

        je = JournalEntry(
            company_id=company.id,
            entry_date=je_date,
            description=f"Standard Operational Entry {je_idx + 1}",
            reference=f"JE-2026-{je_idx + 1:04d}",
            status=DocumentStatus.POSTED,
            source="AUTOMATED_POSTING",
        )
        session.add(je)
        await session.flush()

        # Alternate between typical accounting transactions
        if je_idx % 4 == 0:
            # P2P: Dr Expense, Cr AP
            exp = rng.choice(
                [it_acc, cogs_acc, rent_acc, travel_acc, office_acc, inv_acc, salary_acc]
            )
            session.add(
                JournalEntryLine(
                    journal_entry_id=je.id,
                    ledger_account_id=exp.id,
                    debit=je_amt,
                    credit=Decimal("0.00"),
                    description="Operating Expense",
                )
            )
            session.add(
                JournalEntryLine(
                    journal_entry_id=je.id,
                    ledger_account_id=ap_acc.id,
                    debit=Decimal("0.00"),
                    credit=je_amt,
                    description="Accounts Payable Liability",
                )
            )
        elif je_idx % 4 == 1:
            # Payment: Dr AP, Cr Cash
            session.add(
                JournalEntryLine(
                    journal_entry_id=je.id,
                    ledger_account_id=ap_acc.id,
                    debit=je_amt,
                    credit=Decimal("0.00"),
                    description="Accounts Payable Settlement",
                )
            )
            session.add(
                JournalEntryLine(
                    journal_entry_id=je.id,
                    ledger_account_id=cash_acc.id,
                    debit=Decimal("0.00"),
                    credit=je_amt,
                    description="Cash Disbursement",
                )
            )
        elif je_idx % 4 == 2:
            # O2C: Dr AR, Cr Revenue
            session.add(
                JournalEntryLine(
                    journal_entry_id=je.id,
                    ledger_account_id=ar_acc.id,
                    debit=je_amt,
                    credit=Decimal("0.00"),
                    description="Accounts Receivable",
                )
            )
            session.add(
                JournalEntryLine(
                    journal_entry_id=je.id,
                    ledger_account_id=rev_acc.id,
                    debit=Decimal("0.00"),
                    credit=je_amt,
                    description="Product / Service Revenue",
                )
            )
        else:
            # Customer Collection: Dr Cash, Cr AR
            session.add(
                JournalEntryLine(
                    journal_entry_id=je.id,
                    ledger_account_id=cash_acc.id,
                    debit=je_amt,
                    credit=Decimal("0.00"),
                    description="Cash Inflow",
                )
            )
            session.add(
                JournalEntryLine(
                    journal_entry_id=je.id,
                    ledger_account_id=ar_acc.id,
                    debit=Decimal("0.00"),
                    credit=je_amt,
                    description="Accounts Receivable Clearance",
                )
            )

    await session.flush()

    # 8. Expense Reports (Target: exactly 80)
    for exp_idx in range(80):
        emp = users[exp_idx % len(users)]
        exp_date = start_date + timedelta(days=rng.randint(2, 88))
        tot = Decimal(str(rng.randint(2500, 65000)))

        session.add(
            ExpenseReport(
                company_id=company.id,
                employee_id=emp.id,
                report_number=f"EXP-2026-{exp_idx + 1:03d}",
                expense_date=exp_date,
                currency="INR",
                total=tot,
                status=DocumentStatus.APPROVED if exp_idx < 65 else DocumentStatus.OPEN,
            )
        )

    await session.flush()

    # Save ground_truth.json
    if save_ground_truth:
        data_dir = Path(__file__).resolve().parent
        gt_file = data_dir / "ground_truth.json"
        with open(gt_file, "w") as f:
            json.dump(ground_truth, f, indent=2)

    return {
        "status": "seeded",
        "company_id": str(company.id),
        "invoices": 450,
        "purchase_orders": 410,
        "goods_receipts": 390,
        "bank_transactions": 1500,
        "ledger_entries": 600,
        "expense_reports": 80,
        "employees": 12,
        "ground_truth_count": len(ground_truth),
    }
