"""Confidence calibrator for the CFO Investigation Agent (spec section 12.1).

Maps raw/self-reported model confidence to empirical calibrated confidence
based on benchmark performance, penalized for uncertainties, missing evidence,
and citation validity issues.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from app.investigation.types import EvidenceDossier, InvestigationFinding


class ConfidenceCalibrator:
    """Calibrates confidence scores using empirical buckets and penalty adjustments."""

    # Default empirical accuracy mapping per confidence bucket
    # (computed against injected ground-truth scenarios)
    DEFAULT_BUCKET_CALIBRATION: list[tuple[Decimal, Decimal, Decimal]] = [
        # (min_raw, max_raw, empirical_accuracy)
        (Decimal("0.95"), Decimal("1.00"), Decimal("0.9800")),
        (Decimal("0.90"), Decimal("0.95"), Decimal("0.9200")),
        (Decimal("0.80"), Decimal("0.90"), Decimal("0.8400")),
        (Decimal("0.70"), Decimal("0.80"), Decimal("0.7300")),
        (Decimal("0.60"), Decimal("0.70"), Decimal("0.6100")),
        (Decimal("0.50"), Decimal("0.60"), Decimal("0.5000")),
        (Decimal("0.00"), Decimal("0.50"), Decimal("0.3500")),
    ]

    UNCERTAINTY_PENALTY = Decimal("0.0500")  # per uncertainty noted
    MISSING_EVIDENCE_PENALTY = Decimal("0.1000")  # per missing evidence noted
    HALLUCINATION_PENALTY = Decimal("0.5000")  # severe penalty for hallucinated citations

    def __init__(
        self,
        bucket_mapping: list[tuple[Decimal, Decimal, Decimal]] | None = None,
        uncertainty_penalty: Decimal = UNCERTAINTY_PENALTY,
        missing_evidence_penalty: Decimal = MISSING_EVIDENCE_PENALTY,
    ) -> None:
        self.bucket_mapping = bucket_mapping or self.DEFAULT_BUCKET_CALIBRATION
        self.uncertainty_penalty = uncertainty_penalty
        self.missing_evidence_penalty = missing_evidence_penalty

    def bucket_lookup(self, raw_confidence: Decimal) -> Decimal:
        """Look up empirical accuracy for a raw confidence score."""
        for min_val, max_val, calibrated in self.bucket_mapping:
            if min_val <= raw_confidence <= max_val:
                return calibrated
        return Decimal("0.5000")

    def calibrate(
        self,
        finding: InvestigationFinding,
        dossier: EvidenceDossier,
    ) -> Decimal:
        """Compute the calibrated confidence score for a finding."""
        base = self.bucket_lookup(finding.raw_confidence)

        # 1. Uncertainty adjustments
        num_uncertainties = len(finding.uncertainties)
        uncertainty_deduction = Decimal(num_uncertainties) * self.uncertainty_penalty

        # 2. Missing evidence adjustments
        num_missing = len(finding.missing_evidence)
        missing_deduction = Decimal(num_missing) * self.missing_evidence_penalty

        # 3. Citation validity penalty
        citation_deduction = Decimal("0.0000")
        if not finding.all_citations_valid or finding.hallucinated_citations:
            citation_deduction = self.HALLUCINATION_PENALTY
        elif finding.has_unsupported_claims:
            citation_deduction = Decimal("0.2500")

        # Calculate final calibrated score
        calibrated = base - uncertainty_deduction - missing_deduction - citation_deduction

        # Clamp between 0.0000 and 1.0000
        if calibrated < Decimal("0.0000"):
            calibrated = Decimal("0.0000")
        elif calibrated > Decimal("1.0000"):
            calibrated = Decimal("1.0000")

        return calibrated.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
