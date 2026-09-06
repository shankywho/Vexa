# ADR 004: Controlled Autonomy

## Context
Corporate financial operations balance speed against risk. Routine, low-value items should not burden human controllers, while material adjustments or potential fraud require executive oversight.

## Problem
Binary autonomy ("fully manual" vs "fully autonomous") is impractical for finance. Full automation introduces unacceptable financial risk, while full manual review creates bottlenecked close cycles.

## Decision
Implement a **4-Tier Controlled Autonomy Framework**:
1. **Level 0 (OBSERVE):** Telemetry only; zero mutations. Assigned when evidence is incomplete or calculations fail.
2. **Level 1 (RECOMMEND):** Forensic root-cause analysis routed to CFO. Assigned to high-risk events (vendor bank account modifications, payment fragmentation, cash anomalies).
3. **Level 2 (STAGE):** Compensating entries or emails prepared in draft form. Assigned to standard variances exceeding the materiality cap ($50,000). Requires Controller approval.
4. **Level 3 (EXECUTE):** Autonomously resolves immaterial variances ($\le \$50,000$) with $\ge 0.95$ calibrated confidence and verified arithmetic.
5. **Hard Prohibition:** The system has **zero** authority to move money or execute banking transfers.

## Alternatives Considered
* **Confidence-Only Thresholding:** Auto-resolving any case where model confidence $\ge 90\%$. Rejected because uncalibrated LLM confidence is notoriously overconfident.
* **Pure Amount Thresholding:** Auto-resolving any variance under $50k$ without qualitative checks. Rejected because small transactions can be part of structured fraud or vendor bank change exploits.

## Consequences
* **Positive:** Drastically reduces routine manual reconciliation work while ensuring high-risk and material decisions always require human authorization.
* **Trade-off:** Requires maintenance of policy configuration schemas and staged approval queues.
