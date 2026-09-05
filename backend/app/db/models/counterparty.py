"""Counterparty models: Vendor and Customer (spec section 6)."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPkMixin
from app.domain.enums import DocumentStatus

if TYPE_CHECKING:
    from app.db.models.procurement import Invoice


class Vendor(UUIDPkMixin, TimestampMixin, Base):
    """A supplier that issues invoices to the company."""

    __tablename__ = "vendors"

    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    tax_id: Mapped[str | None] = mapped_column(String(64), index=True)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status"), default=DocumentStatus.OPEN, nullable=False
    )
    bank_account_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("bank_accounts.id"), nullable=True
    )
    risk_metadata: Mapped[dict | None] = mapped_column("risk_metadata_json", Text)

    invoices: Mapped[list[Invoice]] = relationship(back_populates="vendor")


class Customer(UUIDPkMixin, TimestampMixin, Base):
    """A buyer of the company's products/services."""

    __tablename__ = "customers"

    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status"), default=DocumentStatus.OPEN, nullable=False
    )
