# Agent Runs API Reference

Endpoints for inspecting autonomous agent runs and granular execution step telemetry. Router: [`backend/app/api/routes/agent_runs.py`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-7/backend/app/api/routes/agent_runs.py).

---

## Endpoints

### 1. Get Agent Run
`GET /api/agent-runs/{id}`
* **Description:** Retrieves metadata, duration, model, prompt version, and status for a specific agent run.
* **Response:** [`AgentRunRead`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-7/backend/app/domain/schemas.py).

### 2. Get Agent Steps
`GET /api/agent-runs/{id}/steps`
* **Description:** Retrieves the chronological sequence of granular reasoning and tool execution steps logged by the agent.
* **Response:** Array of `AgentStepRead`.
* **Example Item:**
  ```json
  {
    "id": "e932b132-0941-450e-a4b5-555cb5ef4833",
    "agent_run_id": "8f56e6d1-12c8-4796-98ec-923f03b2241e",
    "step_number": 1,
    "step_type": "dossier_inspection",
    "tool_name": "EvidenceDossierBuilder",
    "status": "COMPLETED",
    "latency_ms": 14,
    "citations_valid": true,
    "created_at": "2026-09-06T02:24:00Z"
  }
  ```
