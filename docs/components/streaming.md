# Real-Time Streaming & SSE Component Deep Dive

The Streaming component delivers real-time telemetry from asynchronous agents, close task executors, and audit loggers to connected web clients via HTTP Server-Sent Events (SSE).

---

## 1. Package Structure

Located at [`backend/app/streaming/`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-7/backend/app/streaming/):

```
app/streaming/
├── __init__.py
└── bus.py        # AgentEventBus (In-memory async pub/sub, SSE formatter)
```

---

## 2. Event Bus Architecture

The [`AgentEventBus`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-7/backend/app/streaming/bus.py#L22) is an in-memory asynchronous publish-subscribe engine:
* **Subscribers:** Clients subscribe per `close_run_id` via `GET /api/close-runs/{id}/stream`. Each connection holds an `asyncio.Queue`.
* **Publishers:** Any backend service (Close Controller, Investigation Agent, Action Service) publishes events using `await agent_event_bus.publish(close_run_id, payload)`.
* **Decoupling:** Publishing is non-blocking. If no clients are connected, events are silently dropped without affecting database transactions.
* **SSE Formatting:** The helper `format_sse(data, event)` serializes payloads into standard SSE text frames:
  ```text
  event: close_run_state_change
  data: {"close_run_id":"c1f7a4e0...","previous_status":"INGESTING","new_status":"RECONCILING","version":2}

  ```

---

## 3. Streaming Event Taxonomy

| Event Name | Producer | Payload Highlights | Description |
| :--- | :--- | :--- | :--- |
| **`close_run_state_change`** | State Machine | `previous_status`, `new_status`, `version` | Notifies frontend of CloseRun transitions. |
| **`close_task_state_change`** | State Machine | `task_id`, `task_type`, `status`, `summary` | Notifies frontend of task starts/completions. |
| **`agent_step`** | Investigation Agent | `step_number`, `tool_name`, `status`, `latency_ms` | Streams granular reasoning steps in real-time. |
| **`actions_executed`** | Action Service | `exception_id`, `actions_count`, `actions` | Broadcasts autonomous or approved actions. |
| **`heartbeat`** | Event Bus | `timestamp`, `alive` | Keep-alive packet emitted every 15s to prevent proxy timeouts. |

---

## 4. Replay Compatibility

The SSE bus interface is identical in both `LIVE` and `REPLAY` modes. When the system operates in replay mode, [`TracePlayer`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-7/backend/app/demo/trace_player.py) emits stored events through the exact same SSE formatting, enabling frontend dashboards to render real-time animations with 100% demo consistency.
