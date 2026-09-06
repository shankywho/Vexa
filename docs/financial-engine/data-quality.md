# Data Quality & Ingestion Integrity

Before executing accounting reconciliations, Vexa validates the structural completeness of financial data feeds to prevent closing books over incomplete records.

---

## 1. Data Quality Checks

Implemented in [`detect_data_ingestion_gaps`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-7/backend/app/reconciliation/rules.py#L320):

### 1.1 Bank Feed Continuity Check
* **Rule:** Treasury feeds must contain unbroken date coverage for the close period.
* **Detection:** The engine sorts bank transactions chronologically and flags any calendar gap exceeding 3 business days without transactions.
* **Exception:** Emits `DATA_INGESTION_GAP` with impact equal to the missing period's estimated cash flow.

### 1.2 General Ledger Sequence Discontinuities
* **Rule:** Journal entries must follow an unbroken serial numbering sequence (e.g. `JE-1001`, `JE-1002`, `JE-1003`).
* **Detection:** Missing sequence numbers indicate unposted batches, dropped ERP payloads, or manual database deletions.
* **Exception:** Emits `DATA_INGESTION_GAP`.

---

## 2. Close Blocking Invariant

`DATA_INGESTION_GAP` is defined as a **Close-Blocking Exception**:
* The Close Run cannot advance from `INGESTING` or `RECONCILING` to `READY_TO_CLOSE` while any data ingestion gap remains unresolved.
* Autonomy Level is locked to `RECOMMEND` (Level 1), requiring data engineering or IT intervention to restore feed completeness.
