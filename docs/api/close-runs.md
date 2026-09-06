# Close Runs API Reference

Endpoints for initiating, monitoring, and streaming month-end close runs. Router: [`backend/app/api/routes/close_runs.py`](../../backend/app/api/routes/close_runs.py).

---

## Endpoints

### 1. Create Close Run
`POST /api/close-runs` (Status: `201 Created`)
* **Description:** Initializes a new month-end close run in `CREATED` state.
* **Request:**
  ```json
  {
    "company_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "period_start": "2026-08-01",
    "period_end": "2026-08-31"
  }
  ```
* **Response:** [`CloseRunRead`](../../backend/app/domain/schemas.py).

### 2. List Close Runs
`GET /api/close-runs`
* **Description:** Lists all close runs for the current tenant company.
* **Response:** Array of `CloseRunRead`.

### 3. Get Close Run
`GET /api/close-runs/{id}`
* **Description:** Retrieves details and current lifecycle status for a specific close run.
* **Response:** `CloseRunRead`.

### 4. Start Close Run
`POST /api/close-runs/{id}/start`
* **Description:** Kicks off the autonomous close workflow DAG (transitions `CREATED -> INGESTING -> RECONCILING -> ...`).
* **Response:** `CloseRunRead` (status: `INGESTING` or `RECONCILING`).

### 5. Get Close Tasks
`GET /api/close-runs/{id}/tasks`
* **Description:** Retrieves the status and summaries of all 10 close DAG tasks.
* **Response:** Array of `CloseTaskRead`.

### 6. Get Close Exceptions
`GET /api/close-runs/{id}/exceptions`
* **Description:** Lists all exceptions detected during this close run.
* **Response:** Array of `ExceptionRead`.

### 7. Download Close Package
`GET /api/close-runs/{id}/package`
* **Description:** Compiles and downloads the sealed, audited close package JSON artifact.
* **Response:** `ClosePackageRead`.

### 8. Get Close Audit Trail
`GET /api/close-runs/{id}/audit`
* **Description:** Retrieves all immutable audit events tied to this close run.
* **Response:** Array of `AuditEventRead`.

### 9. Stream Close Run Telemetry (SSE)
`GET /api/close-runs/{id}/stream`
* **Description:** Real-time Server-Sent Events stream delivering live task updates, agent reasoning steps, and state transitions.
* **Headers:** `Content-Type: text/event-stream`.
* **Example Event:**
  ```text
  event: close_run_state_change
  data: {"close_run_id":"c1f7a4e0...","previous_status":"INGESTING","new_status":"RECONCILING","version":2}
  ```
