# ADR 005: Live vs Replay Demo Architecture

## Context
Demonstrating multi-agent systems live in front of judges, auditors, or executive committees presents extreme operational risk due to non-deterministic LLM response times, rate limits, and network flakiness.

## Problem
A live demo failure (such as an API socket drop or a 45-second latency pause) undermines technical credibility, even if the underlying code is sound. Conversely, video recordings or hard-coded mock frontends feel synthetic and fail to demonstrate real system capabilities.

## Decision
Implement a **First-Class Demo Safety Net** with dual `LIVE` and `REPLAY` modes:
1. **`LIVE` Mode:** Full execution across PostgreSQL, graph construction, LLM investigation, independent verification, and real-time SSE telemetry.
2. **`REPLAY` Mode:** Replays pre-recorded golden traces captured by `TraceRecorder` during rehearsal runs at authentic real-time pacing via `TracePlayer`.
3. **Identical API Surface:** Both modes publish through the exact same Server-Sent Events stream (`GET /api/close-runs/{id}/stream`), ensuring the frontend UI cannot distinguish between live execution and replay.
4. **Operational Policy:** Default to `LIVE` mode for presentations; switch instantaneously to `REPLAY` via `POST /api/demo/mode` if network or provider instability is detected prior to presenting.

## Alternatives Considered
* **Live-Only Execution:** Hoping external LLM APIs and venue Wi-Fi remain stable during presentations. Rejected as unacceptably risky.
* **Mocked Frontend UI:** Hard-coding animation states in React. Rejected because it circumvents the real backend API, defeating the purpose of an engineering demonstration.

## Consequences
* **Positive:** 100% demo reliability; deterministic timing; proves system telemetry fidelity without risking on-stage failure.
* **Trade-off:** Requires maintenance of `demo_traces` database tables and trace recording tools.
