#!/usr/bin/env bash
set -e

echo "==> [Vexa] Bootstrapping autonomous month-end close backend..."

# Run database migrations to HEAD
echo "==> [Vexa] Applying database migrations (alembic upgrade head)..."
python -m alembic upgrade head || {
    echo "==> [Vexa] Warning: alembic upgrade encountered an issue, proceeding to application startup..."
}

# Idempotently seed demo company and ground-truth records
echo "==> [Vexa] Checking & seeding NovaScale AI demo dataset..."
python -m app.data.seed || {
    echo "==> [Vexa] Warning: seed script encountered an issue, proceeding to application startup..."
}

# Start Uvicorn server
PORT="${PORT:-8000}"
echo "==> [Vexa] Launching FastAPI Uvicorn server on 0.0.0.0:${PORT}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT}"
