# ADR 003: Independent Verification

## Context
When an autonomous agent investigates a financial anomaly and proposes an action (e.g. posting a correcting journal entry), institutional governance requires validation prior to execution.

## Problem
Allowing an agent to verify its own conclusions introduces self-confirmation bias. If an agent hallucinates or makes a faulty deduction during investigation, asking the same agent to "verify" the output almost always reproduces the original error.

## Decision
Enforce a strict architectural separation between **Investigation** and **Verification**:
1. The **Investigation Agent** acts as an advocate/detective: formulating hypotheses, citing evidence, and proposing an autonomy action.
2. The **Verification Agent** acts as an independent magistrate:
   - **Gate 1 (Calculation Verification):** Re-derives the variance directly from raw database rows without reading the agent's prose claims.
   - **Gate 2 (Completeness Verification):** Verifies that required documents exist and zero citations are hallucinated.
   - **Gate 3 (Policy Gate):** Applies materiality caps, relative thresholds, and hard escalation overrides.
3. Verification failure permanently blocks autonomous action and demotes the proposal to `OBSERVE` or `STAGE`.

## Alternatives Considered
* **Self-Reflective Prompting:** Asking the LLM in a single thread to critique its own work before responding. Rejected because LLMs reliably fail to catch their own arithmetic errors or hallucinated citations.
* **Single Combined Agent:** Having one agent perform investigation, arithmetic checking, and policy evaluation. Rejected due to lack of segregation of duties.

## Consequences
* **Positive:** Eliminates confirmation bias; guarantees that no autonomous action is executed without passing independent mathematical and policy checks.
* **Trade-off:** Adds an additional processing stage to the close pipeline.
