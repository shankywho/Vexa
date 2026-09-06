# Reconciliation Rules & Tolerances

This document details the deterministic rules, tolerances, multi-currency conversions, and math governing the Vexa reconciliation engine.

---

## 1. Rule Catalog & Tolerances

All tolerances are configured in [`app/reconciliation/config.py`](../../backend/app/reconciliation/config.py):

| Rule / Field | Default Tolerance | Description |
| :--- | :---: | :--- |
| **`amount_tolerance_absolute`** | `$0.01` | Absolute difference allowed between record totals. |
| **`amount_tolerance_relative`** | `0.01` (1%) | Percentage variance allowed between record totals. |
| **`date_tolerance_days`** | `7` days | Maximum calendar gap between payment and bank clearance. |
| **`tax_tolerance_absolute`** | `$1.00` | Rounding tolerance for sales tax and VAT line items. |
| **`fx_tolerance_relative`** | `0.005` (0.5%)| Currency rounding tolerance during foreign exchange conversions. |

---

## 2. Three-Way Matching Algorithm

Implemented in [`evaluate_three_way_match`](../../backend/app/reconciliation/rules.py#L30):

```
Invoice (Total, Lines)
    ├── Compared with Purchase Order (Authorized Amount & Lines)
    └── Compared with Goods Receipts (Warehouse Quantities Received)
```

### Evaluation Steps:
1. **Purchase Order Authorization:**
   If `Invoice.po_id` is missing and invoice is non-recurring, emits `MISSING_DOCUMENT`.
2. **Multi-Currency Normalization:**
   If `Invoice.currency != PO.currency`, calls [`FxService.convert`](../../backend/app/services/fx_service.py) on `Invoice.invoice_date`.
3. **Total Price Variance:**
   $$\Delta_{price} = | \text{Invoice.total} - \text{PO.total} |$$
   If $\Delta_{price} > 0.01$ and $\frac{\Delta_{price}}{\text{PO.total}} > 0.01$, flags `PO_MISMATCH`.
4. **Goods Receipt Quantity Matching:**
   $$\text{Quantity Discrepancy} = \text{Billed Quantity} - \sum \text{Received Quantity}$$
   If goods receipts confirm fewer items than billed, flags `RECEIPT_MISMATCH` with financial impact equal to:
   $$\text{Impact} = \text{Quantity Discrepancy} \times \text{Unit Price}$$

---

## 3. Bank Statement to Payment Matching

Implemented in [`match_bank_tx_to_payments`](../../backend/app/reconciliation/rules.py#L180):
* **Amount Comparison:** Matches bank line amount against payment disbursement amount within `$0.01`.
* **Date Window:** Settlement date must fall within $\pm 7$ calendar days of `Payment.payment_date`.
* **Reference Heuristics:** Matches check numbers, wire beneficiary references, or invoice numbers embedded in bank line descriptions.
* **Exceptions:**
  - Unmatched bank debit $\rightarrow$ `BANK_GL_MISMATCH`.
  - Unmatched bank credit with no customer AR voucher $\rightarrow$ `CASH_ANOMALY`.
  - Customer remittance less than expected invoice $\rightarrow$ `AR_MISMATCH`.

---

## 4. General Ledger Double-Entry Rules

Implemented in [`verify_journal_entry_balance`](../../backend/app/reconciliation/rules.py#L260):
$$\sum \text{Debits} - \sum \text{Credits} = 0.00$$
If the imbalance exceeds `$0.00`, the transaction violates fundamental accounting law and is flagged as `GL_MAPPING_ERROR`.
