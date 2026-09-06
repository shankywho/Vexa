# Vexa — Frontend Requirements Specification (FRS)
## Autonomous Office of the CFO | Month-End Close Operating System

> **Document Version:** 2.0.0  
> **Status:** Approved for Implementation  
> **Target Application:** Authenticated B2B Enterprise Web Application (Excluding Public Landing/Marketing Page)  
> **Backend Specification Companion:** [`CLOSEPILOT_BACKEND_CONTEXT_V2.md`](./CLOSEPILOT_BACKEND_CONTEXT_V2.md) & [`README.md`](./README.md)  
> **Core Positioning:** *"Investigate. Verify. Close."*

---

## 1. Executive Summary & Design Principles

### 1.1 Scope of this Specification
This document defines the comprehensive frontend requirements, information architecture, routing hierarchy, persona workflows, layout components, and page-by-page screen specifications for the **Vexa** authenticated web platform. 

**Explicit Scope Boundary:** This specification intentionally **excludes** public marketing pages, hero landing sections, public feature pitch decks, and consumer landing experiences. It begins strictly at authenticated application boundaries: workspace/tenant selection, month-end close execution, real-time agent telemetry, forensic investigation, human approvals, SOX audit trails, close package sign-off, CFO-Bench calibration, and the live/replay demo control suite.

### 1.2 Core Product Mission
Vexa is an evidence-first autonomous finance operations platform for enterprise month-end close. Unlike generic AI chatbots or OCR extraction tools, Vexa automates the end-to-end month-end closing cycle with mathematical determinism, graph-based forensic evidence, calibrated confidence ratings, and SOX-compliant human governance:
```text
Financial Records (Invoices, POs, Receipts, Payments, Bank, GL)
     │
     ▼
[ 10-Pass Deterministic Reconciliation ] ──► Detects Variances
     │
     ▼
[ Exception Engine & Financial Evidence Graph ] ──► Assembles Ranked Dossier
     │
     ▼
[ Bounded CFO Investigation Agent ] ──► Root-Cause Forensic Reasoning
     │
     ▼
[ 3-Gate Independent Verification Engine ] ──► Arithmetic & Policy Gate
     │
     ▼
[ Calibrated Confidence & Materiality Gate ]
     │
     ├──► Level 3: AUTO-RESOLVE (Compensating Adjustment, <= $50k)
     ├──► Level 2: STAGE (Controller Review Required)
     ├──► Level 1: RECOMMEND / ESCALATE (CFO Authorization Required)
     └──► Level 0: OBSERVE (Forensic Record Only)
     │
     ▼
[ Real-Time SSE Telemetry & Versioned Audit Trail ]
     │
     ▼
[ Evidence-Backed Close Package (JSON / Certified PDF) ] ──► READY / BLOCKED
```

### 1.3 UI/UX Design Tenets
1. **Forensic Density & Clarity:** High-density financial presentation inspired by institutional trading terminals and modern enterprise developer tools (Stripe, Linear, Bloomberg). Zero visual fluff.
2. **Mathematical Precision & Fixed-Point Decimals:** Accounting numbers are rendered with deterministic precision, tabular numerals (`font-mono`), standard financial parenthetical negatives `(1,240.50)`, and multi-currency symbol support (`USD`, `INR`, `EUR`, `GBP`). Never rely on JavaScript floating-point arithmetic.
3. **Calibrated Confidence Visuals:** The UI must never display raw uncalibrated LLM confidence without distinction. Every AI decision visually couples raw confidence with calibrated confidence (e.g., `97% Raw → 91% Calibrated`), indicating empirical reliability against ground truth.
4. **Non-Destructive Financial Governance:** Every mutating action (compensating entry, vendor contact, approval) shows its reversible status. The UI provides a dedicated SOX-compliant rollback/reversal path for every executed decision.
5. **Real-Time Agent Streaming (SSE):** Streaming telemetry shows the Close Controller and specialized agents executing live tools (`reconcile_bank_to_ledger`, `traverse_financial_graph`, `calculate_variance`) with sub-second progress updates.
6. **Demo Safety Net Transparency:** A persistent, unobtrusive indicator reveals whether the current workspace is running in `LIVE` execution or `REPLAY` trace playback, allowing presenters to demonstrate golden scenarios with zero stage risk.

---

## 2. Role-Based Access Control (RBAC) & Persona Matrix

Vexa enforces strict segregation of duties as mandated by SOX Section 404. The frontend adapts its navigation, action buttons, inspection panels, and authorization gates across five distinct roles:

| Persona / Role | Responsibilities | Key Frontend Permissions & Actions | Restricted Views & Operations |
| :--- | :--- | :--- | :--- |
| **`VIEWER`** | Read-only stakeholder, external financial observer, junior analyst. | Can view Close Runs, tasks, reconciliation tables, exceptions, evidence dossiers, and generated close packages. | Cannot approve, reject, resolve, or reverse exceptions. Cannot start close runs or alter policies. |
| **`ACCOUNTANT`** | Senior Staff Accountant, AP/AR specialist. | Initiates close runs; reviews daily reconciliation grids; investigates exceptions; triggers manual resolution notes; stages Level 2 remedial journal entries. | Cannot approve Level 2 staged actions; cannot authorize Level 1 CFO escalations; cannot execute reversals. |
| **`CONTROLLER`** | Accounting Controller, Accounting Director. | Oversees 10-task close DAG; reviews and approves Level 2 staged actions; rejects invalid proposals; manages variance thresholds and policy settings. | Cannot sign off final close if critical fraud anomalies remain unresolved; cannot authorize reversals on CFO-escalated items without dual sign-off. |
| **`CFO`** | Chief Financial Officer, VP Finance. | Ultimate authority; authorizes Level 1 escalations (payment fragmentation, vendor bank modifications, cash anomalies); signs off on the final Close Package; authorizes post-close action reversals. | All operational permissions granted. |
| **`ADMIN`** | Platform Administrator, Solutions Engineer. | Configures company entities, currency FX rates, confidence calibration tables, manages API keys, seeds demo data, and toggles `LIVE` vs. `REPLAY` demo mode. | Unrestricted configuration access. |

### 2.1 RBAC Action Permission Matrix
| Action / Mutation | Viewer | Accountant | Controller | CFO | Admin | API Endpoint Invoked |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Create / Start Close Run** | ❌ | ✅ | ✅ | ✅ | ✅ | `POST /api/close-runs`, `POST /api/close-runs/{id}/start` |
| **Inspect Evidence & Graph** | ✅ | ✅ | ✅ | ✅ | ✅ | `GET /api/exceptions/{id}/evidence` |
| **Stage Compensating Action** | ❌ | ✅ | ✅ | ✅ | ✅ | `POST /api/exceptions/{id}/resolve` |
| **Approve Staged Action (Level 2)** | ❌ | ❌ | ✅ | ✅ | ✅ | `POST /api/exceptions/{id}/approve` |
| **Reject Staged Action** | ❌ | ❌ | ✅ | ✅ | ✅ | `POST /api/exceptions/{id}/reject` |
| **Escalate to Senior Exec (Level 1)**| ❌ | ✅ | ✅ | ✅ | ✅ | `POST /api/exceptions/{id}/escalate` |
| **Reverse / Rollback Action** | ❌ | ❌ | ❌ | ✅ | ✅ | `POST /api/exceptions/{id}/reverse` |
| **Generate Close Package** | ❌ | ✅ | ✅ | ✅ | ✅ | `GET /api/close-runs/{id}/package` |
| **Run CFO-Bench Suite** | ❌ | ❌ | ❌ | ✅ | ✅ | `POST /api/benchmarks/run` |
| **Toggle LIVE / REPLAY Demo Mode** | ❌ | ❌ | ❌ | ❌ | ✅ | `POST /api/demo/mode` |
| **Edit Materiality / Policies** | ❌ | ❌ | ✅ | ✅ | ✅ | `POST /api/policies` |

---

## 3. Complete Routing Architecture & Navigation Schema

The authenticated client uses clean URL hierarchy, preserving deep-linking for exceptions, audit events, benchmark scenarios, and close runs.

```
/ (Redirect) ─────────────► /close-runs (or /tenants if none selected)
├── /tenants
├── /close-runs
│    ├── /close-runs/new (Modal or Full Page)
│    └── /close-runs/:runId
│         ├── /overview           (Default tab)
│         ├── /tasks              (10-Task DAG & Pipeline)
│         ├── /telemetry          (Live Agent Activity & SSE Stream)
│         ├── /reconciliation     (Bank, AP, AR, PO, Receipts)
│         ├── /exceptions         (Exception Workbench & Filter Matrix)
│         │    └── /:exceptionId  (Forensic Investigation Dossier & Evidence Graph)
│         ├── /approvals          (Human Staging & Decision Queue)
│         ├── /audit              (SOX Audit Trail & Reversals)
│         └── /package            (Close Package & Executive Sign-off)
├── /benchmarks
│    ├── /overview                (CFO-Bench Matrix & Regression Suite)
│    └── /:benchmarkId            (Run Details & Scenario Inspector)
├── /calibration                  (Confidence Calibration Studio & ECE Curve)
├── /demo-center                  (Live vs Replay Mode & Golden Trace Player)
├── /policies                     (Materiality & Autonomy Policy Rules)
└── /settings                     (Tenant Management & FX Rate Master)
```

### 3.1 Route Registry
| Path | Page Component | Allowed Roles | Layout Shell | Query Params Supported | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `/tenants` | `TenantSelectPage` | All | `MinimalShell` | `redirect_to` | Select active operating company (e.g., NovaScale AI) or create a new tenant. |
| `/close-runs` | `CloseRunsListPage` | All | `AppShell` | `status`, `year`, `limit`, `offset` | Historical and active close runs list with readiness status indicators. |
| `/close-runs/new` | `CreateCloseRunModal` | Acc, Ctrl, CFO, Admin | Modal over `/close-runs` | — | Select period start/end dates and initialize month-end workflow. |
| `/close-runs/:runId` | `CloseRunLayout` | All | `CloseRunShell` | — | Shell layout providing run header, KPI summary, and nested sub-navigation tabs. |
| `/close-runs/:runId/overview` | `CloseRunOverviewPage` | All | `CloseRunShell` | — | High-level summary of close readiness, task completion %, blockers, and financial impact at risk. |
| `/close-runs/:runId/tasks` | `CloseTasksDAGPage` | All | `CloseRunShell` | `view` (`dag` \| `list`) | Visual dependency DAG and execution list for the 10 Close Tasks. |
| `/close-runs/:runId/telemetry` | `AgentTelemetryPage` | All | `CloseRunShell` | `agent`, `status`, `follow` | Real-time SSE streaming terminal of agent steps, tool calls, model fallbacks, and token metrics. |
| `/close-runs/:runId/reconciliation` | `ReconciliationGridPage` | All | `CloseRunShell` | `domain` (`BANK` \| `AP` \| `AR` \| `PO`), `status` | Subledger matching grids, multi-currency conversion records, and match status tags. |
| `/close-runs/:runId/exceptions` | `ExceptionsWorkbenchPage` | All | `CloseRunShell` | `type`, `severity`, `status`, `autonomy`, `q` | Searchable, filterable ledger of all detected discrepancies and anomalies. |
| `/close-runs/:runId/exceptions/:exceptionId` | `ExceptionDossierPage` | All | `CloseRunShell` | `tab` (`dossier` \| `graph` \| `history`) | Forensic detail page with Evidence Graph visualizer, calculation proofs, citations, and action bar. |
| `/close-runs/:runId/approvals` | `ApprovalsQueuePage` | Acc, Ctrl, CFO, Admin | `CloseRunShell` | `status` (`PENDING` \| `APPROVED` \| `REJECTED`) | Centralized queue for Controller and CFO sign-offs on staged actions. |
| `/close-runs/:runId/audit` | `AuditTrailPage` | All | `CloseRunShell` | `event_type`, `control_id`, `actor_type` | Immutable SOX audit events, versioned prompt/policy IDs, and post-action reversal console. |
| `/close-runs/:runId/package` | `ClosePackagePage` | All | `CloseRunShell` | `format` (`view` \| `json` \| `pdf`) | Formal Month-End Close Package, readiness certification, executive sign-off, and export. |
| `/benchmarks` | `CFOBenchDashboardPage` | CFO, Admin | `AppShell` | `limit`, `offset` | Evaluation dashboard displaying historical CFO-Bench runs, scenario pass rates, and regression diffs. |
| `/benchmarks/:benchmarkId` | `CFOBenchDetailPage` | CFO, Admin | `AppShell` | `scenario_key`, `category` | Scenario-by-scenario analysis of all 35 injected ground-truth cases. |
| `/calibration` | `CalibrationStudioPage` | Ctrl, CFO, Admin | `AppShell` | `period` | Visual calibration curve, Expected Calibration Error (ECE) metric, and bucket accuracy tables. |
| `/demo-center` | `DemoSafetyNetPage` | Admin | `AppShell` | `trace_id` | Interactive HUD for toggling LIVE vs. REPLAY mode, speed multipliers (0.5x to 10x), and trace recorder. |
| `/policies` | `PolicyConfigPage` | Ctrl, CFO, Admin | `AppShell` | `version` | Threshold editor for auto-resolution limits ($50k cap), required confidence, and approval chains. |
| `/settings` | `TenantSettingsPage` | Admin | `AppShell` | `tab` (`company` \| `fx` \| `users`) | Organization profile, currency FX rate master tables, and user directory. |

---

## 4. End-to-End User Workflows

### Workflow 1: Initiating a Month-End Close & Auto-Ingestion
```text
Accountant / Controller
       │
       ▼
[ Click "+ New Close Run" ] ──► Modal prompts Period Start & End (e.g. 2026-03-01 to 2026-03-31)
       │
       ▼
[ Submit: POST /api/close-runs ] ──► System validates no duplicate open run exists
       │
       ▼
[ Redirects to /close-runs/:id/overview ] ──► State: CREATED
       │
       ▼
[ Click "Start Month-End Close" ] ──► POST /api/close-runs/:id/start
       │
       ▼
Transitions to INGESTING ──► Establishes SSE stream connection (GET /api/close-runs/:id/stream)
       │
       ▼
Close Controller launches 10 close tasks in topological dependency order.
```

### Workflow 2: Real-Time Monitoring & Telemetry Streaming
```text
User navigates to /close-runs/:id/telemetry or views top execution bar
       │
       ▼
EventSource connects to /api/close-runs/:id/stream
       │
       ├── Event: close_run_state_change ──► Updates global close status badge & progress bar
       ├── Event: close_task_state_change ──► Nodes in 10-Task DAG turn from PENDING to IN_PROGRESS to COMPLETED
       ├── Event: agent_step ──► Emits Agent Activity logs:
       │    ├── Agent: Reconciliation Agent -> tool: reconcile_invoice_to_po() -> Status: MISMATCH
       │    ├── Agent: Investigation Agent -> tool: traverse_financial_graph() -> Root Cause Found
       │    └── Agent: Verification Agent -> tool: verify_calculations() -> Calibrated Conf: 0.9100
       └── Event: actions_executed ──► Live toast notification: "Auto-resolved EX-004 ($14.20 rounding variance)"
```

### Workflow 3: Forensic Exception Triage & Investigation
```text
Controller / Accountant opens /close-runs/:id/exceptions
       │
       ▼
Filter: Severity = CRITICAL / HIGH, Autonomy = STAGE (Level 2) or RECOMMEND (Level 1)
       │
       ▼
Clicks exception: e.g. "EX-042: Quantity mismatch on NovaScale AI Server Ingestion"
       │
       ▼
Opens /close-runs/:id/exceptions/EX-042:
       ├── Evidence Dossier: Displays Invoice ($16,00,000 / 1000 units), PO (800 units), Receipt (760 units)
       ├── Graph Visualizer: Interactive visual graph showing Vendor -> Invoice -> PO -> Goods Receipt
       ├── Deterministic Math Box: Shows 240 units unreceived @ ₹1,600 = ₹3,84,000 variance (Calculated, not guessed)
       ├── Citation Validation: All citations linked to valid database primary keys (Zero hallucinated citations)
       └── Autonomy Decision Box:
            ├── Raw Model Confidence: 0.9700
            ├── Calibrated Confidence: 0.9000 (Bucket 0.90–0.95 accuracy)
            └── Recommended Action: STAGE -> Request Corrected Invoice & Hold Payment
```

### Workflow 4: Human Approval, Escalation & Resolution
```text
From the Exception Dossier Action Toolbar:
       │
       ├── [ ACTION A: Controller approves Level 2 Staged Entry ]
       │     │
       │     ▼
       │   Enters optional approval note -> POST /api/exceptions/:id/approve
       │   Action executed -> Audit event written -> Status changes to RESOLVED.
       │
       ├── [ ACTION B: Controller escalates ambiguous fraud signal to CFO (Level 1) ]
       │     │
       │     ▼
       │   Clicks "Escalate to CFO" -> Modal prompts reason ("Payment fragmentation pattern detected")
       │   POST /api/exceptions/:id/escalate -> Status changes to ESCALATED.
       │   CFO receives notification in /approvals queue.
       │
       └── [ ACTION C: Manual Resolution with Document Override ]
             │
             ▼
           Accountant attaches credit memo reference -> POST /api/exceptions/:id/resolve
           Status changes to RESOLVED -> Reason captured in immutable audit trail.
```

### Workflow 5: Post-Close Reversal & SOX Rollback
```text
Auditor or CFO notices an approved action must be rescinded after close review
       │
       ▼
Navigates to /close-runs/:id/audit or the resolved exception's history tab
       │
       ▼
Clicks "Reverse Action" on executed action row
       │
       ▼
Reversal Modal opens:
  - Displays original action: Staged compensating journal entry $4,250.00
  - Shows proposed reversal entry: Counter-debit/credit to void impact
  - Requires mandatory justification note (e.g., "Vendor provided updated proof of delivery")
       │
       ▼
Submit: POST /api/exceptions/:id/reverse
  - Backend writes non-destructive reversal record (reversal_actions)
  - Exception status automatically updates to REOPENED
  - 2 SOX audit events generated (Original + Reversal) with Policy/Prompt version IDs
  - Close Run readiness reverts from READY_TO_CLOSE to BLOCKED until re-evaluated.
```

### Workflow 6: Readiness Sign-Off & Close Package Generation
```text
Controller / CFO navigates to /close-runs/:id/package
       │
       ▼
System executes readiness pre-flight check:
  - Are all 10 close tasks COMPLETED?
  - Are there 0 open CRITICAL or HIGH blocking exceptions?
  - Is financial impact at risk == $0.00?
       │
       ├── If BLOCKERS exist:
       │     - Displays red banner: "Close Blocked: 2 unresolved critical items ($1,450,000 at risk)"
       │     - Direct deep-links to blocking exceptions
       │     - "Sign Off & Close Books" button is disabled.
       │
       └── If ALL CLEAR:
             - Displays green banner: "Books Ready to Close (100% Reconciled)"
             - CFO clicks "Certify & Lock Period" -> CloseRunStatus transitions to CLOSED
             - Generates downloadable certified Close Package (Structured JSON + Certified PDF with cryptographic checksum).
```

### Workflow 7: Demo Safety Net & Presentation Mode (LIVE vs. REPLAY)
```text
Presenter / Admin opens Demo Safety Net HUD (Floating bar or /demo-center)
       │
       ▼
Current Mode Toggle: [ LIVE ] ◄───► [ REPLAY ]
       │
       ├── In REPLAY Mode:
       │     - Presenter selects a Golden Scenario:
       │         * Scenario 1: Payment Fragmentation (14 payments of ₹1,00,000 for ₹14.5L invoice)
       │         * Scenario 2: Quantity Mismatch (Invoice 1,000 vs. Received 760 units)
       │         * Scenario 3: Clean Multi-Currency Transaction (Auto-Resolved)
       │     - Sets Playback Speed: [ 0.5x | 1.0x | 2.0x | 5.0x | Instant ]
       │     - Hits "Play Trace" -> SSE stream emits pre-recorded real-time frames
       │     - UI renders live animations, graph builds, and calculations identically to a live run.
       │
       └── In LIVE Mode:
             - Interacts with live LLM agents and deterministic backend tools.
             - If any external provider rate-limit or timeout occurs, presenter can flip to REPLAY with 1 click without refreshing page.
```

---

## 5. Global Layout Shell & Reusable Navigation Sections

The application uses an enterprise two-tier shell with an ultra-responsive layout:

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ TOP NAVIGATION BAR                                                                                     │
│ [Logo: VEXA] │ [Tenant: NovaScale AI ▼] │ [Run: Mar 2026 Close (INGESTING) ▼] │ [Search ⌘K] │ [Demo: LIVE] │ [User: CFO ▼] │
├─────────────────────────┬──────────────────────────────────────────────────────────────────────────────┤
│ COLLAPSIBLE SIDEBAR     │ MAIN CONTENT WORKSPACE                                                       │
│                         │                                                                              │
│ OPERATIONS              │  [Page Header / Breadcrumbs / Quick Actions]                                 │
│ ├─ Overview             │  ──────────────────────────────────────────────────────────────────────────  │
│ ├─ Close Tasks (DAG)    │  [Top Metric / KPI Strip]                                                    │
│ ├─ Live Telemetry (SSE) │  ──────────────────────────────────────────────────────────────────────────  │
│ ├─ Reconciliation       │  [Primary Tabbed Content / Data Grid / Visual Graph]                         │
│ └─ Exceptions (14)      │                                                                              │
│                         │                                                                              │
│ GOVERNANCE              │                                                                              │
│ ├─ Approvals Queue (3)  │                                                                              │
│ ├─ SOX Audit Trail      │                                                                              │
│ └─ Close Package        │                                                                              │
│                         │                                                                              │
│ QUALITY & EVALUATION    │                                                                              │
│ ├─ CFO-Bench Studio     │                                                                              │
│ └─ Calibration (ECE)    │                                                                              │
│                         │                                                                              │
│ SYSTEM                  │                                                                              │
│ ├─ Demo Control Center  │                                                                              │
│ ├─ Policy Engine        │                                                                              │
│ └─ Settings & FX Rates  │                                                                              │
└─────────────────────────┴──────────────────────────────────────────────────────────────────────────────┘
│ BOTTOM FLOATING DEMO CONTROLLER HUD (Visible when Demo Mode Active)                                    │
│ [Mode: REPLAY] [Trace: Golden-AP-Fragmentation] [▶ Play | ❚❚ Pause] [Speed: 1x 2x 5x] [Step: 14/42]   │
└────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 5.1 Top Navigation Bar Elements
* **Tenant Switcher Dropdown:** Displays active company name, base currency tag (`USD`), and allows switching between tenants (via `GET /api/companies`).
* **Active Close Run Selector:** Quick switcher displaying active close period, status indicator pill (colored by `CloseRunStatus`), and version tag.
* **Global Command Palette (`⌘K` / `Ctrl+K`):** Instant search across Invoices, Purchase Orders, Goods Receipts, Vendors, Exception IDs, and Audit control codes (`AP-03`, `PROC-04`).
* **Demo Status Badge & Controller Toggle:** Pill displaying current execution mode:
  * Green `LIVE`: Directly connected to agent engine.
  * Purple `REPLAY (Speed: 2x)`: Streaming pre-recorded golden demo trace.
* **Notification Center:** Badge showing count of pending approvals and critical blockers.
* **User Profile & Persona Switcher:** Displays active user, current role (`CFO`, `CONTROLLER`, `ACCOUNTANT`, `VIEWER`), and provides a 1-click role switcher for testing and demonstration purposes.

### 5.2 Collapsible Sidebar Navigation
Divided into 4 functional zones with dynamic counters:
1. **Operations Zone:**
   * **Overview:** System readiness, KPI cards, high-level summary.
   * **Close Tasks:** DAG visualization and sequential task runner.
   * **Live Telemetry:** Streaming agent step logs, tool calls, and model latency metrics.
   * **Reconciliation:** Subledger reconciliation tables (Bank, AP, AR, PO, Receipts).
   * **Exceptions:** Filterable list of all detected anomalies with badge count of open items.
2. **Governance Zone:**
   * **Approvals Queue:** Centralized approval list for Controller/CFO with badge count of pending actions.
   * **SOX Audit Trail:** Immutable append-only log with prompt/policy versions and reversal actions.
   * **Close Package:** Final close compilation, sign-off status, and PDF/JSON export.
3. **Quality & Evaluation Zone:**
   * **CFO-Bench Studio:** Accuracy benchmarks across 35 injected ground-truth scenarios.
   * **Calibration:** ECE calibration curve, reliability diagrams, and confidence bucket performance.
4. **System Zone:**
   * **Demo Control Center:** Live trace recorder, trace player, and golden scenario launcher.
   * **Policy Engine:** Materiality thresholds, auto-resolution limits, and approval policies.
   * **Settings & FX Rates:** Multi-currency exchange rate tables and organization details.

### 5.3 Global Slide-Over Inspection Drawer
A universal slide-over drawer opens from the right edge when any financial entity is clicked anywhere in the application (in data grids, graph nodes, or audit events):
* **Supported Entities:** Invoice, Purchase Order, Goods Receipt, Payment Voucher, Bank Transaction, Journal Entry, Vendor Master.
* **Content:** Displays full raw record metadata, JSON view, linked document relationships, and currency converted values.
* **Non-Disruptive:** Allows the user to inspect underlying evidence without losing their scroll position or filter state on the main page.

---

## 6. Page-by-Page Screen Requirements (Excluding Landing Page)

---

### Page 1: Tenant & Workspace Selection (`/tenants`)
* **URL:** `/tenants`
* **Target Roles:** All Roles
* **Purpose:** Select the operating enterprise or create a new multi-tenant sandbox before accessing month-end closing records.
* **Page Sections:**
  1. **Header Section:** Organization Directory, active tenant indicator, search bar.
  2. **Tenant Cards Grid:**
     * Displays existing companies (e.g. **NovaScale AI**).
     * Card attributes: Legal Name, Base Currency (`USD`, `INR`, etc.), Fiscal Year End, Active Close Runs count, Total Ingested Transactions.
     * Status indicator: `Active`, `Data Seeded`, `In Progress Close`.
  3. **"+ Create Tenant" Modal Dialog:**
     * Fields: Company Name, Legal Entity Name, Tax ID / GSTIN, Base Currency dropdown (`USD`, `INR`, `EUR`, `GBP`), Fiscal Year End date.
     * Action: `POST /api/companies`.
* **State & API Contracts:**
  * Read: `GET /api/companies`
  * Create: `POST /api/companies`

---

### Page 2: Close Runs Hub & Historical Archive (`/close-runs`)
* **URL:** `/close-runs`
* **Target Roles:** All Roles
* **Purpose:** High-level dashboard of all fiscal close periods—historical, in-progress, and scheduled.
* **Page Sections:**
  1. **Page Header:**
     * Breadcrumbs: `Home > Close Runs`
     * Title: "Month-End Close Cycles"
     * Actions:
       * `[ + New Close Run ]` Button (opens creation modal).
       * Filter dropdowns: Year selector, Status filter (`ALL`, `INGESTING`, `RECONCILING`, `WAITING_FOR_HUMAN`, `READY_TO_CLOSE`, `CLOSED`, `BLOCKED`).
  2. **Global Metrics Strip (4 KPI Cards):**
     * **Total Close Cycles:** Lifetime completed close runs count.
     * **Active Close Period:** Current running period (e.g., "March 2026") with status tag.
     * **Average Days to Close:** Historic average closing duration (e.g., "1.4 business days").
     * **Autonomous Resolution Rate:** Historic percentage of exceptions auto-resolved under Level 3 (e.g., "78.4%").
  3. **Close Runs Data Table:**
     * Columns:
       * **Period:** Date range (e.g., `2026-03-01 → 2026-03-31`).
       * **Status:** Color-coded status badge (`CREATED`, `INGESTING`, `RECONCILING`, `INVESTIGATING`, `VERIFYING`, `WAITING_FOR_HUMAN`, `RESOLVING`, `READY_TO_CLOSE`, `CLOSED`, `BLOCKED`, `FAILED`).
       * **Version:** Compare-and-swap concurrency integer (`v1`, `v2`, etc.).
       * **Started At / Completed At:** Formatted timestamp and duration.
       * **Completion %:** Progress bar indicating finished close tasks (out of 10).
       * **Exceptions:** Count pill split by severity (`3 Critical`, `5 High`, `12 Low`).
       * **Actions:** `[ Enter Command Center → ]` link button.
  4. **Create Close Run Modal (`/close-runs/new`):**
     * Form inputs: `Period Start` (date picker), `Period End` (date picker).
     * Pre-flight notice: Verifies whether transactions and bank feeds exist for the selected period.
     * Submit button: `Initialize Close Run` (`POST /api/close-runs`).
* **State & API Contracts:**
  * Read: `GET /api/close-runs?limit=100&offset=0`
  * Create: `POST /api/close-runs` (Body: `{ "period_start": "YYYY-MM-DD", "period_end": "YYYY-MM-DD" }`)

---

### Page 3: Close Run Command Center (`/close-runs/:runId/overview`)
* **URL:** `/close-runs/:runId/overview` (Default tab of `/close-runs/:runId`)
* **Target Roles:** All Roles
* **Purpose:** Executive command center providing the single pane of glass for a specific month-end close cycle.
* **Page Sections:**
  1. **Run Status Banner:**
     * Dynamic banner reflecting state machine status:
       * If `BLOCKED`: Red alert with count of material blocking exceptions and financial risk at stake.
       * If `WAITING_FOR_HUMAN`: Amber alert displaying pending approvals count with a 1-click link to `/approvals`.
       * If `READY_TO_CLOSE`: Green banner with "Ready for Certification" and quick sign-off button.
       * If `CLOSED`: Blue banner with closed timestamp, certifying officer, and download button for the audit package.
     * Action button: If status is `CREATED`, prominent `[ Start Month-End Close ]` button (`POST /api/close-runs/{id}/start`).
  2. **Top Metric Cards (5 Cards):**
     * **Close Readiness:** Circular progress gauge showing overall completion % (e.g., `82%`).
     * **10-Task Execution Progress:** e.g., `8/10 Completed`, `1 In Progress`, `1 Pending`.
     * **Exception Triage:** e.g., `24 Total` (`16 Auto-Resolved`, `5 Staged`, `3 Escalated`).
     * **Financial Exposure At Risk:** Total monetary variance of open critical/high exceptions (e.g., `$1,450,000.00`).
     * **Confidence Calibration Index:** Average calibrated confidence across decisions (e.g., `0.942`).
  3. **Split View: Workflow Progress vs. Live Activity Feed:**
     * **Left Column: 10-Task Pipeline Status Mini-Board:**
       * Vertical list of the 10 Close Tasks with status icons, assigned agent, and completion duration.
       * Clickable items link directly to `/tasks`.
     * **Right Column: Live Stream Snippet (Last 5 Agent Events):**
       * Streaming terminal snippet showing real-time agent tool executions.
       * Link to full terminal: `[ View Live Telemetry Stream → ]`.
  4. **Material Blockers & High-Priority Exceptions Drawer List:**
     * Table of open exceptions requiring immediate action with columns: `Type`, `Severity`, `Variance`, `Calibrated Confidence`, `Quick Action` (`Review`, `Escalate`).
* **State & API Contracts:**
  * Read Run: `GET /api/close-runs/{id}`
  * Read Tasks: `GET /api/close-runs/{id}/tasks`
  * Read Exceptions: `GET /api/close-runs/{id}/exceptions?limit=10`
  * Start Run: `POST /api/close-runs/{id}/start`

---

### Page 4: 10-Task Close Workflow Pipeline (`/close-runs/:runId/tasks`)
* **URL:** `/close-runs/:runId/tasks`
* **Target Roles:** All Roles
* **Purpose:** Visual representation and execution management of the 10 canonical Close Tasks executed in strict dependency DAG order.
* **Page Sections:**
  1. **View Toggle:** `[ Interactive DAG Graph View ]` vs. `[ Sequential List View ]`.
  2. **Interactive DAG Visualization (Rendered via React Flow):**
     * Visual nodes with real-time status pulses:
       1. `BANK_RECONCILIATION` ──► 2. `PAYMENT_RECONCILIATION`
       3. `INVOICE_VALIDATION` ──► 4. `AP_RECONCILIATION` ──► 5. `AR_RECONCILIATION`
       (All above feed into) ──► 6. `VARIANCE_ANALYSIS` ──► 7. `ACCRUAL_REVIEW`
       ──► 8. `EXCEPTION_REVIEW` ──► 9. `FINAL_VERIFICATION` ──► 10. `CLOSE_PACKAGE`
     * Node card contains: Task Name, Assigned Agent (`Reconciliation Agent`, `Financial Analyst`, etc.), Status badge, Execution duration, and Discrepancies found count.
     * Clicking a node opens a side panel detailing the task's inputs, outputs, and tool call logs.
  3. **Sequential Task Execution Table:**
     * Table columns:
       * **Order / Sequence:** Step 1 to 10.
       * **Task Type:** Human-readable title and domain badge.
       * **Status:** `PENDING` (gray), `IN_PROGRESS` (animated blue pulse), `COMPLETED` (green check), `FAILED` (red cross), `BLOCKED` (amber lock).
       * **Assigned Agent:** Named autonomous agent orchestrator.
       * **Started At / Completed At:** Timestamp and execution latency.
       * **Result Summary:** Key findings (e.g. "Reconciled 1,500 bank transactions. Detected 2 unmapped entries.").
       * **Actions:** `[ Inspect Steps ]` button.
* **State & API Contracts:**
  * Read: `GET /api/close-runs/{id}/tasks`
  * Live updates: Listens to SSE event `close_task_state_change`.

---

### Page 5: Live Agent Telemetry & Reasoning Stream (`/close-runs/:runId/telemetry`)
* **URL:** `/close-runs/:runId/telemetry`
* **Target Roles:** All Roles (Crucial for Demo Presenters and Auditors)
* **Purpose:** Real-time visibility into the autonomous cognition, tool executions, calculations, and fallbacks of the agent swarm.
* **Page Sections:**
  1. **Stream Control Header:**
     * Connection status pill: Green `Connected (SSE)` / Amber `Reconnecting...`.
     * Autoscroll toggle: `[ Auto-scroll to Bottom (ON/OFF) ]`.
     * Filters:
       * Filter by Agent: `All`, `Close Controller`, `Reconciliation Agent`, `Investigation Agent`, `Financial Analyst`, `Verification Agent`, `Action Agent`.
       * Filter by Tool: e.g. `reconcile_invoice_to_po`, `traverse_financial_graph`, `calculate_variance`, `convert_amount`.
       * Filter by Status: `ALL`, `RUNNING`, `SUCCESS`, `FAILED`.
     * Latency & Token Budget Display: Cumulative tokens used, cost in USD, and average tool latency.
  2. **Streaming Execution Terminal:**
     * Monospace log viewer formatted with syntax highlighting:
       * **Timestamp & Agent Tag:** e.g., `[14:02:11.452] [InvestigationAgent]`.
       * **Step Number & Type:** e.g., `Step 3 / TOOL_CALL`.
       * **Tool Invocation Accordion:** Expandable block showing exact input parameters and returned output payload.
       * **Reasoning Snippet:** Natural language explanation formulated by the agent.
       * **Calculated Metrics Badge:** Shows calculated variance, FX rate applied, and citation IDs.
  3. **Agent State Summary Strip:**
     * Real-time avatar indicators for all 6 agents showing their active status: `IDLE`, `RUNNING (Tool: traverse_financial_graph)`, or `COMPLETED`.
* **State & API Contracts:**
  * SSE Endpoint: `GET /api/close-runs/{id}/stream`
  * Historical Fallback: `GET /api/agent-runs/{id}/steps`

---

### Page 6: Multi-Subledger Reconciliation Workstation (`/close-runs/:runId/reconciliation`)
* **URL:** `/close-runs/:runId/reconciliation`
* **Target Roles:** Accountant, Controller, Auditor
* **Purpose:** Detailed review of the 10-pass deterministic matching engine across Bank, AP, AR, Procurement, and General Ledger.
* **Page Sections:**
  1. **Subledger Domain Tabs:**
     * `[ Bank ↔ Ledger ]` (Treasury)
     * `[ Invoice ↔ Purchase Order ]` (3-Way Matching)
     * `[ Invoice ↔ Goods Receipt ]` (Quantity Matching)
     * `[ Invoice ↔ Payment ]` (Disbursements)
     * `[ Accounts Receivable ↔ Remittances ]` (Collections)
  2. **Subledger Summary Cards (3 Cards):**
     * **Total Matched Volume:** e.g., `$18,420,150.00 (98.4%)`.
     * **Unreconciled Variance:** e.g., `$384,000.00 (1.6%)`.
     * **FX Conversions Applied:** e.g., `18 cross-currency conversions verified`.
  3. **Reconciliation Data Grid:**
     * Columns:
       * **Source Record A:** ID, Date, Entity Name, Stated Amount, Currency.
       * **Matched Record B:** ID, Date, Reference No, Stated Amount, Currency.
       * **FX Conversion Details:** Rate applied, quote currency, rate effective date (from `fx_rates`).
       * **Variance / Delta:** Exact mathematical difference. Zero variance highlighted in green.
       * **Status Badge:** `MATCHED` (green), `PARTIAL` (amber), `MISMATCH` (red), `MISSING` (purple).
       * **Confidence Score:** Deterministic match confidence (e.g., `1.00`).
       * **Action:** `[ View Evidence ]` / `[ Create Exception ]`.
* **State & API Contracts:**
  * Read: `GET /api/close-runs/{id}/tasks` & Subledger reconciliation tool outputs.

---

### Page 7: Financial Exception Workbench (`/close-runs/:runId/exceptions`)
* **URL:** `/close-runs/:runId/exceptions`
* **Target Roles:** All Roles
* **Purpose:** Centralized workbench for browsing, searching, and triaging all detected variances, policy violations, and fraud signals.
* **Page Sections:**
  1. **Workbench Filter & Search Toolbar:**
     * Free-text search input (filters across exception ID, vendor, invoice number, root-cause description).
     * Dropdown: **Exception Type** (16 canonical types: `DUPLICATE_INVOICE`, `PO_MISMATCH`, `PAYMENT_FRAGMENTATION`, etc.).
     * Dropdown: **Severity** (`ALL`, `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`).
     * Dropdown: **Status** (`ALL`, `OPEN`, `INVESTIGATING`, `STAGED`, `RESOLVED`, `AUTO_RESOLVED`, `ESCALATED`, `REOPENED`).
     * Dropdown: **Autonomy Level** (`OBSERVE`, `RECOMMEND`, `STAGE`, `EXECUTE`).
  2. **Exception Summary Metrics:**
     * Horizontal pill counters for quick filtering:
       * `[ All (32) ]` | `[ Critical Blockers (3) ]` | `[ Staged for Review (5) ]` | `[ Auto-Resolved (21) ]` | `[ Escalated (3) ]`.
  3. **Exceptions Table:**
     * Columns:
       * **Exception ID:** Clickable link (e.g. `EX-042`).
       * **Type & SOX Control:** Badge with type name + mapped control (e.g., `PO_MISMATCH [PROC-04]`).
       * **Severity Pill:** Critical (red with pulse icon), High (amber), Medium (yellow), Low (gray).
       * **Counterparty / Reference:** Vendor or Customer name + Source Document reference.
       * **Financial Impact:** Formatted monetary amount with currency code (e.g., `₹3,84,000.00`).
       * **Confidence Display:** Coupled pill displaying: `Raw: 0.97` | `Calibrated: 0.90`.
       * **Autonomy Level:** Level badge (e.g. `Level 2: STAGE`).
       * **Status:** Current operational state badge.
       * **Assigned Role:** `Controller`, `CFO`, or `Autonomous Action Agent`.
       * **Quick Actions:** Contextual dropdown button: `[ Review Dossier ]`, `[ Approve ]`, `[ Escalate ]`.
* **State & API Contracts:**
  * Read: `GET /api/close-runs/{id}/exceptions?limit=500&offset=0`

---

### Page 8: Forensic Investigation Dossier & Evidence Graph (`/close-runs/:runId/exceptions/:exceptionId`)
* **URL:** `/close-runs/:runId/exceptions/:exceptionId`
* **Target Roles:** All Roles (Primary operational screen for investigation)
* **Purpose:** The forensic deep-dive screen for an individual exception, presenting the bounded evidence dossier, calculation proofs, citations, interactive relationship graph, and action controls.
* **Page Sections:**
  1. **Dossier Header & Status Bar:**
     * Breadcrumbs: `Close Runs > [Period] > Exceptions > [Exception ID]`
     * Title: Exception Type + Short Description (e.g., `EX-042: Billed Quantity Exceeds Physical Goods Receipt`).
     * Status Badges: Severity, Current Status, Assigned Reviewer, SOX Control ID.
     * Top Action Toolbar (Role-Aware):
       * `[ Approve & Execute Staged Action ]` (Green button, Controller/CFO only).
       * `[ Reject Staged Action ]` (Red outline button, Controller/CFO only).
       * `[ Escalate to CFO ]` (Amber button, opens escalation modal).
       * `[ Manual Resolve ]` (Neutral button, opens override modal).
       * `[ Reverse / Rollback ]` (Available if status is `RESOLVED` or `AUTO_RESOLVED`).
  2. **Split View: Forensic Investigation Panels:**
     * **Left Pane (60% width): Forensic Dossier & Proofs:**
       * **Executive Summary & Root Cause:** Synthesized reasoning explaining the root discrepancy.
       * **Deterministic Calculation Verification Box:**
         * Formula display: e.g. `(Billed Qty: 1,000 - Received Qty: 760) × Unit Price: ₹1,600.00 = Variance: ₹3,84,000.00`.
         * Deterministic verification badge: `Verified by Deterministic Math Engine (Diff = 0.00)`.
       * **Evidence Records Breakdown:**
         * Side-by-side comparison cards for all linked documents:
           * **Card 1: Invoice** (Number, Date, Total, Line Items table).
           * **Card 2: Purchase Order** (PO Number, Approved Qty, Unit Price).
           * **Card 3: Goods Receipt** (Receipt Number, Physical Received Qty, Warehouse Sign-off).
           * **Card 4: Bank / Payment Records** (if applicable).
       * **Citation & Provenance Table:**
         * Table of every claim made by the agent paired with the exact source record ID, database primary key, and verification status (`Zero Hallucinations Verified`).
       * **Autonomy & Confidence Evaluation:**
         * Breakdown of how autonomy was determined:
           * Materiality Check: `$46,000.00 <= $50,000.00 Cap` (Passed).
           * Raw Model Confidence: `0.9700`.
           * Calibrated Confidence: `0.9100` (Applied bucket mapping).
           * Policy Result: `STAGE (Level 2) - Requires Controller Approval due to quantity variance policy`.
     * **Right Pane (40% width): Interactive Financial Evidence Graph:**
       * Rendered visual graph (React Flow or SVG force-directed):
         * Visual nodes representing entities: `Vendor (NovaScale AI)`, `Invoice (INV-821)`, `PO (PO-4421)`, `Goods Receipt (GR-8831)`, `Payment (PAY-102)`, `GL Account (2100-AP)`.
         * Directional edges showing causal relationships: `issued`, `references`, `fulfilled_by`, `paid_by`.
         * Highlighting anomalous edges in red (e.g. discrepancy link between Invoice and Goods Receipt).
         * Node click displays full metadata in slide-over inspector.
  3. **Audit History & Reversals Tab:**
     * Chronological timeline of all events related to this exception: Creation, Investigation, Verification, Human Reviews, and Reversals.
* **State & API Contracts:**
  * Read Exception: `GET /api/exceptions/{id}`
  * Read Evidence Dossier: `GET /api/exceptions/{id}/evidence`
  * Approve: `POST /api/exceptions/{id}/approve` (Body: `{ "actor": "controller", "notes": "..." }`)
  * Reject: `POST /api/exceptions/{id}/reject` (Body: `{ "actor": "controller", "notes": "..." }`)
  * Escalate: `POST /api/exceptions/{id}/escalate` (Body: `{ "target_role": "CFO", "reason": "..." }`)
  * Resolve: `POST /api/exceptions/{id}/resolve` (Body: `{ "notes": "..." }`)
  * Reverse: `POST /api/exceptions/{id}/reverse` (Body: `{ "reason": "...", "reversed_by": "cfo" }`)

---

### Page 9: Human Approvals & Action Staging Queue (`/close-runs/:runId/approvals`)
* **URL:** `/close-runs/:runId/approvals`
* **Target Roles:** Controller, CFO, Admin
* **Purpose:** Centralized inbox for human-in-the-loop decisions, grouping items staged by Level 2 autonomy or escalated to Level 1.
* **Page Sections:**
  1. **Approval Category Tabs:**
     * `[ Pending Controller Approvals (5) ]` (Level 2 Staged items).
     * `[ Pending CFO Escalations (2) ]` (Level 1 Material/Fraud items).
     * `[ Historical Approved / Rejected Log ]`.
  2. **Approval Request Cards / Table:**
     * Each row/card displays:
       * **Exception Summary & Impact:** ID, Category, Counterparty, Monetary Value.
       * **Proposed Remedial Action:**
         * E.g., `Stage Compensating Journal Entry: Debit Unbilled GRNI ($4,200) / Credit Accrued AP ($4,200)`.
         * E.g., `Draft Vendor Inquiry Email: Request credit note for 240 missing units`.
       * **Calibrated Confidence Score:** e.g., `0.920 (High Reliability)`.
       * **Evidence Summary:** Mini-pills of linked source records.
       * **Quick Approval Controls:**
         * Input field for review notes.
         * `[ Approve & Execute ]` Button.
         * `[ Reject / Re-Investigate ]` Button.
         * `[ View Full Forensic Dossier → ]` Link.
  3. **Batch Approval Bar (For Controller):**
     * Multi-select checkboxes to batch approve routine Level 2 staged adjustments below $10,000.
* **State & API Contracts:**
  * Read: `GET /api/close-runs/{id}/exceptions?status=STAGED,ESCALATED`
  * Approve: `POST /api/exceptions/{id}/approve`
  * Reject: `POST /api/exceptions/{id}/reject`

---

### Page 10: Immutable SOX Audit Trail & Reversal Center (`/close-runs/:runId/audit`)
* **URL:** `/close-runs/:runId/audit`
* **Target Roles:** All Roles (Primary workspace for Auditors and Compliance Officers)
* **Purpose:** Provides a complete, append-only, cryptographic audit log of every system decision, agent step, human approval, and post-action reversal, fully cross-referenced to SOX internal control IDs.
* **Page Sections:**
  1. **Audit Filter Bar:**
     * Filter by Event Type (`EXCEPTION_DECISION`, `APPROVAL`, `REVERSAL`, `CLOSE_RUN_STATE_CHANGE`, `ACTION_EXECUTED`).
     * Filter by SOX Control ID (`AP-03`, `AP-07`, `PROC-04`, `BANK-01`, `GL-02`, `REV-01`, `CLOSE-01`).
     * Filter by Actor (`Autonomous Agent`, `Controller`, `CFO`, `System`).
     * Date/Time range picker.
  2. **Audit Metrics Strip:**
     * **Total Audit Events Recorded:** e.g., `1,428 events`.
     * **Agent Prompt Versions Referenced:** e.g., `investigator-v3`, `verifier-v2`.
     * **Active Policy Version:** e.g., `policy-v2`.
     * **Total Reversals Executed:** e.g., `1 reversal (Non-destructive)`.
  3. **Audit Events Master Table:**
     * Columns:
       * **Timestamp (UTC):** Exact ISO timestamp with millisecond precision.
       * **Event Type:** Tagged event category.
       * **SOX Control ID:** Linked control code with tooltip description.
       * **Actor & Agent:** Actor name + Prompt Version ID (e.g. `Agent: investigator [v3]`).
       * **Policy Version ID:** Exact version integer or hash (e.g. `policy-v2`).
       * **Entity Ref:** Linked Exception ID, Close Run ID, or Journal Entry ID.
       * **Decision & Reason:** Natural language rationale + Calibrated Confidence.
       * **Financial Impact:** Monetary value involved.
       * **Action Taken / Status:** E.g., `STAGED`, `APPROVED`, `EXECUTED`, `REVERSED`.
       * **Inspect Button:** Opens slide-over drawer with raw JSON audit payload.
  4. **Dedicated Reversal Action Console:**
     * Filter tab isolating all `REVERSAL` events.
     * Shows side-by-side comparison:
       * Left: Original executed action and timestamp.
       * Right: Counter-balancing reversal entry, authorizing CFO, and reason.
* **State & API Contracts:**
  * Read: `GET /api/close-runs/{id}/audit?limit=200&offset=0`
  * Global Audit Read: `GET /api/audit-events?limit=100`

---

### Page 11: Close Package & Executive Sign-Off Portal (`/close-runs/:runId/package`)
* **URL:** `/close-runs/:runId/package`
* **Target Roles:** Controller, CFO, Auditor
* **Purpose:** The capstone deliverable of the month-end close: pre-flight readiness checklist, executive sign-off certification, and export of the audit-backed close package.
* **Page Sections:**
  1. **Close Readiness Pre-Flight Checklist:**
     * Grid of 4 automated health cards:
       * **10 Close Tasks Status:** `10/10 Completed` (Pass: Green check).
       * **Blocking Exceptions:** `0 Open Critical/High Items` (Pass / Fail).
       * **Unresolved Financial Exposure:** `$0.00 at risk` (Pass / Fail).
       * **Verification Engine Check:** `100% Arithmetic & Policy Verified` (Pass).
     * If any check fails: Displays list of blockers with direct links to resolve them.
  2. **Executive Certification & Lock Action:**
     * If all checks pass:
       * Formal certification statement: *"I certify that the financial records for the period [Period] have been reconciled, investigated, and verified in accordance with corporate accounting policy and SOX internal controls."*
       * Sign-off controls: Checkbox confirmation + CFO digital signature field.
       * Button: `[ Certify & Lock Period ]` (Transitions `CloseRun` to `CLOSED`).
  3. **Close Package Preview & Summary Tabs:**
     * **Executive Summary Tab:** Period metrics, total reconciliation volume, net adjustments, variance breakdown.
     * **Task Completion Matrix Tab:** Summary of each task, duration, and findings.
     * **Resolved Exceptions Register Tab:** Full log of all resolved exceptions, root causes, and actions.
     * **Audit Trail Excerpt Tab:** Key governance events, policy version references, and sign-offs.
     * **Confidence Calibration Appendix Tab:** Summary of calibration accuracy for all decisions made during this close.
  4. **Export & Download Center:**
     * `[ Download Structured JSON Package ]` (Full machine-readable file).
     * `[ Download Certified PDF Close Package ]` (Formatted executive binder with cryptographic SHA-256 integrity hash).
* **State & API Contracts:**
  * Read: `GET /api/close-runs/{id}/package`

---

### Page 12: CFO-Bench Evaluation Studio (`/benchmarks` & `/benchmarks/:benchmarkId`)
* **URL:** `/benchmarks` & `/benchmarks/:benchmarkId`
* **Target Roles:** CFO, Admin, Machine Learning / Quant Engineers
* **Purpose:** Rigorous benchmark evaluation suite testing Vexa against all 35 injected ground-truth scenarios (the synthetic NovaScale AI dataset).
* **Page Sections:**
  1. **Benchmark Suite Header:**
     * Overall Score Pill: `35 / 35 Scenarios Passed (F1 Score: 1.00)`.
     * Metric Strip:
       * **Root Cause Accuracy:** `100%`.
       * **Evidence Retrieval Accuracy:** `100%`.
       * **Financial Calculation Accuracy:** `100% (Zero Arithmetic Error)`.
       * **Action Correctness:** `100%`.
       * **Expected Calibration Error (ECE):** `0.024`.
     * Action: `[ Run Full CFO-Bench Suite ]` Button (`POST /api/benchmarks/run`).
  2. **Historical Benchmark Runs Table (`/benchmarks`):**
     * Columns: Run ID, Date/Time, Agent Prompt Version, Total Scenarios, Passed Scenarios, Accuracy %, Average Latency, Total Cost ($), Actions.
  3. **Scenario Matrix Grid (`/benchmarks/:benchmarkId`):**
     * Interactive table displaying all 35 test cases categorized by scenario group:
       * `5 Duplicate Invoices`
       * `4 PO Mismatches`
       * `3 Receipt Mismatches`
       * `4 Duplicate Payments`
       * `3 Unusual Vendor Activity`
       * `2 Payment Fragmentation Patterns` (Critical Demo Cases)
       * `3 Missing Documents`
       * `3 Incorrect GL Mappings`
       * `2 Incorrect Accruals`
       * `2 AR Mismatches`
       * `2 Cash Anomalies`
     * Columns for each scenario:
       * **Scenario Key & Name:** e.g., `AP-FRAG-01: Structured Payments Under Approval Threshold`.
       * **Expected Root Cause vs. Actual Agent Diagnosis:** Diff visualizer.
       * **Required Evidence Retrieved:** Pill list of record IDs with match indicators.
       * **Expected Action vs. Actual Action:** E.g., `Expected: ESCALATE | Actual: ESCALATE`.
       * **Calculation Diff:** E.g., `$0.00`.
       * **Calibrated Confidence:** E.g., `0.940`.
       * **Result Status Badge:** Green `PASS` / Red `FAIL`.
       * **Actions:** `[ View Trace ]` (opens the exact agent execution path).
* **State & API Contracts:**
  * List Runs: `GET /api/benchmarks?limit=20`
  * Run Suite: `POST /api/benchmarks/run`
  * Get Run Detail: `GET /api/benchmarks/{id}`

---

### Page 13: Confidence Calibration Studio (`/calibration`)
* **URL:** `/calibration`
* **Target Roles:** Controller, CFO, Admin
* **Purpose:** Visual analytics proving that Vexa’s reported confidence is empirically calibrated against ground truth (solving the "how do you know 95% means 95% correct?" requirement).
* **Page Sections:**
  1. **Calibration Overview Metrics:**
     * **Expected Calibration Error (ECE):** e.g., `0.021` (Target: `< 0.05`).
     * **Max Calibration Error (MCE):** e.g., `0.048`.
     * **Total Evaluated Decisions:** e.g., `350 ground-truth samples`.
  2. **Reliability Diagram (Visual Chart):**
     * Dual-axis calibration plot:
       * X-axis: Stated Confidence Buckets (`0.50–0.60`, `0.60–0.70`, `0.70–0.80`, `0.80–0.90`, `0.90–0.95`, `0.95–1.00`).
       * Y-axis: Empirical Accuracy Rate (0.0 to 1.0).
       * Perfect Calibration Line (45-degree diagonal reference).
       * Actual Model Bar Chart vs. Diagonal Reference showing tight convergence.
  3. **Calibration Bucket Breakdown Table:**
     * Columns:
       * **Confidence Range:** e.g., `0.90 – 0.95`.
       * **Sample Count:** e.g., `84 decisions`.
       * **Mean Reported Confidence:** e.g., `0.924`.
       * **Actual Empirical Accuracy:** e.g., `0.917`.
       * **Calibration Error (Delta):** e.g., `+0.007`.
       * **Policy Mapping Rule:** Active mapping formula applied by the Policy Engine.
  4. **Human Override Statistics Section:**
     * Graphs showing frequency of human overrides across confidence buckets.
     * Identifies potential policy tuning candidates where human decisions diverge from agent suggestions.
* **State & API Contracts:**
  * Read Calibration Report: `GET /api/benchmarks/calibration`
  * Read Human Correction Stats: `GET /api/exceptions/corrections/stats`

---

### Page 14: Demo Safety Net & Trace Controller (`/demo-center`)
* **URL:** `/demo-center`
* **Target Roles:** Admin, Presenter
* **Purpose:** Control panel for presentation reliability, allowing immediate switching between live execution and deterministic replay of golden demo traces.
* **Page Sections:**
  1. **Execution Mode Master Toggle:**
     * Prominent 2-state toggle switch:
       * `[ LIVE EXECUTION ]` (Runs real asynchronous agents against FastAPI backend).
       * `[ REPLAY MODE ]` (Streams pre-recorded golden traces over SSE with zero stage risk).
     * Visual status banner warning the presenter of the active mode.
  2. **Golden Demo Scenarios Showcase:**
     * Three pre-configured golden demo scenario cards:
       * **Scenario 1: Payment Fragmentation (Anti-Fraud / CFO Escalation):**
         * Description: Invoice for ₹14,50,000 paid via 14 separate ₹1,00,000 disbursements to the same vendor.
         * Expected Outcome: Escalation to CFO, calibrated confidence 0.90, zero false-positive fraud hallucination.
         * Action: `[ Launch & Stream Scenario 1 ]`.
       * **Scenario 2: Three-Way Quantity Mismatch (Controller Review):**
         * Description: Invoice 1,000 units vs PO 800 units vs Receipt 760 units.
         * Expected Outcome: Staged hold on payment, calculated variance ₹3,84,000.
         * Action: `[ Launch & Stream Scenario 2 ]`.
       * **Scenario 3: Clean Multi-Currency Transaction (Autonomous Close):**
         * Description: Multi-currency invoice matching PO, Receipt, Bank, and GL with verified FX conversion.
         * Expected Outcome: Autonomous Level 3 resolution, clean audit trail.
         * Action: `[ Launch & Stream Scenario 3 ]`.
  3. **Recorded Traces Archive:**
     * Table of all captured execution traces:
       * Columns: Trace Title, Scenario Key, Total Steps, Total Duration, Golden Flag, Recorded Timestamp.
       * Actions: `[ Play Replay ]`, `[ Inspect JSON ]`, `[ Delete ]`.
  4. **Live Trace Recorder:**
     * Tool to record an ongoing or completed close run into a permanent replayable demo fixture (`POST /api/demo/record`).
* **State & API Contracts:**
  * Get Mode: `GET /api/demo/mode`
  * Set Mode: `POST /api/demo/mode` (Body: `{ "mode": "LIVE" | "REPLAY", "close_run_id": "..." }`)
  * List Traces: `GET /api/demo/traces`
  * Seed Traces: `POST /api/demo/traces/seed`
  * Stream Replay: `GET /api/demo/traces/{id}/stream`

---

### Page 15: Policy & Materiality Configuration (`/policies`)
* **URL:** `/policies`
* **Target Roles:** Controller, CFO, Admin
* **Purpose:** Manage the deterministic rules, materiality limits, and approval chains that govern autonomous actions.
* **Page Sections:**
  1. **Active Policy Version Banner:**
     * Displays current active policy version (e.g. `policy-v2`) and timestamp.
     * Version history dropdown to inspect historical policy configurations.
  2. **Materiality & Autonomy Gates Form:**
     * **Maximum Autonomous Resolution Cap:** Currency input (Default: `$50,000.00`). Discrepancies above this amount cannot be auto-resolved regardless of confidence.
     * **Minimum Calibrated Confidence for Level 3:** Percentage slider (Default: `95.0%`).
     * **Zero Money Movement Enforcement:** Locked toggle switch (`ALWAYS ON - System cannot execute direct wire/disbursements`).
     * **High-Impact Escalation Threshold:** Currency threshold requiring dual CFO sign-off (Default: `$100,000.00`).
  3. **Exception Type Policy Overrides:**
     * Matrix of all 16 exception types with configurable default autonomy:
       * E.g., `PAYMENT_FRAGMENTATION` ──► Locked to `Level 1: RECOMMEND / ESCALATE`.
       * E.g., `VENDOR_BANK_CHANGE_ANOMALY` ──► Locked to `Level 1: ESCALATE`.
       * E.g., `DUPLICATE_INVOICE` ──► Configurable (`STAGE` or `AUTO_RESOLVE if amount < $1,000`).
  4. **Approval Role Chains:**
     * Definition of required approvers per exception tier.
* **State & API Contracts:**
  * Read Policies: `GET /api/policies`
  * Versioned Audit: Updates generate versioned `policy_versions` database records.

---

### Page 16: Organization Profile & Multi-Currency FX Master (`/settings`)
* **URL:** `/settings`
* **Target Roles:** Admin
* **Purpose:** Manage corporate tenant metadata and deterministic foreign exchange (FX) rate tables.
* **Page Sections:**
  1. **Company Profile Tab:**
     * Legal Entity Name, Headquarters, Tax Registration / GSTIN, Base Reporting Currency (`USD`, `INR`, `EUR`, `GBP`), Fiscal Year End calendar.
  2. **Multi-Currency FX Rate Master Tab:**
     * Essential for multi-currency reconciliation compliance (Section 6.1 of Backend Context).
     * Currency Pairs Table:
       * Columns: Base Currency, Quote Currency, Effective Exchange Rate, Effective Date, Source (`ECB`, `Federal Reserve`, `RBI`), Actions.
       * Filter by currency pair (e.g., `USD/INR`, `EUR/USD`, `GBP/USD`).
       * `[ + Add Exchange Rate ]` Modal:
         * Inputs: Base Currency, Quote Currency, Decimal Rate (8 decimal places), Effective Date.
         * Validation: Rate must be positive decimal; auto-calculates reciprocal inverse rate.
  3. **User Management Tab:**
     * Directory of enterprise users, active status, assigned SOX roles (`VIEWER`, `ACCOUNTANT`, `CONTROLLER`, `CFO`, `ADMIN`).
* **State & API Contracts:**
  * Read Company: `GET /api/companies/{id}`
  * Read FX Rates: `GET /api/fx-rates`
  * Convert Amount Verification: Deterministic tool `convert_amount()`

---

## 7. Component & State Architecture Specifications

### 7.1 Client-Side State Management Hierarchy
```text
┌────────────────────────────────────────────────────────────┐
│ 1. URL & Search Query State (nuqs / React Router search)   │
│    Active tab, pagination, filters, search query, modal ID │
└─────────────────────────────┬──────────────────────────────┘
                              ▼
┌────────────────────────────────────────────────────────────┐
│ 2. Server Cache Layer (TanStack Query / React Query v5)    │
│    REST API data, automatic caching, garbage collection    │
└─────────────────────────────┬──────────────────────────────┘
                              ▼
┌────────────────────────────────────────────────────────────┐
│ 3. Real-Time Telemetry Store (Zustand / Event Bus Hook)    │
│    Active SSE connections, incoming agent steps, DAG pulses│
└─────────────────────────────┬──────────────────────────────┘
                              ▼
┌────────────────────────────────────────────────────────────┐
│ 4. Local UI State (React useState / useReducer)            │
│    Drawer open/close, drag-and-drop, form inputs, tooltips │
└────────────────────────────────────────────────────────────┘
```

### 7.2 Real-Time SSE Bus Hook (`useCloseRunStream`)
```typescript
interface StreamEvent {
  type: "close_run_state_change" | "close_task_state_change" | "agent_step" | "actions_executed" | "heartbeat";
  close_run_id: string;
  payload: any;
  timestamp: string;
}

export function useCloseRunStream(closeRunId: string, options?: { traceId?: string; playbackSpeed?: number }) {
  // 1. Establishes EventSource to /api/close-runs/{id}/stream
  // 2. Handles automatic reconnect with exponential backoff (1s, 2s, 5s, max 30s)
  // 3. Emits typed events to TanStack Query invalidation listeners:
  //    - "close_run_state_change" -> queryClient.invalidateQueries(["close-run", closeRunId])
  //    - "close_task_state_change" -> queryClient.invalidateQueries(["close-tasks", closeRunId])
  //    - "actions_executed" -> queryClient.invalidateQueries(["exceptions", closeRunId])
  // 4. Appends agent_step events to an in-memory streaming terminal buffer
}
```

### 7.3 Mathematical & Decimal Formatting Rules
To eliminate financial rounding errors and formatting ambiguity:
1. **Never use `Number.toFixed(2)` for financial calculations:** All math operations are calculated on the backend via Python `Decimal`. The frontend receives decimal strings and formats them using fixed-point formatting utilities.
2. **Tabular Numerals:** All financial amounts, unit quantities, and exchange rates must use monospace typography:
   ```css
   font-variant-numeric: tabular-nums;
   font-family: var(--font-mono);
   ```
3. **Accounting Negatives:** Negative variances must be displayed with parentheses rather than leading minus signs:
   * Positive Variance: `+$12,450.00` (Emerald Green)
   * Negative Variance: `($12,450.00)` (Rose Red)
   * Zero / Reconciled: `$0.00` (Slate Gray)
4. **Currency Symbols:** Multi-currency values must always include explicit ISO currency suffixes or symbols: `USD ($)`, `INR (₹)`, `EUR (€)`, `GBP (£)`.

### 7.4 Graph Visualizer Component Specifications
* **Library:** `@xyflow/react` (React Flow v12) or custom SVG Canvas.
* **Node Types:**
  * `EntityNode`: Represents Vendor, Customer, Bank Account, GL Account (Hexagonal or rounded rectangle).
  * `DocumentNode`: Represents Invoice, Purchase Order, Goods Receipt, Payment Voucher (Card style with document icon, ID, amount, date).
  * `DiscrepancyNode`: Represents Exception (Pulsing amber/red diamond).
* **Edge Types:**
  * Solid directional arrow: Standard relationship (`references`, `issued`, `paid_by`).
  * Dashed red arrow: Variance or mismatch detected (`qty_mismatch`, `amount_mismatch`).
* **Interactivity:**
  * Zoom, Pan, Fit-to-screen controls.
  * Node click opens entity drawer.
  * Hovering an edge highlights the calculation formula and variance in a floating tooltip.

---

## 8. Error Handling, Accessibility (a11y) & Resilience

### 8.1 API Error Handling & Idempotency
* **Idempotency Headers:** All state-mutating requests (`/approve`, `/reject`, `/escalate`, `/resolve`, `/reverse`, `/start`) generate a unique client-side UUID sent in the `Idempotency-Key` HTTP header. This prevents duplicate financial actions if the user double-clicks or experiences network latency.
* **Global Error Banner:** Catches HTTP 400/409/500 errors and renders human-readable explanations (e.g., "Cannot start close run: Concurrency conflict. Run was updated by another user").
* **Optimistic UI with Rollback:** Staging approvals optimistically update the UI to `RESOLVED` while displaying an execution spinner; if the API rejects the action, the card automatically rolls back to `STAGED` and surfaces a toast alert.

### 8.2 Accessibility (WCAG 2.1 AA Compliance)
* **Contrast Ratios:** All text and financial badges maintain a minimum 4.5:1 contrast ratio against dark and light mode backgrounds.
* **Screen Reader Accessibility:** All status pills and badges include descriptive `aria-label` tags (e.g. `aria-label="Severity Critical: Requires immediate CFO authorization"`).
* **Keyboard Navigation:** Full keyboard navigation support across data tables and tabs using `Tab`, `Shift+Tab`, `Arrow` keys, and `Enter` for row expansion.
* **Focus Trap Modals:** Approval and Reversal dialogs trap keyboard focus and dismiss cleanly on `Escape`.

---

## 9. Verification & Acceptance Checklist

Before declaring the frontend implementation complete, verify the following acceptance criteria:

- [ ] **No Landing Page Content:** The application starts strictly at authenticated routes (`/tenants` or `/close-runs`). Zero marketing hero sections exist.
- [ ] **All Routes Functional:** Every route specified in Section 3 resolves correctly with dedicated error boundaries and layout wrappers.
- [ ] **Role-Based Adaptation:** Switching persona between Viewer, Accountant, Controller, CFO, and Admin dynamically adjusts action permissions and button states.
- [ ] **Real-Time Telemetry:** The SSE stream displays live agent steps, tool executions, and state changes without requiring page refreshes.
- [ ] **Forensic Evidence Dossier:** Exception detail pages display the side-by-side evidence cards, deterministic calculation box, verified citations, and interactive relationship graph.
- [ ] **Non-Destructive Reversal Path:** Executed actions can be reversed through `/api/exceptions/{id}/reverse`, creating linked reversal audit events and reopening the exception.
- [ ] **Calibrated Confidence Display:** Confidence badges clearly indicate both raw and calibrated values (e.g. `Raw: 0.97 | Calibrated: 0.91`).
- [ ] **Demo Mode Switch:** Presenters can toggle between `LIVE` and `REPLAY` modes, adjust playback speed, and run pre-recorded golden demo scenarios seamlessly.
- [ ] **CFO-Bench & Calibration Studio:** All 35 injected ground-truth benchmark scenarios and the reliability curve render with complete accuracy metrics.
- [ ] **Certified Close Package:** Clean readiness check passes only when 10 close tasks are complete and zero blocking exceptions remain.
