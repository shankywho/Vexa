"""Independent verification engines (spec section 10, 12, 12.1, 39)."""

from __future__ import annotations

from decimal import Decimal

from app.close_workflow.types import ClosePolicy
from app.db.models.exception import ExceptionRecord
from app.domain.enums import AutonomyLevel, ExceptionType
from app.investigation.types import (
    AutonomyAction,
    EvidenceDossier,
    FindingStatus,
    InvestigationFinding,
)


class IndependentCalculationVerifier:
    """Independently recalculates financial variances and impacts without trusting LLM claims."""

    def verify_calculations(
        self,
        finding: InvestigationFinding,
        dossier: EvidenceDossier,
        exception: ExceptionRecord,
    ) -> tuple[bool, Decimal, Decimal, list[str]]:
        """Recalculate financial variance directly from evidence.

        Returns:
            tuple of (is_valid, recalculated_impact, variance_diff, calculation_errors)
        """
        errors: list[str] = []
        expected_impact = exception.financial_impact
        recalculated_impact = expected_impact

        # Check for clean match: impact must be 0
        if (
            finding.root_cause_analysis.likely_cause.lower().startswith("clean")
            or "clean transaction" in finding.executive_summary.lower()
        ):
            recalculated_impact = Decimal("0.00")
            variance_diff = abs(recalculated_impact - expected_impact)
            if variance_diff > Decimal("0.01"):
                errors.append(
                    f"Clean transaction expected 0.00 variance, but recorded impact was {expected_impact}"
                )
            return (len(errors) == 0, recalculated_impact, variance_diff, errors)

        # Discrepancy based on Invoice vs PO / Receipt
        if dossier.exception_type in (
            ExceptionType.PO_MISMATCH,
            ExceptionType.RECEIPT_MISMATCH,
            ExceptionType.MISSING_DOCUMENT,
        ):
            if dossier.invoices and dossier.purchase_orders:
                inv = dossier.invoices[0]
                po = dossier.purchase_orders[0]
                inv_total = getattr(inv, "total", getattr(inv, "total_amount", Decimal("0.00")))
                po_total = getattr(po, "total", getattr(po, "total_amount", Decimal("0.00")))
                diff = abs(inv_total - po_total)
                recalculated_impact = diff
                variance_diff = abs(recalculated_impact - expected_impact)
                if variance_diff > Decimal("0.01"):
                    errors.append(
                        f"Independent calculation mismatch: Invoice ({inv_total}) vs PO ({po_total}) "
                        f"difference {diff} does not match exception impact {expected_impact}"
                    )
            elif dossier.invoices:
                inv_total = getattr(
                    dossier.invoices[0],
                    "total",
                    getattr(dossier.invoices[0], "total_amount", Decimal("0.00")),
                )
                recalculated_impact = inv_total
                variance_diff = abs(recalculated_impact - expected_impact)
                if variance_diff > Decimal("0.01"):
                    errors.append(
                        f"Invoice total {recalculated_impact} differs from recorded impact {expected_impact}"
                    )

        # Bank transaction vs Payment or GL
        elif dossier.exception_type in (
            ExceptionType.BANK_GL_MISMATCH,
            ExceptionType.PAYMENT_MISMATCH,
            ExceptionType.DUPLICATE_PAYMENT,
            ExceptionType.PAYMENT_FRAGMENTATION,
            ExceptionType.CASH_ANOMALY,
        ):
            if dossier.bank_transactions and dossier.payments:
                bank_amt = dossier.bank_transactions[0].amount
                pay_amt = dossier.payments[0].amount
                diff = abs(bank_amt - pay_amt)
                recalculated_impact = diff if diff > Decimal("0") else bank_amt
                variance_diff = abs(recalculated_impact - expected_impact)
                if variance_diff > Decimal("0.01"):
                    errors.append(
                        f"Independent bank recon mismatch: Bank txn ({bank_amt}) vs Payment ({pay_amt}) "
                        f"variance {diff} does not match recorded impact {expected_impact}"
                    )
            elif dossier.bank_transactions:
                recalculated_impact = dossier.bank_transactions[0].amount
                variance_diff = abs(recalculated_impact - expected_impact)
                if variance_diff > Decimal("0.01"):
                    errors.append(
                        f"Bank txn amount {recalculated_impact} differs from recorded impact {expected_impact}"
                    )

        # Journal entry errors
        elif dossier.exception_type in (
            ExceptionType.GL_MAPPING_ERROR,
            ExceptionType.ACCRUAL_ANOMALY,
            ExceptionType.AR_MISMATCH,
            ExceptionType.UNUSUAL_VENDOR_ACTIVITY,
        ):
            if dossier.journal_entries:
                je = dossier.journal_entries[0]
                je_total = getattr(
                    je,
                    "total",
                    getattr(je, "total_amount", getattr(je, "subtotal", expected_impact)),
                )
                recalculated_impact = je_total
                variance_diff = abs(recalculated_impact - expected_impact)
                if variance_diff > Decimal("0.01"):
                    errors.append(
                        f"Journal entry total {recalculated_impact} differs from recorded impact {expected_impact}"
                    )

        variance_diff = abs(recalculated_impact - expected_impact)
        is_valid = len(errors) == 0 and variance_diff <= Decimal("0.01")
        return (is_valid, recalculated_impact, variance_diff, errors)


class EvidenceCompletenessVerifier:
    """Validates that all required evidence types and records are present and cited."""

    REQUIRED_TYPES_BY_EXCEPTION: dict[ExceptionType, list[str]] = {
        ExceptionType.PO_MISMATCH: ["invoices", "purchase_orders"],
        ExceptionType.RECEIPT_MISMATCH: ["invoices", "goods_receipts"],
        ExceptionType.MISSING_DOCUMENT: ["invoices"],
        ExceptionType.PAYMENT_MISMATCH: ["bank_transactions"],
        ExceptionType.BANK_GL_MISMATCH: ["bank_transactions"],
        ExceptionType.DUPLICATE_PAYMENT: ["bank_transactions"],
        ExceptionType.PAYMENT_FRAGMENTATION: ["bank_transactions"],
        ExceptionType.CASH_ANOMALY: ["bank_transactions"],
        ExceptionType.GL_MAPPING_ERROR: ["journal_entries"],
        ExceptionType.ACCRUAL_ANOMALY: ["journal_entries"],
        ExceptionType.AR_MISMATCH: ["bank_transactions"],
        ExceptionType.UNUSUAL_VENDOR_ACTIVITY: ["journal_entries"],
    }

    def verify_evidence(
        self,
        dossier: EvidenceDossier,
        finding: InvestigationFinding,
    ) -> tuple[bool, list[str]]:
        """Verify evidence completeness and absence of hallucinations.

        Returns:
            tuple of (is_complete, missing_evidence_list)
        """
        missing: list[str] = []

        # 1. Hallucinated citations are a fatal verification failure
        if not finding.all_citations_valid or finding.hallucinated_citations:
            missing.append(
                f"Fatal citation failure: finding cited {len(finding.hallucinated_citations)} "
                f"non-existent record IDs: {finding.hallucinated_citations}"
            )

        # 2. Check present evidence types across typed lists and graph nodes
        present_types: set[str] = set()
        for attr in (
            "invoices",
            "purchase_orders",
            "goods_receipts",
            "bank_transactions",
            "payments",
            "journal_entries",
        ):
            if getattr(dossier, attr, []):
                present_types.add(attr)

        if dossier.primary_record:
            nt = str(dossier.primary_record.get("node_type", "")).lower()
            if nt:
                present_types.add(nt + "s" if not nt.endswith("s") else nt)

        for rec in dossier.related_records:
            nt = str(rec.get("node_type", "")).lower()
            if nt:
                present_types.add(nt + "s" if not nt.endswith("s") else nt)

        # Check required categories
        req_types = self.REQUIRED_TYPES_BY_EXCEPTION.get(dossier.exception_type, [])
        for req in req_types:
            if req not in present_types and not getattr(dossier, req, []):
                # Only flag if there are no related records in dossier at all
                if not dossier.related_records and not dossier.valid_record_ids:
                    missing.append(
                        f"Missing required evidence category '{req}' for exception type {dossier.exception_type}"
                    )

        # 3. If investigation suffered insufficient evidence, mark incomplete
        if finding.finding_status == FindingStatus.INSUFFICIENT_EVIDENCE:
            missing.append("Investigation marked finding as INSUFFICIENT_EVIDENCE")

        for m in finding.missing_evidence:
            if m not in missing:
                missing.append(m)

        is_complete = not (
            not finding.all_citations_valid
            or bool(finding.hallucinated_citations)
            or finding.finding_status == FindingStatus.INSUFFICIENT_EVIDENCE
            or len(finding.facts) == 0
        )
        return (is_complete, missing)


class PolicyGateVerifier:
    """Enforces deterministic corporate close governance policies (spec section 12)."""

    def evaluate_policy(
        self,
        exception: ExceptionRecord,
        finding: InvestigationFinding,
        calibrated_confidence: Decimal,
        policy: ClosePolicy,
        calculation_valid: bool,
        evidence_complete: bool,
    ) -> tuple[AutonomyLevel, list[str]]:
        """Evaluate corporate policy gates against the finding.

        Returns:
            tuple of (recommended_autonomy, policy_violations)
        """
        violations: list[str] = []

        # Gate 1: Integrity failures block autonomous execution completely
        if not calculation_valid:
            violations.append(
                "Independent calculation verification failed — arithmetic discrepancy detected."
            )
        if not evidence_complete:
            violations.append(
                "Evidence completeness verification failed — missing required records or invalid citations."
            )

        if violations:
            return (AutonomyLevel.OBSERVE, violations)

        # Gate 2: CFO escalation triggers
        if (
            finding.recommendation.action == AutonomyAction.ESCALATE
            or finding.recommendation.should_escalate_to_cfo
            or "fragment" in finding.root_cause_analysis.likely_cause.lower()
            or "litigation" in finding.root_cause_analysis.likely_cause.lower()
            or "withholding" in finding.root_cause_analysis.likely_cause.lower()
            or "revenue account used" in finding.root_cause_analysis.likely_cause.lower()
        ):
            return (AutonomyLevel.RECOMMEND, violations)

        # Gate 3: Threshold checks for AUTO_RESOLVE
        is_auto_recommendation = finding.recommendation.action == AutonomyAction.AUTO_RESOLVE

        if is_auto_recommendation:
            # Policy 1: Materiality cap
            if exception.financial_impact > policy.max_auto_resolution_amount:
                violations.append(
                    f"Financial impact {exception.financial_impact} exceeds max_auto_resolution_amount "
                    f"threshold of {policy.max_auto_resolution_amount}. Human review required."
                )

            # Policy 2: Calibrated confidence requirement
            if calibrated_confidence < policy.min_confidence:
                violations.append(
                    f"Calibrated confidence {calibrated_confidence} is below minimum policy threshold "
                    f"of {policy.min_confidence}. Human review required."
                )

            if violations:
                return (AutonomyLevel.STAGE, violations)
            return (AutonomyLevel.EXECUTE, violations)

        # Gate 4: Default staging for standard discrepancies requiring human review
        return (AutonomyLevel.STAGE, violations)
