# ClosePilot — Backend Context (v2, Refined)
## Autonomous Month-End Close | Syndicate Track 2

> **Purpose:** This file is the single source of truth an autonomous coding agent or any team member should read before building, modifying, or extending ClosePilot. It supersedes the v1 context file — it keeps the original architecture and adds the fixes required to make the system demo-safe, benchmarkable, and judge-ready: model/latency policy, replay/recording mode, unified benchmark dataset, calibrated confidence, versioned audit trail, rollback path, and live agent-activity streaming.

---

## 0. Executive Summary

**ClosePilot** is an evidence-first autonomous finance operations system for **month-end close**.

The goal is not a generic "AI CFO" chatbot, invoice OCR tool, dashboard, or fraud detector. The goal is to automate a real internal finance workflow end-to-end:

```text
Financial data → Understand financial state → Reconcile → Detect exceptions
→ Investigate root cause → Verify evidence + calculations → Decide autonomy level
→ Auto-resolve OR escalate to human → Record audit trail → Generate close package
→ Mark close ready / blocked
```

### Core product statement

> **ClosePilot autonomously reconciles a company's financial records, investigates exceptions across a financial evidence graph, resolves safe cases, escalates risky/ambiguous decisions, and produces an evidence-backed close package — with every decision reproducible, either live or from a recorded trace.**

### Core positioning

**Investigate. Verify. Close.**

---

## 1. Problem Statement

ClosePilot targets **Syndicate / Maximor Track 2 — Autonomous Office of the CFO**.

Scope: bank reconciliation, AP reconciliation, AR reconciliation, invoice/PO/receipt reconciliation, payment-to-invoice matching, ledger reconciliation, variance analysis, accrual candidates, anomaly/exception detection, exception investigation, human approval/escalation, close readiness, audit evidence, close package generation.

Do **not** expand into consumer banking, trading, lending, or a payment product.

---

## 2. What We Are NOT Building

- generic AI CFO chatbot / "chat with your financial data"
- invoice OCR only, or invoice→PO matching only
- expense tracker, generic dashboard, standalone fraud detector
- autonomous money movement, tax filing system, complete ERP
- full GAAP accounting engine, real banking integrations
- dozens of superficial agents

Fraud/anomaly detection is one exception category, not the product.

---

## 3. Core Technical Thesis

Not "can an LLM understand an invoice?" but:

> **Can an autonomous system find the right financial evidence, connect related records, determine root cause, reproduce the calculation, make the correct decision, know when it must stop for a human — and do all of this reproducibly enough to demonstrate live or from a trace?**

```text
Evidence-first + Deterministic finance engine + Agentic investigation
+ Independent verification + Controlled autonomy + Calibrated confidence
+ Auditability + Reproducibility
```

The LLM must never be the sole source of truth for arithmetic, balances, permissions, financial state transitions, or tenant identity.

---

## 4. High-Level Backend Architecture

```text
                         ┌──────────────────────┐
                         │   API / Close Run     │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │  CLOSE CONTROLLER    │
                         │       AGENT          │
                         └──────────┬───────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              ▼                     ▼                     ▼
       RECONCILIATION           FINANCIAL             INVESTIGATION
           AGENT                 ANALYST                 AGENT
              │                     │                     │
              └─────────────────────┼─────────────────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ FINANCIAL STATE /    │
                         │   EVIDENCE GRAPH      │
                         └──────────┬───────────┘
                                    │
                     ┌──────────────┼──────────────┐
                     ▼              ▼              ▼
                  INVOICES          PO           RECEIPTS
                     │              │              │
                     └──────────────┼──────────────┘
                                    │
                     ┌──────────────┼──────────────┐
                     ▼              ▼              ▼
                  PAYMENTS         BANK            GL
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ VERIFICATION AGENT    │
                         │ (uses calibrated      │
                         │  confidence table)    │
                         └──────────┬───────────┘
                                    │
                         ┌──────────┴──────────┐
                         ▼                     ▼
                    SAFE ACTION           ESCALATION
                         │                     │
                         ▼                     ▼
                    ACTION AGENT            HUMAN
                         │                     │
                         └──────────┬──────────┘
                                    ▼
                       AUDIT TRAIL (versioned) / STATE
                                    │
                         ┌──────────┴──────────┐
                         ▼                     ▼
                  SSE AGENT-STEP           CLOSE PACKAGE
                     STREAM
                         │
                         ▼
              LIVE/REPLAY DEMO LAYER
              (records + replays traces)
```

---

## 5. Backend Components

### 5.1 API Layer
Python, FastAPI, Pydantic, async endpoints where useful.

Responsibilities: create/list close runs, start a close, retrieve close status, retrieve exceptions + evidence, approve/reject/escalate exceptions, inspect agent runs, retrieve audit events, retrieve benchmark results, stream live agent activity.

The API must never allow arbitrary financial mutations, and every mutating call must be idempotent (Section 31).

### 5.2 Model & Latency Policy (NEW — lock this before agent work starts)

- **Primary model:** decide and record here once chosen; do not leave implicit in code.
- **Fallback provider/model:** required — if the primary model errors or times out, fall back automatically rather than failing the step.
- **Per-call timeout:** every agent tool call/LLM call has a hard timeout. On timeout → the step is marked `FAILED` or `WAITING_FOR_RETRY` (never silently skipped, see Section 32).
- **Per-close-run latency budget:** track expected latency for a full close run (30+ exceptions × up to 6 agents). Anything expected to exceed a live-demo-friendly window should be pre-computed and served via the replay layer (Section 37), not run live under time pressure.
- **Cost/token metadata** captured per call for benchmark reporting (Section 25/26).

### 5.3 Database
PostgreSQL. Relational tables are the source of financial truth. The LLM's conversational memory is never financial state.

Suggested core tables:

```text
companies, users, roles
close_runs, close_tasks

vendors, customers

invoices, invoice_lines
purchase_orders, purchase_order_lines
goods_receipts, goods_receipt_lines

payments
bank_accounts, bank_transactions

ledger_accounts
journal_entries, journal_entry_lines

expense_reports, contracts

fx_rates                         -- NEW

reconciliation_results, reconciliation_matches

exceptions, exception_evidence, exception_actions

agent_runs, agent_steps, tool_calls

policies, policy_versions        -- NEW (versioned)
agent_prompt_versions            -- NEW

approval_requests
reversal_actions                 -- NEW (rollback trail)

audit_events

benchmark_scenarios, benchmark_runs, benchmark_results

demo_traces                      -- NEW (recorded replay fixtures)
```

---

## 6. Financial Data Model

(Unchanged from v1 for Vendor, Customer, Invoice, Invoice Line, Purchase Order, Goods Receipt, Payment, Bank Transaction, Journal Entry, Journal Entry Line — see field lists below.)

```text
Vendor: id, company_id, name, tax_id, status, bank_account_id, risk_metadata, created_at
Customer: id, company_id, name, status, created_at
Invoice: id, company_id, vendor_id, invoice_number, invoice_date, due_date, currency, subtotal, tax, total, status, source_document_id, created_at
Invoice Line: id, invoice_id, description, quantity, unit_price, amount, po_line_id
Purchase Order: id, company_id, vendor_id, po_number, order_date, currency, total, status
Goods Receipt: id, company_id, po_id, receipt_number, receipt_date, status
Payment: id, company_id, vendor_id, invoice_id, bank_account_id, amount, currency, payment_date, beneficiary_reference, status
Bank Transaction: id, company_id, bank_account_id, transaction_date, amount, currency, direction, counterparty, reference, status
Journal Entry: id, company_id, entry_date, description, reference, status, source
Journal Entry Line: id, journal_entry_id, ledger_account_id, debit, credit, description
```

### 6.1 FX Rate Table (NEW)

```text
fx_rates:
  id
  base_currency
  quote_currency
  rate
  effective_date
  source
```

Rule: any comparison, reconciliation, or aggregation involving records in different currencies **must** resolve through `fx_rates` via a deterministic tool (`convert_amount()`), never via an LLM estimating an exchange rate. If a required rate is missing for the effective date, the reconciliation returns `MISSING` status, not a guessed value.

All monetary amounts use decimal-safe representations. Never floating-point arithmetic for accounting calculations.

---

## 7. Financial Evidence Graph

Implemented on PostgreSQL relationship tables for MVP — no dedicated graph database required.

**Core node types:** COMPANY, VENDOR, CUSTOMER, INVOICE, INVOICE_LINE, PURCHASE_ORDER, PO_LINE, GOODS_RECEIPT, RECEIPT_LINE, PAYMENT, BANK_ACCOUNT, BANK_TRANSACTION, LEDGER_ACCOUNT, JOURNAL_ENTRY, EXPENSE, CONTRACT, EXCEPTION.

**Core relationships:**
```text
VENDOR ──issued──> INVOICE
INVOICE ──references──> PO
INVOICE ──contains──> INVOICE_LINE
PO ──contains──> PO_LINE
PO ──fulfilled_by──> GOODS_RECEIPT
GOODS_RECEIPT ──contains──> RECEIPT_LINE
INVOICE ──paid_by──> PAYMENT
PAYMENT ──appears_as──> BANK_TRANSACTION
BANK_TRANSACTION ──mapped_to──> JOURNAL_ENTRY
JOURNAL_ENTRY ──posts_to──> LEDGER_ACCOUNT
EXCEPTION ──supported_by──> EVIDENCE
```

The graph answers: *"What financial records explain this event?"* and *"What evidence is causally/operationally related to this exception?"*

---

## 8. Reconciliation Engine

Primarily deterministic: invoice↔PO, invoice↔receipt, invoice↔payment, bank↔ledger, AR↔customer, AP↔vendor.

Structured output contract:

```json
{
  "status": "MATCHED | PARTIAL | MISMATCH | MISSING",
  "confidence": 0.0,
  "matched_records": [],
  "mismatches": [],
  "financial_impact": "0.00",
  "evidence_ids": [],
  "fx_conversion_applied": false
}
```

Configurable tolerances: quantity, amount, date, currency rules (via `fx_rates`), duplicate rules, vendor matching rules.

Never let an LLM decide whether `1000 + 200 = 1200`.

---

## 9. Exception Engine

Every mismatch/anomaly becomes an `Exception`.

Fields: `id, company_id, close_run_id, type, severity, status, financial_impact, confidence, calibrated_confidence, root_cause, recommended_action, autonomy_level, created_at, resolved_at, assigned_to`.

**Exception types:** DUPLICATE_INVOICE, PO_MISMATCH, RECEIPT_MISMATCH, PAYMENT_MISMATCH, BANK_GL_MISMATCH, MISSING_DOCUMENT, DUPLICATE_PAYMENT, UNUSUAL_VENDOR_ACTIVITY, PAYMENT_FRAGMENTATION, AR_MISMATCH, ACCRUAL_ANOMALY, GL_MAPPING_ERROR, CASH_ANOMALY, OTHER.

Note the added `calibrated_confidence` field — see Section 12.1.

---

## 10. Agent Architecture

Small number of meaningful agents. Every agent call is wrapped by the Section 5.2 timeout/fallback policy and structured output (Pydantic).

**Agent 1 — Close Controller:** create close plan, schedule/execute tasks, delegate to specialists, monitor state, determine blockers, trigger verification, determine close readiness. Orchestrator, not calculator.

**Agent 2 — Reconciliation Agent:** invoke reconciliation tools, interpret ambiguous matches, create exceptions, request additional evidence, summarize results.
```text
Agent → deterministic reconciliation tool → structured result → Agent interpretation
```

**Agent 3 — Investigation Agent** (most important): retrieve evidence, traverse the financial graph, inspect related records, compare historical behavior, identify root cause, calculate/invoke calculation tools, explain the exception, recommend action.

Tools: `search_evidence()`, `get_invoice()`, `get_purchase_order()`, `get_receipt()`, `get_payment_history()`, `get_vendor_history()`, `get_bank_transactions()`, `get_ledger_entries()`, `traverse_financial_graph()`, `calculate_variance()`, `compare_periods()`, `convert_amount()`, `get_policy()`.

**Agent 4 — Financial Analyst:** variance analysis, cash impact, materiality analysis, accrual candidates, period-over-period changes, close summary. Calculations via deterministic tools.

**Agent 5 — Verification Agent:** independent from Investigation. Input = decision + evidence + calculations + policy. Asks: can the decision be reproduced? Is required evidence present? Are calculations correct? Is the action allowed? Is human review required?

Output:
```json
{
  "verified": true,
  "confidence": 0.96,
  "calibrated_confidence": 0.91,
  "missing_evidence": [],
  "calculation_errors": [],
  "policy_violations": [],
  "recommended_autonomy": "AUTO_RESOLVE"
}
```
A failed verification blocks autonomous execution.

**Agent 6 — Action Agent:** only permitted actions — `create_review_task()`, `draft_vendor_email()`, `stage_journal_entry()`, `mark_exception_resolved()`, `mark_exception_escalated()`, `generate_close_package()`. No autonomous money movement. Actions idempotent.

---

## 11. Controlled Autonomy

Based on evidence, **calibrated** confidence, materiality, and policy.

- **Level 0 — Observe:** identifies an issue, takes no action.
- **Level 1 — Recommend:** proposes an action.
- **Level 2 — Stage:** prepares the action, requires approval.
- **Level 3 — Execute:** executes a safe, policy-approved action.

Decision inputs: calibrated confidence, financial impact, evidence completeness, policy, exception type, historical consistency, verification result.

```text
LOW RISK + HIGH CALIBRATED CONFIDENCE + COMPLETE EVIDENCE → AUTO RESOLVE
MEDIUM RISK / AMBIGUITY → HUMAN REVIEW
HIGH IMPACT / INSUFFICIENT EVIDENCE / POLICY CONFLICT → CFO ESCALATION
```

Human review is a core product capability, not a fallback.

---

## 12. Policy Engine

Data/configuration-driven, fully deterministic — never embedded in prompts.

```json
{
  "max_auto_resolution_amount": "50000.00",
  "min_confidence": 0.95,
  "high_impact_requires_human": true,
  "money_movement_allowed": false
}
```

Config fields: `max_auto_resolution_amount`, `required_confidence`, `required_evidence_types`, `allowed_auto_actions`, `materiality_threshold`, `approval_roles`, vendor-specific rules, close-blocking exception types.

### 12.1 Confidence Calibration (NEW)

LLM self-reported confidence is not treated as a true probability. Build a calibration step:

1. Run all agents against the ground-truth injected exceptions (Section 21).
2. Bucket reported confidence (e.g., 0.5–0.6, 0.6–0.7, ... 0.9–1.0).
3. Compute **actual accuracy per bucket** against ground truth.
4. Store this mapping (`confidence_calibration` table or config) and apply it to produce `calibrated_confidence` on every exception/verification output.
5. The policy engine's `min_confidence` threshold is evaluated against **calibrated_confidence**, not the raw LLM value.

Document this explicitly — it is the answer to "how do you know 0.95 actually means 95% correct?"

---

## 13. Audit Trail (Versioned)

Every important decision is auditable and append-only.

Record: who/what acted, agent, **agent_prompt_version_id**, **policy_version_id**, timestamp, input references, evidence IDs, tool calls, calculations, decision, raw confidence, calibrated confidence, action, approval, result.

```json
{
  "event_type": "EXCEPTION_DECISION",
  "exception_id": "EX-042",
  "agent": "investigator",
  "agent_prompt_version_id": "investigator-v3",
  "policy_version_id": "policy-v2",
  "evidence_ids": ["INV-821", "PO-4421", "GR-8831"],
  "decision": "ESCALATE",
  "reason": "Invoice quantity exceeds received quantity",
  "financial_impact": "384000.00",
  "confidence": 0.97,
  "calibrated_confidence": 0.90
}
```

### 13.1 Versioning (NEW)

`policy_versions` and `agent_prompt_versions` tables store every deployed policy config and agent prompt/config, each with an incrementing version ID and timestamp. Every audit event references a specific version ID — never a bare name string. This makes every historical decision fully reproducible against the exact policy/prompt that produced it.

### 13.2 Rollback / Reversal Path (NEW)

If a human approver reverses a staged or executed action **after** the fact:

- Create a `reversal_actions` record linked to the original `exception_actions` row (never delete or mutate the original).
- Re-open the associated exception (`status → REOPENED`).
- Write two audit events: the original decision (already recorded) and the reversal, both timestamped and versioned.
- If the reversed action had downstream effects (e.g., a staged journal entry), the reversal must explicitly unstage/void it through the same idempotent action tools, not a direct DB edit.

---

## 14. Close Run State Machine

```text
CREATED → INGESTING → RECONCILING → INVESTIGATING → VERIFYING
→ WAITING_FOR_HUMAN → RESOLVING → FINAL_VERIFICATION → READY_TO_CLOSE → CLOSED
```
Failure state: `FAILED`. Blocked state: `BLOCKED` (material unresolved exceptions).

### 14.1 Concurrency Control (NEW)

`close_runs` carries a `version` integer column. Every state transition is a compare-and-swap (`UPDATE ... WHERE id = ? AND version = ? SET status = ?, version = version + 1`), or uses a Postgres advisory lock keyed on `close_run_id` for the duration of the transition. Two simultaneous "start" triggers must result in exactly one successful transition and one rejected/no-op — never a corrupted or duplicated state.

---

## 15. Close Tasks

```text
BANK_RECONCILIATION, AP_RECONCILIATION, AR_RECONCILIATION, INVOICE_VALIDATION,
PAYMENT_RECONCILIATION, VARIANCE_ANALYSIS, ACCRUAL_REVIEW, EXCEPTION_REVIEW,
FINAL_VERIFICATION, CLOSE_PACKAGE
```

---

## 16. Tools / Service Layer

Agents interact with typed backend tools, never the database directly.

```text
start_close_run(), get_close_status()
list_open_close_tasks(), complete_close_task()
get_invoice(), get_invoice_lines(), get_purchase_order(), get_receipt(),
get_payment(), get_bank_transaction(), get_ledger_entry()
reconcile_invoice_to_po(), reconcile_invoice_to_receipt(),
reconcile_invoice_to_payment(), reconcile_bank_to_ledger()
search_evidence(), traverse_financial_graph(), get_vendor_history(), get_customer_history()
calculate_variance(), calculate_financial_impact(), compare_periods(), convert_amount()
create_exception(), update_exception()
get_policy(), evaluate_autonomy(), calibrate_confidence()
create_review_request(), approve_exception(), reject_exception(), escalate_exception()
reverse_action()                      -- NEW
stage_action(), execute_safe_action()
write_audit_event(), generate_close_package()
```

All tools need strict schemas and authorization.

---

## 17. API Surface

```text
POST   /api/companies
GET    /api/companies/{id}

POST   /api/close-runs
GET    /api/close-runs
GET    /api/close-runs/{id}
POST   /api/close-runs/{id}/start

GET    /api/close-runs/{id}/tasks
GET    /api/close-runs/{id}/exceptions
GET    /api/close-runs/{id}/stream          -- NEW: SSE live agent-step feed

GET    /api/exceptions/{id}
GET    /api/exceptions/{id}/evidence
POST   /api/exceptions/{id}/approve
POST   /api/exceptions/{id}/reject
POST   /api/exceptions/{id}/escalate
POST   /api/exceptions/{id}/resolve
POST   /api/exceptions/{id}/reverse         -- NEW: rollback path

GET    /api/agent-runs/{id}
GET    /api/agent-runs/{id}/steps

GET    /api/audit-events
GET    /api/close-runs/{id}/audit

GET    /api/benchmarks
POST   /api/benchmarks/run
GET    /api/benchmarks/{id}
GET    /api/benchmarks/calibration          -- NEW: confidence calibration report

GET    /api/close-runs/{id}/package

POST   /api/demo/mode                        -- NEW: toggle LIVE / REPLAY
GET    /api/demo/traces/{id}                 -- NEW: fetch a recorded trace
```

Use consistent error schemas.

---

## 18. LLM Responsibilities

Appropriate for: document interpretation, classification, ambiguous matching, root-cause reasoning, exception explanation, prioritization, natural-language summaries, drafting communications.

Never authoritative for: arithmetic, balances, ledger totals, policy thresholds, permissions, money amounts, state transitions, approval rules, FX conversion, tenant identity.

Model, fallback, and timeout policy: see Section 5.2. Use structured output / Pydantic models for every agent decision.

---

## 19. Retrieval Strategy

Layered: 1) exact ID/reference lookup → 2) relational filtering → 3) graph traversal → 4) historical lookup → 5) semantic retrieval only where useful. Do not blindly embed every financial record and search a vector database — financial identifiers, amounts, dates, and relationships are better handled through deterministic queries. Always preserve source IDs.

---

## 20. Synthetic Company Dataset

Fictional company: **NovaScale AI**. ~3 months of financial history.

```text
3 bank accounts, 42 vendors, 18 customers, 12 employees
1,500 bank transactions, 450 invoices, 410 purchase orders,
390 receipts, 600 ledger entries, 80 expense reports
```

Create known ground truth. Include at least two currency pairs in the dataset so `fx_rates` and `convert_amount()` are actually exercised, not just defined.

---

## 21. Injected Exceptions (Also the CFO-Bench Ground Truth — see Section 25)

Deliberately create ~30–35 known scenarios, injected into the same NovaScale AI dataset built in Phase 1:

```text
5 duplicate invoices        4 PO mismatches
3 receipt mismatches        4 duplicate payments
3 unusual vendor activity   2 payment fragmentation patterns
3 missing documents         3 incorrect GL mappings
2 incorrect accruals        2 AR mismatches
2 cash anomalies
```

The agent must not know where the injected issues are. Maintain a private ground-truth mapping (`ground_truth.json`) for evaluation — this single mapping is used both for the live demo scenarios (Sections 22–24) and as the CFO-Bench scenario set (Section 25). There is no separate benchmark dataset to build.

---

## 22. Critical Demo Scenario — Payment Fragmentation

```text
Invoice: ₹14,50,000   PO: ₹14,50,000   Receipt: ₹14,50,000
Payments: ₹1,00,000 × 14, same vendor, same beneficiary,
          same invoice/reference, same settlement window
```

Correct reasoning: underlying invoice/procurement records reconcile; payment pattern is anomalous; evidence is insufficient to classify fraud; policy/risk requires human review.

```text
Decision: ESCALATE
Reason: payment fragmentation anomaly
Evidence: 14 related transactions
Financial impact: ₹14,50,000
```

## 23. Second Demo Scenario — Quantity Mismatch

Invoice: 1,000 units × ₹1,600 = ₹16,00,000. PO: 800 units. Receipt: 760 units.
Agent computes (via deterministic tool): 240 unit difference × ₹1,600 = ₹3,84,000.
Expected action: **HUMAN REVIEW / REQUEST CORRECTED INVOICE**.

## 24. Third Demo Scenario — Clean Transaction

Invoice✓ PO✓ Receipt✓ Payment✓ Bank✓ GL✓ → **AUTO RESOLVE**. Proves ClosePilot reduces human workload, not just finds problems.

All three scenarios must have a recorded fallback trace per Section 37.

---

## 25. CFO-Bench (Unified Dataset)

Built directly from the Section 21 ground truth — **not** a separate 50-scenario dataset. Each of the ~30–35 injected exceptions becomes one scenario:

```json
{
  "expected_root_cause": "...",
  "required_evidence": [],
  "expected_action": "AUTO_RESOLVE | STAGE | ESCALATE | REFUSE",
  "financial_impact": "0.00",
  "human_review_required": true
}
```

### Metrics
evidence retrieval accuracy, root-cause accuracy, financial calculation accuracy, action correctness, escalation correctness, false positive rate, false negative rate, evidence completeness, auditability, latency, cost per case, **confidence calibration error** (Section 12.1).

The most important metric: *Did the agent make the correct finance decision with the correct evidence and correct autonomy level?*

Run the full benchmark **before** judging and store results — never compute all 30+ scenarios live under judges' time pressure. Offer to re-run a small subset live if asked.

---

## 26. Benchmark Runner

```text
benchmark scenario → create isolated company state → run ClosePilot
→ capture agent trace → compare against ground truth → calculate metrics
→ store BenchmarkResult
```

Never leak ground truth into production agent prompts. Store every benchmark trace so it can also serve as a Section 37 replay fixture if needed.

---

## 27. Observability / Neatlogs

Capture: close run, agent, agent version, prompt/version metadata, tool call, tool arguments, tool result, retrieved evidence, decision, verification, action, latency, token/cost metadata.

A trace reconstructs the full path, e.g.:
```text
Controller → Reconciler → reconcile_invoice_to_po() → MISMATCH
→ Investigator → get_invoice() → get_po() → get_receipt() → calculate_variance()
→ Verifier → ESCALATE
```
Do not store sensitive secrets in traces.

---

## 28. Agent Orchestrator (AO)

Required part of the hackathon workflow — use it as the actual development/orchestration environment, not bolted on at submission time. Backend conceptually exposes: Close Controller, Reconciliation Agent, Investigation Agent, Financial Analyst, Verification Agent, Action Agent. Follow the current AO SDK/API available in the project environment rather than inventing unsupported interfaces. Record meaningful AO development sessions for the submission story.

---

## 29. Security

Implement: authentication, authorization, role-based permissions, company/tenant isolation, tool-level permissions, action allowlists, audit logging, idempotency, input validation, secret management.

Roles: VIEWER (read only), ACCOUNTANT (reconciliation + stage actions), CONTROLLER (approve selected exceptions), CFO (approve material/high-risk decisions, authorize reversals), ADMIN (system configuration).

Never allow an agent to bypass authorization.

---

## 30. Multi-Tenancy

Every financial object carries `company_id`. Never trust a company ID supplied by an agent — tenant context comes from authenticated request context only. Every query touching financial data enforces tenant isolation.

---

## 31. Idempotency

`start_close_run()`, `create_exception()`, `stage_action()`, `approve_exception()`, `resolve_exception()`, `reverse_action()` must be idempotent where appropriate. Never create duplicate financial actions from an agent retry.

---

## 32. Failure Handling

Tolerate: LLM timeout, tool timeout, database failure, malformed model output, missing evidence, conflicting records, verification failure, human approval timeout, duplicate tool call, agent retry, partial close completion.

If an agent fails: **do not** silently mark the task complete. Instead: `FAILED` or `WAITING_FOR_RETRY`, and preserve the trace. On LLM/tool timeout, apply the Section 5.2 fallback provider before surfacing `FAILED`.

---

## 33. Financial Safety Rules

- No autonomous money movement.
- No irreversible financial mutation without explicit authorization — and every mutation must have a defined reversal path (Section 13.2).
- No automatic classification of fraud from weak evidence.
- No LLM-generated accounting number without deterministic verification.
- No close completion while blocking exceptions remain.
- No autonomy decision based on raw, uncalibrated confidence.

A safer system that knows when to stop is preferable to an agent that appears "more autonomous."

---

## 34. Close Readiness

Compute: `close_completion_percentage`, `open_exceptions`, `blocking_exceptions`, `unreviewed_material_items`, `verification_failures`, `pending_approvals`, `financial_impact_at_risk`.

`READY` only if all required close tasks are complete and no blocking exception remains. Otherwise `BLOCKED`.

---

## 35. Close Package

Contains: close summary, reconciliation summary, exception summary, resolved/unresolved exceptions, financial impacts, human approvals, audit events (with version references), verification results, agent execution summary, close readiness, **reversal history**, **calibration summary**.

Generate structured JSON first. PDF/export can follow.

---

## 36. Recommended Repository Structure

```text
backend/
├── app/
│   ├── main.py
│   ├── api/
│   │   ├── routes/ (companies.py, close_runs.py, exceptions.py, agents.py, audit.py, benchmarks.py, demo.py)
│   │   └── dependencies.py
│   ├── agents/ (controller.py, reconciler.py, investigator.py, analyst.py, verifier.py, action.py)
│   ├── tools/ (reconciliation.py, evidence.py, graph.py, calculations.py, fx.py, policies.py, actions.py)
│   ├── domain/ (models/, schemas/, enums/)
│   ├── services/ (close_service.py, exception_service.py, verification_service.py,
│   │              audit_service.py, benchmark_service.py, calibration_service.py, demo_service.py)
│   ├── db/ (models/, migrations/, session.py)
│   ├── evaluation/ (scenarios/, runner.py, metrics.py)
│   ├── data/ (generator.py, seed.py)
│   ├── demo/ (trace_recorder.py, trace_player.py)
│   └── config.py
├── tests/ (unit/, integration/, agent/, evaluation/)
├── scripts/ (seed_demo.py, run_benchmark.py, record_demo_trace.py)
├── alembic.ini
├── pyproject.toml
└── README.md
```

Adapt to any existing repository. Do not rewrite working infrastructure unnecessarily.

---

## 37. Demo Safety Net — Live/Replay Mode (NEW)

The single biggest live-demo risk with non-deterministic agents is visible breakage in front of judges. Mitigate with a first-class replay layer:

- `demo_traces` table stores a full captured trace (inputs, tool calls, outputs, timings) for each golden demo scenario, produced from the best rehearsal run.
- `app/demo/trace_recorder.py` captures a live run into a trace fixture.
- `app/demo/trace_player.py` replays a stored trace at real-time pace through the same API/SSE surface used by live mode, so the frontend cannot tell the difference.
- `POST /api/demo/mode` toggles `LIVE` vs `REPLAY` per close run.
- Decision policy: default to `LIVE` for the actual demo; fall back to `REPLAY` immediately if final rehearsal shows any instability (rate limits, latency spikes, inconsistent reasoning). This decision is made before going on stage, not improvised live.

---

## 38. Testing Strategy

**Unit:** financial calculations, matching, tolerances, FX conversion, policy engine, state transitions, permissions, idempotency.

**Integration:** close run, reconciliation, exception creation, investigation, verification, approval, close readiness, reversal flow, concurrent close-run start.

**Agent:** structured output, tool selection, missing evidence, conflicting evidence, unsafe action, verification rejection.

**Evaluation:** run the full CFO-Bench regression suite after meaningful agent changes; re-check calibration whenever a prompt/policy version changes.

---

## 39. Acceptance Criteria

Backend is MVP-complete when it can:

- **Data:** create a synthetic company, ingest/seed financial records (incl. multi-currency), preserve relationships.
- **Close:** start a month-end close, execute close tasks, track progress/state safely under concurrent triggers.
- **Reconciliation:** reconcile bank↔GL, invoice↔PO, invoice↔receipt, invoice↔payment, across currencies via `fx_rates`.
- **Exceptions:** detect mismatches, create structured exceptions, calculate financial impact, classify severity.
- **Investigation:** retrieve related evidence, traverse relationships, determine root cause, cite source record IDs.
- **Verification:** independently validate decisions, reject unsupported decisions, validate calculations.
- **Autonomy:** auto-resolve safe cases using calibrated confidence, stage medium-risk actions, escalate high-risk/ambiguous cases.
- **Audit:** record every important decision with policy/prompt version references, preserve evidence and trace, record human approval and any reversal.
- **Benchmark:** run the unified CFO-Bench scenario set, calculate accuracy/safety/calibration metrics, compare regressions.
- **Demo safety:** produce and successfully replay at least one recorded trace per golden scenario.
- **Close:** determine READY/BLOCKED, generate a structured close package.

---

## 40. Golden Backend Demo Flow

```text
POST /close-runs → START CLOSE → INGEST/LOAD DATA
→ BANK RECON → AP RECON → AR RECON → INVOICE VALIDATION
→ EXCEPTIONS DETECTED → INVESTIGATION → EVIDENCE GRAPH → ROOT CAUSE
→ DETERMINISTIC CALCULATION → VERIFICATION (calibrated confidence)
→ [AUTO RESOLVED | HUMAN REVIEW | CFO ESCALATION]
→ FINAL VERIFICATION → CLOSE PACKAGE → BLOCKED / READY
```

Target demo numbers are illustrative and should only be reported if the seeded dataset actually produces them. Live vs. replay decided per Section 37.

---

## 41. Engineering Principles

1. Financial truth lives in the database, not in prompts.
2. LLMs reason; deterministic code calculates.
3. Every consequential decision must have evidence.
4. Every autonomous action must pass policy evaluated on **calibrated** confidence.
5. Verification is independent from investigation.
6. Human review is a first-class workflow.
7. Every action must be auditable and reference a specific policy/prompt version.
8. Agents use tools; they do not directly mutate financial state.
9. Retries must be safe and idempotent.
10. Never hide uncertainty — report calibrated confidence, not raw model confidence.
11. Prefer fewer capable agents over many superficial agents.
12. Optimize for measurable finance outcomes, not agent theatrics.
13. Benchmark every important behavior, and pre-compute results before judging.
14. Preserve tenant isolation at every layer.
15. No irreversible financial operation by default — every mutation has a reversal path.
16. Every demo scenario must be reproducible live or via replay.

---

## 42. Competitive Differentiation

Differentiates from generic AI CFOs, invoice extraction agents, AP automation agents, simple reconciliation tools, generic multi-agent finance demos, and financial dashboards through:

```text
FINANCIAL EVIDENCE GRAPH + ROOT-CAUSE INVESTIGATION + INDEPENDENT VERIFICATION
+ CALIBRATED CONTROLLED AUTONOMY + VERSIONED AUDIT TRAIL + CFO-BENCH
+ LIVE/REPLAY DEMO RELIABILITY
```

Not "our AI understands finance" but: **"our agent can make a finance decision, prove it from source evidence, verify it independently, know whether to act or escalate — and we can show you exactly how confident it actually is, with numbers to back it."**

---

## 43. Research-Informed Design Principles

- **FinBalance:** multi-document reconciliation is hard for LLMs; plausible outputs can still fail to bind to evidence. → structured records, deterministic calculations, explicit evidence relationships, independent verification.
- **FinRCA-Bench:** retrieval architecture drives root-cause performance. → exact structured lookup + graph traversal before semantic retrieval.
- **CFAgentBench:** financial agents need explicit action controls. → action staging, approval, policy gates, refusal/escalation.

These are architectural principles, not claims that ClosePilot has achieved any benchmark score.

---

## 44. Backend-Only Scope Boundary

Excludes frontend screens, React components, visual design, CSS, dashboard layout, chat UI, assistant-ui implementation. The backend exposes clean APIs/events (including the SSE agent-step stream, Section 17) so a frontend can consume: close state, tasks, exceptions, evidence, agent activity, verification, approvals, audit events, benchmark results, calibration report, close package.

---

## 45. Definition of "Done"

ClosePilot backend is successful when an independent coding agent (or teammate) can clone the repository, read this document, seed NovaScale AI, start a close run, observe autonomous reconciliation/investigation/verification with calibrated confidence, safely resolve or escalate exceptions, inspect the versioned evidence/audit trail, reverse an approval and see it correctly reflected, run CFO-Bench, and replay a recorded golden demo trace indistinguishably from a live run — all without undocumented assumptions.

### Final mental model

```text
                    CLOSEPILOT
              "Can we close the books?"
                        ↓
                   CONTROLLER
                        ↓
              ┌─────────┴─────────┐
              ↓                   ↓
         RECONCILE             ANALYZE
              ↓                   ↓
              └─────────┬─────────┘
                        ↓
                   EXCEPTIONS
                        ↓
                  INVESTIGATE
                        ↓
                 EVIDENCE GRAPH
                        ↓
              VERIFY (calibrated)
                        ↓
              ┌─────────┴─────────┐
              ↓                   ↓
           SAFE                UNSAFE
              ↓                   ↓
          AUTO ACT             HUMAN
              └─────────┬─────────┘
                        ↓
              AUDIT (versioned, reversible)
                        ↓
                  CLOSE PACKAGE
                        ↓
                READY / BLOCKED

        [ every step recordable → replayable ]
```

---

## One-line instruction to any coding agent

> **Build ClosePilot as an evidence-first autonomous month-end-close backend: deterministic finance engine + financial evidence graph + specialized agents with locked model/timeout policy + independent verification with calibrated confidence + policy-controlled, reversible actions + human escalation + versioned, complete auditability + unified CFO-Bench evaluation + a live/replay demo safety layer.**
