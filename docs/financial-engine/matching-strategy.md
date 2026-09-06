# Matching Strategy

This document describes the multi-tiered matching strategies used by Vexa to reconcile records across disparate accounting databases.

---

## 1. Matching Hierarchy

Vexa employs a layered matching sequence designed to maximize deterministic precision before applying heuristic rules:

```
Tier 1: Exact Primary Key / Foreign Key Match (Invoice.po_id == PO.id)
                          │ (If Unmatched)
                          ▼
Tier 2: Exact Document Reference Match (Invoice.po_number == PO.po_number)
                          │ (If Unmatched)
                          ▼
Tier 3: 3-Way Procurement Match (Invoice Lines <-> PO Lines <-> Receipt Lines)
                          │ (If Unmatched)
                          ▼
Tier 4: Bank Statement Settlement Window Match (+/- 7 days, Counterparty, Amount)
                          │ (If Unmatched)
                          ▼
Tier 5: Exception Generation & Unbilled Candidate Flagging
```

---

## 2. Two-Way vs Three-Way Matching

* **Two-Way Match:** Applied to service and software subscriptions (e.g. AWS, Slack) where physical goods are not delivered. Compares Invoice to Purchase Order / Contract terms.
* **Three-Way Match:** Applied to tangible inventory and equipment. Compares Invoice, Purchase Order, and warehouse Goods Receipts.
* **Unbilled Receipts (GRNI):** Warehouse receipts that have no matching bill generate Goods-Receipt-Not-Invoiced accrual entries to prevent understated liabilities.

---

## 3. Duplicate Detection Strategy

Duplicate detection runs at two operational levels:
1. **Duplicate Invoices:** Same `vendor_id` and `invoice_number` received more than once.
2. **Duplicate Payments:** Multiple disbursements clearing for the exact same amount against the same vendor within a 14-day window.
3. **Fragmented Payments (Structuring):** A cluster of payments where individual amounts fall just below an internal approval threshold (e.g. ₹1,00,000 vs ₹10,00,000 threshold), but aggregate to an outstanding invoice balance.
