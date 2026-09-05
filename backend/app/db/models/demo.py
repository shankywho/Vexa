"""Demo traces database model for Live/Replay safety net (spec section 37)."""

from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPkMixin


class DemoTrace(UUIDPkMixin, TimestampMixin, Base):
    """A captured golden execution trace for live/replay safety net."""

    __tablename__ = "demo_traces"

    company_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=True, index=True
    )
    scenario_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    events_json: Mapped[str] = mapped_column(Text, nullable=False)
    total_steps: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_golden: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    @property
    def events(self) -> list[dict[str, Any]]:
        if not self.events_json:
            return []
        try:
            return json.loads(self.events_json)
        except Exception:
            return []

    @events.setter
    def events(self, value: list[dict[str, Any]] | str) -> None:
        if isinstance(value, str):
            self.events_json = value
        else:
            self.events_json = json.dumps(value)
