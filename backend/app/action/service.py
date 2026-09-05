"""Action and Human Review Service (spec section 10, 11, 13.2, 17)."""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.action.agent import ActionAgent
from app.action.reversal import ReversalEngine
from app.action.tools import ActionTools
from app.action.types import ActionResult, ActionType, ReversalResult
from app.audit.service import AuditService
from app.db.models.exception import ExceptionAction, ExceptionRecord, ReversalAction
from app.db.repository import (
    ExceptionActionRepository,
    ExceptionRepository,
    ReversalActionRepository,
)
from app.db.base import utcnow
from app.domain.enums import AuditEventType, ExceptionStatus, Role
from app.investigation.types import InvestigationFinding
from app.verification.types import VerificationResult


class ActionService:
    """Service providing action execution, human approval, rejection, and reversal workflows."""

    def __init__(self, session: AsyncSession, company_id: uuid.UUID) -> None:
        self.session = session
        self.company_id = company_id
        self.agent = ActionAgent(session, company_id)
        self.tools = ActionTools(session, company_id)
        self.reversal_engine = ReversalEngine(session, company_id)
        self.action_repo = ExceptionActionRepository(session, company_id)
        self.reversal_repo = ReversalActionRepository(session, company_id)
        self.exc_repo = ExceptionRepository(session, company_id)
        self.audit_service = AuditService(session, company_id)

    async def execute_for_verification(
        self,
        exception_id: uuid.UUID,
        finding: InvestigationFinding,
        verification: VerificationResult,
    ) -> list[ActionResult]:
        """Execute autonomous actions guided by independent verification."""
        return await self.agent.execute_for_verification(exception_id, finding, verification)

    async def approve_exception(
        self,
        exception_id: uuid.UUID,
        actor: str = "controller",
        notes: str | None = None,
    ) -> ActionResult:
        """Human approver approves an exception and executes staged actions (spec section 17)."""
        exc = await self.exc_repo.get_by_id(exception_id)
        if not exc:
            raise ValueError(f"Exception {exception_id} not found for company {self.company_id}")

        now = utcnow()
        # Mark staged actions as EXECUTED
        staged_actions = await self.action_repo.list_staged(exception_id)
        for act in staged_actions:
            act.status = "EXECUTED"
            act.executed_at = now

        exc.status = ExceptionStatus.RESOLVED
        exc.resolved_at = now

        payload = {
            "notes": notes or "Approved by human reviewer.",
            "staged_actions_executed": len(staged_actions),
        }

        action = await self.action_repo.create(
            exception_id=exception_id,
            action_type=ActionType.MARK_EXCEPTION_RESOLVED,
            status="EXECUTED",
            payload=payload,
            actor=actor,
            executed_at=now,
        )

        await self.audit_service.record_event(
            event_type=AuditEventType.APPROVAL,
            actor=actor,
            entity_type="exception",
            entity_id=exception_id,
            payload=payload,
        )

        return ActionResult(
            action_id=action.id,
            exception_id=exception_id,
            action_type=ActionType.MARK_EXCEPTION_RESOLVED,
            status="EXECUTED",
            payload=payload,
            actor=actor,
            executed_at=now,
            message=f"Exception approved and resolved by {actor}.",
        )

    async def reject_exception(
        self,
        exception_id: uuid.UUID,
        actor: str = "controller",
        notes: str | None = None,
    ) -> ActionResult:
        """Human approver rejects a staged resolution or finding (spec section 17)."""
        exc = await self.exc_repo.get_by_id(exception_id)
        if not exc:
            raise ValueError(f"Exception {exception_id} not found for company {self.company_id}")

        # Void any staged actions
        staged_actions = await self.action_repo.list_staged(exception_id)
        for act in staged_actions:
            act.status = "VOID"

        # Keep exception OPEN for re-investigation
        exc.status = ExceptionStatus.OPEN
        exc.resolved_at = None

        payload = {"rejection_reason": notes or "Resolution rejected by reviewer."}
        now = utcnow()
        action = await self.action_repo.create(
            exception_id=exception_id,
            action_type=ActionType.CREATE_REVIEW_TASK,
            status="EXECUTED",
            payload=payload,
            actor=actor,
            executed_at=now,
        )

        await self.audit_service.record_event(
            event_type=AuditEventType.ACTION_EXECUTED,
            actor=actor,
            entity_type="exception",
            entity_id=exception_id,
            payload=payload,
        )

        return ActionResult(
            action_id=action.id,
            exception_id=exception_id,
            action_type=ActionType.CREATE_REVIEW_TASK,
            status="EXECUTED",
            payload=payload,
            actor=actor,
            executed_at=now,
            message=f"Resolution rejected by {actor}. Exception returned to OPEN.",
        )

    async def escalate_exception(
        self,
        exception_id: uuid.UUID,
        target_role: Role | str = Role.CFO,
        reason: str | None = None,
        actor: str = "controller",
    ) -> ActionResult:
        """Manually or programmatically escalate exception to CFO (spec section 17)."""
        return await self.tools.mark_exception_escalated(
            exception_id=exception_id,
            escalation_reason=reason or "Manual escalation to senior leadership",
            target_role=target_role,
            actor=actor,
        )

    async def reverse_action(
        self,
        action_id: uuid.UUID,
        reason: str,
        reversed_by: str = "controller",
    ) -> ReversalResult:
        """Rollback a previously executed or staged action (spec section 13.2)."""
        return await self.reversal_engine.reverse_action(
            action_id=action_id,
            reason=reason,
            reversed_by=reversed_by,
        )

    async def list_actions_for_exception(self, exception_id: uuid.UUID) -> Sequence[ExceptionAction]:
        return await self.action_repo.list_by_exception(exception_id)

    async def list_reversals_for_exception(self, exception_id: uuid.UUID) -> Sequence[ReversalAction]:
        return await self.reversal_repo.list_by_exception(exception_id)
