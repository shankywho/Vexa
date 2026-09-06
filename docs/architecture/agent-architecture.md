# Vexa Agent Architecture

Vexa deploys specialized autonomous agents designed around institutional finance workflows. Unlike generic conversational assistants, Vexa agents operate within bounded mathematical and structural constraints.

---

## 1. Core Architectural Axiom

> **"LLMs reason; deterministic code calculates financial truth."**

In Vexa, large language models are treated as qualitative reasoning engines, semantic translators, and hypothesis generators. They are **never** granted authority over:
* **Financial Calculations:** Arithmetic, variances, tax amounts, and ledger balances are computed by deterministic Python routines using fixed-point `Decimal` arithmetic.
* **Transaction Identity:** Entity mapping and record identity are resolved through relational database foreign keys and exact identifier matching.
* **Financial Impact:** Monetary impacts are calculated directly from primary database rows (`Invoice.total`, `Payment.amount`, `PurchaseOrder.total`).
* **Corporate Governance & Policy:** Autonomy thresholds, approval chains, and escalation rules are hardcoded in deterministic policy modules.
* **Money Movement:** The agent system has **zero** capability to disburse funds, trigger ACH/wire transfers, or modify banking credentials.

---

## 2. Agent Catalog & Boundaries

```
                         ┌───────────────────────────────────┐
                         │      Close Workflow Controller    │
                         │    (Orchestrator · Deterministic) │
                         └─────────────────┬─────────────────┘
                                           │
         ┌─────────────────────────────────┼─────────────────────────────────┐
         ▼                                 ▼                                 ▼
┌───────────────────┐            ┌───────────────────┐             ┌───────────────────┐
│ Reconciliation    │            │ Financial Analyst │             │ CFO Investigation │
│ Engine            │            │ Agent             │             │ Agent             │
│ (10-Pass Matcher) │            │ (Variance & Cash) │             │ (Root-Cause RCA)  │
└────────┬──────────┘            └───────────────────┘             └─────────┬─────────┘
         │                                                                   │
         ▼                                                                   ▼
┌───────────────────┐                                              ┌───────────────────┐
│ Financial         │◄─────────────────────────────────────────────┤ Evidence Dossier  │
│ Evidence Graph    │                                              │ Builder           │
└───────────────────┘                                              └─────────┬─────────┘
                                                                             │
                                                                             ▼
                                                                   ┌───────────────────┐
                                                                   │ Citation          │
                                                                   │ Validator         │
                                                                   └─────────┬─────────┘
                                                                             │
                                                                             ▼
                                                                   ┌───────────────────┐
                                                                   │ Independent       │
                                                                   │ Verification      │
                                                                   └─────────┬─────────┘
                                                                             │
                                                                             ▼
                                                                   ┌───────────────────┐
                                                                   │ Action & Reversal │
                                                                   │ Service           │
                                                                   └───────────────────┘
```

### Summary of Agent Specialization

| Agent | Class | Execution Nature | Authority Boundary |
| :--- | :--- | :--- | :--- |
| **Close Controller** | [`CloseWorkflowController`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-7/backend/app/close_workflow/controller.py) | Deterministic DAG Runner | Coordinates task lifecycle and monitors close readiness. |
| **Financial Analyst** | [`FinancialAnalystAgent`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-7/backend/app/analyst/agent.py) | Hybrid (Deterministic Tools) | Generates executive summaries, account variances, and burn rate analyses. |
| **CFO Investigator** | [`CFOInvestigationAgent`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-7/backend/app/investigation/agent.py) | LLM with Fallback | Formulates root-cause hypotheses over bounded evidence dossiers. |
| **Independent Verifier** | [`VerificationAgent`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-7/backend/app/verification/agent.py) | Deterministic Rules Engine | Recalculates variances, verifies evidence, and enforces policy gates. |
| **Action Agent** | [`ActionAgent`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-7/backend/app/action/agent.py) | Deterministic Service | Executes allowed adjustments, stages proposals, and logs audit entries. |

---

## 3. The Bounded Evidence Dossier Pattern

To prevent agents from hallucinating phantom invoices or querying arbitrary customer data, the CFO Investigation Agent is supplied with an **`EvidenceDossier`**:

```python
# app/investigation/types.py
class EvidenceDossier(BaseModel):
    exception_id: uuid.UUID
    company_id: uuid.UUID
    exception_type: ExceptionType
    severity: ExceptionSeverity
    financial_impact: Decimal
    currency: str
    valid_record_ids: set[str]      # Whitelist of primary database IDs
    valid_evidence_ids: set[str]    # Whitelist of typed evidence nodes
    primary_record: dict[str, Any]  # The mismatched record triggering exception
    related_records: list[dict[str, Any]] # Graph-connected records (POs, Receipts, Payments)
    ranked_nodes: list[dict[str, Any]]    # Multi-hop context ranked by PageRank
    graph_edges: list[dict[str, Any]]     # Structural relationships
```

### Operational Rules:
1. **Scope Bounding:** The agent can only reason about records explicitly included in `valid_record_ids` and `valid_evidence_ids`.
2. **Deterministic Pre-assembly:** The dossier is assembled by [`EvidenceDossierBuilder`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-7/backend/app/investigation/dossier_builder.py) prior to invoking the LLM.
3. **Immutability:** The dossier is frozen. The LLM cannot fetch additional database records at runtime.

---

## 4. Citation Hallucination Guard

Every finding generated by the Investigation Agent must pass through [`CitationValidator`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-7/backend/app/investigation/citation_validator.py):
* **Fact Citations:** Every factual assertion must link directly to a `record_id` or `evidence_id`.
* **Inference Citations:** Every logical deduction must reference supporting evidence IDs.
* **Zero Tolerance for Hallucinations:** If any cited identifier does not exist in `dossier.valid_record_ids`, the citation is flagged as hallucinated:
  - Citation accuracy is penalized.
  - Confidence calibrator docks 0.50 points (`HALLUCINATION_PENALTY`).
  - Independent Verification Gate 2 immediately rejects the finding.

---

## 5. Confidence Calibration Engine

LLMs frequently exhibit overconfidence, reporting 99% certainty on incorrect reasoning. Vexa uses empirical confidence calibration ([`ConfidenceCalibrator`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-7/backend/app/investigation/calibration.py)):

$$C_{calibrated} = \text{BucketLookup}(C_{raw}) - \Delta_{uncertainty} - \Delta_{missing} - \Delta_{citation}$$

* **Empirical Buckets:** Mapped from empirical accuracy against the 35 injected ground-truth scenarios:
  - Raw $[0.95 - 1.00] \rightarrow 0.9800$
  - Raw $[0.90 - 0.95] \rightarrow 0.9200$
  - Raw $[0.80 - 0.90] \rightarrow 0.8400$
  - Raw $[0.70 - 0.80] \rightarrow 0.7300$
  - Raw $[0.60 - 0.70] \rightarrow 0.6100$
  - Raw $[0.50 - 0.60] \rightarrow 0.5000$
  - Raw $[0.00 - 0.50] \rightarrow 0.3500$
* **Deductions:**
  - `UNCERTAINTY_PENALTY = 0.05` per reported uncertainty.
  - `MISSING_EVIDENCE_PENALTY = 0.10` per missing supporting record.
  - `HALLUCINATION_PENALTY = 0.50` if any citation is fabricated.

Policy decisions (such as auto-resolution) evaluate against **`calibrated_confidence`**, never raw model outputs.

---

## 6. Circuit Breaker & Safety Guarantees

The Investigation Agent is protected by runtime circuit breakers:
* **Maximum Agent Steps:** Capped at 15 steps (`investigation_max_steps`). Exceeding this raises `InvestigationCircuitBreakerTripped(reason="STEP_LIMIT")`.
* **Wall-Clock Timeout:** Capped at 30.0 seconds (`investigation_max_seconds`). Exceeding this raises `InvestigationCircuitBreakerTripped(reason="TIMEOUT")`.
* **Safe Termination:** Tripping the circuit breaker sets `AgentRun.status = FAILED` (or `TIMED_OUT`), records an audit log, emits an SSE failure event, and safely returns execution to the controller. The system never hangs or enters infinite reasoning loops.
