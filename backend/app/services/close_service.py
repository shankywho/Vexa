"""Close-run service foundation (spec sections 14, 14.1).

Phase 1 ships the state-machine scaffolding: tenant-scoped creation and
compare-and-swap (CAS) state transitions with optimistic locking so two
concurrent triggers cannot corrupt/duplicate state. The close *execution*
engine is a later phase.
"""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.close_run import CloseRun, CloseTask
from app.db.models.tenancy import Company
from app.domain.enums import CloseRunStatus, CloseTaskStatus, CloseTaskType

# Allowed state transitions (spec section 14).
ALLOWED_TRANSITIONS: dict[CloseRunStatus, set[CloseRunStatus]] = {
    CloseRunStatus.CREATED: {
        CloseRunStatus.INGESTING,
        CloseRunStatus.FAILED,
        CloseRunStatus.BLOCKED,
    },
    CloseRunStatus.INGESTING: {
        CloseRunStatus.RECONCILING,
        CloseRunStatus.FAILED,
        CloseRunStatus.BLOCKED,
    },
    CloseRunStatus.RECONCILING: {
        CloseRunStatus.INVESTIGATING,
        CloseRunStatus.FAILED,
        CloseRunStatus.BLOCKED,
    },
    CloseRunStatus.INVESTIGATING: {
        CloseRunStatus.VERIFYING,
        CloseRunStatus.WAITING_FOR_HUMAN,
        CloseRunStatus.FAILED,
        CloseRunStatus.BLOCKED,
    },
    CloseRunStatus.VERIFYING: {
        CloseRunStatus.INVESTIGATING,
        CloseRunStatus.FINAL_VERIFICATION,
        CloseRunStatus.WAITING_FOR_HUMAN,
        CloseRunStatus.FAILED,
        CloseRunStatus.BLOCKED,
    },
    CloseRunStatus.WAITING_FOR_HUMAN: {
        CloseRunStatus.VERIFYING,
        CloseRunStatus.RESOLVING,
        CloseRunStatus.FAILED,
        CloseRunStatus.BLOCKED,
    },
    CloseRunStatus.RESOLVING: {
        CloseRunStatus.FINAL_VERIFICATION,
        CloseRunStatus.FAILED,
        CloseRunStatus.BLOCKED,
    },
    CloseRunStatus.FINAL_VERIFICATION: {
        CloseRunStatus.READY_TO_CLOSE,
        CloseRunStatus.BLOCKED,
        CloseRunStatus.FAILED,
    },
    CloseRunStatus.READY_TO_CLOSE: {CloseRunStatus.CLOSED, CloseRunStatus.BLOCKED},
    CloseRunStatus.CLOSED: set(),
    CloseRunStatus.FAILED: {CloseRunStatus.CREATED},
    CloseRunStatus.BLOCKED: set(),
}

# Default close-task catalogue created with every close run (spec section 15).
DEFAULT_CLOSE_TASKS: list[CloseTaskType] = [
    CloseTaskType.BANK_RECONCILIATION,
    CloseTaskType.AP_RECONCILIATION,
    CloseTaskType.AR_RECONCILIATION,
    CloseTaskType.INVOICE_VALIDATION,
    CloseTaskType.PAYMENT_RECONCILIATION,
    CloseTaskType.VARIANCE_ANALYSIS,
    CloseTaskType.ACCRUAL_REVIEW,
    CloseTaskType.EXCEPTION_REVIEW,
    CloseTaskType.FINAL_VERIFICATION,
    CloseTaskType.CLOSE_PACKAGE,
]


class CloseRunError(ValueError):
    """Close-run domain error (invalid transition, missing tenant, ...)."""


class CloseRunService:
    """Tenant-scoped close-run operations."""

    def __init__(self, session: AsyncSession, company_id: uuid.UUID) -> None:
        self.session = session
        self.company_id = company_id

    async def _require_company(self) -> None:
        exists = await self.session.scalar(select(Company.id).where(Company.id == self.company_id))
        if exists is None:
            raise CloseRunError(f"Company {self.company_id} does not exist")

    async def create_close_run(self, *, period_start: date, period_end: date) -> CloseRun:
        """Create a close run (idempotent for the same period)."""
        await self._require_company()
        existing = await self.session.scalar(
            select(CloseRun).where(
                CloseRun.company_id == self.company_id,
                CloseRun.period_start == period_start,
                CloseRun.period_end == period_end,
                CloseRun.status != CloseRunStatus.CLOSED,
            )
        )
        if existing is not None:
            return existing

        close_run = CloseRun(
            company_id=self.company_id,
            period_start=period_start,
            period_end=period_end,
            status=CloseRunStatus.CREATED,
            version=1,
        )
        self.session.add(close_run)
        await self.session.flush()
        for task_type in DEFAULT_CLOSE_TASKS:
            self.session.add(
                CloseTask(
                    close_run_id=close_run.id, task_type=task_type, status=CloseTaskStatus.PENDING
                )
            )
        await self.session.flush()
        return close_run

    async def transition(self, close_run_id: uuid.UUID, new_status: CloseRunStatus) -> CloseRun:
        """CAS state transition: only one concurrent caller wins.

        Uses ``UPDATE ... WHERE id=? AND version=? AND status=<expected>`` so
        a stale version or a competing transition is rejected with
        :class:`CloseRunError` instead of corrupting state (spec 14.1).
        """
        close_run = await self.session.get(CloseRun, close_run_id)
        if close_run is None:
            raise CloseRunError(f"Close run {close_run_id} does not exist")
        if close_run.company_id != self.company_id:
            raise CloseRunError("Close run is not in this tenant")

        current = close_run.status
        if new_status not in ALLOWED_TRANSITIONS.get(current, set()):
            raise CloseRunError(f"Invalid transition {current} -> {new_status}")

        result = await self.session.execute(
            update(CloseRun)
            .where(
                CloseRun.id == close_run_id,
                CloseRun.version == close_run.version,
                CloseRun.status == current,
            )
            .values(status=new_status, version=CloseRun.version + 1)
            .returning(CloseRun.version)
        )
        new_version = result.scalar_one_or_none()
        if new_version is None:
            raise CloseRunError("Concurrent modification; close run state changed elsewhere")
        await self.session.refresh(close_run)
        return close_run

    async def list_close_runs(self, *, limit: int = 100) -> list[CloseRun]:
        """List tenant-scoped close runs, newest first."""
        stmt = (
            select(CloseRun)
            .where(CloseRun.company_id == self.company_id)
            .order_by(CloseRun.created_at.desc())
            .limit(limit)
        )
        result = await self.session.scalars(stmt)
        return list(result.all())
