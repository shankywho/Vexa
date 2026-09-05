"""Types and schemas for Action Agent and Rollback Engine (spec section 10, 11, 13.2)."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ActionType(StrEnum):
    """Permitted autonomous actions (spec section 10)."""

    CREATE_REVIEW_TASK = "CREATE_REVIEW_TASK"
    DRAFT_VENDOR_EMAIL = "DRAFT_VENDOR_EMAIL"
    STAGE_JOURNAL_ENTRY = "STAGE_JOURNAL_ENTRY"
    MARK_EXCEPTION_RESOLVED = "MARK_EXCEPTION_RESOLVED"
    MARK_EXCEPTION_ESCALATED = "MARK_EXCEPTION_ESCALATED"
    VOID_STAGED_ENTRY = "VOID_STAGED_ENTRY"
    GENERATE_CLOSE_PACKAGE = "GENERATE_CLOSE_PACKAGE"


class ActionResult(BaseModel):
    """Structured result of an action execution."""

    model_config = ConfigDict(frozen=True)

    action_id: uuid.UUID
    exception_id: uuid.UUID
    action_type: ActionType
    status: str  # STAGED | EXECUTED | REVERSED | VOID
    payload: dict = Field(default_factory=dict)
    actor: str = "action_agent"
    executed_at: datetime | None = None
    message: str = ""


class ReversalResult(BaseModel):
    """Rollback trail output for a reversed action (spec section 13.2)."""

    model_config = ConfigDict(frozen=True)

    reversal_id: uuid.UUID
    exception_action_id: uuid.UUID
    exception_id: uuid.UUID
    reason: str
    reversed_by: str
    reversed_at: datetime
    reopened_exception: bool = True
    voided_side_effects: list[str] = Field(default_factory=list)
    message: str = ""
