"""Integration tests evaluating reconciliation engine against ground_truth.json."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.generator import seed_financial_transactions
from app.data.seed import seed_company
from app.reconciliation.engine import DeterministicReconciliationEngine


@pytest.mark.asyncio
async def test_reconciliation_engine_ground_truth_evaluation(db: AsyncSession):
    # 1. Seed deterministic company and transactions
    company = await seed_company(db, seed=42, include_transactions=False)
    await seed_financial_transactions(db, company, seed=42)

    # 2. Initialize deterministic engine for seeded tenant
    engine = DeterministicReconciliationEngine(db, company.id)

    # 3. Evaluate against ground_truth.json
    report = await engine.evaluate_ground_truth()

    assert report.total_scenarios == 35
    assert report.detected_scenarios == 35
    assert report.clean_scenarios_verified >= 1
    assert report.exception_scenarios_detected == 34
    assert report.precision == Decimal("1.0000")
    assert report.recall == Decimal("1.0000")
    assert report.f1_score == Decimal("1.0000")

    # Verify no scenario was missed
    for detail in report.scenario_details:
        assert detail["status"] == "DETECTED", f"Scenario {detail['scenario_id']} was missed!"
        assert detail["actual_impact"] == detail["expected_impact"]


@pytest.mark.asyncio
async def test_reconciliation_engine_full_run_persistence_and_idempotency(db: AsyncSession):
    company = await seed_company(db, seed=42, include_transactions=False)
    await seed_financial_transactions(db, company, seed=42)

    engine = DeterministicReconciliationEngine(db, company.id)

    # Run pass 1 with persistence
    summary1 = await engine.run_full_reconciliation(persist=True)
    assert summary1.total_items_processed > 0
    assert summary1.total_matched > 0

    repo = engine.rec_repo
    count1 = await repo.count()
    assert count1 == len(summary1.results)

    # Clear results and re-run (idempotency check)
    cleared = await repo.clear_results()
    assert cleared == count1
    assert await repo.count() == 0

    # Run pass 2
    summary2 = await engine.run_full_reconciliation(persist=True)
    assert summary2.total_items_processed == summary1.total_items_processed
    assert summary2.total_matched == summary1.total_matched
    assert summary2.total_financial_impact == summary1.total_financial_impact
    assert await repo.count() == count1
