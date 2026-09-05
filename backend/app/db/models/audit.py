"""Audit-trail foundation (spec sections 13, 13.1).

- ``audit_events``: append-only ledger of every important decision.
- ``policy_versions`` / ``agent_prompt_versions``: versioned configurations
  referenced by audit events so every historical decision is reproducible
  against the exact policy/prompt that produced it.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPkMixin
from app.domain.enums import AuditEventType


class PolicyVersion(UUIDPkMixin, TimestampMixin, Base):
    """An immutable snapshot of a deployed policy configuration."""

    __tablename__ = "policy_versions"

    version_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    policy_config: Mapped[dict] = mapped_column("policy_config_json", Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    deployed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AgentPromptVersion(UUIDPkMixin, TimestampMixin, Base):
    """An immutable snapshot of a deployed agent prompt/configuration."""

    __tablename__ = "agent_prompt_versions"

    agent_name: Mapped[str] = mapped_column(String(64), nullable=False)
    version_id: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_config: Mapped[dict] = mapped_column("prompt_config_json", Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    deployed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("agent_name", "version_id", name="uq_agent_prompt_versions_agent_version"),
    )


class AuditEvent(UUIDPkMixin, Base):
    """Append-only audit record for an important decision/action.

    The ``created_at`` timestamp is server-side by default; rows are never
    updated or deleted in normal operation.
    """

    __tablename__ = "audit_events"

    company_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True
    )
    close_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("close_runs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    event_type: Mapped[AuditEventType] = mapped_column(
        Enum(AuditEventType, name="audit_event_type"), nullable=False, index=True
    )
    actor: Mapped[str | None] = mapped_column(String(255))
    actor_type: Mapped[str | None] = mapped_column(String(32))  # USER | AGENT | SYSTEM
    agent_name: Mapped[str | None] = mapped_column(String(64))
    agent_prompt_version_id: Mapped[str | None] = mapped_column(String(64))
    policy_version_id: Mapped[str | None] = mapped_column(String(64))
    exception_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("exceptions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    decision: Mapped[str | None] = mapped_column(String(64))
    reason: Mapped[str | None] = mapped_column(Text)
    financial_impact: Mapped[Decimal | None] = mapped_column(Numeric(20, 2))
    currency: Mapped[str | None] = mapped_column(String(3))
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(6, 4))
    calibrated_confidence: Mapped[Decimal | None] = mapped_column(Numeric(6, 4))
    evidence_ids: Mapped[dict | None] = mapped_column("evidence_ids_json", Text)
    metadata_: Mapped[dict | None] = mapped_column("metadata_json", Text)  # tool calls, refs, etc.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
