"""Deterministic foreign exchange conversion service (spec sections 6.1, 16).

Rule: any comparison, reconciliation, or aggregation involving records in
different currencies must resolve through ``fx_rates`` via a deterministic
tool (``convert_amount()``), never via an LLM estimating an exchange rate.
If a required rate is missing for the effective date, the reconciliation
returns ``MISSING`` status, not a guessed value.

All monetary amounts use decimal-safe representations. Never floating-point
arithmetic for accounting calculations.
"""

from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repository import FxRateRepository
from app.domain.schemas import FxConversionResult


class FxRateNotFoundError(ValueError):
    """Raised when no FX rate is available for the requested pair and effective date."""

    def __init__(self, from_currency: str, to_currency: str, effective_date: date) -> None:
        super().__init__(
            f"No FX rate found for {from_currency}/{to_currency} on {effective_date} "
            "(exact date required, no estimation)"
        )
        self.from_currency = from_currency
        self.to_currency = to_currency
        self.effective_date = effective_date


class FxService:
    """Deterministic FX rate resolution and conversion service."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = FxRateRepository(session)

    @staticmethod
    def _validate_decimal(amount: Decimal | int | str) -> Decimal:
        """Enforce decimal-safe arithmetic (reject floats)."""
        if isinstance(amount, float):
            msg = (
                f"Floating-point financial amounts are strictly forbidden: {amount}. "
                "Use Decimal, str, or int."
            )
            raise TypeError(msg)
        if isinstance(amount, Decimal):
            return amount
        return Decimal(str(amount))

    async def get_rate(
        self,
        from_currency: str,
        to_currency: str,
        effective_date: date,
        *,
        allow_inverse: bool = True,
    ) -> tuple[Decimal, bool, str | None] | None:
        """Resolve the exchange rate between two currencies on an effective date.

        Returns (rate, is_inverse, source) or None if neither direct nor inverse
        rate is found.
        """
        from_curr = from_currency.upper()
        to_curr = to_currency.upper()

        if from_curr == to_curr:
            return (Decimal("1.0"), False, "IDENTITY")

        # 1. Direct rate lookup: base=from, quote=to
        direct = await self.repo.get_rate(from_curr, to_curr, effective_date)
        if direct is not None:
            return (direct.rate, False, direct.source)

        # 2. Inverse rate lookup: base=to, quote=from (if allowed)
        if allow_inverse:
            inverse = await self.repo.get_rate(to_curr, from_curr, effective_date)
            if inverse is not None and inverse.rate > 0:
                inv_rate = (Decimal("1") / inverse.rate).quantize(
                    Decimal("0.00000001"), rounding=ROUND_HALF_UP
                )
                return (inv_rate, True, inverse.source)

        return None

    async def convert_amount(
        self,
        amount: Decimal | int | str,
        from_currency: str,
        to_currency: str,
        effective_date: date,
        *,
        precision: int = 2,
    ) -> FxConversionResult:
        """Deterministically convert an amount from one currency to another.

        Raises FxRateNotFoundError if the rate is missing for the effective date.
        """
        amt = self._validate_decimal(amount)
        from_curr = from_currency.upper()
        to_curr = to_currency.upper()

        if from_curr == to_curr:
            return FxConversionResult(
                original_amount=amt,
                from_currency=from_curr,
                to_currency=to_curr,
                effective_date=effective_date,
                rate=Decimal("1.0"),
                converted_amount=amt.quantize(Decimal(10) ** -precision, rounding=ROUND_HALF_UP),
                is_inverse=False,
                is_identity=True,
                source="IDENTITY",
                status="MATCHED",
            )

        resolved = await self.get_rate(from_curr, to_curr, effective_date, allow_inverse=True)
        if resolved is None:
            raise FxRateNotFoundError(from_curr, to_curr, effective_date)

        rate, is_inv, source = resolved
        converted = (amt * rate).quantize(Decimal(10) ** -precision, rounding=ROUND_HALF_UP)

        return FxConversionResult(
            original_amount=amt,
            from_currency=from_curr,
            to_currency=to_curr,
            effective_date=effective_date,
            rate=rate,
            converted_amount=converted,
            is_inverse=is_inv,
            is_identity=False,
            source=source,
            status="MATCHED",
        )

    async def try_convert_amount(
        self,
        amount: Decimal | int | str,
        from_currency: str,
        to_currency: str,
        effective_date: date,
        *,
        precision: int = 2,
    ) -> FxConversionResult:
        """Try converting an amount.

        If the rate is missing, returns status='MISSING' without guessing or estimating.
        """
        try:
            return await self.convert_amount(
                amount,
                from_currency,
                to_currency,
                effective_date,
                precision=precision,
            )
        except FxRateNotFoundError:
            amt = self._validate_decimal(amount)
            return FxConversionResult(
                original_amount=amt,
                from_currency=from_currency.upper(),
                to_currency=to_currency.upper(),
                effective_date=effective_date,
                rate=Decimal("0"),
                converted_amount=Decimal("0"),
                is_inverse=False,
                is_identity=False,
                source=None,
                status="MISSING",
            )
