# Exceptions API Reference

Endpoints for inspecting financial exceptions, retrieving bounded evidence dossiers, executing human approvals, and triggering 1-click reversals. Router: [`backend/app/api/routes/exceptions.py`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-7/backend/app/api/routes/exceptions.py).

---

## Endpoints

### 1. Get Human Correction Statistics
`GET /api/exceptions/corrections/stats`
* **Description:** Retrieves aggregate human review and override statistics overall, by exception type, and by confidence bucket, including advisory tuning candidates.
* **Response:** [`HumanCorrectionStatsRead`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-7/backend/app/domain/schemas.py).

### 2. Get Exception Details
`GET /api/exceptions/{id}`
* **Description:** Retrieves single exception record by ID.
* **Response:** `ExceptionRead`.

### 3. Get Exception Evidence Dossier
`GET /api/exceptions/{id}/evidence`
* **Description:** Retrieves the bounded evidence graph nodes, related transactions, and investigation dossier for this exception.
* **Response:** `ExceptionEvidenceRead`.

### 4. Approve Staged Exception
`POST /api/exceptions/{id}/approve`
* **Description:** Human reviewer approves a staged proposal, executing any pending compensating adjustments and marking the exception `RESOLVED`.
* **Request:**
  ```json
  {
    "actor": "sarah_controller",
    "notes": "Verified with vendor account manager; quantity discrepancy confirmed."
  }
  ```
* **Response:** `ActionResponse`.

### 5. Reject Exception Proposal
`POST /api/exceptions/{id}/reject`
* **Description:** Human reviewer rejects an autonomous or staged proposal.
* **Request:** `ActionRequest`.
* **Response:** `ActionResponse`.

### 6. Escalate Exception
`POST /api/exceptions/{id}/escalate`
* **Description:** Formally routes an exception to executive management (CFO or Audit Committee).
* **Request:** `ActionRequest`.
* **Response:** `ActionResponse`.

### 7. Resolve Exception Directly
`POST /api/exceptions/{id}/resolve`
* **Description:** Manually marks an exception as resolved.
* **Request:** `ActionRequest`.
* **Response:** `ActionResponse`.

### 8. Reverse Executed Action (Rollback)
`POST /api/exceptions/{id}/reverse`
* **Description:** 1-click rollback of a previously executed or approved action. Voids staged payloads, reopens the exception to `REOPENED`, and emits dual audit events.
* **Request:**
  ```json
  {
    "action_id": "4b684cfa-2bb0-4d40-9a3c-b17a1262d984",
    "reason": "Debit memo was applied to wrong vendor subsidiary.",
    "actor": "cfo_alex"
  }
  ```
* **Response:** `ActionResponse`.
