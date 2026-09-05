"""Deterministic financial calculation tools for the Financial Analyst Agent (spec section 10)."""

from __future__ import annotations

import logging
import uuid
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.analyst.types import (
    AccrualCandidate,
    CashImpactSummary,
    MaterialityFinding,
    VarianceItem,
)
from app.db.models.banking import BankAccount, BankTransaction
from app.db.models.exception import ExceptionRecord
from app.db.models.ledger import JournalEntry, JournalEntryLine, LedgerAccount
from app.db.models.procurement import GoodsReceipt, Invoice, PurchaseOrder
from app.domain.enums import BankTransactionDirection

logger = logging.getLogger(__name__)


class FinancialAnalystTools:
    """Deterministic financial tools for financial analysis and variance computation."""

    def __init__(self, session: AsyncSession, company_id: uuid.UUID) -> None:
        self.session = session
        self.company_id = company_id

    async def calculate_account_variances(
        self,
        materiality_threshold: Decimal = Decimal("50000.00"),
    ) -> list[VarianceItem]:
        """Compute General Ledger account variances deterministically."""
        accounts = (
            await self.session.scalars(
                select(LedgerAccount).where(LedgerAccount.company_id == self.company_id)
            )
        ).all()

        variances: list[VarianceItem] = []
        for acct in accounts:
            # Query journal entry lines for this account
            stmt = (
                select(
                    func.coalesce(func.sum(JournalEntryLine.debit), Decimal("0")),
                    func.coalesce(func.sum(JournalEntryLine.credit), Decimal("0")),
                )
                .join(JournalEntry, JournalEntryLine.journal_entry_id == JournalEntry.id)
                .where(
                    JournalEntry.company_id == self.company_id,
                    JournalEntryLine.ledger_account_id == acct.id,
                )
            )
            res = (await self.session.execute(stmt)).first()
            total_debit, total_credit = (
                res if res else (Decimal("0"), Decimal("0"))
            )

            # Assets & Expenses are normal debit balances; Liabilities, Equity, Revenue are normal credit
            if acct.account_type in ("ASSET", "EXPENSE"):
                current_bal = total_debit - total_credit
            else:
                current_bal = total_credit - total_debit

            # Historical baseline (for seed data or prior balance)
            prior_bal = Decimal("0.00")
            variance_amt = current_bal - prior_bal

            pct = None
            if prior_bal != Decimal("0.00"):
                pct = ((variance_amt / prior_bal) * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            is_material = abs(variance_amt) >= materiality_threshold
            explanation = ""
            if is_material:
                explanation = f"Material balance variance of {variance_amt} {acct.currency} exceeds threshold {materiality_threshold}"

            variances.append(
                VarianceItem(
                    account_code=acct.account_code,
                    account_name=acct.name,
                    account_type=acct.account_type,
                    prior_balance=prior_bal,
                    current_balance=current_bal,
                    variance_amount=variance_amt,
                    variance_percentage=pct,
                    is_material=is_material,
                    explanation=explanation,
                )
            )

        return variances

    async def calculate_cash_summary(self) -> CashImpactSummary:
        """Compute cash balances, inflows, outflows, and net burn rate deterministically."""
        # Fetch cash balance from ledger cash accounts (1000/1010/1020)
        cash_accounts = (
            await self.session.scalars(
                select(LedgerAccount).where(
                    LedgerAccount.company_id == self.company_id,
                    LedgerAccount.account_code.like("10%"),
                )
            )
        ).all()

        stmt = select(
            BankTransaction.direction,
            func.coalesce(func.sum(BankTransaction.amount), Decimal("0")),
        ).where(BankTransaction.company_id == self.company_id).group_by(BankTransaction.direction)
        direction_sums = dict((await self.session.execute(stmt)).all())

        inflows = direction_sums.get(BankTransactionDirection.CREDIT, Decimal("0.00"))
        outflows = direction_sums.get(BankTransactionDirection.DEBIT, Decimal("0.00"))
        net_cf = inflows - outflows

        cash_acct_ids = [a.id for a in cash_accounts]
        if cash_acct_ids:
            stmt_lines = (
                select(
                    func.coalesce(func.sum(JournalEntryLine.debit), Decimal("0")),
                    func.coalesce(func.sum(JournalEntryLine.credit), Decimal("0")),
                )
                .join(JournalEntry, JournalEntryLine.journal_entry_id == JournalEntry.id)
                .where(
                    JournalEntry.company_id == self.company_id,
                    JournalEntryLine.ledger_account_id.in_(cash_acct_ids),
                )
            )
            res = (await self.session.execute(stmt_lines)).first()
            d, c = res if res else (Decimal("0"), Decimal("0"))
            closing_bal = d - c
            opening_bal = closing_bal - net_cf
        else:
            closing_bal = net_cf
            opening_bal = Decimal("0.00")

        burn_rate = Decimal("0.00")
        if net_cf < Decimal("0.00"):
            burn_rate = abs(net_cf)

        runway = None
        if burn_rate > Decimal("0.00") and closing_bal > Decimal("0.00"):
            runway = (closing_bal / burn_rate).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)

        # Risk items query (exceptions with cash impact)
        risk_stmt = select(ExceptionRecord).where(
            ExceptionRecord.company_id == self.company_id,
            ExceptionRecord.financial_impact > Decimal("50000.00"),
        )
        large_excs = (await self.session.scalars(risk_stmt)).all()
        risk_items = [f"{e.type.value}: {e.financial_impact} {e.currency} ({e.root_cause or 'Unverified discrepancy'})" for e in large_excs]
        high_risk_outflows = sum((e.financial_impact for e in large_excs), Decimal("0.00"))

        return CashImpactSummary(
            opening_cash_balance=opening_bal,
            closing_cash_balance=closing_bal,
            net_cash_flow=net_cf,
            operating_inflows=inflows,
            operating_outflows=outflows,
            monthly_burn_rate=burn_rate,
            runway_months=runway,
            high_risk_cash_outflows=high_risk_outflows,
            risk_items=risk_items,
        )

    async def find_accrual_candidates(self) -> list[AccrualCandidate]:
        """Identify unbilled goods receipts or open commitments requiring month-end accrual."""
        # Find goods receipts that have no matching invoice
        stmt = (
            select(GoodsReceipt)
            .options(
                selectinload(GoodsReceipt.purchase_order).selectinload(PurchaseOrder.vendor),
                selectinload(GoodsReceipt.lines),
            )
            .where(GoodsReceipt.company_id == self.company_id)
        )
        receipts = (await self.session.scalars(stmt)).all()

        candidates: list[AccrualCandidate] = []
        for gr in receipts:
            # Check if invoice exists for this receipt's PO
            inv_stmt = select(Invoice).where(
                Invoice.company_id == self.company_id,
                Invoice.po_id == gr.po_id,
            )
            invoices = (await self.session.scalars(inv_stmt)).all()
            if not invoices:
                # Unbilled receipt
                po = gr.purchase_order
                amount = po.total if po else Decimal("0.00")
                vendor_name = po.vendor.name if po and po.vendor else None
                candidates.append(
                    AccrualCandidate(
                        record_id=str(gr.id),
                        record_type="GOODS_RECEIPT",
                        reference_number=gr.receipt_number,
                        vendor_name=vendor_name,
                        amount=amount,
                        currency="USD",
                        receipt_date=gr.receipt_date.isoformat(),
                        reason="Goods received but no vendor invoice received (GRNI accrual candidate)",
                        suggested_gl_account="2100",
                    )
                )

        return candidates

    async def analyze_materiality(
        self, materiality_threshold: Decimal = Decimal("100000.00")
    ) -> list[MaterialityFinding]:
        """Find items exceeding the materiality threshold that require CFO attention."""
        findings: list[MaterialityFinding] = []

        stmt = select(ExceptionRecord).where(
            ExceptionRecord.company_id == self.company_id,
            ExceptionRecord.financial_impact >= materiality_threshold,
        )
        material_excs = (await self.session.scalars(stmt)).all()
        for exc in material_excs:
            findings.append(
                MaterialityFinding(
                    category="EXCEPTION",
                    reference=str(exc.id),
                    amount=exc.financial_impact,
                    threshold=materiality_threshold,
                    requires_cfo_attention=True,
                    notes=f"Exception {exc.type.value} of {exc.financial_impact} {exc.currency} exceeds materiality limit",
                )
            )

        return findings
