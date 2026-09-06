# Vexa Backend

Evidence-first autonomous month-end-close backend for the **Autonomous Office of the CFO**.

Current Status:
* **156/156 tests passing**
* **35/35 CFO-Bench ground-truth scenarios verified (F1: 1.00)**
* **Deterministic 10-pass reconciliation engine active**
* **Financial evidence graph with PageRank relevance scoring**
* **CFO investigation agent with zero-hallucination citation validation**
* **3-gate independent verification engine with calibrated confidence**
* **Live and replay Server-Sent Events (SSE) streaming engine**
* **Immutable audit trail with deterministic SOX control catalog**

See the root documentation for the full architectural specification:
* [Repository README](../README.md)
* [Technical Documentation Suite](../docs/README.md)
* [Architecture Overview](../docs/architecture/overview.md)
* [API Reference](../docs/api/overview.md)

---

## Requirements

* Python 3.12+
* PostgreSQL 16+ (with asyncpg support)
* [uv](https://github.com/astral-sh/uv) (recommended)

---

## Quickstart

```bash
cd backend
uv sync --dev

# Configure database URL (see app/config.py for defaults)
export VEXA_DB_URL="postgresql+asyncpg://localhost:5432/vexa"

# Create application and test databases
createdb vexa
createdb vexa_test

# Run Alembic migrations to current HEAD
uv run alembic upgrade head

# Seed synthetic company "NovaScale AI" with baseline transactions and 35 anomalies
uv run python -m app.data.seed

# Run the API server on http://localhost:8000
uv run uvicorn app.main:app --reload
```

---

## Tests & Verification

```bash
cd backend

# Run full test suite (156 tests)
uv run pytest

# Run Ruff linting and formatting checks
uv run ruff check
uv run ruff format --check

# Check Alembic schema sync
uv run alembic check
```

---

## Backend Layout

```
backend/
├── app/
│   ├── action/            # Action service, 1-click reversals, human correction loop
│   ├── analyst/           # Financial analyst agent & account variance analytics
│   ├── api/               # FastAPI route controllers & dependencies
│   ├── audit/             # SOX control registry & immutable audit service
│   ├── benchmarks/        # 35-scenario benchmark runner & calibration reports
│   ├── close_workflow/    # 10-task DAG orchestrator & CAS state machine
│   ├── data/              # Synthetic company generator & ground truth scenarios
│   ├── db/                # SQLAlchemy async models, sessions & repository layer
│   ├── demo/              # Demo safety net (trace recorder & player)
│   ├── domain/            # Domain enums, schemas & value objects
│   ├── evidence_graph/    # Directed financial knowledge graph & PageRank ranker
│   ├── investigation/     # CFO investigation agent, citations & calibration
│   ├── reconciliation/    # 10-pass deterministic reconciliation engine
│   ├── services/          # Close service & multi-currency FX service
│   ├── streaming/         # Real-time Server-Sent Events (SSE) bus
│   ├── verification/      # 3-gate independent verification engine
│   ├── config.py          # Application configuration (pydantic-settings)
│   └── main.py            # FastAPI application factory & lifespan
├── alembic/               # PostgreSQL schema migrations
├── scripts/               # CLI utility scripts
└── tests/                 # Unit & integration test suites (156 passing tests)
```
