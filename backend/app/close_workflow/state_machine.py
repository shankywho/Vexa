"""Close-run and task state machines with CAS and audit trail (spec sections 14, 15)."""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import AuditService
from app.db.base import utcnow
from app.db.models.close_run import CloseRun, CloseTask
from app.domain.enums import (
    AuditEventType,
    CloseRunStatus,
    CloseTaskStatus,
    CloseTaskType,
)

logger = logging.getLogger(__name__)

# Allowed state transitions for CloseRun (spec section 14).
ALLOWED_CLOSE_RUN_TRANSITIONS: dict[CloseRunStatus, set[CloseRunStatus]] = {
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
        CloseRunStatus.RESOLVING,
        CloseRunStatus.FINAL_VERIFICATION,
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
        CloseRunStatus.FINAL_VERIFICATION,
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
        CloseRunStatus.WAITING_FOR_HUMAN,
        CloseRunStatus.BLOCKED,
        CloseRunStatus.FAILED,
    },
    CloseRunStatus.READY_TO_CLOSE: {
        CloseRunStatus.CLOSED,
        CloseRunStatus.BLOCKED,
        CloseRunStatus.WAITING_FOR_HUMAN,
    },
    CloseRunStatus.CLOSED: set(),
    CloseRunStatus.FAILED: {
        CloseRunStatus.CREATED,
        CloseRunStatus.INGESTING,
        CloseRunStatus.RECONCILING,
    },
    CloseRunStatus.BLOCKED: {
        CloseRunStatus.WAITING_FOR_HUMAN,
        CloseRunStatus.RESOLVING,
        CloseRunStatus.FINAL_VERIFICATION,
        CloseRunStatus.READY_TO_CLOSE,
        CloseRunStatus.CREATED,
        CloseRunStatus.FAILED,
    },
}

# Allowed state transitions for CloseTask (spec section 15).
ALLOWED_TASK_TRANSITIONS: dict[CloseTaskStatus, set[CloseTaskStatus]] = {
    CloseTaskStatus.PENDING: {CloseTaskStatus.IN_PROGRESS, CloseTaskStatus.BLOCKED},
    CloseTaskStatus.IN_PROGRESS: {
        CloseTaskStatus.COMPLETED,
        CloseTaskStatus.FAILED,
        CloseTaskStatus.BLOCKED,
    },
    CloseTaskStatus.FAILED: {CloseTaskStatus.PENDING, CloseTaskStatus.IN_PROGRESS},
    CloseTaskStatus.BLOCKED: {CloseTaskStatus.PENDING, CloseTaskStatus.IN_PROGRESS},
    CloseTaskStatus.COMPLETED: {CloseTaskStatus.PENDING},
}


class CloseRunError(ValueError):
    """Close run domain error (invalid transition, concurrent modification, tenant mismatch)."""


class CloseTaskError(ValueError):
    """Close task domain error (invalid transition, missing task, invalid dependencies)."""


class CloseWorkflowStateMachine:
    """Coordinates state transitions for close runs and tasks with CAS and audit integration."""

    def __init__(
        self,
        session: AsyncSession,
        company_id: uuid.UUID,
        audit_service: AuditService | None = None,
        policy_version_id: str = "policy-v1",
    ) -> None:
        self.session = session
        self.company_id = company_id
        self.audit_service = audit_service or AuditService(session, company_id)
        self.policy_version_id = policy_version_id

    async def transition_close_run(
        self,
        close_run_id: uuid.UUID,
        new_status: CloseRunStatus,
        *,
        actor: str = "close_controller",
        reason: str | None = None,
        metadata_: dict[str, Any] | None = None,
    ) -> CloseRun:
        """Execute a Compare-And-Swap (CAS) state transition on a CloseRun.

        Uses ``UPDATE ... WHERE id=? AND version=? AND status=<current>`` to guarantee
        that competing workers or stale versions fail cleanly without corrupting state.
        """
        close_run = await self.session.get(CloseRun, close_run_id)
        if close_run is None:
            raise CloseRunError(f"Close run {close_run_id} does not exist")
        if close_run.company_id != self.company_id:
            raise CloseRunError("Close run is not in this tenant")

        current = close_run.status
        if current == new_status:
            return close_run

        allowed = ALLOWED_CLOSE_RUN_TRANSITIONS.get(current, set())
        if new_status not in allowed:
            raise CloseRunError(f"Invalid transition {current} -> {new_status}")

        values_to_update: dict[str, Any] = {
            "status": new_status,
            "version": CloseRun.version + 1,
        }
        if current == CloseRunStatus.CREATED and new_status == CloseRunStatus.INGESTING:
            values_to_update["started_at"] = utcnow()
        elif new_status == CloseRunStatus.CLOSED:
            values_to_update["completed_at"] = utcnow()

        result = await self.session.execute(
            update(CloseRun)
            .where(
                CloseRun.id == close_run_id,
                CloseRun.version == close_run.version,
                CloseRun.status == current,
            )
            .values(**values_to_update)
            .returning(CloseRun.version)
        )
        new_version = result.scalar_one_or_none()
        if new_version is None:
            raise CloseRunError("Concurrent modification; close run state changed elsewhere")

        await self.session.refresh(close_run)

        # Append versioned audit event (spec section 13)
        await self.audit_service.record(
            event_type=AuditEventType.CLOSE_RUN_STATE_CHANGE,
            actor=actor,
            actor_type="CONTROLLER",
            agent_name="close_controller",
            policy_version_id=self.policy_version_id,
            close_run_id=close_run_id,
            decision=new_status.value,
            reason=reason or f"Transition from {current.value} to {new_status.value}",
            metadata_={
                "previous_status": current.value,
                "new_status": new_status.value,
                "version": new_version,
                **(metadata_ or {}),
            },
        )

        try:
            from app.streaming.bus import agent_event_bus

            await agent_event_bus.publish(
                close_run_id,
                {
                    "event": "close_run_state_change",
                    "close_run_id": str(close_run_id),
                    "previous_status": current.value,
                    "new_status": new_status.value,
                    "version": new_version,
                    "actor": actor,
                    "reason": reason or f"Transition from {current.value} to {new_status.value}",
                },
            )
        except Exception as bus_err:
            logger.warning("Failed to publish close_run_state_change to SSE bus: %s", bus_err)

        return close_run

    async def transition_task(
        self,
        task_id: uuid.UUID,
        new_status: CloseTaskStatus,
        *,
        actor: str = "close_controller",
        summary: str | None = None,
        metrics: dict[str, Any] | None = None,
        error_message: str | None = None,
    ) -> CloseTask:
        """Transition the lifecycle state of a CloseTask."""
        task = await self.session.get(CloseTask, task_id)
        if task is None:
            raise CloseTaskError(f"Close task {task_id} does not exist")

        current = task.status
        if current == new_status and not summary and not metrics:
            return task

        allowed = ALLOWED_TASK_TRANSITIONS.get(current, set())
        if new_status != current and new_status not in allowed:
            raise CloseTaskError(f"Invalid task transition {current} -> {new_status}")

        task.status = new_status
        now = utcnow()
        if new_status == CloseTaskStatus.IN_PROGRESS and task.started_at is None:
            task.started_at = now
        elif new_status in (
            CloseTaskStatus.COMPLETED,
            CloseTaskStatus.FAILED,
            CloseTaskStatus.BLOCKED,
        ):
            task.completed_at = now

        if summary or metrics or error_message:
            payload = {
                "summary": summary or task.result_summary,
                "metrics": metrics or {},
                "error_message": error_message,
            }
            task.result_summary = json.dumps(payload, default=str)

        await self.session.flush()

        # Append versioned audit event
        await self.audit_service.record(
            event_type=AuditEventType.CLOSE_TASK_STATE_CHANGE,
            actor=actor,
            actor_type="CONTROLLER",
            agent_name="close_controller",
            policy_version_id=self.policy_version_id,
            close_run_id=task.close_run_id,
            decision=new_status.value,
            reason=f"Task {task.task_type.value} state changed to {new_status.value}",
            metadata_={
                "task_id": str(task.id),
                "task_type": task.task_type.value,
                "previous_status": current.value,
                "new_status": new_status.value,
                "summary": summary,
                "metrics": metrics,
                "error_message": error_message,
            },
        )

        if task.close_run_id:
            try:
                from app.streaming.bus import agent_event_bus

                await agent_event_bus.publish(
                    task.close_run_id,
                    {
                        "event": "close_task_state_change",
                        "close_run_id": str(task.close_run_id),
                        "task_id": str(task.id),
                        "task_type": task.task_type.value,
                        "previous_status": current.value,
                        "new_status": new_status.value,
                        "summary": summary,
                        "metrics": metrics,
                        "error_message": error_message,
                    },
                )
            except Exception as bus_err:
                logger.warning("Failed to publish close_task_state_change to SSE bus: %s", bus_err)

        return task

    async def get_tasks(self, close_run_id: uuid.UUID) -> dict[CloseTaskType, CloseTask]:
        """Fetch all close tasks for a close run, indexed by task type."""
        stmt = select(CloseTask).where(CloseTask.close_run_id == close_run_id)
        tasks = (await self.session.scalars(stmt)).all()
        return {t.task_type: t for t in tasks}
