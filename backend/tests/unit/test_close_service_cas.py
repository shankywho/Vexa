"""Close-run state machine tests (spec sections 14, 14.1).

Includes the compare-and-swap concurrency guarantee: two simultaneous
transitions from the same version must produce exactly one winner.
"""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.close_run import CloseRun
from app.db.models.tenancy import Company
from app.domain.enums import (
    CloseRunStatus,
    CloseTaskStatus,
)
from app.services.close_service import (
    DEFAULT_CLOSE_TASKS,
    CloseRunError,
    CloseRunService,
)


async def _setup(db: AsyncSession) -> tuple[Company, CloseRunService]:
    company = Company(name="Concurrency Co", base_currency="USD", is_active=True)
    db.add(company)
    await db.flush()
    return company, CloseRunService(db, company_id=company.id)


async def test_create_close_run_seeds_task_catalogue(db: AsyncSession) -> None:
    company, service = await _setup(db)
    close_run = await service.create_close_run(
        period_start=date(2026, 1, 1), period_end=date(2026, 1, 31)
    )

    assert close_run.status == CloseRunStatus.CREATED
    assert close_run.version == 1

    task_rows = await db.execute(text("SELECT task_type, status FROM close_tasks"))
    task_set = {(r[0], r[1]) for r in task_rows}
    for task_type in DEFAULT_CLOSE_TASKS:
        assert (task_type.value, CloseTaskStatus.PENDING.value) in task_set


async def test_create_close_run_is_idempotent_for_period(db: AsyncSession) -> None:
    company, service = await _setup(db)
    first = await service.create_close_run(
        period_start=date(2026, 2, 1), period_end=date(2026, 2, 28)
    )
    second = await service.create_close_run(
        period_start=date(2026, 2, 1), period_end=date(2026, 2, 28)
    )
    assert first.id == second.id


async def test_valid_transition_sequence(db: AsyncSession) -> None:
    company, service = await _setup(db)
    close_run = await service.create_close_run(
        period_start=date(2026, 3, 1), period_end=date(2026, 3, 31)
    )

    await service.transition(close_run.id, CloseRunStatus.INGESTING)
    await service.transition(close_run.id, CloseRunStatus.RECONCILING)
    await service.transition(close_run.id, CloseRunStatus.INVESTIGATING)
    await service.transition(close_run.id, CloseRunStatus.VERIFYING)
    final = await service.transition(close_run.id, CloseRunStatus.FINAL_VERIFICATION)

    assert final.status == CloseRunStatus.FINAL_VERIFICATION
    assert final.version == 5 + 1  # starting version 1 + 5 transitions


async def test_invalid_transition_rejected(db: AsyncSession) -> None:
    company, service = await _setup(db)
    close_run = await service.create_close_run(
        period_start=date(2026, 3, 1), period_end=date(2026, 3, 31)
    )
    with pytest.raises(CloseRunError, match="Invalid transition"):
        await service.transition(close_run.id, CloseRunStatus.CLOSED)


async def test_cas_rejects_stale_version(engine) -> None:
    """Two concurrent workers read the same version; the loser is rejected.

    Worker A and worker B both see version=1. A transitions and commits.
    B's subsequent transition uses a stale version and must fail with
    ``Concurrent modification`` (spec section 14.1).
    """
    conn_a = await engine.connect()
    conn_b = await engine.connect()
    try:
        # Sessions manage their own transactions so commit() really commits.
        sess_a = AsyncSession(bind=conn_a, expire_on_commit=False)
        sess_b = AsyncSession(bind=conn_b, expire_on_commit=False)

        # Setup committed so both workers can see it.
        company = Company(name="CAS Race Co", base_currency="USD", is_active=True)
        sess_a.add(company)
        await sess_a.flush()
        service_a = CloseRunService(sess_a, company_id=company.id)
        run = await service_a.create_close_run(
            period_start=date(2026, 3, 1), period_end=date(2026, 3, 31)
        )
        await sess_a.commit()

        # Worker B reads the same run at version 1.
        b_run = (await sess_b.scalars(select(CloseRun).where(CloseRun.id == run.id))).one()
        assert b_run.version == 1
        service_b = CloseRunService(sess_b, company_id=company.id)

        # A wins the race and commits version 1 -> 2.
        await service_a.transition(run.id, CloseRunStatus.INGESTING)
        await sess_a.commit()

        # B's CAS update (WHERE version=1 AND status=CREATED) matches 0 rows.
        with pytest.raises(CloseRunError, match="Concurrent modification"):
            await service_b.transition(run.id, CloseRunStatus.INGESTING)

        # Teardown: remove the committed company (DB-level CASCADE cleans up).
        await sess_a.delete(company)
        await sess_a.commit()
        await sess_b.close()
        await sess_a.close()
    finally:
        await conn_b.close()
        await conn_a.close()


async def test_cross_tenant_transition_rejected(db: AsyncSession) -> None:
    company, service = await _setup(db)
    close_run = await service.create_close_run(
        period_start=date(2026, 3, 1), period_end=date(2026, 3, 31)
    )
    other = CloseRunService(db, company_id=company.id)  # same tenant, fine
    assert await other.transition(close_run.id, CloseRunStatus.INGESTING) is not None

    # A different tenant must be rejected.
    other_company = Company(name="Other", base_currency="USD", is_active=True)
    db.add(other_company)
    await db.flush()
    stranger = CloseRunService(db, company_id=other_company.id)
    with pytest.raises(CloseRunError, match="not in this tenant"):
        await stranger.transition(close_run.id, CloseRunStatus.RECONCILING)
