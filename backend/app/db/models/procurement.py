"""Procurement & expense models (spec section 6).

Invoice / InvoiceLine / PurchaseOrder / PurchaseOrderLine / GoodsReceipt /
GoodsReceiptLine / Contract / ExpenseReport.

Monetary amounts are ``Numeric`` (decimal-safe) — never floats.
"""

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
    from app.db.models.banking import Payment
    from app.db.models.counterparty import Vendor
    from app.db.models.procurement import PurchaseOrderLine


class Invoice(UUIDPkMixin, TimestampMixin, Base):
    """A supplier invoice."""

    __tablename__ = "invoices"

    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    vendor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("vendors.id"), nullable=False, index=True
    )
    invoice_number: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(20, 2), default=Decimal("0"), nullable=False)
    tax: Mapped[Decimal] = mapped_column(Numeric(20, 2), default=Decimal("0"), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(20, 2), default=Decimal("0"), nullable=False)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status"), default=DocumentStatus.OPEN, nullable=False
    )
    source_document_id: Mapped[str | None] = mapped_column(String(64))  # original doc ref
    po_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("purchase_orders.id"))

    vendor: Mapped[Vendor] = relationship(back_populates="invoices")
    lines: Mapped[list[InvoiceLine]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan"
    )
    payments: Mapped[list[Payment]] = relationship(back_populates="invoice")


class InvoiceLine(UUIDPkMixin, TimestampMixin, Base):
    """A line item on an invoice."""

    __tablename__ = "invoice_lines"

    invoice_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    description: Mapped[str | None] = mapped_column(Text)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    po_line_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("purchase_order_lines.id"))

    invoice: Mapped[Invoice] = relationship(back_populates="lines")
    po_line: Mapped[PurchaseOrderLine | None] = relationship(back_populates="invoice_lines")


class PurchaseOrder(UUIDPkMixin, TimestampMixin, Base):
    """A purchase order issued to a vendor."""

    __tablename__ = "purchase_orders"

    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    vendor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vendors.id"), nullable=False)
    po_number: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    order_date: Mapped[date] = mapped_column(Date, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(20, 2), default=Decimal("0"), nullable=False)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status"), default=DocumentStatus.OPEN, nullable=False
    )

    lines: Mapped[list[PurchaseOrderLine]] = relationship(
        back_populates="purchase_order", cascade="all, delete-orphan"
    )
    receipts: Mapped[list[GoodsReceipt]] = relationship(back_populates="purchase_order")


class PurchaseOrderLine(UUIDPkMixin, TimestampMixin, Base):
    """A line item on a purchase order."""

    __tablename__ = "purchase_order_lines"

    purchase_order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    description: Mapped[str | None] = mapped_column(Text)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)

    purchase_order: Mapped[PurchaseOrder] = relationship(back_populates="lines")
    invoice_lines: Mapped[list[InvoiceLine]] = relationship(back_populates="po_line")


class GoodsReceipt(UUIDPkMixin, TimestampMixin, Base):
    """Receipt of goods against a purchase order."""

    __tablename__ = "goods_receipts"

    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    po_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("purchase_orders.id"), nullable=False, index=True
    )
    receipt_number: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    receipt_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status"), default=DocumentStatus.OPEN, nullable=False
    )

    purchase_order: Mapped[PurchaseOrder] = relationship(back_populates="receipts")
    lines: Mapped[list[GoodsReceiptLine]] = relationship(
        back_populates="goods_receipt", cascade="all, delete-orphan"
    )


class GoodsReceiptLine(UUIDPkMixin, TimestampMixin, Base):
    """A line item on a goods receipt."""

    __tablename__ = "goods_receipt_lines"

    goods_receipt_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("goods_receipts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    po_line_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("purchase_order_lines.id"))
    description: Mapped[str | None] = mapped_column(Text)
    quantity_received: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)

    goods_receipt: Mapped[GoodsReceipt] = relationship(back_populates="lines")


class Contract(UUIDPkMixin, TimestampMixin, Base):
    """A contract with a vendor/customer (evidence node)."""

    __tablename__ = "contracts"

    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    counterparty_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("vendors.id"))
    contract_number: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date)
    value: Mapped[Decimal | None] = mapped_column(Numeric(20, 2))
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status"), default=DocumentStatus.OPEN, nullable=False
    )


class ExpenseReport(UUIDPkMixin, TimestampMixin, Base):
    """An employee expense report."""

    __tablename__ = "expense_reports"

    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    employee_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    report_number: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    expense_date: Mapped[date] = mapped_column(Date, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(20, 2), default=Decimal("0"), nullable=False)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status"), default=DocumentStatus.OPEN, nullable=False
    )
