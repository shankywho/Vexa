# Vexa System Architecture

This document details the subsystem boundaries, interface contracts, data handoffs, and safety rationales governing the Vexa backend.

---

## 1. Architectural Boundaries Matrix

| Subsystem | Primary Module | Inputs | Outputs | Safety Boundary Rationale |
| :--- | :--- | :--- | :--- | :--- |
| **API Layer** | [`app.api.routes`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/api/routes) | HTTP Requests, JSON payloads, Tenant Auth Context | Pydantic JSON Models, SSE event streams | Validates request inputs; sanitizes errors; enforces tenant boundary; blocks raw DB writes. |
| **Close Workflow** | [`app.close_workflow.controller`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/close_workflow/controller.py) | `close_run_id`, Company context | Task executions, CAS state transitions | Prevents duplicate close runs via Compare-And-Swap (CAS) locking; enforces DAG topological order. |
| **Reconciliation Engine** | [`app.reconciliation.engine`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/reconciliation/engine.py) | Invoices, POs, Receipts, Payments, Bank, GL | `ReconciliationRunSummary`, `ExceptionRecord` rows | 100% deterministic mathematical matching; zero LLM calls; ensures financial arithmetic is unassailable. |
| **Evidence Graph** | [`app.evidence_graph.builder`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/evidence_graph/builder.py) | PostgreSQL relational tables | `FinancialEvidenceGraph`, `EvidenceSubgraph` | Replaces brittle vector search with explicit relational provenance; prevents hallucinated relationships. |
| **Investigation Agent** | [`app.investigation.agent`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/investigation/agent.py) | Bounded `EvidenceDossier`, System Prompts | `InvestigationFinding` (Pydantic) | Agent reasoning is strictly bounded to the dossier; cannot query external tables or mutate state. |
| **LLM Provider** | [`app.investigation.llm_provider`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/investigation/llm_provider.py) | Prompt messages, JSON schemas | Structured JSON strings | Isolates model vendor API; enforces per-call timeouts; provides instant deterministic fallback. |
| **Citation Validation** | [`app.investigation.citation_validator`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/investigation/citation_validator.py) | `InvestigationFinding`, `EvidenceDossier` | `CitationValidationResult` (is_valid, counts) | Fatal verification gate; catches fabricated transaction IDs before findings reach human reviewers. |
| **Verification Engine** | [`app.verification.engine`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/verification/engine.py) | `InvestigationFinding`, Primary records, Policy | `VerificationResult` | Independent double-check; recalculates variances without reading agent claims; prevents confirmation bias. |
| **Confidence Calibration** | [`app.investigation.calibration`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/investigation/calibration.py) | Raw confidence, Uncertainties, Citations | Calibrated Confidence (`Decimal`) | Translates self-reported confidence into empirical probabilities; applies heavy penalties for ambiguities. |
| **Policy Engine** | [`app.verification.engine`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/verification/engine.py) | Finding, Calibrated Confidence, Policy Config | `AutonomyLevel` (`OBSERVE`, `RECOMMEND`, `STAGE`, `EXECUTE`) | Enforces corporate governance; applies materiality caps and relative account thresholds deterministically. |
| **Actions & Reversals** | [`app.action.service`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/action/service.py) | Approved Findings, Human review decisions | `ActionResult`, `ReversalResult` | Enforces **Zero Money Movement**; stages proposals; executes 1-click reversible compensating entries. |
| **Audit Service** | [`app.audit.service`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/audit/service.py) | State transitions, Agent reasoning, Approvals | Immutable `AuditEvent` rows | Append-only institutional record; deterministically maps events to SOX control IDs. |
| **SSE Event Bus** | [`app.streaming.bus`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/streaming/bus.py) | Execution events from agents & controllers | Chunked Server-Sent Events | Non-blocking pub/sub decoupled from database transactions; powers live dashboard telemetry. |
| **Demo & Replay** | [`app.demo.mode`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/demo/mode.py) | `DemoMode` toggle, Recorded `DemoTrace` rows | Real-time SSE stream | Provides 100% demo determinism; shields presentations from LLM rate limits or network dropouts. |
| **Database Repositories**| [`app.db.repository`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/db/repository.py) | Typed parameters + `company_id` | SQLAlchemy model instances | Enforces tenant scoping on every SQL query (`company_id == tenant_id`); eliminates cross-tenant leaks. |

---

## 2. Subsystem Deep Dives & Data Contracts

### 2.1 API Layer & Tenant Resolution
* **Module:** [`backend/app/api/`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/api/)
* **Boundary Rationale:** The API layer provides HTTP serialization, CORS, lifecycle management, and tenant isolation. When requests arrive, [`app/api/dependencies.py`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/api/dependencies.py) resolves the current tenant context. In production, this binds to JWT claims; in development/testing, it defaults to the verified seed company ID.
* **Safety Rules:** The API never exposes raw SQL queries or accepts arbitrary state modifications. Mutating operations (like approvals or reversals) are handled by dedicated service methods that log audit records within the same database transaction.

### 2.2 Close Workflow Controller & Task Orchestrator
* **Module:** [`backend/app/close_workflow/`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/close_workflow/)
* **Boundary Rationale:** Automating a month-end close requires strict sequencing. The [`TaskDependencyResolver`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/close_workflow/dependencies.py) enforces a topological DAG across 10 tasks.
* **State Machine & CAS Concurrency:** State transitions for `CloseRun` and `CloseTask` are governed by [`CloseWorkflowStateMachine`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/close_workflow/state_machine.py). To prevent race conditions from concurrent triggers or parallel workers, every update uses Compare-And-Swap (CAS):
  ```sql
  UPDATE close_runs
  SET status = :new_status, version = version + 1
  WHERE id = :close_run_id AND version = :expected_version AND status = :expected_status
  RETURNING version;
  ```
  If another process modified the close run, the query returns zero rows and raises `CloseRunError`, preserving state integrity.

### 2.3 Deterministic Reconciliation Engine
* **Module:** [`backend/app/reconciliation/`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/reconciliation/)
* **Boundary Rationale:** Financial matching must be reproducible down to the penny. The engine operates across 10 deterministic passes:
  1. Three-Way Matching (Invoices ↔ Purchase Orders ↔ Goods Receipts)
  2. Unbilled Goods Receipts (GRNI Accrual Candidates)
  3. Duplicate Invoice Detection (Vendor ID + Invoice Number)
  4. Payment to Invoice Matching (Overpayments, underpayments, timing variances)
  5. Unusual Vendor Activity (Sudden invoice volume/amount spikes)
  6. Bank Statement Transactions (AR customer short remittances, unrecorded cash)
  7. General Ledger Balance & Mapping (Double-entry balance, account classifications)
  8. Clean Six-Way Match Verification (Verifying perfectly balanced transactions)
  9. Vendor Bank Account Change Anomalies (Detecting changes prior to disbursement)
  10. Data Ingestion Gap Detection (Missing bank dates, GL sequence gaps)
* **Contract:** Produces a [`ReconciliationRunSummary`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/reconciliation/schemas.py) containing structured items and inserts `ExceptionRecord` rows into PostgreSQL.

### 2.4 Evidence Graph & Provenance Layer
* **Module:** [`backend/app/evidence_graph/`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/evidence_graph/)
* **Boundary Rationale:** Traditional RAG vector embeddings lose numerical precision and relational semantics. The [`FinancialEvidenceGraph`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/evidence_graph/graph.py) builds an in-memory directed graph representing real business relationships.
* **Nodes & Edges:** 20 node types (`INVOICE`, `PURCHASE_ORDER`, `BANK_TRANSACTION`, `LEDGER_ACCOUNT`, etc.) and 21 edge types (`REFERENCES_PO`, `PAID_BY_PAYMENT`, `POSTS_TO_LEDGER`, etc.).
* **Relevance Scoring:** When an exception occurs, the [`EvidenceRanker`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/evidence_graph/ranker.py) runs an in-memory personalized PageRank traversal centered on the exception's primary entity, extracting the most relevant 2–4 hop subgraph.

### 2.5 CFO Investigation Agent & Citation Validator
* **Module:** [`backend/app/investigation/`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/investigation/)
* **Boundary Rationale:** The investigation agent reasons over why an exception occurred. To prevent hallucinations and unbounded exploration:
  1. The agent receives an immutable [`EvidenceDossier`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/investigation/types.py) containing strictly bounded record IDs.
  2. The agent outputs a structured [`InvestigationFinding`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/investigation/types.py) with explicit citations for every fact and inference.
  3. The [`CitationValidator`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/investigation/citation_validator.py) checks every cited identifier against the dossier whitelist. If an agent cites a nonexistent ID, it is marked as a hallucination, penalizing the confidence score and blocking autonomous action.
* **Circuit Breaker:** The agent enforces a maximum step limit (default: 15 steps) and wall-clock timeout (default: 30.0s). If exceeded, the [`InvestigationCircuitBreakerTripped`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/investigation/agent.py) exception aborts execution safely and marks the agent run `TIMED_OUT` or `FAILED`.

### 2.6 Independent Verification Engine & Policy Gates
* **Module:** [`backend/app/verification/`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/verification/)
* **Boundary Rationale:** The investigator agent must not verify its own conclusions. The [`VerificationEngine`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/verification/engine.py) applies three deterministic gates:
  * **Gate 1 (Arithmetic Recalculation):** Reads raw entity totals (e.g. invoice total minus PO total) to verify the claimed variance. If the mathematical discrepancy exceeds $0.01, verification fails.
  * **Gate 2 (Completeness Check):** Confirms that all mandatory evidence types (e.g. invoice, PO, receipt) exist in the dossier and no citations are invalid.
  * **Gate 3 (Policy Gate):** Checks corporate governance rules:
    - Materiality threshold (default: $\le \$50,000$).
    - Relative account balance limit (variance as % of account balance).
    - Calibrated confidence threshold ($\ge 0.95$).
    - High-risk escalation rules (vendor bank account changes, cash anomalies, payment fragmentation).

### 2.7 Actions, Reversals & Human Corrections
* **Module:** [`backend/app/action/`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/action/)
* **Boundary Rationale:**
  * **Zero Money Movement:** The action system is strictly prohibited from disbursing funds or initiating bank transfers.
  * **Compensating Actions:** Resolving an exception creates compensating journal entries or stages vendor inquiry drafts.
  * **1-Click Reversals:** If a human reviewer or CFO reverses an action, [`ReversalEngine`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/action/reversal.py) creates an auditable `ReversalAction` row, reopens the exception, unstages draft entries, and records dual audit events without mutating historical rows.
  * **Correction Learning:** [`HumanCorrectionService`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/action/correction_service.py) logs human overrides against agent recommendations, tracking override rates across confidence buckets and identifying advisory policy tuning candidates.

### 2.8 Audit Trail & SOX Control Registry
* **Module:** [`backend/app/audit/`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/audit/)
* **Boundary Rationale:** Financial systems must satisfy external auditors. The [`AuditService`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/audit/service.py) records append-only `AuditEvent` rows containing actor identity, agent name, prompt version, policy version, evidence IDs, and timestamps.
* **Control Mapping:** Every event deterministically maps to a recognized SOX internal control identifier via [`map_to_control_id`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/audit/controls.py):
  - `AP-03`: Duplicate payment & invoice prevention
  - `AP-07`: Vendor master bank account modification review
  - `PROC-04`: 3-way procurement matching
  - `GL-02`: General ledger mapping & balance controls
  - `BANK-01`: Bank reconciliation controls
  - `CLOSE-01`: Period-end close completeness & data ingestion controls
  - `REV-01`: Accounts receivable customer remittance matching
  - `EXP-01`: Accrued liabilities & expense anomaly review

### 2.9 Real-Time Streaming & Demo Safety Net
* **Module:** [`backend/app/streaming/`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/streaming/) & [`backend/app/demo/`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/demo/)
* **Boundary Rationale:** The async [`AgentEventBus`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/streaming/bus.py) broadcasts granular task transitions, agent reasoning steps, and audit logs over HTTP Server-Sent Events (SSE). The [`DemoModeManager`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/demo/mode.py) allows switching between `LIVE` execution and `REPLAY` playback. In replay mode, [`TracePlayer`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/demo/trace_player.py) streams pre-recorded golden traces at authentic intervals, providing absolute demonstration reliability.
