"""Streaming event bus for SSE real-time agent and workflow activity (spec sections 17, 37)."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections import defaultdict
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

logger = logging.getLogger(__name__)


def format_sse(data: dict[str, Any], event: str | None = None) -> str:
    """Format a payload as a Server-Sent Events (SSE) standard data chunk."""
    payload_str = json.dumps(data)
    if event:
        return f"event: {event}\ndata: {payload_str}\n\n"
    return f"data: {payload_str}\n\n"


class AgentEventBus:
    """In-memory publish/subscribe event bus keyed by close_run_id."""

    def __init__(self) -> None:
        self._subscribers: dict[uuid.UUID, set[asyncio.Queue[dict[str, Any]]]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def publish(self, close_run_id: uuid.UUID, event: dict[str, Any]) -> None:
        """Publish an event to all subscribers listening to close_run_id."""
        async with self._lock:
            queues = list(self._subscribers.get(close_run_id, set()))

        for q in queues:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning("Subscriber queue full for close run %s", close_run_id)

    @asynccontextmanager
    async def subscribe(
        self, close_run_id: uuid.UUID, max_queue_size: int = 256
    ) -> AsyncIterator[asyncio.Queue[dict[str, Any]]]:
        """Subscribe to live events for close_run_id."""
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=max_queue_size)
        async with self._lock:
            self._subscribers[close_run_id].add(queue)
        try:
            yield queue
        finally:
            async with self._lock:
                self._subscribers[close_run_id].discard(queue)
                if not self._subscribers[close_run_id]:
                    self._subscribers.pop(close_run_id, None)


# Global singleton event bus instance
agent_event_bus = AgentEventBus()
