"""Human correction and outcome tracking model (spec section 13.2 / 17)."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPkMixin


class HumanCorrection(UUIDPkMixin, TimestampMixin, Base):
    """An auditable record of a human reviewer outcome or override on an exception."""

    __tablename__ = "human_corrections"

    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    exception_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("exceptions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    close_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("close_runs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    original_decision: Mapped[str] = mapped_column(String(64), nullable=False)
    human_decision: Mapped[str] = mapped_column(String(64), nullable=False)
    original_confidence: Mapped[Decimal | None] = mapped_column(Numeric(6, 4))
    calibrated_confidence: Mapped[Decimal | None] = mapped_column(Numeric(6, 4))
    exception_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    policy_version_id: Mapped[str | None] = mapped_column(String(64))
    reviewer_role: Mapped[str] = mapped_column(String(64), default="CONTROLLER", nullable=False)
    actor: Mapped[str] = mapped_column(String(255), default="controller", nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
