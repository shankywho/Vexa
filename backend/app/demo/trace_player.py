"""Trace player replaying captured golden demo traces through SSE (spec section 37)."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any

from app.db.models.demo import DemoTrace
from app.streaming.bus import format_sse

logger = logging.getLogger(__name__)


class TracePlayer:
    """Plays back captured execution traces as real-time Server-Sent Events (SSE)."""

    def __init__(self, playback_speed: float = 1.0, simulate_delay: bool = True) -> None:
        """
        Initialize the trace player.

        :param playback_speed: Speed multiplier (1.0 = real-time, 2.0 = 2x speed, 10.0 = 10x speed).
        :param simulate_delay: If False, emits all events immediately without sleeping.
        """
        self.playback_speed = max(0.1, playback_speed)
        self.simulate_delay = simulate_delay

    async def play_trace(
        self,
        trace: DemoTrace,
        close_run_id: str | None = None,
    ) -> AsyncIterator[str]:
        """
        Asynchronously yield SSE strings for each event in the trace at timed intervals.
        """
        events: list[dict[str, Any]] = trace.events
        if not events:
            logger.warning("Trace %s has no events to play", trace.id)
            yield format_sse({"type": "completed", "empty": True}, event="completed")
            return

        prev_offset_ms = 0

        for event in events:
            curr_offset_ms = event.get("offset_ms", prev_offset_ms)
            delta_ms = max(0, curr_offset_ms - prev_offset_ms)

            if self.simulate_delay and delta_ms > 0:
                delay_sec = (delta_ms / 1000.0) / self.playback_speed
                await asyncio.sleep(delay_sec)

            prev_offset_ms = curr_offset_ms

            # Shallow clone event to optionally inject current close_run_id if provided
            payload = dict(event)
            if close_run_id is not None:
                payload["close_run_id"] = close_run_id

            event_type = payload.get("event") or payload.get("type") or "message"
            yield format_sse(payload, event=event_type)
