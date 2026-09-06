# ADR 003: Independent Verification

## Context
When an autonomous agent investigates a financial anomaly and proposes an action (e.g. posting a correcting journal entry), institutional governance requires validation prior to execution.

## Problem
Allowing an agent to verify its own conclusions introduces self-confirmation bias. If an agent hallucinates or makes a faulty deduction during investigation, asking the same agent to "verify" the output almost always reproduces the original error.

## Decision
Enforce a strict architectural separation between **Investigation** and **Verification**:
1. The **Investigation Agent** acts as an advocate/detective: formulating hypotheses, citing evidence, and proposing an autonomy action (Primary Model: Mistral `codestral-latest` 22B).
2. The **Verification Agent** acts as an independent magistrate on a separate physical LLM provider (Primary Model: Groq `qwen/qwen3.8-27b` LPUs):
   - **Gate 1 (Calculation Verification):** Re-derives the variance directly from raw database rows without reading the agent's prose claims.
   - **Gate 2 (Completeness Verification):** Verifies that required documents exist and zero citations are hallucinated via `CitationValidator`.
   - **Gate 3 (Policy Gate):** Applies materiality caps, relative thresholds, and hard escalation overrides.
3. **Cross-Model Independence Guarantee:**
   - In production, `investigation_agent` and `verification_agent` are strictly forbidden from sharing a primary LLM provider (`ConfigurationError` raised at startup).
   - If runtime network failover forces both agents onto the same fallback provider, `independence_compromised=True` is stamped, a `-0.1000` penalty is deducted from `calibrated_confidence`, and an audit warning is emitted.
4. **Zero Arithmetic Authority:**
   - All financial figures (`financial_impact`, `currency`, `exception_id`) are immutable attributes from bounded evidence dossiers, never computed or altered by LLMs.
5. Verification failure permanently blocks autonomous action and demotes the proposal to `OBSERVE` or `STAGE`.

## Alternatives Considered
* **Self-Reflective Prompting:** Asking the LLM in a single thread to critique its own work before responding. Rejected because LLMs reliably fail to catch their own arithmetic errors or hallucinated citations.
* **Single Combined Agent:** Having one agent perform investigation, arithmetic checking, and policy evaluation. Rejected due to lack of segregation of duties.
* **Homogeneous Verification:** Running both investigator and verifier on the same LLM vendor. Rejected because correlated vendor priors can propagate inductive errors.

## Consequences
* **Positive:** Eliminates confirmation bias and vendor-correlated errors; guarantees that no autonomous action is executed without passing independent mathematical, cross-provider, and policy checks.
* **Trade-off:** Adds an additional processing stage to the close pipeline (~1.1s latency overhead). Measured total LLM cost across all 3 providers remains under $0.025 per month-end close.
