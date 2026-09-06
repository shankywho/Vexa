# End-to-End Financial Data Flow

This document details the complete data lifecycle as transactions flow from primary ingestion sources through reconciliation, investigation, independent verification, and close package assembly.

---

## 1. Complete Financial Data Lifecycle

```mermaid
sequenceDiagram
    autonumber
    participant Bank as Bank Statements & Feeds
    participant ERP as ERP & Procurement (Invoices, POs, Receipts)
    participant DB as PostgreSQL (Relational Tables)
    participant Recon as 10-Pass Reconciliation Engine
    participant Graph as Evidence Graph Builder
    participant Invest as Investigation Agent
    participant Verif as Independent Verification Engine
    participant Action as Action Service
    participant Audit as Audit Trail
    participant Package as Close Package

    Note over Bank,ERP: Phase 1: Ingestion & Seeding
    Bank->>DB: Ingest Bank Accounts & Transactions
    ERP->>DB: Ingest Invoices, POs, Goods Receipts, Vendors, GL
    
    Note over DB,Recon: Phase 2: Reconciliation
    Recon->>DB: Batch Load Financial Records (Tenant Scoped)
    Recon->>Recon: Execute Passes 1-10 (3-Way, FX, Duplicates, Gaps)
    Recon->>DB: Persist ReconciliationResults & ReconciliationMatches
    Recon->>DB: Persist Detected ExceptionRecords

    Note over DB,Invest: Phase 3: Graph Assembly & Investigation
    Graph->>DB: Query Relational Entities
    Graph->>Graph: Construct FinancialEvidenceGraph (20 Node Types)
    loop For Each ExceptionRecord
        Graph->>Graph: Run Personalized PageRank (4 Hops)
        Graph->>Invest: Package Bounded EvidenceDossier
        Invest->>Invest: Formulate Root-Cause & Recommendation
        Invest->>Invest: Validate Citations against Dossier Whitelist
        Invest->>DB: Persist AgentRun & AgentStep Telemetry

        Note over Invest,Action: Phase 4: Verification & Autonomy
        Invest->>Verif: Submit VerificationRequest
        Verif->>Verif: Gate 1: Recalculate Variance from DB Rows
        Verif->>Verif: Gate 2: Check Evidence Completeness
        Verif->>Verif: Gate 3: Evaluate Materiality & Policy
        Verif-->>Action: VerificationResult (AutonomyLevel)
        
        alt AutonomyLevel == EXECUTE (Level 3)
            Action->>DB: Execute Compensating Journal Entry
            Action->>DB: Mark Exception AUTO_RESOLVED
        else AutonomyLevel in (STAGE, RECOMMEND)
            Action->>DB: Stage Proposal (Awaiting Controller/CFO)
        end
        Action->>Audit: Record AuditEvent (SOX Control Tagged)
    end

    Note over DB,Package: Phase 5: Close Packaging
    Package->>DB: Collect Reconciliation Summaries, Exceptions, Audit Log
    Package->>Package: Assemble ClosePackage JSON & Export Artifacts
```

---

## 2. Transformation Pipeline Stages

### Stage 1: Ingestion & Relational Persistence
* **Source Systems:** Treasury bank feeds, Accounts Payable invoices, procurement Purchase Orders, warehouse Goods Receipts, and General Ledger journal batches.
* **Storage Contract:** Relational tables in PostgreSQL (`invoices`, `purchase_orders`, `bank_transactions`, `journal_entries`, etc.) with strict foreign keys and non-nullable `company_id`.
* **Integrity Guard:** Floating-point numbers are forbidden; monetary values are stored in `Numeric(18, 4)` and operated on via Python `Decimal`.

### Stage 2: Reconciliation & Exception Generation
* **Processing:** Deterministic batch evaluation across 10 passes.
* **Output:**
  - Matched items generate `ReconciliationMatch` records.
  - Discrepancies generate `ExceptionRecord` entries with initial `financial_impact`, `severity`, and `exception_type`.

### Stage 3: Graph Construction & Dossier Bounding
* **Processing:** The `FinancialEvidenceGraphBuilder` queries tenant rows and instantiates an in-memory graph.
* **Extraction:** For each exception, a bounded `EvidenceDossier` is built containing:
  - Whitelist of `valid_record_ids`
  - Primary offending record
  - Up to 4-hop related records and edges
  - Top 10 ranked evidence nodes

### Stage 4: Agent Reasoning & Citation Verification
* **Processing:** The CFO Investigation Agent receives the dossier and outputs:
  - Structured facts (each citing an explicit record ID)
  - Inferences (each citing supporting evidence)
  - Root cause explanation
  - Recommended action
* **Guard:** `CitationValidator` scans all cited IDs against the dossier whitelist. Any unrecognized ID is flagged as a hallucination, triggering severe confidence penalties.

### Stage 5: Verification, Action & Reversal
* **Processing:** `VerificationEngine` independently computes the variance arithmetic.
* **Gatekeeper:** `PolicyGateVerifier` determines whether the item qualifies for `AUTO_RESOLVE` ($\le \$50k$, calibrated confidence $\ge 0.95$) or requires human staging/escalation.
* **Audit:** Every action logs an append-only `AuditEvent` with actor, prompt version, policy version, and SOX control ID (`AP-03`, `PROC-04`, etc.).

### Stage 6: Close Package Assembly
* **Output:** A sealed, immutable close package containing close run metrics, task states, exception tallies, audit footprints, and calibration reports.
