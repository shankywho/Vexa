"""Action and Human Review Service (spec section 10, 11, 13.2, 17)."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.action.agent import ActionAgent
from app.action.correction_service import HumanCorrectionService
from app.action.reversal import ReversalEngine
from app.action.tools import ActionTools
from app.action.types import ActionResult, ActionType, ReversalResult
from app.audit.service import AuditService
from app.db.base import utcnow
from app.db.models.exception import ExceptionAction, ReversalAction
from app.db.repository import (
    ExceptionActionRepository,
    ExceptionRepository,
    ReversalActionRepository,
)
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
        self.correction_service = HumanCorrectionService(session, company_id)

    async def execute_for_verification(
        self,
        exception_id: uuid.UUID,
        finding: InvestigationFinding,
        verification: VerificationResult,
    ) -> list[ActionResult]:
        """Execute autonomous actions guided by independent verification."""
        results = await self.agent.execute_for_verification(exception_id, finding, verification)
        exc = await self.exc_repo.get_by_id(exception_id)
        if exc and exc.close_run_id:
            try:
                from app.streaming.bus import agent_event_bus

                await agent_event_bus.publish(
                    exc.close_run_id,
                    {
                        "event": "actions_executed",
                        "close_run_id": str(exc.close_run_id),
                        "exception_id": str(exception_id),
                        "actions_count": len(results),
                        "actions": [r.action_type.value for r in results],
                    },
                )
            except Exception:
                pass
        return results

    async def approve_exception(
        self,
        exception_id: uuid.UUID,
        actor: str = "controller",
        notes: str | None = None,
        materiality_threshold: Decimal | None = None,
    ) -> ActionResult:
        """Human approver approves an exception and executes staged actions (spec section 17)."""
        exc = await self.exc_repo.get_by_id(exception_id)
        if not exc:
            raise ValueError(f"Exception {exception_id} not found for company {self.company_id}")

        staged_actions = await self.action_repo.list_staged(exception_id)

        # Segregation-of-duties check (spec section 17 / FIX 2):
        # If financial impact exceeds the materiality threshold, the approving actor
        # cannot be the same actor who prepared/staged the action.
        effective_threshold = (
            materiality_threshold if materiality_threshold is not None else Decimal("50000.00")
        )
        is_material = exc.financial_impact is None or exc.financial_impact > effective_threshold

        if is_material:
            for act in staged_actions:
                if act.actor and act.actor.strip().lower() == actor.strip().lower():
                    reason_msg = (
                        f"Segregation-of-duties violation: Actor '{actor}' prepared "
                        f"staged action {act.id} and cannot approve their own "
                        f"adjustment. Independent review required."
                    )
                    await self.audit_service.record_event(
                        event_type=AuditEventType.EXCEPTION_DECISION,
                        actor=actor,
                        entity_type="exception",
                        entity_id=exception_id,
                        decision="SOD_VIOLATION",
                        reason=reason_msg,
                        financial_impact=exc.financial_impact,
                        currency=exc.currency,
                        payload={
                            "decision": "SOD_VIOLATION",
                            "attempted_by": actor,
                            "preparer": act.actor,
                            "action_id": str(act.id),
                            "financial_impact": str(exc.financial_impact)
                            if exc.financial_impact is not None
                            else None,
                        },
                    )
                    raise ValueError(reason_msg)

        now = utcnow()
        # Mark staged actions as EXECUTED
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

        # Record human correction / outcome
        orig_dec = exc.autonomy_level.value if exc.autonomy_level else "STAGE"
        await self.correction_service.record_correction(
            exception_id=exception_id,
            original_decision=orig_dec,
            human_decision="APPROVED",
            close_run_id=exc.close_run_id,
            original_confidence=exc.confidence,
            calibrated_confidence=exc.calibrated_confidence,
            exception_type=exc.type.value if exc.type else "UNKNOWN",
            policy_version_id="policy-v1",
            reviewer_role="controller",
            actor=actor,
            reason=notes or "Approved by human reviewer.",
        )

        if exc.close_run_id:
            try:
                from app.streaming.bus import agent_event_bus

                await agent_event_bus.publish(
                    exc.close_run_id,
                    {
                        "event": "exception_approved",
                        "close_run_id": str(exc.close_run_id),
                        "exception_id": str(exception_id),
                        "actor": actor,
                    },
                )
            except Exception:
                pass

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

        # Record human correction / outcome
        orig_dec = exc.autonomy_level.value if exc.autonomy_level else "STAGE"
        await self.correction_service.record_correction(
            exception_id=exception_id,
            original_decision=orig_dec,
            human_decision="REJECTED",
            close_run_id=exc.close_run_id,
            original_confidence=exc.confidence,
            calibrated_confidence=exc.calibrated_confidence,
            exception_type=exc.type.value if exc.type else "UNKNOWN",
            policy_version_id="policy-v1",
            reviewer_role="controller",
            actor=actor,
            reason=notes or "Resolution rejected by reviewer.",
        )

        if exc.close_run_id:
            try:
                from app.streaming.bus import agent_event_bus

                await agent_event_bus.publish(
                    exc.close_run_id,
                    {
                        "event": "exception_rejected",
                        "close_run_id": str(exc.close_run_id),
                        "exception_id": str(exception_id),
                        "actor": actor,
                    },
                )
            except Exception:
                pass

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
        result = await self.tools.mark_exception_escalated(
            exception_id=exception_id,
            escalation_reason=reason or "Manual escalation to senior leadership",
            target_role=target_role,
            actor=actor,
        )
        exc = await self.exc_repo.get_by_id(exception_id)
        if exc and exc.close_run_id:
            try:
                from app.streaming.bus import agent_event_bus

                await agent_event_bus.publish(
                    exc.close_run_id,
                    {
                        "event": "exception_escalated",
                        "close_run_id": str(exc.close_run_id),
                        "exception_id": str(exception_id),
                        "actor": actor,
                        "target_role": str(target_role),
                    },
                )
            except Exception:
                pass
        return result

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

    async def list_actions_for_exception(
        self, exception_id: uuid.UUID
    ) -> Sequence[ExceptionAction]:
        return await self.action_repo.list_by_exception(exception_id)

    async def list_reversals_for_exception(
        self, exception_id: uuid.UUID
    ) -> Sequence[ReversalAction]:
        return await self.reversal_repo.list_by_exception(exception_id)
