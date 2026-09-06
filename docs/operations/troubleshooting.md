# Troubleshooting Guide

Common issues, root causes, and resolution steps for the Vexa backend.

---

## 1. Database Connection & Setup Issues

### Issue: `asyncpg.exceptions.InvalidCatalogNameError: database "vexa" does not exist`
* **Root Cause:** PostgreSQL database has not been created.
* **Resolution:**
  ```bash
  createdb vexa
  uv run alembic upgrade head
  ```

### Issue: Integration tests fail with `database "vexa_test" does not exist`
* **Root Cause:** The integration test fixture requires an isolated test database.
* **Resolution:**
  ```bash
  createdb vexa_test
  ```

---

## 2. Close Run Concurrency Conflicts

### Issue: `CloseRunError: Concurrent modification; close run state changed elsewhere`
* **Root Cause:** Two processes attempted to start or advance the same close run simultaneously. Vexa's Compare-And-Swap (CAS) state machine blocked the stale update.
* **Resolution:** Re-fetch the close run via `GET /api/close-runs/{id}` to obtain the latest `version` integer before triggering another state transition.

---

## 3. Agent Timeouts & Circuit Breaker Trips

### Issue: Agent run transitions to `TIMED_OUT` or `FAILED`
* **Root Cause:** External model API latency exceeded `VEXA_INVESTIGATION_MAX_SECONDS` (30s) or loop exceeded `VEXA_INVESTIGATION_MAX_STEPS` (15 steps).
* **Resolution:**
  1. Inspect the agent step log via `GET /api/agent-runs/{id}/steps`.
  2. If using an external LLM, verify API key credentials and consider falling back to `VEXA_LLM_PROVIDER="deterministic"` for offline stability.

---

## 4. Port Conflicts

### Issue: `[Errno 48] Address already in use (port 8000)`
* **Root Cause:** An existing Uvicorn or web server instance is running on port 8000.
* **Resolution:**
  ```bash
  lsof -i :8000
  kill -9 <PID>
  # Or start on an alternate port:
  uv run uvicorn app.main:app --port 8001
  ```
