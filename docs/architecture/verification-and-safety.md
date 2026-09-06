# Verification and Safety Architecture

Vexa is engineered under a zero-trust model for artificial intelligence in corporate finance. Every autonomous action, variance deduction, and policy recommendation must pass through independent, deterministic verification layers before executing or reaching human reviewers.

---

## 1. The Verification & Safety Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│               1. CFO Investigation Agent                    │
│   (Hypothesis Generation · Root-Cause Analysis · Citations) │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│            2. Citation Hallucination Guard                  │
│       (Validates all cited IDs against Dossier Whitelist)   │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│           3. Independent Verification Engine                │
│   ├── Gate 1: Independent Calculation Verifier              │
│   │   (Direct DB recalculation; zero trust in LLM claims)   │
│   └── Gate 2: Evidence Completeness Verifier                │
│       (Confirms required documents present & valid)         │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│             4. Empirical Confidence Calibrator              │
│   (Maps raw score to ground-truth buckets; applies penalties)│
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 5. Corporate Policy Gate                    │
│   ├── Materiality Cap: Impact <= $50,000                    │
│   ├── Relative Materiality: Impact <= % of Account Balance  │
│   ├── Calibrated Confidence >= 0.95                         │
│   └── Hard Escalation Overrides (Fraud, Bank Changes, Gaps) │
└──────────────────────────────┬──────────────────────────────┘
                               │
              ┌────────────────┴────────────────┐
              ▼                                 ▼
┌───────────────────────────┐     ┌───────────────────────────┐
│     Autonomy Level 3      │     │    Autonomy Level 1 / 2   │
│       AUTO_RESOLVE        │     │  STAGE / ESCALATE TO CFO  │
│ (Compensating Adjustment) │     │ (Human Review Required)   │
└───────────────────────────┘     └───────────────────────────┘
```

---

## 2. Gate 1: Independent Calculation Verification

The [`IndependentCalculationVerifier`](../../backend/app/verification/engine.py#L18) recalculates financial variances directly from source database records without inspecting the agent's textual narrative.

### Verification Logic:
1. **Clean Transactions:** If an exception is identified as a clean match, recalculated impact **must** equal `Decimal("0.00")`. Any recorded variance $> 0.01$ fails verification.
2. **Procurement Discrepancies (PO / Receipt Mismatch):**
   $$\Delta_{calc} = | \text{Invoice.total} - \text{PO.total} |$$
   The recalculated difference is compared against `ExceptionRecord.financial_impact`. If $|\Delta_{calc} - \text{Impact}| > 0.01$, verification fails.
3. **Banking & Disbursements (Bank-to-GL, Payment Mismatch):**
   $$\Delta_{calc} = | \text{BankTransaction.amount} - \text{Payment.amount} |$$
   If no payment exists, $\Delta_{calc} = \text{BankTransaction.amount}$.
4. **General Ledger Discrepancies:**
   Journal entry debit and credit totals are summed directly from [`JournalEntryLine`](../../backend/app/db/models/ledger.py) rows to confirm double-entry balance.

If any arithmetic discrepancy occurs, the verifier records a calculation error and permanently demotes the autonomy level to `OBSERVE` (blocking autonomous action).

---

## 3. Gate 2: Evidence Completeness Verification

The [`EvidenceCompletenessVerifier`](../../backend/app/verification/engine.py#L150) enforces that required evidentiary categories exist in the dossier:

```python
REQUIRED_TYPES_BY_EXCEPTION = {
    ExceptionType.PO_MISMATCH: ["invoices", "purchase_orders"],
    ExceptionType.RECEIPT_MISMATCH: ["invoices", "goods_receipts"],
    ExceptionType.MISSING_DOCUMENT: ["invoices"],
    ExceptionType.PAYMENT_MISMATCH: ["bank_transactions"],
    ExceptionType.BANK_GL_MISMATCH: ["bank_transactions"],
    ExceptionType.DUPLICATE_PAYMENT: ["bank_transactions"],
    ExceptionType.PAYMENT_FRAGMENTATION: ["bank_transactions"],
    ExceptionType.CASH_ANOMALY: ["bank_transactions"],
    ExceptionType.GL_MAPPING_ERROR: ["journal_entries"],
    ExceptionType.ACCRUAL_ANOMALY: ["journal_entries"],
    ExceptionType.AR_MISMATCH: ["bank_transactions"],
    ExceptionType.UNUSUAL_VENDOR_ACTIVITY: ["journal_entries"],
    ExceptionType.VENDOR_BANK_CHANGE_ANOMALY: ["payments"],
    ExceptionType.DATA_INGESTION_GAP: [],
}
```

### Hallucination Elimination:
If [`CitationValidator`](../../backend/app/investigation/citation_validator.py) flags even a single hallucinated citation (`record_id` not found in dossier), Gate 2 immediately fails:
```python
if not finding.all_citations_valid or finding.hallucinated_citations:
    missing.append(f"Fatal citation failure: finding cited non-existent IDs: {finding.hallucinated_citations}")
```

---

## 4. Gate 3: Policy Gates & Autonomy Determination

The [`PolicyGateVerifier`](../../backend/app/verification/engine.py#L239) evaluates whether an issue can be autonomously resolved or must be escalated to a human controller:

### 4.1 Hard Safety Overrides (Mandatory CFO Escalation)
Any exception matching these criteria is immediately locked to **Autonomy Level 1 (`RECOMMEND`)**:
* Exception is `VENDOR_BANK_CHANGE_ANOMALY` (suspected vendor master modification / payment fraud).
* Exception is `DATA_INGESTION_GAP` (missing bank feed dates or broken GL batch sequence).
* Causal text indicates payment fragmentation, litigation holds, tax withholdings, or unapproved revenue accounts.

### 4.2 Materiality Thresholds
For standard discrepancies proposing `AUTO_RESOLVE`:
1. **Absolute Materiality Cap:**
   $$\text{Financial Impact} \le \text{policy.max\_auto\_resolution\_amount} \quad (\text{Default: } \$50,000.00)$$
   *Per-account overrides can define lower caps for sensitive balance sheet lines via `policy.account_materiality_thresholds`.*
2. **Relative Materiality (% of Account Balance):**
   $$\frac{|\text{Variance}|}{|\text{Account Balance}|} \times 100 \le \text{policy.materiality\_pct\_of\_account\_balance}$$
   If an exception exceeds either limit, the action is downgraded to `STAGE` (requiring human controller review).

### 4.3 Calibrated Confidence Threshold
$$\text{Calibrated Confidence} \ge \text{policy.min\_confidence} \quad (\text{Default: } 0.9500)$$
Evaluated against empirical calibrated confidence, never the raw LLM score.

---

## 5. Investigation Circuit Breaker

The Investigation Agent is bounded by strict resource and time limits in [`app/config.py`](../../backend/app/config.py):

| Parameter | Configuration Setting | Default Value | Description |
| :--- | :--- | :---: | :--- |
| **Max Steps** | `investigation_max_steps` | `15` | Max tool/reasoning steps per investigation |
| **Max Time** | `investigation_max_seconds` | `30.0s` | Maximum wall-clock runtime per investigation |
| **Timeout** | `llm_timeout_seconds` | `30.0s` | Timeout for external HTTP model requests |

### Tripped State Handling:
If an agent loop exceeds 15 steps or 30 seconds:
1. Raises [`InvestigationCircuitBreakerTripped`](../../backend/app/investigation/agent.py#L49) with reason `"STEP_LIMIT"` or `"TIMEOUT"`.
2. Updates `AgentRun.status = FAILED` or `TIMED_OUT`.
3. Emits `AuditEventType.AGENT_RUN_COMPLETED` recording circuit breaker trip.
4. Publishes `agent_run_failed` event to the real-time SSE bus.
5. Safely terminates without blocking the overall Close Run orchestrator.

---

## 6. Action Safety & 1-Click Reversals

### Zero Money Movement Invariant
Vexa is strictly segregated from banking disbursement APIs. Permitted actions are restricted to:
* `MARK_EXCEPTION_RESOLVED`
* `STAGE_JOURNAL_ENTRY` (staged draft only)
* `DRAFT_VENDOR_EMAIL` (staged draft only)
* `CREATE_REVIEW_TASK`
* `MARK_EXCEPTION_ESCALATED`

### The Reversal Engine
If an action is reversed by a human reviewer:
1. [`ReversalEngine`](../../backend/app/action/reversal.py) creates a new `ReversalAction` record pointing to the original `ExceptionAction.id`.
2. The original action status is updated to `REVERSED` (historical rows are never deleted).
3. The associated exception is reopened (`status = REOPENED`, `resolved_at = None`).
4. Any downstream effects (such as staged draft journal entries) are explicitly voided.
5. Emits dual audit events: `REVERSAL` and `EXCEPTION_REOPENED`.
