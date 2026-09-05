# ClosePilot (Vexa) Backend

Evidence-first autonomous month-end-close backend.

**Scope (Phase 1):** Engineering foundation only — application structure,
configuration, PostgreSQL, SQLAlchemy, Alembic, core domain models,
tenant/company boundary, API foundation, audit foundation, testing
infrastructure, and a deterministic seed foundation.

This phase does **not** build the reconciliation engine, investigation
agents, evidence graph, CFO-Bench, reliability engine, or any frontend.
See `CLOSEPILOT_BACKEND_CONTEXT_V2.md` (repository root) for the full
architecture specification.

## Requirements

- Python 3.12
- PostgreSQL (tested against 18.x)

## Quickstart

```bash
cd backend
uv sync --dev

# Configuration via environment variables (see app/config.py for defaults)
export VEXA_DB_URL="postgresql+asyncpg://localhost:5432/vexa"

# Create the database (once)
createdb vexa

# Run Alembic migrations to build the schema
uv run alembic upgrade head

# Run the API on http://localhost:8000
uv run uvicorn app.main:app --reload
```

## Tests

```bash
cd backend
uv run pytest
```

Integration tests require a PostgreSQL database `vexa_test` on localhost.

## Repository layout

```
backend/
├── app/
│   ├── main.py            # FastAPI app factory & lifespan
│   ├── config.py          # pydantic-settings configuration
│   ├── api/               # API routers & dependencies
│   ├── domain/            # enums, value objects, domain logic
│   ├── db/                # SQLAlchemy session/engine, models
│   ├── services/          # application services
│   ├── audit/             # audit-trail foundation
│   └── data/              # deterministic seed/generator foundation
├── alembic/               # migrations
├── scripts/               # CLI entrypoints (seed, etc.)
└── tests/                 # unit + integration
```
