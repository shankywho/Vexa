"""Confidence calibration and ECE calculation engine (spec section 12.1)."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from app.benchmarks.types import (
    CalibrationBucket,
    ConfidenceCalibrationReport,
    ScenarioBenchmarkResult,
)


def compute_calibration_report(
    results: list[ScenarioBenchmarkResult],
) -> ConfidenceCalibrationReport:
    """Compute empirical calibration buckets and Expected Calibration Error (ECE)."""
    bucket_definitions = [
        (Decimal("0.90"), Decimal("1.00"), "0.90 - 1.00"),
        (Decimal("0.80"), Decimal("0.90"), "0.80 - 0.90"),
        (Decimal("0.70"), Decimal("0.80"), "0.70 - 0.80"),
        (Decimal("0.60"), Decimal("0.70"), "0.60 - 0.70"),
        (Decimal("0.50"), Decimal("0.60"), "0.50 - 0.60"),
        (Decimal("0.00"), Decimal("0.50"), "0.00 - 0.50"),
    ]

    total = len(results)
    if total == 0:
        return ConfidenceCalibrationReport(
            total_predictions=0,
            expected_calibration_error=Decimal("0.0000"),
            maximum_calibration_error=Decimal("0.0000"),
            buckets=[],
        )

    buckets: list[CalibrationBucket] = []
    weighted_ece_sum = Decimal("0.0000")
    max_gap = Decimal("0.0000")

    for min_c, max_c, label in bucket_definitions:
        # Items matching bucket range
        if max_c == Decimal("1.00"):
            items = [r for r in results if min_c <= r.raw_confidence <= max_c]
        else:
            items = [r for r in results if min_c <= r.raw_confidence < max_c]

        count = len(items)
        if count > 0:
            avg_conf = (sum((r.raw_confidence for r in items), Decimal("0")) / count).quantize(
                Decimal("0.0001"), rounding=ROUND_HALF_UP
            )
            # Correct if both action matched and zero hallucinated citations
            correct_count = sum(1 for r in items if r.action_matched and r.citations_valid)
            empirical_acc = (Decimal(correct_count) / Decimal(count)).quantize(
                Decimal("0.0001"), rounding=ROUND_HALF_UP
            )
            gap = abs(avg_conf - empirical_acc).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
            weighted_ece_sum += (Decimal(count) / Decimal(total)) * gap
            if gap > max_gap:
                max_gap = gap
        else:
            avg_conf = ((min_c + max_c) / Decimal("2")).quantize(Decimal("0.0001"))
            empirical_acc = Decimal("0.0000")
            gap = Decimal("0.0000")

        buckets.append(
            CalibrationBucket(
                bucket_range=label,
                min_confidence=min_c,
                max_confidence=max_c,
                count=count,
                avg_confidence=avg_conf,
                empirical_accuracy=empirical_acc,
                calibration_gap=gap,
            )
        )

    ece = weighted_ece_sum.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    mce = max_gap.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

    return ConfidenceCalibrationReport(
        total_predictions=total,
        expected_calibration_error=ece,
        maximum_calibration_error=mce,
        buckets=buckets,
    )
