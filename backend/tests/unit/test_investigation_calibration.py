"""Unit tests for ConfidenceCalibrator (spec section 12.1)."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

from app.domain.enums import ExceptionSeverity, ExceptionType, Role
from app.investigation.calibration import ConfidenceCalibrator
from app.investigation.types import (
    AutonomyAction,
    EvidenceDossier,
    FindingStatus,
    InvestigationFinding,
    InvestigationRecommendation,
    RootCauseAnalysis,
)


@pytest.fixture
def empty_dossier() -> EvidenceDossier:
    return EvidenceDossier(
        exception_id=uuid.uuid4(),
        company_id=uuid.uuid4(),
        exception_type=ExceptionType.PO_MISMATCH,
        severity=ExceptionSeverity.HIGH,
        financial_impact=Decimal("1000.00"),
        currency="USD",
        valid_record_ids=set(),
        valid_evidence_ids=set(),
    )


def test_confidence_calibration_empirical_buckets(empty_dossier: EvidenceDossier):
    calibrator = ConfidenceCalibrator()

    # Raw confidence 0.98 falls in [0.95, 1.00] -> empirical accuracy 0.9800
    finding = InvestigationFinding(
        exception_id=empty_dossier.exception_id,
        exception_type=empty_dossier.exception_type,
        finding_status=FindingStatus.COMPLETED,
        root_cause_analysis=RootCauseAnalysis(
            primary_category="TEST",
            summary="test",
            likely_cause="test",
            is_genuine_discrepancy=False,
            is_timing_or_operational=False,
        ),
        recommendation=InvestigationRecommendation(
            action=AutonomyAction.AUTO_RESOLVE,
            target_role=Role.ACCOUNTANT,
            recommended_action="Resolve",
            should_block_close=False,
            should_escalate_to_cfo=False,
        ),
        raw_confidence=Decimal("0.9800"),
        all_citations_valid=True,
    )

    calibrated = calibrator.calibrate(finding, empty_dossier)
    assert calibrated == Decimal("0.9800")

    # Raw confidence 0.85 falls in [0.80, 0.90] -> 0.8400
    finding_mid = finding.model_copy(update={"raw_confidence": Decimal("0.8500")})
    assert calibrator.calibrate(finding_mid, empty_dossier) == Decimal("0.8400")


def test_confidence_calibration_penalizes_uncertainties_and_missing_evidence(
    empty_dossier: EvidenceDossier,
):
    calibrator = ConfidenceCalibrator()

    finding = InvestigationFinding(
        exception_id=empty_dossier.exception_id,
        exception_type=empty_dossier.exception_type,
        finding_status=FindingStatus.COMPLETED,
        root_cause_analysis=RootCauseAnalysis(
            primary_category="TEST",
            summary="test",
            likely_cause="test",
            is_genuine_discrepancy=False,
            is_timing_or_operational=False,
        ),
        recommendation=InvestigationRecommendation(
            action=AutonomyAction.STAGE,
            target_role=Role.CONTROLLER,
            recommended_action="Review",
            should_block_close=True,
            should_escalate_to_cfo=False,
        ),
        raw_confidence=Decimal("0.9800"),  # base: 0.9800
        uncertainties=["Uncertainty A", "Uncertainty B"],  # -0.1000
        missing_evidence=["Missing Doc 1"],  # -0.1000
        all_citations_valid=True,
    )

    # 0.9800 - (2 * 0.0500) - (1 * 0.1000) = 0.7800
    calibrated = calibrator.calibrate(finding, empty_dossier)
    assert calibrated == Decimal("0.7800")


def test_confidence_calibration_severely_penalizes_hallucinations(empty_dossier: EvidenceDossier):
    calibrator = ConfidenceCalibrator()

    finding = InvestigationFinding(
        exception_id=empty_dossier.exception_id,
        exception_type=empty_dossier.exception_type,
        finding_status=FindingStatus.COMPLETED,
        root_cause_analysis=RootCauseAnalysis(
            primary_category="TEST",
            summary="test",
            likely_cause="test",
            is_genuine_discrepancy=False,
            is_timing_or_operational=False,
        ),
        recommendation=InvestigationRecommendation(
            action=AutonomyAction.AUTO_RESOLVE,
            target_role=Role.ACCOUNTANT,
            recommended_action="Resolve",
            should_block_close=False,
            should_escalate_to_cfo=False,
        ),
        raw_confidence=Decimal("0.9900"),  # base 0.9800
        all_citations_valid=False,
        hallucinated_citations=["fake-citation-id"],  # -0.5000 deduction
    )

    calibrated = calibrator.calibrate(finding, empty_dossier)
    # 0.9800 - 0.5000 = 0.4800
    assert calibrated == Decimal("0.4800")
