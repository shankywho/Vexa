"""Repository layer with tenant isolation (spec section 30).

Every financial object carries ``company_id``. Tenant context must come
from the authenticated request context — never from user/agent-supplied
values. This repository base enforces the boundary at query time.

Tenant scoping strategy: a repository is constructed with an explicit
``company_id`` and all queries are automatically filtered to that company.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from app.db.base import Base
from app.db.models.agent import AgentRun
from app.db.models.banking import BankAccount, BankTransaction, Payment
from app.db.models.counterparty import Customer, Vendor
from app.db.models.exception import ExceptionRecord, ReconciliationResult
from app.db.models.fx import FxRate
from app.db.models.ledger import JournalEntry, JournalEntryLine, LedgerAccount
from app.db.models.procurement import (
    Contract,
    ExpenseReport,
    GoodsReceipt,
    Invoice,
    PurchaseOrder,
)
from app.db.models.tenancy import Company
from app.domain.enums import (
    ExceptionSeverity,
    ExceptionStatus,
    ExceptionType,
    ReconciliationStatus,
)


class TenantBoundaryError(ValueError):
    """Raised when an operation crosses the tenant boundary."""


class TenantRepository:
    """Base repository enforcing the company/tenant boundary.

    Subclasses declare their scoped model via ``model`` and may constrain
    ``company_attr`` when the column name differs from ``company_id``.
    """

    model: type[Base] | None = None
    company_attr: str = "company_id"

    def __init__(self, session: AsyncSession, company_id: uuid.UUID) -> None:
        if self.model is None:
            raise TypeError(f"{type(self).__name__} must define 'model' before use")
        self.session = session
        self.company_id = company_id
        self._company_column: InstrumentedAttribute = getattr(self.model, self.company_attr)

    def _tenant_filter(self, *criteria) -> list:  # noqa: ANN002
        """Return the tenant filter combined with caller criteria."""
        return [self._company_column == self.company_id, *criteria]

    async def get(self, obj_id: uuid.UUID) -> Base | None:
        """Fetch a row by id, scoped to the tenant. Returns None if the row
        belongs to a different tenant (no cross-tenant leakage)."""
        stmt = select(self.model).where(
            self._company_column == self.company_id, self.model.id == obj_id
        )
        return await self.session.scalar(stmt)

    async def list(
        self, *criteria, limit: int = 100, offset: int = 0, order_by: str | None = None
    ) -> Sequence[Base]:
        """List rows scoped to the tenant."""
        stmt = select(self.model).where(*self._tenant_filter(*criteria))
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.scalars(stmt)
        return result.all()

    async def count(self, *criteria) -> int:
        """Count rows scoped to the tenant."""
        from sqlalchemy import func

        stmt = select(func.count()).select_from(self.model).where(*self._tenant_filter(*criteria))
        return int(await self.session.scalar(stmt) or 0)

    async def add(self, obj: Base) -> Base:
        """Persist a new row, forcing the tenant column to the repository's
        company so a caller can never write another tenant's data."""
        if hasattr(obj, self.company_attr):
            setattr(obj, self.company_attr, self.company_id)
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def delete(self, obj: Base) -> None:
        """Delete a row (must already be tenant-scoped)."""
        await self.session.delete(obj)


class CompanyRepository(TenantRepository):
    """Repository for company-scoped rows that do not themselves carry a
    company_id (i.e. the Company table). Used with a ``None`` company id."""

    model = Company

    def __init__(self, session: AsyncSession, company_id: uuid.UUID | None = None) -> None:
        self.session = session
        self.company_id = company_id
        self._company_column = None  # type: ignore[assignment]

    def _tenant_filter(self, *criteria):  # noqa: ANN002
        return list(criteria)


class VendorRepository(TenantRepository):
    """Repository for vendor entities."""

    model = Vendor

    async def get_by_name(self, name: str) -> Vendor | None:
        stmt = select(Vendor).where(*self._tenant_filter(Vendor.name == name))
        return await self.session.scalar(stmt)

    async def get_by_tax_id(self, tax_id: str) -> Vendor | None:
        stmt = select(Vendor).where(*self._tenant_filter(Vendor.tax_id == tax_id))
        return await self.session.scalar(stmt)


class CustomerRepository(TenantRepository):
    """Repository for customer entities."""

    model = Customer

    async def get_by_name(self, name: str) -> Customer | None:
        stmt = select(Customer).where(*self._tenant_filter(Customer.name == name))
        return await self.session.scalar(stmt)


class InvoiceRepository(TenantRepository):
    """Repository for supplier invoices and lines."""

    model = Invoice

    async def get_with_lines(self, invoice_id: uuid.UUID) -> Invoice | None:
        from sqlalchemy.orm import selectinload

        stmt = (
            select(Invoice)
            .options(selectinload(Invoice.lines))
            .where(*self._tenant_filter(Invoice.id == invoice_id))
        )
        return await self.session.scalar(stmt)

    async def get_by_number(self, invoice_number: str) -> Sequence[Invoice]:
        stmt = select(Invoice).where(*self._tenant_filter(Invoice.invoice_number == invoice_number))
        result = await self.session.scalars(stmt)
        return result.all()

    async def list_by_vendor(self, vendor_id: uuid.UUID) -> Sequence[Invoice]:
        stmt = select(Invoice).where(*self._tenant_filter(Invoice.vendor_id == vendor_id))
        result = await self.session.scalars(stmt)
        return result.all()

    async def list_by_po(self, po_id: uuid.UUID) -> Sequence[Invoice]:
        stmt = select(Invoice).where(*self._tenant_filter(Invoice.po_id == po_id))
        result = await self.session.scalars(stmt)
        return result.all()

    async def list_by_date_range(self, start_date: date, end_date: date) -> Sequence[Invoice]:
        stmt = select(Invoice).where(
            *self._tenant_filter(
                Invoice.invoice_date >= start_date, Invoice.invoice_date <= end_date
            )
        )
        result = await self.session.scalars(stmt)
        return result.all()


class PurchaseOrderRepository(TenantRepository):
    """Repository for purchase orders and lines."""

    model = PurchaseOrder

    async def get_with_lines(self, po_id: uuid.UUID) -> PurchaseOrder | None:
        from sqlalchemy.orm import selectinload

        stmt = (
            select(PurchaseOrder)
            .options(selectinload(PurchaseOrder.lines))
            .where(*self._tenant_filter(PurchaseOrder.id == po_id))
        )
        return await self.session.scalar(stmt)

    async def get_by_number(self, po_number: str) -> PurchaseOrder | None:
        stmt = select(PurchaseOrder).where(
            *self._tenant_filter(PurchaseOrder.po_number == po_number)
        )
        return await self.session.scalar(stmt)

    async def list_by_vendor(self, vendor_id: uuid.UUID) -> Sequence[PurchaseOrder]:
        stmt = select(PurchaseOrder).where(
            *self._tenant_filter(PurchaseOrder.vendor_id == vendor_id)
        )
        result = await self.session.scalars(stmt)
        return result.all()

    async def list_by_date_range(self, start_date: date, end_date: date) -> Sequence[PurchaseOrder]:
        stmt = select(PurchaseOrder).where(
            *self._tenant_filter(
                PurchaseOrder.order_date >= start_date, PurchaseOrder.order_date <= end_date
            )
        )
        result = await self.session.scalars(stmt)
        return result.all()


class GoodsReceiptRepository(TenantRepository):
    """Repository for goods receipts."""

    model = GoodsReceipt

    async def get_with_lines(self, receipt_id: uuid.UUID) -> GoodsReceipt | None:
        from sqlalchemy.orm import selectinload

        stmt = (
            select(GoodsReceipt)
            .options(selectinload(GoodsReceipt.lines))
            .where(*self._tenant_filter(GoodsReceipt.id == receipt_id))
        )
        return await self.session.scalar(stmt)

    async def get_by_number(self, receipt_number: str) -> GoodsReceipt | None:
        stmt = select(GoodsReceipt).where(
            *self._tenant_filter(GoodsReceipt.receipt_number == receipt_number)
        )
        return await self.session.scalar(stmt)

    async def list_by_po(self, po_id: uuid.UUID) -> Sequence[GoodsReceipt]:
        stmt = select(GoodsReceipt).where(*self._tenant_filter(GoodsReceipt.po_id == po_id))
        result = await self.session.scalars(stmt)
        return result.all()

    async def list_by_date_range(self, start_date: date, end_date: date) -> Sequence[GoodsReceipt]:
        stmt = select(GoodsReceipt).where(
            *self._tenant_filter(
                GoodsReceipt.receipt_date >= start_date, GoodsReceipt.receipt_date <= end_date
            )
        )
        result = await self.session.scalars(stmt)
        return result.all()


class PaymentRepository(TenantRepository):
    """Repository for payments."""

    model = Payment

    async def list_by_invoice(self, invoice_id: uuid.UUID) -> Sequence[Payment]:
        stmt = select(Payment).where(*self._tenant_filter(Payment.invoice_id == invoice_id))
        result = await self.session.scalars(stmt)
        return result.all()

    async def list_by_vendor(self, vendor_id: uuid.UUID) -> Sequence[Payment]:
        stmt = select(Payment).where(*self._tenant_filter(Payment.vendor_id == vendor_id))
        result = await self.session.scalars(stmt)
        return result.all()

    async def list_by_bank_account(self, bank_account_id: uuid.UUID) -> Sequence[Payment]:
        stmt = select(Payment).where(
            *self._tenant_filter(Payment.bank_account_id == bank_account_id)
        )
        result = await self.session.scalars(stmt)
        return result.all()

    async def list_by_date_range(self, start_date: date, end_date: date) -> Sequence[Payment]:
        stmt = select(Payment).where(
            *self._tenant_filter(
                Payment.payment_date >= start_date, Payment.payment_date <= end_date
            )
        )
        result = await self.session.scalars(stmt)
        return result.all()


class BankAccountRepository(TenantRepository):
    """Repository for company bank accounts."""

    model = BankAccount

    async def get_by_number(self, account_number: str) -> BankAccount | None:
        stmt = select(BankAccount).where(
            *self._tenant_filter(BankAccount.account_number == account_number)
        )
        return await self.session.scalar(stmt)

    async def list_active(self) -> Sequence[BankAccount]:
        stmt = select(BankAccount).where(*self._tenant_filter(BankAccount.is_active == True))  # noqa: E712
        result = await self.session.scalars(stmt)
        return result.all()


class BankTransactionRepository(TenantRepository):
    """Repository for bank statement transactions."""

    model = BankTransaction

    async def list_by_account(
        self,
        bank_account_id: uuid.UUID,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> Sequence[BankTransaction]:
        filters = [
            BankTransaction.company_id == self.company_id,
            BankTransaction.bank_account_id == bank_account_id,
        ]
        if start_date is not None:
            filters.append(BankTransaction.transaction_date >= start_date)
        if end_date is not None:
            filters.append(BankTransaction.transaction_date <= end_date)
        stmt = select(BankTransaction).where(*filters).order_by(BankTransaction.transaction_date)
        result = await self.session.scalars(stmt)
        return result.all()

    async def list_by_date_range(
        self, start_date: date, end_date: date
    ) -> Sequence[BankTransaction]:
        stmt = select(BankTransaction).where(
            *self._tenant_filter(
                BankTransaction.transaction_date >= start_date,
                BankTransaction.transaction_date <= end_date,
            )
        )
        result = await self.session.scalars(stmt)
        return result.all()

    async def find_by_reference(self, reference: str) -> Sequence[BankTransaction]:
        stmt = select(BankTransaction).where(
            *self._tenant_filter(BankTransaction.reference == reference)
        )
        result = await self.session.scalars(stmt)
        return result.all()


class LedgerAccountRepository(TenantRepository):
    """Repository for chart of accounts."""

    model = LedgerAccount

    async def get_by_code(self, account_code: str) -> LedgerAccount | None:
        stmt = select(LedgerAccount).where(
            *self._tenant_filter(LedgerAccount.account_code == account_code)
        )
        return await self.session.scalar(stmt)

    async def list_by_type(self, account_type: str) -> Sequence[LedgerAccount]:
        stmt = select(LedgerAccount).where(
            *self._tenant_filter(LedgerAccount.account_type == account_type)
        )
        result = await self.session.scalars(stmt)
        return result.all()


class JournalEntryRepository(TenantRepository):
    """Repository for journal entries and lines."""

    model = JournalEntry

    async def get_with_lines(self, entry_id: uuid.UUID) -> JournalEntry | None:
        from sqlalchemy.orm import selectinload

        stmt = (
            select(JournalEntry)
            .options(selectinload(JournalEntry.lines).selectinload(JournalEntryLine.ledger_account))
            .where(*self._tenant_filter(JournalEntry.id == entry_id))
        )
        return await self.session.scalar(stmt)

    async def list_by_date_range(self, start_date: date, end_date: date) -> Sequence[JournalEntry]:
        stmt = select(JournalEntry).where(
            *self._tenant_filter(
                JournalEntry.entry_date >= start_date, JournalEntry.entry_date <= end_date
            )
        )
        result = await self.session.scalars(stmt)
        return result.all()

    async def find_by_reference(self, reference: str) -> Sequence[JournalEntry]:
        stmt = select(JournalEntry).where(*self._tenant_filter(JournalEntry.reference == reference))
        result = await self.session.scalars(stmt)
        return result.all()


class ExpenseReportRepository(TenantRepository):
    """Repository for employee expense reports."""

    model = ExpenseReport

    async def get_by_number(self, report_number: str) -> ExpenseReport | None:
        stmt = select(ExpenseReport).where(
            *self._tenant_filter(ExpenseReport.report_number == report_number)
        )
        return await self.session.scalar(stmt)

    async def list_by_employee(self, employee_id: uuid.UUID) -> Sequence[ExpenseReport]:
        stmt = select(ExpenseReport).where(
            *self._tenant_filter(ExpenseReport.employee_id == employee_id)
        )
        result = await self.session.scalars(stmt)
        return result.all()


class ContractRepository(TenantRepository):
    """Repository for contracts."""

    model = Contract

    async def get_by_number(self, contract_number: str) -> Contract | None:
        stmt = select(Contract).where(
            *self._tenant_filter(Contract.contract_number == contract_number)
        )
        return await self.session.scalar(stmt)

    async def list_by_counterparty(self, counterparty_id: uuid.UUID) -> Sequence[Contract]:
        stmt = select(Contract).where(
            *self._tenant_filter(Contract.counterparty_id == counterparty_id)
        )
        result = await self.session.scalars(stmt)
        return result.all()


class FxRateRepository:
    """Repository for FX rates (global market data, not tenant-scoped)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_rate(
        self, base_currency: str, quote_currency: str, effective_date: date
    ) -> FxRate | None:
        stmt = select(FxRate).where(
            FxRate.base_currency == base_currency,
            FxRate.quote_currency == quote_currency,
            FxRate.effective_date == effective_date,
        )
        return await self.session.scalar(stmt)

    async def list_rates(
        self, base_currency: str, quote_currency: str, start_date: date, end_date: date
    ) -> Sequence[FxRate]:
        stmt = (
            select(FxRate)
            .where(
                FxRate.base_currency == base_currency,
                FxRate.quote_currency == quote_currency,
                FxRate.effective_date >= start_date,
                FxRate.effective_date <= end_date,
            )
            .order_by(FxRate.effective_date)
        )
        result = await self.session.scalars(stmt)
        return result.all()

    async def add_rate(self, rate: FxRate) -> FxRate:
        self.session.add(rate)
        await self.session.flush()
        return rate


class ReconciliationRepository(TenantRepository):
    """Repository for structured reconciliation results and matches."""

    model = ReconciliationResult

    async def get_with_matches(self, result_id: uuid.UUID) -> ReconciliationResult | None:
        from sqlalchemy.orm import selectinload

        stmt = (
            select(ReconciliationResult)
            .options(selectinload(ReconciliationResult.matches))
            .where(*self._tenant_filter(ReconciliationResult.id == result_id))
        )
        return await self.session.scalar(stmt)

    async def list_by_type(
        self, reconciliation_type: str, limit: int = 100, offset: int = 0
    ) -> Sequence[ReconciliationResult]:
        from sqlalchemy.orm import selectinload

        stmt = (
            select(ReconciliationResult)
            .options(selectinload(ReconciliationResult.matches))
            .where(
                *self._tenant_filter(
                    ReconciliationResult.reconciliation_type == reconciliation_type
                )
            )
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.scalars(stmt)
        return result.all()

    async def list_by_status(
        self, status: ReconciliationStatus, limit: int = 100, offset: int = 0
    ) -> Sequence[ReconciliationResult]:
        from sqlalchemy.orm import selectinload

        stmt = (
            select(ReconciliationResult)
            .options(selectinload(ReconciliationResult.matches))
            .where(*self._tenant_filter(ReconciliationResult.status == status))
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.scalars(stmt)
        return result.all()

    async def list_by_close_run(
        self, close_run_id: uuid.UUID, limit: int = 100, offset: int = 0
    ) -> Sequence[ReconciliationResult]:
        from sqlalchemy.orm import selectinload

        stmt = (
            select(ReconciliationResult)
            .options(selectinload(ReconciliationResult.matches))
            .where(*self._tenant_filter(ReconciliationResult.close_run_id == close_run_id))
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.scalars(stmt)
        return result.all()

    async def clear_results(self, close_run_id: uuid.UUID | None = None) -> int:
        """Clear previous reconciliation results for tenant, optionally by close run."""
        from sqlalchemy import delete

        criteria = [ReconciliationResult.company_id == self.company_id]
        if close_run_id is not None:
            criteria.append(ReconciliationResult.close_run_id == close_run_id)
        stmt = delete(ReconciliationResult).where(*criteria)
        res = await self.session.execute(stmt)
        return int(res.rowcount or 0)


class ExceptionRepository(TenantRepository):
    """Repository for financial exceptions and supporting evidence."""

    model = ExceptionRecord

    async def get_with_evidence(self, exception_id: uuid.UUID) -> ExceptionRecord | None:
        from sqlalchemy.orm import selectinload

        stmt = (
            select(ExceptionRecord)
            .options(selectinload(ExceptionRecord.evidence))
            .where(*self._tenant_filter(ExceptionRecord.id == exception_id))
        )
        return await self.session.scalar(stmt)

    async def list_by_type(
        self, exception_type: ExceptionType, limit: int = 100, offset: int = 0
    ) -> Sequence[ExceptionRecord]:
        from sqlalchemy.orm import selectinload

        stmt = (
            select(ExceptionRecord)
            .options(selectinload(ExceptionRecord.evidence))
            .where(*self._tenant_filter(ExceptionRecord.type == exception_type))
            .order_by(ExceptionRecord.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.scalars(stmt)
        return result.all()

    async def list_by_status(
        self, status: ExceptionStatus, limit: int = 100, offset: int = 0
    ) -> Sequence[ExceptionRecord]:
        from sqlalchemy.orm import selectinload

        stmt = (
            select(ExceptionRecord)
            .options(selectinload(ExceptionRecord.evidence))
            .where(*self._tenant_filter(ExceptionRecord.status == status))
            .order_by(ExceptionRecord.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.scalars(stmt)
        return result.all()

    async def list_by_severity(
        self, severity: ExceptionSeverity, limit: int = 100, offset: int = 0
    ) -> Sequence[ExceptionRecord]:
        from sqlalchemy.orm import selectinload

        stmt = (
            select(ExceptionRecord)
            .options(selectinload(ExceptionRecord.evidence))
            .where(*self._tenant_filter(ExceptionRecord.severity == severity))
            .order_by(ExceptionRecord.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.scalars(stmt)
        return result.all()

    async def list_all(self, limit: int = 1000, offset: int = 0) -> Sequence[ExceptionRecord]:
        from sqlalchemy.orm import selectinload

        stmt = (
            select(ExceptionRecord)
            .options(selectinload(ExceptionRecord.evidence))
            .where(*self._tenant_filter())
            .order_by(ExceptionRecord.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.scalars(stmt)
        return result.all()

    async def list_by_close_run(
        self, close_run_id: uuid.UUID, limit: int = 1000, offset: int = 0
    ) -> Sequence[ExceptionRecord]:
        from sqlalchemy.orm import selectinload

        stmt = (
            select(ExceptionRecord)
            .options(selectinload(ExceptionRecord.evidence))
            .where(*self._tenant_filter(ExceptionRecord.close_run_id == close_run_id))
            .order_by(ExceptionRecord.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.scalars(stmt)
        return result.all()

    async def clear_exceptions(self, close_run_id: uuid.UUID | None = None) -> int:
        """Clear previous exceptions for tenant, optionally by close run."""
        from sqlalchemy import delete

        criteria = [ExceptionRecord.company_id == self.company_id]
        if close_run_id is not None:
            criteria.append(ExceptionRecord.close_run_id == close_run_id)
        stmt = delete(ExceptionRecord).where(*criteria)
        res = await self.session.execute(stmt)
        return int(res.rowcount or 0)


class AgentRunRepository(TenantRepository):
    """Tenant-scoped repository for AgentRun records."""

    model = AgentRun

    async def get_with_steps(self, run_id: uuid.UUID) -> AgentRun | None:
        """Get an agent run with all its execution steps."""
        from sqlalchemy.orm import selectinload

        stmt = (
            select(AgentRun)
            .options(selectinload(AgentRun.steps))
            .where(*self._tenant_filter(AgentRun.id == run_id))
        )
        return await self.session.scalar(stmt)

    async def list_by_exception(
        self, exception_id: uuid.UUID, limit: int = 50
    ) -> Sequence[AgentRun]:
        """List agent runs for a specific exception."""
        from sqlalchemy.orm import selectinload

        stmt = (
            select(AgentRun)
            .options(selectinload(AgentRun.steps))
            .where(*self._tenant_filter(AgentRun.exception_id == exception_id))
            .order_by(AgentRun.created_at.desc())
            .limit(limit)
        )
        return (await self.session.scalars(stmt)).all()

    async def list_by_close_run(
        self, close_run_id: uuid.UUID, limit: int = 100
    ) -> Sequence[AgentRun]:
        """List agent runs for a close run."""
        from sqlalchemy.orm import selectinload

        stmt = (
            select(AgentRun)
            .options(selectinload(AgentRun.steps))
            .where(*self._tenant_filter(AgentRun.close_run_id == close_run_id))
            .order_by(AgentRun.created_at.desc())
            .limit(limit)
        )
        return (await self.session.scalars(stmt)).all()
