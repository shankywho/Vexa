"""Close-run models (spec sections 14, 15, 14.1).

``CloseRun`` carries a ``version`` integer used for compare-and-swap state
transitions (concurrency control, spec section 14.1).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPkMixin
from app.domain.enums import CloseRunStatus, CloseTaskStatus, CloseTaskType


class CloseRun(UUIDPkMixin, TimestampMixin, Base):
    """A single month-end close run for a company."""

    __tablename__ = "close_runs"

    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    period_start: Mapped[date] = mapped_column(nullable=False)
    period_end: Mapped[date] = mapped_column(nullable=False)
    status: Mapped[CloseRunStatus] = mapped_column(
        Enum(CloseRunStatus, name="close_run_status"),
        default=CloseRunStatus.CREATED,
        nullable=False,
        index=True,
    )
    # Optimistic-lock version for compare-and-swap state transitions (§14.1)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    close_summary: Mapped[str | None] = mapped_column(Text)

    tasks: Mapped[list[CloseTask]] = relationship(
        back_populates="close_run", cascade="all, delete-orphan"
    )


class CloseTask(UUIDPkMixin, TimestampMixin, Base):
    """A task within a close run."""

    __tablename__ = "close_tasks"

    close_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("close_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    task_type: Mapped[CloseTaskType] = mapped_column(
        Enum(CloseTaskType, name="close_task_type"), nullable=False
    )
    status: Mapped[CloseTaskStatus] = mapped_column(
        Enum(CloseTaskStatus, name="close_task_status"),
        default=CloseTaskStatus.PENDING,
        nullable=False,
    )
    assigned_to: Mapped[str | None] = mapped_column(String(255))  # agent or user identifier
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    result_summary: Mapped[str | None] = mapped_column(Text)

    close_run: Mapped[CloseRun] = relationship(back_populates="tasks")
