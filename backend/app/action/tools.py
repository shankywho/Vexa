"""Idempotent tool implementation for Action Agent (spec section 10, 16, 31)."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.action.types import ActionResult, ActionType
from app.audit.service import AuditService
from app.db.base import utcnow
from app.db.repository import ExceptionActionRepository, ExceptionRepository
from app.domain.enums import AuditEventType, ExceptionStatus, Role


class ActionTools:
    """Permitted autonomous action execution tools with idempotency guarantees."""

    def __init__(self, session: AsyncSession, company_id: uuid.UUID) -> None:
        self.session = session
        self.company_id = company_id
        self.action_repo = ExceptionActionRepository(session, company_id)
        self.exc_repo = ExceptionRepository(session, company_id)
        self.audit_service = AuditService(session, company_id)

    async def create_review_task(
        self,
        exception_id: uuid.UUID,
        title: str,
        description: str,
        assigned_to: Role | str = Role.CONTROLLER,
        actor: str = "action_agent",
    ) -> ActionResult:
        """Idempotently create a human review task for an exception."""
        # Check if identical review task already exists
        existing_actions = await self.action_repo.list_by_exception(exception_id)
        for act in existing_actions:
            if act.action_type == ActionType.CREATE_REVIEW_TASK and act.status != "REVERSED":
                return ActionResult(
                    action_id=act.id,
                    exception_id=exception_id,
                    action_type=ActionType.CREATE_REVIEW_TASK,
                    status=act.status,
                    payload=act.payload or {},
                    actor=act.actor or actor,
                    executed_at=act.executed_at,
                    message="Existing review task returned (idempotent).",
                )

        payload = {
            "title": title,
            "description": description,
            "assigned_to": str(assigned_to),
        }
        now = utcnow()
        action = await self.action_repo.create(
            exception_id=exception_id,
            action_type=ActionType.CREATE_REVIEW_TASK,
            status="EXECUTED",
            payload=payload,
            actor=actor,
            executed_at=now,
        )

        # Update exception assigned_to
        exc = await self.exc_repo.get_by_id(exception_id)
        if exc:
            exc.assigned_to = str(assigned_to)

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
            message=f"Review task assigned to {assigned_to}.",
        )

    async def draft_vendor_email(
        self,
        exception_id: uuid.UUID,
        vendor_name: str,
        subject: str,
        body: str,
        context: dict | None = None,
        actor: str = "action_agent",
    ) -> ActionResult:
        """Idempotently stage a drafted email to a vendor for discrepancy clarification."""
        existing_actions = await self.action_repo.list_by_exception(exception_id)
        for act in existing_actions:
            if act.action_type == ActionType.DRAFT_VENDOR_EMAIL and act.status == "STAGED":
                return ActionResult(
                    action_id=act.id,
                    exception_id=exception_id,
                    action_type=ActionType.DRAFT_VENDOR_EMAIL,
                    status="STAGED",
                    payload=act.payload or {},
                    actor=act.actor or actor,
                    executed_at=act.executed_at,
                    message="Existing staged vendor draft returned (idempotent).",
                )

        payload = {
            "vendor_name": vendor_name,
            "subject": subject,
            "body": body,
            "context": context or {},
        }
        now = utcnow()
        action = await self.action_repo.create(
            exception_id=exception_id,
            action_type=ActionType.DRAFT_VENDOR_EMAIL,
            status="STAGED",
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
            action_type=ActionType.DRAFT_VENDOR_EMAIL,
            status="STAGED",
            payload=payload,
            actor=actor,
            executed_at=now,
            message=f"Vendor draft prepared for {vendor_name} (STAGED for review).",
        )

    async def stage_journal_entry(
        self,
        exception_id: uuid.UUID,
        memo: str,
        lines: list[dict],
        currency: str = "USD",
        actor: str = "action_agent",
    ) -> ActionResult:
        """Idempotently stage a proposed adjusting journal entry without posting directly."""
        existing_actions = await self.action_repo.list_by_exception(exception_id)
        for act in existing_actions:
            if act.action_type == ActionType.STAGE_JOURNAL_ENTRY and act.status == "STAGED":
                return ActionResult(
                    action_id=act.id,
                    exception_id=exception_id,
                    action_type=ActionType.STAGE_JOURNAL_ENTRY,
                    status="STAGED",
                    payload=act.payload or {},
                    actor=act.actor or actor,
                    executed_at=act.executed_at,
                    message="Existing staged journal entry returned (idempotent).",
                )

        payload = {
            "memo": memo,
            "lines": lines,
            "currency": currency,
        }
        now = utcnow()
        action = await self.action_repo.create(
            exception_id=exception_id,
            action_type=ActionType.STAGE_JOURNAL_ENTRY,
            status="STAGED",
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
            action_type=ActionType.STAGE_JOURNAL_ENTRY,
            status="STAGED",
            payload=payload,
            actor=actor,
            executed_at=now,
            message="Adjusting journal entry staged for approval.",
        )

    async def void_staged_entry(
        self,
        action_id: uuid.UUID,
        reason: str,
        actor: str = "controller",
    ) -> ActionResult:
        """Void/unstage a staged journal entry or action."""
        act = await self.action_repo.get_by_id(action_id)
        if not act:
            raise ValueError(f"Action {action_id} not found for company {self.company_id}")

        act.status = "VOID"
        payload = act.payload or {}
        payload["void_reason"] = reason
        payload["voided_by"] = actor
        payload["voided_at"] = utcnow().isoformat()
        act.payload = payload

        await self.audit_service.record_event(
            event_type=AuditEventType.ACTION_EXECUTED,
            actor=actor,
            entity_type="exception_action",
            entity_id=action_id,
            payload=payload,
        )

        return ActionResult(
            action_id=act.id,
            exception_id=act.exception_id,
            action_type=ActionType(act.action_type),
            status="VOID",
            payload=payload,
            actor=actor,
            executed_at=act.executed_at,
            message=f"Staged entry voided: {reason}",
        )

    async def mark_exception_resolved(
        self,
        exception_id: uuid.UUID,
        resolution_note: str,
        actor: str = "action_agent",
        auto_resolved: bool = False,
    ) -> ActionResult:
        """Mark an exception as resolved (or auto-resolved) and write audit record."""
        exc = await self.exc_repo.get_by_id(exception_id)
        if not exc:
            raise ValueError(f"Exception {exception_id} not found for company {self.company_id}")

        target_status = ExceptionStatus.AUTO_RESOLVED if auto_resolved else ExceptionStatus.RESOLVED
        now = utcnow()
        exc.status = target_status
        exc.resolved_at = now
        exc.recommended_action = resolution_note

        payload = {
            "target_status": str(target_status),
            "resolution_note": resolution_note,
            "auto_resolved": auto_resolved,
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
            event_type=AuditEventType.EXCEPTION_RESOLVED,
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
            message=f"Exception marked as {target_status}.",
        )

    async def mark_exception_escalated(
        self,
        exception_id: uuid.UUID,
        escalation_reason: str,
        target_role: Role | str = Role.CFO,
        actor: str = "action_agent",
    ) -> ActionResult:
        """Mark an exception as escalated and assign to senior personnel."""
        exc = await self.exc_repo.get_by_id(exception_id)
        if not exc:
            raise ValueError(f"Exception {exception_id} not found for company {self.company_id}")

        now = utcnow()
        exc.status = ExceptionStatus.ESCALATED
        exc.assigned_to = str(target_role)

        payload = {
            "target_role": str(target_role),
            "escalation_reason": escalation_reason,
        }

        action = await self.action_repo.create(
            exception_id=exception_id,
            action_type=ActionType.MARK_EXCEPTION_ESCALATED,
            status="EXECUTED",
            payload=payload,
            actor=actor,
            executed_at=now,
        )

        await self.audit_service.record_event(
            event_type=AuditEventType.EXCEPTION_ESCALATED,
            actor=actor,
            entity_type="exception",
            entity_id=exception_id,
            payload=payload,
        )

        return ActionResult(
            action_id=action.id,
            exception_id=exception_id,
            action_type=ActionType.MARK_EXCEPTION_ESCALATED,
            status="EXECUTED",
            payload=payload,
            actor=actor,
            executed_at=now,
            message=f"Exception escalated to {target_role}: {escalation_reason}",
        )
