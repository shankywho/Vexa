"""Schemas and domain models for CFO-Bench and confidence calibration (spec sections 12.1, 25)."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ScenarioBenchmarkResult(BaseModel):
    """Detailed benchmark evaluation for a single injected ground-truth scenario."""

    scenario_id: str
    scenario_type: str
    expected_root_cause: str
    actual_root_cause: str
    root_cause_matched: bool
    expected_action: str
    actual_action: str
    action_matched: bool
    expected_financial_impact: Decimal
    actual_financial_impact: Decimal
    impact_matched: bool
    expected_human_review: bool
    actual_human_review: bool
    human_review_matched: bool
    citations_valid: bool
    hallucinated_citations_count: int
    raw_confidence: Decimal
    calibrated_confidence: Decimal
    latency_ms: int


class CalibrationBucket(BaseModel):
    """A confidence bucket evaluating empirical accuracy vs reported confidence."""

    bucket_range: str
    min_confidence: Decimal
    max_confidence: Decimal
    count: int
    avg_confidence: Decimal
    empirical_accuracy: Decimal
    calibration_gap: Decimal


class ConfidenceCalibrationReport(BaseModel):
    """Calibration report quantifying Expected Calibration Error (ECE) (spec section 12.1)."""

    total_predictions: int
    expected_calibration_error: Decimal  # ECE
    maximum_calibration_error: Decimal  # MCE
    buckets: list[CalibrationBucket]
    calibration_formula: str = "ECE = sum( (count_b / N) * |acc_b - conf_b| )"
    policy_min_confidence_threshold: Decimal = Decimal("0.95")
    policy_calibrated_confidence: Decimal = Decimal("0.9100")
    explanation: str = (
        "Quantifies accuracy per confidence bucket. Evaluates policy min_confidence "
        "against calibrated probabilities rather than raw model self-reporting."
    )


class BenchmarkRunSummary(BaseModel):
    """Full summary of a CFO-Bench execution across the unified ground truth dataset."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: uuid.UUID
    run_timestamp: str
    total_scenarios: int
    evaluated_scenarios: int
    root_cause_accuracy: Decimal
    action_accuracy: Decimal
    financial_calculation_accuracy: Decimal
    escalation_correctness: Decimal
    hallucination_rate: Decimal  # Target: 0.0000
    expected_calibration_error: Decimal
    avg_calibrated_confidence: Decimal
    avg_latency_ms: int
    total_cost_usd: Decimal
    scenario_details: list[ScenarioBenchmarkResult] = Field(default_factory=list)
    calibration_report: ConfidenceCalibrationReport

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
