"""Unit tests for exception routing and close readiness service (spec sections 11, 12, 34)."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.close_workflow.readiness import CloseReadinessService
from app.close_workflow.routing import ExceptionRouter
from app.close_workflow.types import ClosePolicy
from app.db.models.close_run import CloseRun, CloseTask
from app.db.models.exception import ExceptionRecord
from app.db.models.tenancy import Company
from app.domain.enums import (
    AutonomyLevel,
    CloseRunStatus,
    CloseTaskStatus,
    CloseTaskType,
    ExceptionSeverity,
    ExceptionStatus,
    ExceptionType,
)


def test_exception_router_auto_resolve() -> None:
    policy = ClosePolicy(
        max_auto_resolution_amount=Decimal("50000.00"),
        min_confidence=Decimal("0.95"),
    )
    router = ExceptionRouter(policy)

    exc = ExceptionRecord(
        id=uuid.uuid4(),
        company_id=uuid.uuid4(),
        type=ExceptionType.OTHER,
        severity=ExceptionSeverity.LOW,
        status=ExceptionStatus.OPEN,
        financial_impact=Decimal("250.00"),
        confidence=Decimal("0.99"),
        currency="USD",
    )

    decision = router.route_exception(exc, policy)
    assert decision.routing == "AUTO_RESOLVE"
    assert decision.autonomy_level == AutonomyLevel.EXECUTE
    assert decision.is_blocking is False


def test_exception_router_human_review() -> None:
    policy = ClosePolicy(
        max_auto_resolution_amount=Decimal("50000.00"),
        materiality_threshold=Decimal("100000.00"),
        min_confidence=Decimal("0.95"),
    )
    router = ExceptionRouter(policy)

    exc = ExceptionRecord(
        id=uuid.uuid4(),
        company_id=uuid.uuid4(),
        type=ExceptionType.PO_MISMATCH,
        severity=ExceptionSeverity.MEDIUM,
        status=ExceptionStatus.OPEN,
        financial_impact=Decimal("65000.00"),  # > 50k, < 100k
        confidence=Decimal("0.98"),
        currency="USD",
    )

    decision = router.route_exception(exc, policy)
    assert decision.routing == "HUMAN_REVIEW"
    assert decision.autonomy_level == AutonomyLevel.STAGE
    assert decision.is_blocking is True


def test_exception_router_cfo_escalation() -> None:
    policy = ClosePolicy(
        materiality_threshold=Decimal("100000.00"),
        blocking_exception_types={ExceptionType.PAYMENT_FRAGMENTATION},
    )
    router = ExceptionRouter(policy)

    # 1. High-risk exception type
    exc_frag = ExceptionRecord(
        id=uuid.uuid4(),
        company_id=uuid.uuid4(),
        type=ExceptionType.PAYMENT_FRAGMENTATION,
        severity=ExceptionSeverity.HIGH,
        status=ExceptionStatus.OPEN,
        financial_impact=Decimal("1400000.00"),
        confidence=Decimal("1.00"),
        currency="INR",
    )

    decision = router.route_exception(exc_frag, policy)
    assert decision.routing == "CFO_ESCALATION"
    assert decision.autonomy_level == AutonomyLevel.RECOMMEND
    assert decision.is_blocking is True


def test_exception_router_calibrated_confidence_precedence() -> None:
    policy = ClosePolicy(
        max_auto_resolution_amount=Decimal("50000.00"),
        min_confidence=Decimal("0.95"),
    )
    router = ExceptionRouter(policy)

    # High raw confidence (0.99) but low calibrated confidence (0.80) -> HUMAN_REVIEW
    exc_low_cal = ExceptionRecord(
        id=uuid.uuid4(),
        company_id=uuid.uuid4(),
        type=ExceptionType.OTHER,
        severity=ExceptionSeverity.LOW,
        status=ExceptionStatus.OPEN,
        financial_impact=Decimal("200.00"),
        confidence=Decimal("0.99"),
        calibrated_confidence=Decimal("0.80"),
        currency="USD",
    )
    decision = router.route_exception(exc_low_cal, policy)
    assert decision.routing == "HUMAN_REVIEW"
    assert decision.is_blocking is True

    # Low raw confidence (0.80) but high calibrated confidence (0.98) -> AUTO_RESOLVE
    exc_high_cal = ExceptionRecord(
        id=uuid.uuid4(),
        company_id=uuid.uuid4(),
        type=ExceptionType.OTHER,
        severity=ExceptionSeverity.LOW,
        status=ExceptionStatus.OPEN,
        financial_impact=Decimal("200.00"),
        confidence=Decimal("0.80"),
        calibrated_confidence=Decimal("0.98"),
        currency="USD",
    )
    decision2 = router.route_exception(exc_high_cal, policy)
    assert decision2.routing == "AUTO_RESOLVE"
    assert decision2.is_blocking is False

    # Missing confidence (None) -> treats as 0.0000 -> HUMAN_REVIEW
    exc_none = ExceptionRecord(
        id=uuid.uuid4(),
        company_id=uuid.uuid4(),
        type=ExceptionType.OTHER,
        severity=ExceptionSeverity.LOW,
        status=ExceptionStatus.OPEN,
        financial_impact=Decimal("200.00"),
        confidence=None,
        calibrated_confidence=None,
        currency="USD",
    )
    decision3 = router.route_exception(exc_none, policy)
    assert decision3.routing == "HUMAN_REVIEW"
    assert decision3.is_blocking is True


def test_resolved_exception_is_not_blocking() -> None:
    policy = ClosePolicy()
    router = ExceptionRouter(policy)

    exc_resolved = ExceptionRecord(
        id=uuid.uuid4(),
        company_id=uuid.uuid4(),
        type=ExceptionType.UNUSUAL_VENDOR_ACTIVITY,
        severity=ExceptionSeverity.HIGH,
        status=ExceptionStatus.RESOLVED,
        financial_impact=Decimal("950000.00"),
        currency="USD",
    )

    decision = router.route_exception(exc_resolved, policy)
    assert decision.is_blocking is False


async def test_close_readiness_blocked_by_open_tasks(db: AsyncSession) -> None:
    company = Company(name="Readiness Test Co", base_currency="USD", is_active=True)
    db.add(company)
    await db.flush()

    close_run = CloseRun(
        company_id=company.id,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 1, 31),
        status=CloseRunStatus.INVESTIGATING,
        version=1,
    )
    db.add(close_run)
    await db.flush()

    # Seed 5 completed tasks, 5 pending tasks
    for i, t_type in enumerate(CloseTaskType):
        status = CloseTaskStatus.COMPLETED if i < 5 else CloseTaskStatus.PENDING
        db.add(CloseTask(close_run_id=close_run.id, task_type=t_type, status=status))
    await db.flush()

    readiness_service = CloseReadinessService(db, company.id)
    readiness = await readiness_service.calculate_readiness(close_run.id)

    assert readiness.is_ready is False
    assert readiness.status == CloseRunStatus.BLOCKED
    assert readiness.completed_tasks == 5
    assert readiness.total_tasks == 10
    assert readiness.close_completion_percentage == Decimal("50.00")
    assert any("remain incomplete" in b for b in readiness.blockers)


async def test_close_readiness_ready_when_tasks_complete_and_no_blockers(
    db: AsyncSession,
) -> None:
    company = Company(name="Ready Co", base_currency="USD", is_active=True)
    db.add(company)
    await db.flush()

    close_run = CloseRun(
        company_id=company.id,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 1, 31),
        status=CloseRunStatus.FINAL_VERIFICATION,
        version=1,
    )
    db.add(close_run)
    await db.flush()

    # All 10 tasks completed
    for t_type in CloseTaskType:
        db.add(
            CloseTask(
                close_run_id=close_run.id,
                task_type=t_type,
                status=CloseTaskStatus.COMPLETED,
            )
        )
    await db.flush()

    readiness_service = CloseReadinessService(db, company.id)
    readiness = await readiness_service.calculate_readiness(close_run.id)

    assert readiness.is_ready is True
    assert readiness.status == CloseRunStatus.READY_TO_CLOSE
    assert readiness.completed_tasks == 10
    assert readiness.blocking_exceptions == 0
    assert readiness.close_completion_percentage == Decimal("100.00")
    assert len(readiness.blockers) == 0
