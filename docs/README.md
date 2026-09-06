# Vexa Documentation Index

Welcome to the technical documentation for **Vexa — Autonomous Office of the CFO**.

This documentation reflects the actual production implementation in the repository. Vexa is an evidence-first autonomous finance operations backend engineered to automate the month-end close with mathematical rigor, independent verification, and controlled autonomy.

---

## Documentation Structure

```
docs/
├── architecture/          # High-level system design, workflows & safety models
├── components/            # Deep-dives into individual backend engines & subsystems
├── financial-engine/      # Deterministic reconciliation rules, matching & materiality
├── agents/                # Autonomous agent specifications, tools & LLM safety bounds
├── api/                   # REST API surface, OpenAPI schemas & SSE streaming contracts
├── operations/            # Setup, deployment, testing, configuration & troubleshooting
└── decisions/             # Architecture Decision Records (ADRs)
```

---

## Navigation Guide

### 1. [Architecture](./architecture/overview.md)
Understand the end-to-end design, invariants, and multi-agent coordination principles.
* [System Overview](./architecture/overview.md) — High-level architecture and financial processing pipeline.
* [System Architecture](./architecture/system-architecture.md) — Subsystem boundaries, responsibilities, and safety boundaries.
* [Close Workflow](./architecture/close-workflow.md) — 10-task DAG orchestration, state machine, and CAS concurrency control.
* [Agent Architecture](./architecture/agent-architecture.md) — Agent roles, tool boundaries, and "LLMs reason; code calculates" principle.
* [Evidence Graph](./architecture/evidence-graph.md) — Directed knowledge graph, 20 node types, 21 edge types, and PageRank relevance scoring.
* [Verification & Safety](./architecture/verification-and-safety.md) — 3-gate independent verification, citation guards, and circuit breakers.
* [Autonomy Model](./architecture/autonomy-model.md) — Levels 0–3, policy gates, and human escalation thresholds.
* [Data Flow](./architecture/data-flow.md) — End-to-end data lifecycle from bank transaction to close package.

### 2. [Components](./components/close-workflow.md)
Detailed engineering specifications for core backend packages.
* [Close Workflow Controller](./components/close-workflow.md) — DAG resolver, task executor, and close readiness engine.
* [Reconciliation Engine](./components/reconciliation.md) — 10-pass deterministic matching pipeline.
* [Investigation Engine](./components/investigation.md) — Dossier builder, hypothesis generator, and citation validator.
* [Evidence Graph Subsystem](./components/evidence-graph.md) — In-memory traversal, graph serialization, and tenant isolation.
* [Independent Verification](./components/verification.md) — Calculation verifier, completeness checker, and policy gates.
* [Actions & Reversals](./components/actions.md) — Safe action execution, staged proposals, and compensating journal entry reversals.
* [Audit & SOX Controls](./components/audit-controls.md) — Immutable append-only audit trail and deterministic SOX control mapping.
* [Streaming & SSE Bus](./components/streaming.md) — Server-Sent Events bus, event taxonomy, and live frontend telemetry.
* [Benchmarks Runner](./components/benchmarks.md) — 35-scenario CFO benchmark runner, evaluation harness, and calibration reports.
* [Demo System](./components/demo-system.md) — Live execution vs. real-time replay player and trace recorder.
* [Database & Storage](./components/database.md) — PostgreSQL schema, repository layer, and multi-tenant scoping.

### 3. [Financial Engine](./financial-engine/reconciliation-rules.md)
The deterministic mathematical core of Vexa.
* [Reconciliation Rules](./financial-engine/reconciliation-rules.md) — Exact 2-way/3-way matching, tolerances, and multi-currency FX.
* [Matching Strategy](./financial-engine/matching-strategy.md) — Heuristics, multi-pass matching sequence, and unbilled receipts.
* [Materiality](./financial-engine/materiality.md) — Absolute, relative (% of balance), and per-account materiality thresholds.
* [Exception Taxonomy](./financial-engine/exception-taxonomy.md) — 16 canonical exception types and severity classifications.
* [Data Quality](./financial-engine/data-quality.md) — Ingestion gap detection, GL sequence discontinuities, and feed integrity.

### 4. [Agents](./agents/investigation-agent.md)
Autonomous reasoning specialists and safety wrappers.
* [CFO Investigation Agent](./agents/investigation-agent.md) — Root-cause discovery, evidence gathering, and dossier inspection.
* [Financial Analyst Agent](./agents/analyst-agent.md) — Variance analysis, burn rate, cash impact, and close summaries.
* [Independent Verification Agent](./agents/verification-agent.md) — 3-gate verifier ensuring calculation and policy correctness.
* [Action Agent](./agents/action-agent.md) — Executing permitted actions with strict money-movement prohibition.
* [LLM Safety & Guardrails](./agents/llm-safety.md) — Provider abstraction, citation validation, deterministic fallback, and timeouts.

### 5. [REST API](./api/overview.md)
Complete endpoint references, request/response models, and status codes.
* [API Overview](./api/overview.md) — Authentication, tenancy headers, and common error responses.
* [Close Runs API](./api/close-runs.md) — Lifecycle control, task inspection, close packages, and SSE streaming.
* [Exceptions API](./api/exceptions.md) — Exception queries, dossiers, approvals, rejections, escalations, and reversals.
* [Agent Runs API](./api/agents.md) — Agent execution history and granular step telemetry.
* [Audit API](./api/audit.md) — SOX audit event streams and control verification logs.
* [Benchmarks API](./api/benchmarks.md) — Triggering benchmark evaluations and retrieving calibration reports.
* [Demo API](./api/demo.md) — Toggling LIVE / REPLAY modes and trace replay streaming.

### 6. [Operations](./operations/local-development.md)
Guides for engineers and operators running Vexa.
* [Local Development](./operations/local-development.md) — Quickstart, environment setup, and dependency management with uv.
* [Configuration Reference](./operations/configuration.md) — Environment variables, settings defaults, and tuning flags.
* [Database Operations](./operations/database.md) — PostgreSQL provisioning, Alembic migrations, and seed scripts.
* [Testing Guide](./operations/testing.md) — Running unit, integration, and tenant isolation test suites.
* [Troubleshooting](./operations/troubleshooting.md) — Common error patterns, database locks, and agent timeout debugging.

### 7. [Architecture Decision Records (ADRs)](./decisions/001-deterministic-financial-truth.md)
Key architectural trade-offs and design choices.
* [ADR 001: Deterministic Financial Truth](./decisions/001-deterministic-financial-truth.md) — Why LLMs never calculate balances or verify equations.
* [ADR 002: Evidence-First Agents](./decisions/002-evidence-first-agents.md) — Bounding agent reasoning to explicit graph dossiers.
* [ADR 003: Independent Verification](./decisions/003-independent-verification.md) — Separating hypothesis generation from independent verification.
* [ADR 004: Controlled Autonomy](./decisions/004-controlled-autonomy.md) — 4-tier autonomy with calibrated confidence and materiality gates.
* [ADR 005: Live vs Replay Demo Architecture](./decisions/005-live-replay-demo.md) — Eliminating live presentation failure modes through deterministic trace replays.

### 8. [Frontend Web Application](https://vexa-workspace.vercel.app/)
Authenticated client architecture, workflows, routes, and screen specifications.
* [Live Frontend Workspace](https://vexa-workspace.vercel.app/) — High-density financial command center for month-end close execution, real-time SSE telemetry, and certified close package generation.



