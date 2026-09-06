# Database Operations & Migrations

This guide details managing the PostgreSQL schema, running migrations with Alembic, and maintaining data integrity.

---

## 1. Alembic Migrations

The database schema is versioned under [`backend/alembic/versions/`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/alembic/versions/).

### Apply Migrations to HEAD
```bash
cd backend
uv run alembic upgrade head
```

### Verify Migration Synchronization
Ensure all SQLAlchemy models match the current database schema:
```bash
uv run alembic check
```

### Generate a New Migration
When modifying model classes in `app/db/models/`:
```bash
uv run alembic revision --autogenerate -m "describe schema change"
```
*Always review generated migration scripts before applying them to production.*

---

## 2. Seeding & Resetting Data

### Deterministic Seed Script
Seeds the synthetic company **NovaScale AI** with multi-currency records and 35 injected anomalies:
```bash
uv run python -m app.data.seed
```

### Complete Database Reset
To drop and re-create a clean database:
```bash
dropdb vexa
createdb vexa
uv run alembic upgrade head
uv run python -m app.data.seed
```
