"""Audit-trail service (spec sections 13, 13.1).

Append-only recording of important decisions. Every event references
specific policy/prompt version ids (never bare names) so decisions are
reproducible against the exact configuration that produced them.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.controls import map_to_control_id
from app.db.base import utcnow
from app.db.models.audit import AgentPromptVersion, AuditEvent, PolicyVersion
from app.domain.enums import AuditEventType


def _json_serializable(value: object) -> object:
    """Coerce non-serializable values (Decimal, uuid, datetime) to JSON-safe."""
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


class AuditService:
    """Records audit events for a given tenant context."""

    def __init__(self, session: AsyncSession, company_id: uuid.UUID | None = None) -> None:
        self.session = session
        self.company_id = company_id

    async def record(
        self,
        *,
        event_type: AuditEventType,
        actor: str | None = None,
        actor_type: str | None = None,
        agent_name: str | None = None,
        agent_prompt_version_id: str | None = None,
        policy_version_id: str | None = None,
        close_run_id: uuid.UUID | None = None,
        exception_id: uuid.UUID | None = None,
        decision: str | None = None,
        reason: str | None = None,
        financial_impact: Decimal | str | None = None,
        currency: str | None = None,
        confidence: Decimal | None = None,
        calibrated_confidence: Decimal | None = None,
        evidence_ids: list[str] | None = None,
        metadata_: dict | None = None,
        control_id: str | None = None,
    ) -> AuditEvent:
        """Append a new audit event (never updated/deleted afterwards)."""
        if control_id is None:
            exc_type = None
            task_type = None
            if metadata_:
                exc_type = metadata_.get("exception_type")
                task_type = metadata_.get("task_type")
            control_id = map_to_control_id(
                exception_type=exc_type,
                task_type=task_type,
                event_type=event_type,
            )

        event = AuditEvent(
            company_id=self.company_id,
            close_run_id=close_run_id,
            event_type=event_type,
            actor=actor,
            actor_type=actor_type,
            agent_name=agent_name,
            agent_prompt_version_id=agent_prompt_version_id,
            policy_version_id=policy_version_id,
            exception_id=exception_id,
            decision=decision,
            reason=reason,
            financial_impact=Decimal(str(financial_impact))
            if financial_impact is not None
            else None,
            currency=currency,
            confidence=confidence,
            calibrated_confidence=calibrated_confidence,
            evidence_ids=json.dumps(evidence_ids) if evidence_ids is not None else None,
            metadata_=json.dumps(metadata_, default=_json_serializable) if metadata_ else None,
            control_id=control_id,
            created_at=utcnow(),
        )
        self.session.add(event)
        await self.session.flush()
        return event

    async def record_event(
        self,
        *,
        event_type: AuditEventType,
        actor: str | None = None,
        entity_type: str | None = None,
        entity_id: uuid.UUID | None = None,
        payload: dict | None = None,
        agent_name: str | None = None,
        decision: str | None = None,
        reason: str | None = None,
        financial_impact: Decimal | str | None = None,
        currency: str | None = None,
        confidence: Decimal | None = None,
        calibrated_confidence: Decimal | None = None,
        control_id: str | None = None,
    ) -> AuditEvent:
        """Convenience method for recording an event by entity and payload."""
        exception_id = entity_id if entity_type == "exception" else None
        return await self.record(
            event_type=event_type,
            actor=actor,
            agent_name=agent_name,
            exception_id=exception_id,
            decision=decision,
            reason=reason,
            financial_impact=financial_impact,
            currency=currency,
            confidence=confidence,
            calibrated_confidence=calibrated_confidence,
            metadata_=payload,
            control_id=control_id,
        )

    async def list(
        self,
        *,
        close_run_id: uuid.UUID | None = None,
        event_type: AuditEventType | None = None,
        control_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditEvent]:
        """List audit events, tenant-scoped and newest-first."""
        stmt = select(AuditEvent).order_by(AuditEvent.created_at.desc())
        if self.company_id is not None:
            stmt = stmt.where(AuditEvent.company_id == self.company_id)
        if close_run_id is not None:
            stmt = stmt.where(AuditEvent.close_run_id == close_run_id)
        if event_type is not None:
            stmt = stmt.where(AuditEvent.event_type == event_type)
        if control_id is not None:
            stmt = stmt.where(AuditEvent.control_id == control_id)
        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.scalars(stmt)
        return list(result.all())


def parse_json_column(value: str | None) -> object | None:
    """Parse a stored JSON text column back into a Python object."""
    return json.loads(value) if value else None


async def deploy_policy_version(
    session: AsyncSession, *, version_id: str, policy_config: dict, description: str | None = None
) -> PolicyVersion:
    """Register an immutable policy version (spec section 13.1)."""
    version = PolicyVersion(
        version_id=version_id,
        policy_config=json.dumps(policy_config),
        description=description,
        deployed_at=utcnow(),
    )
    session.add(version)
    await session.flush()
    return version


async def deploy_agent_prompt_version(
    session: AsyncSession,
    *,
    agent_name: str,
    version_id: str,
    prompt_config: dict,
    description: str | None = None,
) -> AgentPromptVersion:
    """Register an immutable agent prompt/config version (spec section 13.1)."""
    version = AgentPromptVersion(
        agent_name=agent_name,
        version_id=version_id,
        prompt_config=json.dumps(prompt_config),
        description=description,
        deployed_at=utcnow(),
    )
    session.add(version)
    await session.flush()
    return version
