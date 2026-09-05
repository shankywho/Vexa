"""Integration tests for Financial Analyst Agent and CFO-Bench benchmark runner."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.analyst.agent import FinancialAnalystAgent
from app.benchmarks.runner import CFOBenchRunner
from app.data.generator import seed_financial_transactions
from app.data.seed import seed_company
from app.db.models.agent import AgentRun


@pytest.mark.asyncio
async def test_financial_analyst_agent(client_session: AsyncSession):
    # 1. Seed company & financial data
    company = await seed_company(client_session, name="Analyst Test Co")
    await seed_financial_transactions(client_session, company, save_ground_truth=False)

    # 2. Run Financial Analyst Agent
    agent = FinancialAnalystAgent(client_session, company.id)
    report = await agent.analyze(
        period_start="2026-03-01",
        period_end="2026-03-31",
        materiality_threshold=Decimal("100000.00"),
    )

    # 3. Assert report structure and deterministic calculations
    assert report.company_id == company.id
    assert report.period_start == "2026-03-01"
    assert report.period_end == "2026-03-31"
    assert len(report.variance_items) > 0
    assert isinstance(report.cash_summary.opening_cash_balance, Decimal)
    assert isinstance(report.cash_summary.closing_cash_balance, Decimal)
    assert isinstance(report.cash_summary.net_cash_flow, Decimal)
    assert report.total_accrual_exposure >= Decimal("0.00")
    assert report.period_over_period_summary != ""
    assert report.executive_close_summary != ""
    assert report.agent_run_id is not None

    # 4. Verify AgentRun and AgentStep persisted in DB
    run = await client_session.get(AgentRun, report.agent_run_id)
    assert run is not None
    assert run.agent_name == "financial_analyst_agent"
    assert run.status.value == "COMPLETED"


@pytest.mark.asyncio
async def test_cfo_bench_runner_all_35_scenarios():
    runner = CFOBenchRunner()
    summary = await runner.run_benchmark()

    # Spec sections 21 & 25: 35 injected scenarios
    assert summary.total_scenarios == 35
    assert summary.evaluated_scenarios == 35
    assert len(summary.scenario_details) == 35

    # Target metrics from spec
    assert summary.hallucination_rate == Decimal("0.0000")
    assert summary.action_accuracy >= Decimal("0.9000")
    assert summary.root_cause_accuracy >= Decimal("0.9000")
    assert summary.financial_calculation_accuracy == Decimal("1.0000")
    assert summary.escalation_correctness >= Decimal("0.9000")

    # Calibration report (spec section 12.1)
    cal = summary.calibration_report
    assert cal.total_predictions == 35
    assert cal.expected_calibration_error >= Decimal("0.0000")
    assert cal.maximum_calibration_error >= Decimal("0.0000")
    assert len(cal.buckets) == 6


@pytest.mark.asyncio
async def test_benchmarks_api_endpoints(client: AsyncClient):
    # 1. GET /api/benchmarks
    resp = await client.get("/api/benchmarks")
    assert resp.status_code == 200
    runs = resp.json()
    assert len(runs) >= 1
    run_id = runs[0]["id"]

    # 2. GET /api/benchmarks/{id}
    resp = await client.get(f"/api/benchmarks/{run_id}")
    assert resp.status_code == 200
    run_data = resp.json()
    assert run_data["id"] == run_id
    assert run_data["total_scenarios"] == 35
    assert run_data["hallucination_rate"] == "0.0000"

    # 3. GET /api/benchmarks/calibration
    resp = await client.get("/api/benchmarks/calibration")
    assert resp.status_code == 200
    cal_data = resp.json()
    assert "expected_calibration_error" in cal_data
    assert len(cal_data["buckets"]) == 6

    # 4. POST /api/benchmarks/run
    resp = await client.post("/api/benchmarks/run")
    assert resp.status_code == 201
    new_run = resp.json()
    assert new_run["total_scenarios"] == 35
    assert new_run["evaluated_scenarios"] == 35
