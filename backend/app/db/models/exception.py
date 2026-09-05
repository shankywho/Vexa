"""Exception models (spec sections 9, 13.2) — schema foundation only.

Phase 1 ships the tables; the exception *engine* (detection, investigation,
verification, autonomy) is a later phase.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPkMixin
from app.domain.enums import (
    AutonomyLevel,
    ExceptionSeverity,
    ExceptionStatus,
    ExceptionType,
    ReconciliationStatus,
)

if TYPE_CHECKING:
    pass


class ExceptionRecord(UUIDPkMixin, TimestampMixin, Base):
    """A financial exception detected during a close run."""

    __tablename__ = "exceptions"

    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    close_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("close_runs.id", ondelete="CASCADE"), nullable=True, index=True
    )
    type: Mapped[ExceptionType] = mapped_column(
        Enum(ExceptionType, name="exception_type"), nullable=False, index=True
    )
    severity: Mapped[ExceptionSeverity] = mapped_column(
        Enum(ExceptionSeverity, name="exception_severity"),
        default=ExceptionSeverity.MEDIUM,
        nullable=False,
    )
    status: Mapped[ExceptionStatus] = mapped_column(
        Enum(ExceptionStatus, name="exception_status"),
        default=ExceptionStatus.OPEN,
        nullable=False,
        index=True,
    )
    financial_impact: Mapped[Decimal] = mapped_column(
        Numeric(20, 2), default=Decimal("0"), nullable=False
    )
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(6, 4))
    calibrated_confidence: Mapped[Decimal | None] = mapped_column(Numeric(6, 4))
    root_cause: Mapped[str | None] = mapped_column(Text)
    recommended_action: Mapped[str | None] = mapped_column(Text)
    autonomy_level: Mapped[AutonomyLevel] = mapped_column(
        Enum(AutonomyLevel, name="autonomy_level"),
        default=AutonomyLevel.OBSERVE,
        nullable=False,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    assigned_to: Mapped[str | None] = mapped_column(String(255))
    # Referenced evidence record (primary subject of the exception).
    source_invoice_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("invoices.id"))
    source_po_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("purchase_orders.id"))
    source_receipt_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("goods_receipts.id"))
    source_payment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("payments.id"))
    source_bank_txn_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("bank_transactions.id"))
    source_journal_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("journal_entries.id")
    )
    metadata_json: Mapped[str | None] = mapped_column("metadata_json", Text, nullable=True)

    @property
    def metadata_(self) -> dict | None:
        if not self.metadata_json:
            return None
        try:
            return json.loads(self.metadata_json)
        except Exception:
            return None

    @metadata_.setter
    def metadata_(self, value: dict | str | None) -> None:
        if value is None:
            self.metadata_json = None
        elif isinstance(value, str):
            self.metadata_json = value
        else:
            self.metadata_json = json.dumps(value, default=str)

    evidence: Mapped[list[ExceptionEvidence]] = relationship(
        back_populates="exception_record", cascade="all, delete-orphan"
    )
    actions: Mapped[list[ExceptionAction]] = relationship(
        back_populates="exception_record", cascade="all, delete-orphan"
    )


class ExceptionEvidence(UUIDPkMixin, TimestampMixin, Base):
    """Evidence supporting an exception (spec section 7 / 13)."""

    __tablename__ = "exception_evidence"

    exception_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("exceptions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    evidence_type: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_ref_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    exception_record: Mapped[ExceptionRecord] = relationship(back_populates="evidence")


class ExceptionAction(UUIDPkMixin, TimestampMixin, Base):
    """An action taken (or staged) against an exception.

    Actions are immutable once written; reversals create a new
    ``ReversalAction`` referencing this row (spec section 13.2).
    """

    __tablename__ = "exception_actions"

    exception_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("exceptions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)  # STAGED | EXECUTED | REVERSED
    payload_json: Mapped[str | None] = mapped_column("payload_json", Text)
    actor: Mapped[str | None] = mapped_column(String(255))
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    exception_record: Mapped[ExceptionRecord] = relationship(back_populates="actions")

    @property
    def payload(self) -> dict | None:
        if not self.payload_json:
            return None
        import json

        try:
            return json.loads(self.payload_json)
        except Exception:
            return None

    @payload.setter
    def payload(self, value: dict | str | None) -> None:
        if value is None:
            self.payload_json = None
        elif isinstance(value, str):
            self.payload_json = value
        else:
            import json

            self.payload_json = json.dumps(value, default=str)


class ReversalAction(UUIDPkMixin, TimestampMixin, Base):
    """Rollback trail for a reversed action (spec section 13.2)."""

    __tablename__ = "reversal_actions"

    exception_action_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("exception_actions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    exception_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("exceptions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reason: Mapped[str | None] = mapped_column(Text)
    reversed_by: Mapped[str | None] = mapped_column(String(255))
    reversed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    action: Mapped[ExceptionAction] = relationship()


class ReconciliationResult(UUIDPkMixin, TimestampMixin, Base):
    """Structured output of a deterministic reconciliation (spec section 8)."""

    __tablename__ = "reconciliation_results"

    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    close_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("close_runs.id", ondelete="CASCADE"), nullable=True, index=True
    )
    reconciliation_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[ReconciliationStatus] = mapped_column(
        Enum(ReconciliationStatus, name="reconciliation_status"), nullable=False
    )
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(6, 4))
    financial_impact: Mapped[Decimal] = mapped_column(
        Numeric(20, 2), default=Decimal("0"), nullable=False
    )
    fx_conversion_applied: Mapped[bool] = mapped_column(default=False, nullable=False)
    details_json: Mapped[str | None] = mapped_column("details_json", Text)

    @property
    def details(self) -> dict | None:
        if not self.details_json:
            return None
        import json

        try:
            return json.loads(self.details_json)
        except Exception:
            return None

    @details.setter
    def details(self, value: dict | str | None) -> None:
        if value is None:
            self.details_json = None
        elif isinstance(value, str):
            self.details_json = value
        else:
            import json

            self.details_json = json.dumps(value, default=str)

    matches: Mapped[list[ReconciliationMatch]] = relationship(
        back_populates="result", cascade="all, delete-orphan"
    )


class ReconciliationMatch(UUIDPkMixin, TimestampMixin, Base):
    """A matched-record pair within a reconciliation result."""

    __tablename__ = "reconciliation_matches"

    reconciliation_result_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reconciliation_results.id", ondelete="CASCADE"), nullable=False, index=True
    )
    left_ref_type: Mapped[str] = mapped_column(String(64), nullable=False)
    left_ref_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    right_ref_type: Mapped[str] = mapped_column(String(64), nullable=False)
    right_ref_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    match_type: Mapped[str] = mapped_column(String(32), nullable=False)  # EXACT | FUZZY | FX

    result: Mapped[ReconciliationResult] = relationship(back_populates="matches")
