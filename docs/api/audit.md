# Audit API Reference

Endpoints for retrieving immutable SOX audit events and internal control verification trails. Router: [`backend/app/api/routes/audit.py`](../../backend/app/api/routes/audit.py).

---

## Endpoints

### 1. Query Audit Events
`GET /api/audit-events`
* **Description:** Retrieves paginated immutable audit records, with optional filtering by close run, exception, event type, or SOX control ID.
* **Query Parameters:**
  - `close_run_id` (UUID, optional): Filter by close run.
  - `exception_id` (UUID, optional): Filter by exception.
  - `event_type` (string, optional): Filter by category (`EXCEPTION_DECISION`, `APPROVAL`, `REVERSAL`, etc.).
  - `control_id` (string, optional): Filter by SOX control (`AP-03`, `PROC-04`, `BANK-01`, etc.).
  - `limit` (int, default: 100): Page size limit.
  - `offset` (int, default: 0): Page offset.
* **Response:** Array of [`AuditEventRead`](../../backend/app/domain/schemas.py).
* **Example Item:**
  ```json
  {
    "id": "771b0593-ff26-444a-85ba-b0763833b37c",
    "event_type": "EXCEPTION_DECISION",
    "actor": "cfo_investigation_agent",
    "actor_type": "agent",
    "agent_name": "cfo_investigation_agent",
    "control_id": "PROC-04",
    "prompt_version_id": "cfo-investigator-v2",
    "policy_version_id": "policy-v1",
    "decision": "STAGE",
    "reason": "Quantity mismatch of 240 units ($384,000) exceeds materiality cap.",
    "financial_impact": "384000.00",
    "currency": "USD",
    "confidence": "0.9800",
    "calibrated_confidence": "0.9800",
    "created_at": "2026-09-06T02:24:01Z"
  }
  ```
