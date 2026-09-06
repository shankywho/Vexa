# REST API Overview

The Vexa backend exposes a REST and Server-Sent Events (SSE) surface built with FastAPI.

---

## 1. Base URL & OpenAPI Documentation

* **Base Path:** `/api`
* **Interactive Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
* **ReDoc Specification:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
* **Dynamic OpenAPI JSON:** [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)
* **Static Swagger Specification:** [`docs/api/swagger.json`](./swagger.json) and [`swagger.json`](../../swagger.json)
* **Static OpenAPI Specification:** [`docs/api/openapi.json`](./openapi.json) and [`openapi.json`](../../openapi.json)
* **Export Script:** `python backend/scripts/export_openapi.py` (regenerates static Swagger schemas)

---

## 2. Router Directory

| Endpoint Prefix | Router Module | Description |
| :--- | :--- | :--- |
| **`/api/health`** | [`app.api.routes.health`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/api/routes/health.py) | Liveness probe and database connectivity checks. |
| **`/api/companies`** | [`app.api.routes.companies`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/api/routes/companies.py) | Tenant provisioning and synthetic data seeding triggers. |
| **`/api/close-runs`**| [`app.api.routes.close_runs`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/api/routes/close_runs.py) | Month-end close lifecycle, task inspection, and live SSE stream. |
| **`/api/exceptions`**| [`app.api.routes.exceptions`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/api/routes/exceptions.py) | Exceptions, evidence dossiers, approvals, and 1-click reversals. |
| **`/api/agent-runs`**| [`app.api.routes.agent_runs`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/api/routes/agent_runs.py) | Agent execution history and granular step telemetry. |
| **`/api/audit-events`**| [`app.api.routes.audit`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/api/routes/audit.py) | Immutable SOX audit log queries. |
| **`/api/benchmarks`**| [`app.api.routes.benchmarks`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/api/routes/benchmarks.py) | 35-scenario benchmark execution and calibration reports. |
| **`/api/demo`** | [`app.api.routes.demo`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/api/routes/demo.py) | LIVE vs REPLAY demo mode toggle and trace streaming. |

---

## 3. Standard Error Envelope

Error responses follow standard HTTP status codes with structured detail:
```json
{
  "detail": "Exception 8f56e6d1-12c8-4796-98ec-923f03b2241e not found for company 9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"
}
```
Common HTTP status codes:
* `200 OK` / `201 Created`: Successful request.
* `400 Bad Request`: Domain validation error (e.g. invalid state machine transition).
* `404 Not Found`: Entity does not exist within the tenant boundary.
* `409 Conflict`: Concurrency conflict (CAS version check failed).
* `500 Internal Server Error`: Unhandled server exception.
