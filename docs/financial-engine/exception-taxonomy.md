# Exception Taxonomy

Vexa classifies all financial variances into 16 canonical exception types defined in [`app.domain.enums.ExceptionType`](../../backend/app/domain/enums.py#L53).

---

## 1. Complete Exception Taxonomy

| Exception Type | Domain Category | Typical Severity | Default SOX Control | Description |
| :--- | :--- | :---: | :---: | :--- |
| **`DUPLICATE_INVOICE`** | Accounts Payable | `HIGH` | `AP-03` | Same invoice number submitted multiple times by a vendor. |
| **`PO_MISMATCH`** | Procurement | `HIGH` | `PROC-04` | Price or quantity discrepancy between Invoice and Purchase Order. |
| **`RECEIPT_MISMATCH`** | Warehousing / AP | `HIGH` | `PROC-04` | Billed quantity exceeds physical units confirmed on Goods Receipt. |
| **`PAYMENT_MISMATCH`** | Disbursements | `MEDIUM` | `BANK-01` | Amount cleared at bank differs from ERP payment voucher. |
| **`BANK_GL_MISMATCH`** | Treasury | `HIGH` | `BANK-01` | Unreconciled difference between bank statement and GL cash account. |
| **`MISSING_DOCUMENT`** | Procurement / GRNI | `HIGH` | `PROC-04` | Invoice lacking approved PO, or unbilled Goods Receipt (GRNI). |
| **`DUPLICATE_PAYMENT`** | Disbursements | `CRITICAL` | `AP-03` | Multiple payments disbursed against the same invoice/vendor. |
| **`UNUSUAL_VENDOR_ACTIVITY`** | Vendor Master | `HIGH` | `AP-07` | Sudden volume surge or unprecedented invoice amount. |
| **`PAYMENT_FRAGMENTATION`** | Fraud / Compliance | `CRITICAL` | `AP-03` | Multiple disbursements structured just below approval thresholds. |
| **`AR_MISMATCH`** | Accounts Receivable | `MEDIUM` | `REV-01` | Customer remittance short-pays outstanding invoice. |
| **`ACCRUAL_ANOMALY`** | General Ledger | `MEDIUM` | `EXP-01` | Unreversed accruals or improper timing cutoff. |
| **`GL_MAPPING_ERROR`** | Accounting Policy | `HIGH` | `GL-02` | Out-of-balance journal entry or improper account type classification. |
| **`CASH_ANOMALY`** | Treasury | `CRITICAL` | `BANK-01` | Unidentified cash deposit or withdrawal lacking ledger voucher. |
| **`VENDOR_BANK_CHANGE_ANOMALY`** | Fraud Defense | `CRITICAL` | `AP-07` | Payment routed to newly modified vendor bank account. |
| **`DATA_INGESTION_GAP`** | Data Quality | `CRITICAL` | `CLOSE-01` | Missing calendar dates in bank feeds or non-sequential GL numbers. |
| **`OTHER`** | Miscellaneous | `LOW` | — | Unclassified accounting anomalies. |

---

## 2. Severity Classification Guidelines

* **`CRITICAL`:** Requires immediate executive notification. Hard blocker for close completion. Includes fraud signals, vendor bank changes, data ingestion gaps, and payment fragmentation.
* **`HIGH`:** Material variances ($> \$50,000$), unapproved PO mismatches, double-entry GL imbalances. Requires Controller review.
* **`MEDIUM`:** Standard operational variances (AR short-remittance, timing differences, minor accrual shifts).
* **`LOW`:** Immaterial rounding differences, immaterial fee variances ($\le \$10.00$).
