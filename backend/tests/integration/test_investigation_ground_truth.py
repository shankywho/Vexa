"""Integration test evaluating CFO Investigation Agent against all 35 ground-truth scenarios."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.investigation.evaluation import InvestigationEvaluator


@pytest.mark.asyncio
async def test_investigation_agent_ground_truth_all_35_scenarios():
    evaluator = InvestigationEvaluator()
    report = await evaluator.evaluate_scenarios()

    # Spec section 21/25: 35 total injected scenarios
    assert report.total_scenarios == 35
    assert report.evaluated_scenarios == 35
    assert report.successful_investigations == 35

    # Zero hallucinated citations across the entire dataset
    assert report.hallucination_rate == Decimal("0.0000")

    # High action accuracy (AUTO_RESOLVE, STAGE, ESCALATE)
    assert report.action_accuracy >= Decimal("0.9000")
    assert report.root_cause_accuracy >= Decimal("0.9000")

    # Verify Critical Demo Scenario 1 (Payment Fragmentation)
    frag = next(s for s in report.scenario_details if s["scenario_id"] == "SCENARIO-001")
    assert frag["actual_action"] == "ESCALATE"
    assert frag["citations_valid"] is True
    assert "fragmentation" in frag["actual_root_cause"].lower()

    # Verify Critical Demo Scenario 2 (PO Quantity Mismatch)
    po_mis = next(s for s in report.scenario_details if s["scenario_id"] == "SCENARIO-002")
    assert po_mis["actual_action"] == "STAGE"
    assert po_mis["citations_valid"] is True
    assert "exceeds" in po_mis["actual_root_cause"].lower()

    # Verify Critical Demo Scenario 3 (Clean 6-Way Transaction)
    clean = next(s for s in report.scenario_details if s["scenario_id"] == "SCENARIO-003")
    assert clean["actual_action"] == "AUTO_RESOLVE"
    assert clean["citations_valid"] is True
    assert "clean" in clean["actual_root_cause"].lower()

    # Verify every scenario has 0 hallucinated citations
    for detail in report.scenario_details:
        assert detail["citations_valid"] is True, f"Citation failed in {detail['scenario_id']}"
        assert detail["hallucinations_count"] == 0
