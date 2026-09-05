"""Unit tests for CitationValidator in CFO Investigation Agent."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

from app.domain.enums import ExceptionSeverity, ExceptionType
from app.investigation.citation_validator import CitationValidator
from app.investigation.types import (
    AutonomyAction,
    EvidenceDossier,
    Fact,
    FindingStatus,
    Inference,
    InvestigationFinding,
    InvestigationRecommendation,
    Role,
    RootCauseAnalysis,
)


@pytest.fixture
def sample_dossier() -> EvidenceDossier:
    inv_id = str(uuid.uuid4())
    po_id = str(uuid.uuid4())
    exc_id = uuid.uuid4()
    company_id = uuid.uuid4()

    return EvidenceDossier(
        exception_id=exc_id,
        company_id=company_id,
        exception_type=ExceptionType.PO_MISMATCH,
        severity=ExceptionSeverity.HIGH,
        financial_impact=Decimal("384000.00"),
        currency="INR",
        valid_record_ids={inv_id, po_id, str(exc_id)},
        valid_evidence_ids={f"invoice:{inv_id}", f"purchase_order:{po_id}", f"exception:{exc_id}"},
    )


def test_citation_validator_valid_citations(sample_dossier: EvidenceDossier):
    validator = CitationValidator()
    inv_id = list(sample_dossier.valid_record_ids)[0]
    po_id = list(sample_dossier.valid_record_ids)[1]

    finding = InvestigationFinding(
        exception_id=sample_dossier.exception_id,
        exception_type=sample_dossier.exception_type,
        finding_status=FindingStatus.COMPLETED,
        facts=[
            Fact(
                statement="Invoice exists in ledger.",
                evidence_id=f"invoice:{inv_id}",
                record_type="invoice",
                record_id=inv_id,
            ),
            Fact(
                statement="PO was approved.",
                evidence_id=f"purchase_order:{po_id}",
                record_type="purchase_order",
                record_id=po_id,
            ),
        ],
        inferences=[
            Inference(
                statement="Invoice quantity exceeds PO quantity.",
                supported_by_evidence_ids=[f"invoice:{inv_id}", f"purchase_order:{po_id}"],
                confidence=Decimal("0.9500"),
            )
        ],
        root_cause_analysis=RootCauseAnalysis(
            primary_category="PO_MISMATCH",
            summary="Variance between invoice and PO",
            likely_cause="Quantity variance",
            is_genuine_discrepancy=True,
            is_timing_or_operational=False,
        ),
        recommendation=InvestigationRecommendation(
            action=AutonomyAction.STAGE,
            target_role=Role.CONTROLLER,
            recommended_action="Review quantity variance",
            should_block_close=True,
            should_escalate_to_cfo=False,
        ),
    )

    result = validator.validate_finding(finding, sample_dossier)
    assert result.is_valid is True
    assert result.valid_citations == 6
    assert result.citation_accuracy == 1.0
    assert len(result.hallucinated_citations) == 0
    assert len(result.unsupported_claims) == 0


def test_citation_validator_detects_hallucinations(sample_dossier: EvidenceDossier):
    validator = CitationValidator()
    fake_id = str(uuid.uuid4())

    finding = InvestigationFinding(
        exception_id=sample_dossier.exception_id,
        exception_type=sample_dossier.exception_type,
        finding_status=FindingStatus.COMPLETED,
        facts=[
            Fact(
                statement="Phantom invoice was observed.",
                evidence_id=f"invoice:{fake_id}",
                record_type="invoice",
                record_id=fake_id,
            )
        ],
        inferences=[
            Inference(
                statement="Phantom transaction causes imbalance.",
                supported_by_evidence_ids=[f"invoice:{fake_id}"],
                confidence=Decimal("0.9000"),
            )
        ],
        root_cause_analysis=RootCauseAnalysis(
            primary_category="PO_MISMATCH",
            summary="Phantom discrepancy",
            likely_cause="Hallucinated invoice",
            is_genuine_discrepancy=True,
            is_timing_or_operational=False,
        ),
        recommendation=InvestigationRecommendation(
            action=AutonomyAction.STAGE,
            target_role=Role.CONTROLLER,
            recommended_action="Investigate phantom invoice",
            should_block_close=True,
            should_escalate_to_cfo=False,
        ),
    )

    result = validator.validate_finding(finding, sample_dossier)
    assert result.is_valid is False
    assert result.valid_citations == 0
    assert result.citation_accuracy == 0.0
    assert fake_id in str(result.hallucinated_citations)
    assert len(result.unsupported_claims) == 3


def test_citation_validator_unsupported_facts_and_inferences(sample_dossier: EvidenceDossier):
    validator = CitationValidator()

    finding = InvestigationFinding(
        exception_id=sample_dossier.exception_id,
        exception_type=sample_dossier.exception_type,
        finding_status=FindingStatus.COMPLETED,
        facts=[
            Fact(
                statement="Ungrounded claim with no evidence id.",
                evidence_id="",
                record_type="invoice",
                record_id="",
            )
        ],
        inferences=[
            Inference(
                statement="Unsupported deduction.",
                supported_by_evidence_ids=[],
                confidence=Decimal("0.9000"),
            )
        ],
        root_cause_analysis=RootCauseAnalysis(
            primary_category="PO_MISMATCH",
            summary="Unsupported",
            likely_cause="None",
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
    )

    result = validator.validate_finding(finding, sample_dossier)
    assert result.is_valid is False
    assert len(result.unsupported_claims) == 2
