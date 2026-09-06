# Demo API Reference

Endpoints for managing demonstration safety, toggling between LIVE and REPLAY execution, and streaming pre-recorded golden traces. Router: [`backend/app/api/routes/demo.py`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-7/backend/app/api/routes/demo.py).

---

## Endpoints

### 1. Get Current Demo Mode
`GET /api/demo/mode`
* **Description:** Retrieves the active global demo execution mode (`LIVE` or `REPLAY`).
* **Response:** [`DemoModeRead`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-7/backend/app/domain/schemas.py).

### 2. Set Demo Mode
`POST /api/demo/mode`
* **Description:** Updates the demo mode globally or for a specific close run.
* **Request:**
  ```json
  {
    "mode": "REPLAY",
    "close_run_id": null
  }
  ```
* **Response:** `DemoModeRead`.

### 3. List Demo Traces
`GET /api/demo/traces`
* **Description:** Lists all available recorded traces, including golden presentation fixtures.
* **Response:** Array of `DemoTraceRead`.

### 4. Get Demo Trace Details
`GET /api/demo/traces/{id}`
* **Description:** Retrieves trace metadata, event count, and total recorded duration.
* **Response:** `DemoTraceRead`.

### 5. Record Live Close Run to Trace
`POST /api/demo/record` (Status: `201 Created`)
* **Description:** Captures the telemetry, agent steps, and audit logs of an existing close run into a replayable `DemoTrace`.
* **Request:**
  ```json
  {
    "close_run_id": "c1f7a4e0-7982-41b2-bf23-88229bbf9301",
    "scenario_key": "PAYMENT_FRAGMENTATION",
    "title": "Scenario 1: Payment Fragmentation Live Run",
    "description": "Captured rehearsal run for track 2 presentation.",
    "is_golden": true
  }
  ```
* **Response:** `DemoTraceRead`.

### 6. Seed Golden Demo Traces
`POST /api/demo/traces/seed`
* **Description:** Seeds the database with the default golden trace fixtures for Scenarios 1, 2, and 3.
* **Response:** Array of `DemoTraceRead`.

### 7. Stream Trace Playback (SSE)
`GET /api/demo/traces/{id}/stream`
* **Description:** Plays back a captured trace as real-time Server-Sent Events with authentic delays.
* **Headers:** `Content-Type: text/event-stream`.
