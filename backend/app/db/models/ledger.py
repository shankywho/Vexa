"""Ledger models (spec section 6)."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPkMixin
from app.domain.enums import DocumentStatus

if TYPE_CHECKING:
    from app.db.models.banking import BankTransaction


class LedgerAccount(UUIDPkMixin, TimestampMixin, Base):
    """A chart-of-accounts entry."""

    __tablename__ = "ledger_accounts"

    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_code: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_type: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # ASSET / LIABILITY / EQUITY / REVENUE / EXPENSE
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)


class JournalEntry(UUIDPkMixin, TimestampMixin, Base):
    """A journal entry posting to ledger accounts."""

    __tablename__ = "journal_entries"

    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entry_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    reference: Mapped[str | None] = mapped_column(String(128), index=True)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status"), default=DocumentStatus.POSTED, nullable=False
    )
    source: Mapped[str | None] = mapped_column(String(64))

    lines: Mapped[list[JournalEntryLine]] = relationship(
        back_populates="journal_entry", cascade="all, delete-orphan"
    )
    bank_transactions: Mapped[list[BankTransaction]] = relationship(back_populates="journal_entry")


class JournalEntryLine(UUIDPkMixin, TimestampMixin, Base):
    """A debit/credit line within a journal entry."""

    __tablename__ = "journal_entry_lines"

    journal_entry_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("journal_entries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ledger_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ledger_accounts.id"), nullable=False
    )
    debit: Mapped[Decimal] = mapped_column(Numeric(20, 2), default=Decimal("0"), nullable=False)
    credit: Mapped[Decimal] = mapped_column(Numeric(20, 2), default=Decimal("0"), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    journal_entry: Mapped[JournalEntry] = relationship(back_populates="lines")
    ledger_account: Mapped[LedgerAccount] = relationship()
