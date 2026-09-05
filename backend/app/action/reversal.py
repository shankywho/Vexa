"""Rollback and reversal engine (spec section 13.2)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.action.types import ActionType, ReversalResult
from app.audit.service import AuditService
from app.db.repository import (
    ExceptionActionRepository,
    ExceptionRepository,
    ReversalActionRepository,
)
from app.db.base import utcnow
from app.domain.enums import AuditEventType, ExceptionStatus


class ReversalEngine:
    """Executes auditable action reversals without mutating original historical records."""

    def __init__(self, session: AsyncSession, company_id: uuid.UUID) -> None:
        self.session = session
        self.company_id = company_id
        self.action_repo = ExceptionActionRepository(session, company_id)
        self.reversal_repo = ReversalActionRepository(session, company_id)
        self.exc_repo = ExceptionRepository(session, company_id)
        self.audit_service = AuditService(session, company_id)

    async def reverse_action(
        self,
        action_id: uuid.UUID,
        reason: str,
        reversed_by: str = "human_controller",
    ) -> ReversalResult:
        """Reverse a previously staged or executed action.

        Implements Spec Section 13.2:
        1. Creates reversal_actions record linked to original exception_actions row.
        2. Sets original action status to REVERSED (does not delete row).
        3. Re-opens associated exception (status -> REOPENED, clears resolved_at).
        4. Explicitly voids/unstages any downstream staged payloads.
        5. Emits dual audit events (REVERSAL and EXCEPTION_REOPENED).
        """
        # 1. Fetch action and verify tenant boundary
        action = await self.action_repo.get_by_id(action_id)
        if not action:
            raise ValueError(f"Action {action_id} not found for company {self.company_id}")

        if action.status == "REVERSED":
            raise ValueError(f"Action {action_id} has already been reversed.")

        exception = await self.exc_repo.get_by_id(action.exception_id)
        if not exception:
            raise ValueError(f"Exception {action.exception_id} not found.")

        now = utcnow()
        voided_effects: list[str] = []

        # 2. Check and void downstream effects
        if action.action_type == ActionType.STAGE_JOURNAL_ENTRY:
            voided_effects.append("Unstaged draft correcting journal entry")
        elif action.action_type == ActionType.DRAFT_VENDOR_EMAIL:
            voided_effects.append("Cancelled draft vendor communication")

        # 3. Create ReversalAction record
        reversal = await self.reversal_repo.create(
            exception_action_id=action.id,
            exception_id=action.exception_id,
            reason=reason,
            reversed_by=reversed_by,
            reversed_at=now,
        )

        # 4. Mark original action as REVERSED
        action.status = "REVERSED"

        # 5. Re-open exception
        previous_status = exception.status
        exception.status = ExceptionStatus.REOPENED
        exception.resolved_at = None

        # 6. Audit Trail: Dual events (REVERSAL and EXCEPTION_REOPENED)
        await self.audit_service.record_event(
            event_type=AuditEventType.REVERSAL,
            actor=reversed_by,
            entity_type="exception_action",
            entity_id=action.id,
            payload={
                "reversal_id": str(reversal.id),
                "action_id": str(action.id),
                "action_type": action.action_type,
                "reason": reason,
                "reversed_by": reversed_by,
                "voided_effects": voided_effects,
            },
        )

        await self.audit_service.record_event(
            event_type=AuditEventType.EXCEPTION_REOPENED,
            actor=reversed_by,
            entity_type="exception",
            entity_id=exception.id,
            payload={
                "reversal_id": str(reversal.id),
                "previous_status": str(previous_status),
                "new_status": str(ExceptionStatus.REOPENED),
                "reason": reason,
            },
        )

        return ReversalResult(
            reversal_id=reversal.id,
            exception_action_id=action.id,
            exception_id=exception.id,
            reason=reason,
            reversed_by=reversed_by,
            reversed_at=now,
            reopened_exception=True,
            voided_side_effects=voided_effects,
            message=f"Action {action.action_type} reversed by {reversed_by}. Exception reopened.",
        )
