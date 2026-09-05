"""Banking & payment models (spec section 6)."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPkMixin
from app.domain.enums import BankTransactionDirection, DocumentStatus

if TYPE_CHECKING:
    from app.db.models.ledger import JournalEntry
    from app.db.models.procurement import Invoice


class BankAccount(UUIDPkMixin, TimestampMixin, Base):
    """A company bank account."""

    __tablename__ = "bank_accounts"

    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_number: Mapped[str] = mapped_column(String(64), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    transactions: Mapped[list[BankTransaction]] = relationship(back_populates="bank_account")


class BankTransaction(UUIDPkMixin, TimestampMixin, Base):
    """A single bank statement transaction."""

    __tablename__ = "bank_transactions"

    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    bank_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("bank_accounts.id"), nullable=False, index=True
    )
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    direction: Mapped[BankTransactionDirection] = mapped_column(
        Enum(BankTransactionDirection, name="bank_txn_direction"), nullable=False
    )
    counterparty: Mapped[str | None] = mapped_column(String(255))
    reference: Mapped[str | None] = mapped_column(String(128), index=True)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status"), default=DocumentStatus.OPEN, nullable=False
    )
    journal_entry_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("journal_entries.id"))

    bank_account: Mapped[BankAccount] = relationship(back_populates="transactions")
    journal_entry: Mapped[JournalEntry | None] = relationship(back_populates="bank_transactions")


class Payment(UUIDPkMixin, TimestampMixin, Base):
    """A payment made to a vendor / matched to an invoice."""

    __tablename__ = "payments"

    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    vendor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("vendors.id"))
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("invoices.id"), nullable=True, index=True
    )
    bank_account_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("bank_accounts.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    beneficiary_reference: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status"), default=DocumentStatus.OPEN, nullable=False
    )
    bank_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("bank_transactions.id")
    )

    invoice: Mapped[Invoice | None] = relationship(back_populates="payments")
