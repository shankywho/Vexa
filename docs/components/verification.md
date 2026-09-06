# Independent Verification Component Deep Dive

The Independent Verification component acts as an autonomous firewall, ensuring that no agent recommendation is executed without deterministic arithmetic, evidentiary, and policy validation.

---

## 1. Package Structure

Located at [`backend/app/verification/`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-7/backend/app/verification/):

```
app/verification/
├── __init__.py
├── agent.py       # VerificationAgent (Coordinates 3-gate pipeline)
├── engine.py      # IndependentCalculationVerifier, EvidenceCompletenessVerifier, PolicyGateVerifier
├── service.py     # VerificationService (Application integration layer)
└── types.py       # VerificationRequest, VerificationResult
```

---

## 2. Verification Architecture: The 3 Gates

```
Investigation Finding + Evidence Dossier
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│ Gate 1: Independent Calculation Verifier            │
│ - Recalculates variance from raw database rows      │
│ - Zero trust in LLM claims                          │
│ - Fails if |calc - recorded| > $0.01                │
└──────────────────┬──────────────────────────────────┘
                   │ Pass
                   ▼
┌─────────────────────────────────────────────────────┐
│ Gate 2: Evidence Completeness Verifier              │
│ - Validates mandatory document presence             │
│ - Fails if any citation is hallucinated             │
└──────────────────┬──────────────────────────────────┘
                   │ Pass
                   ▼
┌─────────────────────────────────────────────────────┐
│ Gate 3: Policy Gate Verifier                        │
│ - Evaluates Materiality Cap (<= $50k)               │
│ - Evaluates Relative Materiality (% Account Balance)│
│ - Evaluates Calibrated Confidence (>= 0.95)         │
│ - Flags Hard Escalation Overrides (Fraud, Bank Mod) │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
           VerificationResult
```

---

## 3. Verification Subsystem Engines

### 3.1 `IndependentCalculationVerifier`
Independently computes variances without inspecting the agent's prose:
```python
# app/verification/engine.py
if dossier.exception_type in (ExceptionType.PO_MISMATCH, ExceptionType.RECEIPT_MISMATCH):
    inv = dossier.invoices[0]
    po = dossier.purchase_orders[0]
    inv_total = inv.total
    po_total = po.total
    diff = abs(inv_total - po_total)
    variance_diff = abs(diff - exception.financial_impact)
    if variance_diff > Decimal("0.01"):
        errors.append(f"Calculation mismatch: {diff} != {exception.financial_impact}")
```

### 3.2 `EvidenceCompletenessVerifier`
Verifies that all required supporting documents are cited and present:
* Confirms mandatory categories for the exception type (e.g. `["invoices", "purchase_orders"]` for `PO_MISMATCH`).
* Verifies zero hallucinated citations from [`CitationValidator`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-7/backend/app/investigation/citation_validator.py).

### 3.3 `PolicyGateVerifier`
Enforces corporate close governance policies:
* **Integrity Violations:** If Gate 1 or Gate 2 fails, forces `AutonomyLevel.OBSERVE`.
* **CFO Escalation Overrides:** If the exception involves vendor bank account changes, cash anomalies, or payment fragmentation, forces `AutonomyLevel.RECOMMEND`.
* **Materiality Thresholds:** If financial impact $> \$50,000$ or variance represents $> 5\%$ of account balance, forces `AutonomyLevel.STAGE`.
* **Auto-Resolution:** Only if all gates pass and calibrated confidence $\ge 0.95$ does it emit `AutonomyLevel.EXECUTE`.

---

## 4. Output Contract: `VerificationResult`

Defined in [`app/verification/types.py`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-7/backend/app/verification/types.py#L28):

```json
{
  "exception_id": "b182ef0a-3132-482a-a9fb-10b2d6da6194",
  "verified": true,
  "confidence": "0.9800",
  "calibrated_confidence": "0.9800",
  "missing_evidence": [],
  "calculation_errors": [],
  "policy_violations": [],
  "recommended_autonomy": "STAGE",
  "reproduction_valid": true,
  "evidence_complete": true,
  "calculation_valid": true,
  "recalculated_impact": "384000.00",
  "variance_diff": "0.00",
  "notes": "Independent calculation confirmed variance of $384,000. Staged due to materiality cap ($50,000)."
}
```
