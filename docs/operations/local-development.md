# Local Development Quickstart

This guide covers setting up a local development environment for the Vexa backend.

---

## 1. Prerequisites

* **Python:** Version `3.12` or higher.
* **Database:** PostgreSQL `16.x` or higher running locally on port `5432`.
* **Package Manager:** `uv` (recommended) or standard `pip`.

---

## 2. Installation & Virtual Environment

```bash
# Clone the repository
git clone https://github.com/shankywho/Vexa.git
cd Vexa/backend

# Synchronize virtual environment with development dependencies
uv sync --dev
```

---

## 3. Database Setup & Schema Migrations

Ensure your local PostgreSQL server is running:

```bash
# Set database connection environment variable
export VEXA_DB_URL="postgresql+asyncpg://localhost:5432/vexa"

# Create application database
createdb vexa

# Create test database for integration suites
createdb vexa_test

# Apply Alembic migrations to current HEAD
uv run alembic upgrade head
```

---

## 4. Seeding Synthetic Company Data

Seed the fictional tenant **NovaScale AI** and 35 injected financial anomaly scenarios:

```bash
uv run python -m app.data.seed
```

---

## 5. Starting the API Server

Launch the FastAPI application with live code reload:

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

* API Root: [http://localhost:8000](http://localhost:8000)
* Interactive Swagger Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
* Health Check: [http://localhost:8000/api/health](http://localhost:8000/api/health)
