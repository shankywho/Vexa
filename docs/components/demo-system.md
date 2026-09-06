# Demo System Component Deep Dive

The Demo System provides a first-class safety net to guarantee flawless demonstrations and presentations under live or offline conditions.

---

## 1. Package Structure

Located at [`backend/app/demo/`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/demo/):

```
app/demo/
├── __init__.py
├── mode.py            # DemoModeManager (Global & per-close-run mode toggle)
├── trace_player.py    # TracePlayer (Replays recorded traces as real-time SSE)
└── trace_recorder.py  # TraceRecorder (Captures live runs into PostgreSQL DemoTrace)
```

---

## 2. The Replay Architecture & Rationale

Live demonstrations involving external LLM APIs face severe presentation failure risks:
* Upstream API rate limits or latency spikes (>30s pauses).
* Hallucinations under non-deterministic temperature sampling.
* Venue Wi-Fi disconnections or socket timeouts.

Vexa addresses this with dual execution modes:
* **`LIVE` Mode:** Full execution across PostgreSQL, graph construction, LLM investigation, and real-time verification.
* **`REPLAY` Mode:** Replays verified execution traces captured from flawless rehearsal runs through the **exact same SSE and REST endpoints**.

```
             ┌──────────────────────────────────────────────┐
             │            Frontend Web Client               │
             └──────────────────────▲───────────────────────┘
                                    │
                                    │ Same SSE Format
                                    │ GET /api/close-runs/{id}/stream
                                    │
             ┌──────────────────────┴───────────────────────┐
             │               DemoModeManager                │
             │           (LIVE vs REPLAY Toggle)            │
             └──────────────┬───────────────────────┬───────┘
                            │                       │
                LIVE Mode   │                       │ REPLAY Mode
                            ▼                       ▼
             ┌──────────────────────┐     ┌──────────────────────┐
             │ Close Workflow       │     │ TracePlayer          │
             │ Controller           │     │ (Timed offset delay) │
             └──────────┬───────────┘     └──────────┬───────────┘
                        │                            │
                        ▼                            ▼
             ┌──────────────────────┐     ┌──────────────────────┐
             │ PostgreSQL Live DB   │     │ Stored DemoTrace     │
             │ & External LLM       │     │ (Captured Telemetry) │
             └──────────────────────┘     └──────────────────────┘
```

---

## 3. The 3 Golden Scenarios

The system includes pre-seeded golden traces for the three core demonstration scenarios:

### Scenario 1: Payment Fragmentation (Fraud / Structuring)
* **Key:** `PAYMENT_FRAGMENTATION`
* **Narrative:** Vendor invoice of ₹14,50,000 paid via 14 separate ₹1,00,000 transactions on the same day to circumvent single-transaction approval limits (₹10,00,000).
* **Outcome:** Graph traversal connects all 14 payments; Verifier flags policy conflict; case escalated to CFO (**`ESCALATE`**).

### Scenario 2: Quantity Mismatch (3-Way Procurement Discrepancy)
* **Key:** `QUANTITY_MISMATCH`
* **Narrative:** Vendor bills 1,000 units @ ₹1,600 (₹16,00,000). PO authorized 800 units. Warehouse confirms receipt of 760 units.
* **Outcome:** Recalculates exact variance ($3,84,000); exceeds $50,000 cap; draft debit memo staged for Controller approval (**`STAGE`**).

### Scenario 3: Clean Transaction (Autonomous Auto-Resolution)
* **Key:** `CLEAN_TRANSACTION`
* **Narrative:** Invoice, PO, Receipt, Payment, Bank Transaction, and GL Entry in perfect 6-way balance.
* **Outcome:** Verifier confirms $0.00 variance and complete evidence; automatically resolved (**`AUTO_RESOLVE`**).

---

## 4. Mode Toggling & Trace Playback API

Check current demo mode:
```bash
curl http://localhost:8000/api/demo/mode
```

Switch mode globally or per close run:
```bash
curl -X POST http://localhost:8000/api/demo/mode \
  -H "Content-Type: application/json" \
  -d '{"global_mode": "REPLAY"}'
```

Replay a specific golden trace over SSE:
```bash
curl -N http://localhost:8000/api/demo/traces/{trace_id}/stream
```
