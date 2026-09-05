"""Integration test: deterministic seed → DB, then audit + repository reads."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import AuditService
from app.data.generator import seed_company
from app.domain.enums import AuditEventType


async def _count(db: AsyncSession, table: str) -> int:
    return int((await db.execute(text(f"SELECT count(*) FROM {table}"))).scalar_one())


async def test_seed_company_matches_profile(db: AsyncSession) -> None:
    company = await seed_company(db, seed=42)

    assert company.name == "NovaScale AI"
    assert company.base_currency == "INR"

    # Profile targets (spec section 20).
    assert await _count(db, "vendors") == 42
    assert await _count(db, "customers") == 18
    assert await _count(db, "bank_accounts") == 3
    assert await _count(db, "ledger_accounts") == 60

    # FX coverage: at least three pairs, all within the window.
    fx_count = await _count(db, "fx_rates")
    assert fx_count == 273  # 3 pairs x 91 days (Jan-Mar 2026)

    pairs = set(
        (row[0], row[1])
        for row in (
            await db.execute(text("SELECT DISTINCT base_currency, quote_currency FROM fx_rates"))
        )
    )
    assert ("INR", "USD") in pairs
    assert ("INR", "EUR") in pairs
    assert ("USD", "EUR") in pairs


async def test_seed_is_reproducible(db: AsyncSession) -> None:
    """Two identical seeds produce the same masters; audit trail proves both."""
    company_1 = await seed_company(db, seed=7)
    db.add(company_1)
    await db.flush()

    # Snapshot vendor names from seed 7.
    names_1 = set(
        (await db.execute(text("SELECT name FROM vendors ORDER BY name"))).scalars().all()
    )

    # Reset and reseed with same seed -> identical vendor names.
    await db.execute(text("DELETE FROM vendors"))
    await db.execute(text("DELETE FROM customers"))
    await db.execute(text("DELETE FROM bank_accounts"))
    await db.execute(text("DELETE FROM ledger_accounts"))
    await db.execute(text("DELETE FROM fx_rates"))
    await db.execute(text("DELETE FROM companies"))
    await db.flush()

    company_2 = await seed_company(db, seed=7)
    db.add(company_2)
    await db.flush()

    names_2 = set(
        (await db.execute(text("SELECT name FROM vendors ORDER BY name"))).scalars().all()
    )
    assert names_1 == names_2
    assert len(names_1) == 42


async def test_audit_records_seed_and_company_lifecycle(db: AsyncSession) -> None:
    company = await seed_company(db, seed=42)
    service = AuditService(db, company_id=company.id)
    await service.record(
        event_type=AuditEventType.SEED,
        actor="seed",
        actor_type="SYSTEM",
        reason="NovaScale AI deterministic seed (seed=42)",
    )

    events = await service.list()
    assert len(events) == 1
    assert events[0].event_type == AuditEventType.SEED
