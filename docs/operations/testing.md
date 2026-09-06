# Testing & Verification Guide

Vexa maintains a comprehensive test suite of 156 tests spanning isolated unit tests, multi-tenant integration tests, and benchmark ground-truth evaluations.

---

## 1. Running the Full Test Suite

```bash
cd backend

# Execute all unit and integration tests
uv run pytest
```
*Expected result: 156 passed in ~2.5 minutes.*

---

## 2. Test Partitioning

### Unit Tests ([`backend/tests/unit/`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-7/backend/tests/unit/))
Fast tests validating core logic without requiring external services:
```bash
# Run unit test suite
uv run pytest tests/unit/

# Run specific unit test modules
uv run pytest tests/unit/test_close_workflow_state_machine.py
uv run pytest tests/unit/test_reconciliation_rules.py
uv run pytest tests/unit/test_investigation_citation_validator.py
uv run pytest tests/unit/test_verification_agent.py
```

### Integration Tests ([`backend/tests/integration/`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-7/backend/tests/integration/))
End-to-end tests validating database transactions and multi-tenant isolation against local PostgreSQL (`vexa_test`):
```bash
# Run integration test suite
uv run pytest tests/integration/

# Run ground-truth benchmark evaluation test
uv run pytest tests/integration/test_ground_truth_evaluation.py

# Run multi-tenant boundary test
uv run pytest tests/integration/test_close_workflow_tenant_isolation.py
```

---

## 3. Code Style & Linting Checks

```bash
# Run Ruff lint checks
uv run ruff check

# Run Ruff formatting check
uv run ruff format --check

# Check database schema against Alembic
uv run alembic check
```
