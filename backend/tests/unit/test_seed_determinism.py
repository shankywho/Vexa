"""Deterministic seed foundation tests.

The same seed must produce byte-for-byte identical data; different seeds
must diverge. Counts must match the NovaScale AI profile (spec section 20).
"""

from __future__ import annotations

from datetime import date

from app.data.generator import NOVASCALE_PROFILE, DeterministicSeed


def test_generator_is_deterministic() -> None:
    a = DeterministicSeed(seed=42)
    b = DeterministicSeed(seed=42)

    assert [a.vendor_name() for _ in range(50)] == [b.vendor_name() for _ in range(50)]
    assert [a.customer_name() for _ in range(30)] == [b.customer_name() for _ in range(30)]


def test_generator_diverges_with_different_seed() -> None:
    a = DeterministicSeed(seed=1)
    b = DeterministicSeed(seed=2)
    names_a = [a.vendor_name() for _ in range(50)]
    names_b = [b.vendor_name() for _ in range(50)]
    assert names_a != names_b


def test_ledger_accounts_target_count() -> None:
    gen = DeterministicSeed(seed=42)
    accounts = gen.ledger_accounts()
    assert len(accounts) == 60, "profile target is 60 ledger accounts"
    # Codes are unique.
    codes = [code for code, _, _ in accounts]
    assert len(set(codes)) == len(codes)


def test_fx_rates_cover_all_pairs_and_dates() -> None:
    gen = DeterministicSeed(seed=42)
    start, end = date(2026, 1, 1), date(2026, 3, 31)
    rows = gen.fx_rates(start, end, base_currency="INR")
    pairs = {(base, quote) for base, quote, _, _, _ in rows}
    assert ("INR", "USD") in pairs
    assert ("INR", "EUR") in pairs
    assert ("USD", "EUR") in pairs
    assert len(rows) == 3 * ((end - start).days + 1)


def test_novascale_profile_targets() -> None:
    targets = NOVASCALE_PROFILE["targets"]
    assert targets == {
        "vendors": 42,
        "customers": 18,
        "employees": 12,
        "bank_accounts": 3,
        "ledger_accounts": 60,
    }
