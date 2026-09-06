# Materiality Framework

In financial auditing, materiality governs whether an omission or misstatement could reasonably influence economic decisions. Vexa operationalizes materiality through deterministic policy thresholds.

---

## 1. Materiality Dimensions

Vexa evaluates three concurrent materiality dimensions in [`PolicyGateVerifier`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-7/backend/app/verification/engine.py#L290):

```
                                  Materiality Evaluation
                                            │
        ┌───────────────────────────────────┼───────────────────────────────────┐
        ▼                                   ▼                                   ▼
[ 1. Absolute Cap ]                [ 2. Relative Ratio ]             [ 3. Per-Account Override ]
  Impact <= $50,000                  Impact <= 5.0% of Balance         Custom limits for sensitive lines
```

### 1.1 Absolute Materiality Threshold
* **Default:** `max_auto_resolution_amount = Decimal("50000.00")`
* **Rule:** If the financial variance of an exception exceeds $50,000, autonomous execution is blocked. The proposal is staged for Controller sign-off (`AutonomyLevel.STAGE`).

### 1.2 Relative Materiality Ratio
* **Default:** `materiality_pct_of_account_balance = Decimal("5.0")` (5%)
* **Rule:** Even if an amount is under $50,000, if the variance represents $>5\%$ of the underlying general ledger account's ending balance:
  $$\text{Ratio} = \frac{|\text{Variance}|}{|\text{Account Balance}|} \times 100 > 5.0\%$$
  the variance is deemed material relative to that account and is routed to human review.

### 1.3 Per-Account Materiality Overrides
Companies can specify stricter tolerances for sensitive accounts (e.g. Cash, Executive Travel, Legal Reserves) via `policy.account_materiality_thresholds`:
```json
{
  "1000": "5000.00",   // Cash & Equivalents: strict $5k cap
  "5010": "10000.00",  // Legal Expenses: strict $10k cap
  "2000": "50000.00"   // Accounts Payable: standard $50k cap
}
```

---

## 2. Qualitative Materiality (Zero-Tolerance Overrides)

Certain accounting events are **qualitatively material** regardless of dollar value:
* **Vendor Master Bank Account Modifications:** Subject to mandatory CFO review (`AP-07`).
* **Unrecorded Cash Debits / Credits:** Cash discrepancies cannot be written off autonomously (`BANK-01`).
* **Data Feed Ingestion Gaps:** Incomplete date intervals block the entire close (`CLOSE-01`).
