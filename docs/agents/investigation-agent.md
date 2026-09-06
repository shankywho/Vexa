# CFO Investigation Agent Specification

The CFO Investigation Agent investigates exceptions discovered during reconciliation, identifies root causes, and recommends corrective actions within mathematically bounded dossiers.

---

## 1. Responsibilities & Boundaries

* **Primary Function:** Reason over financial relationships, trace anomalies to root causes, cite verified records, and formulate structured findings.
* **Bounded Input:** Bounded `EvidenceDossier` containing graph neighbors and whitelisted IDs.
* **Output Contract:** Validated [`InvestigationFinding`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-7/backend/app/investigation/types.py#L76).
* **Strict Authority Boundaries:**
  - Cannot query arbitrary SQL tables.
  - Cannot calculate official ledger balances.
  - Cannot approve or disburse payments.

---

## 2. Tools & Investigation Flow

The agent operates across structured steps logged to PostgreSQL table `agent_steps`:

```
Step 1: Dossier Inspection & Whitelist Verification
          │
          ▼
Step 2: Causal Traversal across Graph Edges
          │
          ▼
Step 3: Root-Cause Formulation & Fact Citation
          │
          ▼
Step 4: Citation Validation (Hallucination Detection)
          │
          ▼
Step 5: Confidence Calibration & Audit Trail Emission
```

---

## 3. Circuit Breaker Limits

* **Max Steps:** `15` steps (raises `InvestigationCircuitBreakerTripped(reason="STEP_LIMIT")`).
* **Max Wall-Clock Time:** `30.0s` (raises `InvestigationCircuitBreakerTripped(reason="TIMEOUT")`).
* **Failure State:** Sets `AgentRun.status = FAILED` or `TIMED_OUT`, logs `AuditEventType.AGENT_RUN_COMPLETED`, and publishes an SSE failure event.

---

## 4. Relevant Tests

* Unit Tests: [`tests/unit/test_investigation_calibration.py`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-7/backend/tests/unit/test_investigation_calibration.py), [`tests/unit/test_investigation_citation_validator.py`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-7/backend/tests/unit/test_investigation_citation_validator.py), [`tests/unit/test_investigation_timeout_and_fallback.py`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-7/backend/tests/unit/test_investigation_timeout_and_fallback.py).
* Integration Tests: [`tests/integration/test_investigation_agent_flow.py`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-7/backend/tests/integration/test_investigation_agent_flow.py), [`tests/integration/test_investigation_ground_truth.py`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-7/backend/tests/integration/test_investigation_ground_truth.py).
