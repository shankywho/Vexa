# Independent Verification Agent Specification

The Independent Verification Agent independently verifies hypotheses formulated by the Investigation Agent, ensuring zero-trust verification of accounting assertions.

---

## 1. Responsibilities & Boundaries

* **Core Mission:** Double-check findings, independently re-derive math, verify citation provenance, and enforce corporate policy gates.
* **Separation of Concerns:** The Verification Agent **never** reads the Investigation Agent's calculated numbers as truth. It reads raw database records and recomputes the math from scratch.
* **Inputs:** [`VerificationRequest`](../../backend/app/verification/types.py#L15) containing the raw finding, bounded dossier, and active `ClosePolicy`.
* **Outputs:** [`VerificationResult`](../../backend/app/verification/types.py#L28).

---

## 2. Decision Process & Gates

```
InvestigationFinding
        │
        ▼
[ Independent Calculation Verifier ] ──> Arithmetic Mismatch? ──> Autonomy = OBSERVE
        │ Pass
        ▼
[ Evidence Completeness Verifier ]   ──> Hallucination or Missing? ──> Autonomy = OBSERVE
        │ Pass
        ▼
[ Policy Gate Verifier ]             ──> Hard Escalation Trigger? ──> Autonomy = RECOMMEND
        │ Pass
        ├──> Impact > $50,000?       ──> Autonomy = STAGE
        ├──> Variance > 5% Balance?  ──> Autonomy = STAGE
        ├──> Calibrated Conf < 0.95? ──> Autonomy = STAGE
        └──> All Clean?              ──> Autonomy = EXECUTE
```

---

## 3. Relevant Tests

* Unit Tests: [`tests/unit/test_verification_agent.py`](../../backend/tests/unit/test_verification_agent.py).
* Integration Tests: [`tests/integration/test_verification_action_reversal_flow.py`](../../backend/tests/integration/test_verification_action_reversal_flow.py).
