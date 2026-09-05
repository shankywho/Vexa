"""Deterministic seed foundation (spec section 20).

Provides the NovaScale AI synthetic company profile and deterministic,
seeded data generators. Phase 1 ships the *foundation* — primitives to
generate master data (vendors, customers, bank accounts, ledger accounts,
FX rates) deterministically. The full multi-month transaction dataset and
ground-truth exception injection arrive in a later phase.

Every generator is seeded from a global ``random.Random`` instance so runs
are byte-for-byte reproducible when ``seed_deterministic`` is enabled.
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.banking import BankAccount
from app.db.models.counterparty import Customer, Vendor
from app.db.models.fx import FxRate
from app.db.models.ledger import LedgerAccount
from app.db.models.tenancy import Company
from app.domain.enums import Currency, DocumentStatus

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

# Extended chart-of-accounts labels keyed by code prefix (deterministic).
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
        """Deterministic chart of accounts: (code, name, account_type).

        Expands the base chart to ``target`` accounts using seeded suffixes
        so the result matches the NovaScale profile (60 accounts).
        """
        accounts: list[tuple[str, str, str]] = []
        # First pass: named base accounts (deterministic order).
        for code, label in LEDGER_ACCOUNT_LABELS.items():
            kind = LEDGER_ACCOUNT_TYPES[code]
            accounts.append((code, label, kind))
        # Second pass: expand each family with seeded sub-accounts.
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
                # Deterministic "spot" wiggle of +-2% around a fixed mid-rate.
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
) -> Company:
    """Deterministically create NovaScale AI master data within a session.

    Returns the created company. Safe to call multiple times (idempotent by
    name lookup). Transaction/exception data is a later phase.
    """
    profile = NOVASCALE_PROFILE
    company_name = name or profile["name"]

    existing = await session.execute(Company.__table__.select().where(Company.name == company_name))
    if existing.first() is not None:
        return await session.scalar(Company.__table__.select().where(Company.name == company_name))  # type: ignore[return-value]

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
    return company
