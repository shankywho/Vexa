"""FX rate model (spec section 6.1).

Any comparison/reconciliation/aggregation across currencies must resolve
through ``fx_rates`` via a deterministic conversion — never an LLM estimate.
If a required rate is missing for the effective date, the reconciliation
returns ``MISSING``, never a guessed value.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPkMixin


class FxRate(UUIDPkMixin, TimestampMixin, Base):
    """A currency conversion rate for a specific effective date."""

    __tablename__ = "fx_rates"

    base_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    quote_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    source: Mapped[str | None] = mapped_column(String(64))

    __table_args__ = (
        UniqueConstraint(
            "base_currency",
            "quote_currency",
            "effective_date",
            name="uq_fx_rates_base_quote_date",
        ),
    )
