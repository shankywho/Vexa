# ADR 001: Deterministic Financial Truth

## Context
In corporate accounting, financial balances, variances, tax calculations, and currency conversions require exact mathematical precision. Financial statements must balance to the penny, and audit trails must be verifiable by external regulators.

## Problem
Large Language Models (LLMs) operate via probabilistic next-token prediction. They suffer from stochastic arithmetic rounding errors, inconsistent numerical outputs, and occasional hallucinations. Relying on an LLM to compute ledger balances or determine whether two financial figures match produces non-deterministic accounting records that fail audit scrutiny.

## Decision
Enforce the strict architectural invariant: **"LLMs reason; deterministic code calculates financial truth."**
1. All financial calculations (sums, differences, ratios, FX conversions) are executed strictly in deterministic Python using fixed-point `Decimal` arithmetic.
2. The reconciliation engine operates across 10 deterministic passes with zero LLM calls.
3. LLMs are restricted to semantic synthesis, qualitative root-cause reasoning, and communication drafting within bounded data structures.

## Alternatives Considered
* **End-to-End LLM Accounting Agent:** Using a single prompt or ReAct loop to ingest raw documents and output financial conclusions. Rejected due to catastrophic arithmetic unreliability and hallucination risk.
* **Code Interpreter Tooling:** Allowing an LLM to write and execute arbitrary Python scripts. Rejected due to non-deterministic script generation, security concerns, and unpredictable execution latency.

## Consequences
* **Positive:** 100% mathematical precision across all reconciliations; perfect auditability; zero arithmetic hallucinations.
* **Trade-off:** Requires explicit software engineering of matching rules, tolerance thresholds, and financial data structures rather than delegating logic entirely to a prompt.
