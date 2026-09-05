"""Unit tests for Independent Verification Agent (spec section 10, 12, 12.1)."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

from app.close_workflow.types import ClosePolicy
from app.db.models.exception import ExceptionRecord
from app.db.models.procurement import Invoice, PurchaseOrder
from app.domain.enums import AutonomyLevel, ExceptionSeverity, ExceptionStatus, ExceptionType, Role
from app.investigation.types import (
    AutonomyAction,
    EvidenceDossier,
    FindingStatus,
    InvestigationFinding,
    InvestigationRecommendation,
    RootCauseAnalysis,
)
from app.verification.engine import (
    EvidenceCompletenessVerifier,
    IndependentCalculationVerifier,
    PolicyGateVerifier,
)


@pytest.fixture
def base_exception() -> ExceptionRecord:
    return ExceptionRecord(
        id=uuid.uuid4(),
        company_id=uuid.uuid4(),
        type=ExceptionType.PO_MISMATCH,
        severity=ExceptionSeverity.MEDIUM,
        financial_impact=Decimal("500.00"),
        currency="USD",
        status=ExceptionStatus.OPEN,
    )


@pytest.fixture
def base_finding(base_exception: ExceptionRecord) -> InvestigationFinding:
    return InvestigationFinding(
        exception_id=base_exception.id,
        exception_type=base_exception.type,
        finding_status=FindingStatus.COMPLETED,
        root_cause_analysis=RootCauseAnalysis(
            primary_category="PO_PRICE_VARIANCE",
            summary="Unit price discrepancy",
            likely_cause="Vendor billed 150/unit instead of PO 100/unit across 10 units",
            is_genuine_discrepancy=True,
            is_timing_or_operational=False,
        ),
        recommendation=InvestigationRecommendation(
            action=AutonomyAction.STAGE,
            target_role=Role.CONTROLLER,
            recommended_action="Request credit memo from vendor",
            should_block_close=False,
            should_escalate_to_cfo=False,
        ),
        raw_confidence=Decimal("0.9800"),
        calibrated_confidence=Decimal("0.9600"),
        all_citations_valid=True,
        cited_record_ids=["inv-001", "po-001"],
    )


def test_independent_calculation_verifier_success(
    base_exception: ExceptionRecord, base_finding: InvestigationFinding
):
    verifier = IndependentCalculationVerifier()
    inv = Invoice(
        id=uuid.uuid4(),
        company_id=base_exception.company_id,
        vendor_id=uuid.uuid4(),
        invoice_number="INV-001",
        invoice_date=base_exception.created_at.date() if base_exception.created_at else None,
        total=Decimal("1500.00"),
        currency="USD",
    )
    po = PurchaseOrder(
        id=uuid.uuid4(),
        company_id=base_exception.company_id,
        vendor_id=uuid.uuid4(),
        po_number="PO-001",
        order_date=base_exception.created_at.date() if base_exception.created_at else None,
        total=Decimal("1000.00"),
        currency="USD",
    )
    dossier = EvidenceDossier(
        exception_id=base_exception.id,
        company_id=base_exception.company_id,
        exception_type=ExceptionType.PO_MISMATCH,
        severity=ExceptionSeverity.MEDIUM,
        financial_impact=Decimal("500.00"),
        currency="USD",
        invoices=[inv],
        purchase_orders=[po],
        valid_record_ids={str(inv.id), str(po.id)},
    )

    is_valid, recalc_impact, var_diff, errors = verifier.verify_calculations(
        base_finding, dossier, base_exception
    )
    assert is_valid is True
    assert recalc_impact == Decimal("500.00")
    assert var_diff == Decimal("0.00")
    assert len(errors) == 0


def test_independent_calculation_verifier_detects_mismatch(
    base_exception: ExceptionRecord, base_finding: InvestigationFinding
):
    verifier = IndependentCalculationVerifier()
    # Recorded impact is 500, but invoice vs po variance is 800
    inv = Invoice(
        id=uuid.uuid4(),
        company_id=base_exception.company_id,
        vendor_id=uuid.uuid4(),
        invoice_number="INV-001",
        total=Decimal("1800.00"),
        currency="USD",
    )
    po = PurchaseOrder(
        id=uuid.uuid4(),
        company_id=base_exception.company_id,
        vendor_id=uuid.uuid4(),
        po_number="PO-001",
        total=Decimal("1000.00"),
        currency="USD",
    )
    dossier = EvidenceDossier(
        exception_id=base_exception.id,
        company_id=base_exception.company_id,
        exception_type=ExceptionType.PO_MISMATCH,
        severity=ExceptionSeverity.MEDIUM,
        financial_impact=Decimal("500.00"),
        currency="USD",
        invoices=[inv],
        purchase_orders=[po],
        valid_record_ids={str(inv.id), str(po.id)},
    )

    is_valid, recalc_impact, var_diff, errors = verifier.verify_calculations(
        base_finding, dossier, base_exception
    )
    assert is_valid is False
    assert var_diff == Decimal("300.00")
    assert len(errors) >= 1
    assert "mismatch" in errors[0].lower()


def test_evidence_completeness_verifier(
    base_exception: ExceptionRecord, base_finding: InvestigationFinding
):
    verifier = EvidenceCompletenessVerifier()

    # Case 1: Missing required purchase orders
    inv_single = Invoice(
        id=uuid.uuid4(),
        company_id=base_exception.company_id,
        vendor_id=uuid.uuid4(),
        invoice_number="I1",
        total=Decimal("100"),
        currency="USD",
    )
    dossier_incomplete = EvidenceDossier(
        exception_id=base_exception.id,
        company_id=base_exception.company_id,
        exception_type=ExceptionType.PO_MISMATCH,
        severity=ExceptionSeverity.MEDIUM,
        financial_impact=Decimal("500.00"),
        currency="USD",
        invoices=[inv_single],
        purchase_orders=[],  # Missing!
        valid_record_ids=set(),
    )
    complete, missing = verifier.verify_evidence(dossier_incomplete, base_finding)
    assert complete is False
    assert any("purchase_orders" in m for m in missing)

    # Case 2: Hallucinated citations
    finding_hallucinated = base_finding.model_copy(
        update={
            "all_citations_valid": False,
            "hallucinated_citations": ["fake-id-999"],
        }
    )
    complete_hallu, missing_hallu = verifier.verify_evidence(
        dossier_incomplete, finding_hallucinated
    )
    assert complete_hallu is False
    assert any("fake-id-999" in m for m in missing_hallu)


def test_policy_gate_verifier(base_exception: ExceptionRecord, base_finding: InvestigationFinding):
    verifier = PolicyGateVerifier()
    policy = ClosePolicy(
        max_auto_resolution_amount=Decimal("1000.00"),
        min_confidence=Decimal("0.9500"),
    )

    # Case 1: Safe auto-resolve (small impact, high confidence, clean)
    finding_auto = base_finding.model_copy(
        update={
            "recommendation": InvestigationRecommendation(
                action=AutonomyAction.AUTO_RESOLVE,
                target_role=Role.ACCOUNTANT,
                recommended_action="Auto-resolve clean variance within tolerances",
                should_block_close=False,
                should_escalate_to_cfo=False,
            )
        }
    )
    autonomy, violations = verifier.evaluate_policy(
        exception=base_exception,  # impact 500 <= 1000
        finding=finding_auto,
        calibrated_confidence=Decimal("0.9600"),  # >= 0.95
        policy=policy,
        calculation_valid=True,
        evidence_complete=True,
    )
    assert autonomy == AutonomyLevel.EXECUTE
    assert len(violations) == 0

    # Case 2: Exceeds max auto amount threshold
    high_exc = ExceptionRecord(
        company_id=base_exception.company_id,
        type=ExceptionType.PO_MISMATCH,
        severity=ExceptionSeverity.HIGH,
        financial_impact=Decimal("5000.00"),  # > 1000
        currency="USD",
        status=ExceptionStatus.OPEN,
    )
    autonomy_high, violations_high = verifier.evaluate_policy(
        exception=high_exc,
        finding=finding_auto,
        calibrated_confidence=Decimal("0.9600"),
        policy=policy,
        calculation_valid=True,
        evidence_complete=True,
    )
    assert autonomy_high == AutonomyLevel.STAGE
    assert any("max_auto_resolution_amount" in v for v in violations_high)

    # Case 3: Calculation or evidence invalid blocks to OBSERVE
    autonomy_invalid, violations_invalid = verifier.evaluate_policy(
        exception=base_exception,
        finding=finding_auto,
        calibrated_confidence=Decimal("0.9600"),
        policy=policy,
        calculation_valid=False,  # FAILED
        evidence_complete=True,
    )
    assert autonomy_invalid == AutonomyLevel.OBSERVE
    assert len(violations_invalid) > 0
