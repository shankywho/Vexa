# Reconciliation Engine Component Deep Dive

The Reconciliation Engine is Vexa's deterministic mathematical core. It evaluates six financial data streams (Invoices, POs, Receipts, Payments, Bank Statements, and Journal Entries) across 10 deterministic passes without relying on LLMs for calculations or matching decisions.

---

## 1. Package Structure

Located at [`backend/app/reconciliation/`](../../backend/app/reconciliation/):

```
app/reconciliation/
├── __init__.py
├── config.py            # ReconciliationConfig (Tolerances, thresholds, flags)
├── engine.py            # DeterministicReconciliationEngine (10 matching passes)
├── rules.py             # Matching algorithms, 3-way eval, gap detectors
└── schemas.py           # Output contracts: ReconciliationItemResult, Summary
```

---

## 2. The 10 Reconciliation Passes

### Pass 1: Three-Way Matching & Procurement Reconciliations
* **Target:** Billed Invoices ↔ Authorized Purchase Orders ↔ Goods Receipts.
* **Logic:** Evaluates unit prices, quantities, item descriptions, and totals. Supports multi-currency conversion via [`FxService`](../../backend/app/services/fx_service.py).
* **Outputs:**
  - `MATCHED`: Billed amount matches PO within tolerance ($\le \$0.01$ or $1\%$).
  - `MISMATCH`: Quantity or price variance $\rightarrow$ generates `PO_MISMATCH` or `RECEIPT_MISMATCH`.
  - `MISSING`: Missing PO reference on non-service invoice $\rightarrow$ generates `MISSING_DOCUMENT`.

### Pass 2: Unbilled Goods Receipts (GRNI Accrual Candidates)
* **Target:** Warehouse Goods Receipts without matching vendor bills.
* **Logic:** Flags delivered inventory awaiting invoices to ensure compliance with matching principles.
* **Outputs:** Generates `MISSING_DOCUMENT` (GRNI Accrual Candidate) with financial impact equal to the PO value.

### Pass 3: Duplicate Invoice Detection
* **Target:** Vendor invoices grouped by `(vendor_id, invoice_number)`.
* **Logic:** Identifies duplicate submissions from the same vendor.
* **Outputs:** Flags second and subsequent occurrences as `DUPLICATE_INVOICE` with the duplicate total as the financial impact.

### Pass 4: Payment ↔ Invoice Matching
* **Target:** Billed Invoices ↔ Disbursement Payments.
* **Logic:**
  - Identifies single and split payments settling an invoice.
  - Detects duplicate payments (multiple disbursements against a single bill).
  - Detects payment fragmentation (multiple small disbursements within a narrow settlement window).
* **Outputs:** Generates `DUPLICATE_PAYMENT`, `PAYMENT_FRAGMENTATION`, or `PAYMENT_MISMATCH`.

### Pass 5: Unusual Vendor Activity
* **Target:** Vendor billing history and volume trends.
* **Logic:** Flags sudden spikes or single massive invoices lacking historical baseline.
* **Outputs:** Generates `UNUSUAL_VENDOR_ACTIVITY` with high severity.

### Pass 6: Bank Statement Transactions Matching
* **Target:** Bank Statement Transactions ↔ Recorded Payments & Customer Invoices.
* **Logic:**
  - Matches bank debits/credits against ERP payment records.
  - Identifies customer short-remittances (Accounts Receivable variances).
  - Flags unrecorded cash entries (deposits or withdrawals lacking accounting vouchers).
* **Outputs:** Generates `AR_MISMATCH`, `CASH_ANOMALY`, or `BANK_GL_MISMATCH`.

### Pass 7: General Ledger, GL Mapping & Accruals
* **Target:** Journal Entries and Chart of Accounts.
* **Logic:**
  - Validates double-entry mathematical balance: $\sum \text{Debits} == \sum \text{Credits}$.
  - Validates account type compatibility (e.g. flagging expense items charged to balance sheet asset lines).
  - Evaluates accrual reversals and period-end cutoff dates.
* **Outputs:** Generates `GL_MAPPING_ERROR` or `ACCRUAL_ANOMALY`.

### Pass 8: Clean Six-Way Match Verification
* **Target:** Completely reconciled standard transactions.
* **Logic:** Verifies that Invoice, PO, Receipt, Payment, Bank Transaction, and GL Entry exist in perfect balance.
* **Outputs:** Emits `MATCHED` item with impact `$0.00`, establishing a baseline for auto-resolution.

### Pass 9: Vendor Bank Account Change Anomaly Detection
* **Target:** Vendor Master Records ↔ Scheduled / Cleared Disbursements.
* **Logic:** Compares `vendor.bank_account_id` with `vendor.previous_bank_account_id` and timestamp `vendor.bank_account_changed_at`.
* **Outputs:** If a payment cleared to a recently modified bank account without secondary verification, generates `VENDOR_BANK_CHANGE_ANOMALY` (SOX Control `AP-07`).

### Pass 10: Data Ingestion Gap Detection
* **Target:** Bank feed date sequences and General Ledger entry number series.
* **Logic:** Detects missing calendar dates in bank feeds or non-sequential gaps in GL journal entry numbering.
* **Outputs:** Generates `DATA_INGESTION_GAP` (SOX Control `CLOSE-01`).

---

## 3. Structured Output Contract

The reconciliation engine outputs a [`ReconciliationRunSummary`](../../backend/app/reconciliation/schemas.py#L88):

```json
{
  "company_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "close_run_id": "c1f7a4e0-7982-41b2-bf23-88229bbf9301",
  "total_items_processed": 142,
  "total_matched": 107,
  "total_partial": 0,
  "total_mismatch": 33,
  "total_missing": 2,
  "total_exceptions": 35,
  "total_financial_impact": "1948200.00",
  "detected_exception_types": {
    "DUPLICATE_INVOICE": 5,
    "PO_MISMATCH": 4,
    "RECEIPT_MISMATCH": 3,
    "DUPLICATE_PAYMENT": 4,
    "PAYMENT_FRAGMENTATION": 2,
    "UNUSUAL_VENDOR_ACTIVITY": 3,
    "MISSING_DOCUMENT": 3,
    "GL_MAPPING_ERROR": 3,
    "ACCRUAL_ANOMALY": 2,
    "AR_MISMATCH": 2,
    "CASH_ANOMALY": 2,
    "VENDOR_BANK_CHANGE_ANOMALY": 1,
    "DATA_INGESTION_GAP": 1
  }
}
```
