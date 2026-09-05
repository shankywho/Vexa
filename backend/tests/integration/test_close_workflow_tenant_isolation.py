"""Integration test verifying strict company isolation across close workflow (spec section 30)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.close_workflow.controller import CloseWorkflowController
from app.close_workflow.state_machine import CloseRunError
from app.db.models.exception import ExceptionRecord
from app.db.models.tenancy import Company
from app.domain.enums import (
    CloseRunStatus,
    ExceptionSeverity,
    ExceptionStatus,
    ExceptionType,
)


async def test_close_workflow_tenant_isolation(db: AsyncSession) -> None:
    # 1. Create Company A and Company B
    company_a = Company(name="Tenant A Financials", base_currency="USD", is_active=True)
    company_b = Company(name="Tenant B Financials", base_currency="USD", is_active=True)
    db.add_all([company_a, company_b])
    await db.flush()

    # 2. Setup Close Run for Company A
    controller_a = CloseWorkflowController(db, company_a.id)
    run_a = await controller_a.create_or_get_close_run(
        period_start=date(2026, 7, 1), period_end=date(2026, 7, 31)
    )

    # 3. Setup Close Run for Company B
    controller_b = CloseWorkflowController(db, company_b.id)
    run_b = await controller_b.create_or_get_close_run(
        period_start=date(2026, 7, 1), period_end=date(2026, 7, 31)
    )

    assert run_a.id != run_b.id
    assert run_a.company_id == company_a.id
    assert run_b.company_id == company_b.id

    # 4. Attempting to transition Company A's run via Controller B must be rejected
    with pytest.raises(CloseRunError, match="not in this tenant"):
        await controller_b.state_machine.transition_close_run(run_a.id, CloseRunStatus.INGESTING)

    # 5. Attempting to execute workflow on foreign close run must be rejected
    with pytest.raises(CloseRunError, match="not in this tenant"):
        await controller_b.execute_workflow(run_a.id)

    # 6. Cross-tenant exception review must be rejected
    exc_a = ExceptionRecord(
        company_id=company_a.id,
        close_run_id=run_a.id,
        type=ExceptionType.PO_MISMATCH,
        severity=ExceptionSeverity.HIGH,
        status=ExceptionStatus.OPEN,
        financial_impact=Decimal("75000.00"),
        currency="USD",
    )
    db.add(exc_a)
    await db.flush()

    with pytest.raises(CloseRunError, match="not exist in this tenant"):
        await controller_b.submit_human_review(
            close_run_id=run_a.id,
            exception_id=exc_a.id,
            decision="APPROVED",
            actor="attacker@other.com",
        )

    # 7. Verify Company B readiness sees 0 of Company A's exceptions
    readiness_b = await controller_b.evaluate_readiness(run_b.id)
    assert readiness_b.total_exceptions == 0
    assert readiness_b.blocking_exceptions == 0
