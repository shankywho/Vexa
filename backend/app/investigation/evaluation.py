"""Evaluation framework testing CFO Investigation Agent against ground_truth.json."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.domain.enums import ExceptionSeverity, ExceptionType
from app.investigation.llm_provider import DeterministicInvestigationProvider
from app.investigation.types import (
    EvidenceDossier,
    InvestigationRequest,
)


@dataclass
class InvestigationEvaluationReport:
    """Summary metrics of evaluating the investigation agent across ground truth."""

    total_scenarios: int
    evaluated_scenarios: int
    successful_investigations: int
    action_accuracy: Decimal
    root_cause_accuracy: Decimal
    hallucination_rate: Decimal
    avg_calibrated_confidence: Decimal
    scenario_details: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_scenarios": self.total_scenarios,
            "evaluated_scenarios": self.evaluated_scenarios,
            "successful_investigations": self.successful_investigations,
            "action_accuracy": str(self.action_accuracy),
            "root_cause_accuracy": str(self.root_cause_accuracy),
            "hallucination_rate": str(self.hallucination_rate),
            "avg_calibrated_confidence": str(self.avg_calibrated_confidence),
            "scenario_details": self.scenario_details,
        }


class InvestigationEvaluator:
    """Evaluates the CFO Investigation Agent against the 35 injected ground-truth scenarios."""

    def __init__(self, ground_truth_path: str = "app/data/ground_truth.json") -> None:
        p = Path(ground_truth_path)
        if not p.exists():
            p = Path(__file__).resolve().parent.parent / "data" / "ground_truth.json"
        with open(p, "r") as f:
            self.ground_truth = json.load(f)

    async def evaluate_scenarios(self) -> InvestigationEvaluationReport:
        """Run all 35 ground-truth scenarios through the investigation reasoning engine."""
        provider = DeterministicInvestigationProvider()
        total = len(self.ground_truth)
        matched_actions = 0
        matched_root_causes = 0
        total_citations = 0
        hallucinated_citations = 0
        confidence_sum = Decimal("0.0000")
        details: list[dict[str, Any]] = []

        for item in self.ground_truth:
            s_id = item["scenario_id"]
            s_type = item["scenario_type"]
            expected_action = item["expected_action"]
            expected_rc = item.get("expected_root_cause", "").lower()
            p_id = item.get("primary_record_id", s_id)
            related_ids = item.get("related_record_ids", [])
            impact = Decimal(str(item.get("financial_impact", "0.00")))

            # Map scenario type to ExceptionType enum
            exc_type_map = {
                "PAYMENT_FRAGMENTATION": ExceptionType.PAYMENT_FRAGMENTATION,
                "PO_MISMATCH": ExceptionType.PO_MISMATCH,
                "CLEAN_TRANSACTION": ExceptionType.OTHER,  # impact 0 clean check
                "DUPLICATE_INVOICE": ExceptionType.DUPLICATE_INVOICE,
                "DUPLICATE_PAYMENT": ExceptionType.DUPLICATE_PAYMENT,
                "RECEIPT_MISMATCH": ExceptionType.RECEIPT_MISMATCH,
                "MISSING_DOCUMENT": ExceptionType.MISSING_DOCUMENT,
                "UNUSUAL_VENDOR_ACTIVITY": ExceptionType.UNUSUAL_VENDOR_ACTIVITY,
                "GL_MAPPING_ERROR": ExceptionType.GL_MAPPING_ERROR,
                "ACCRUAL_ANOMALY": ExceptionType.ACCRUAL_ANOMALY,
                "AR_MISMATCH": ExceptionType.AR_MISMATCH,
                "CASH_ANOMALY": ExceptionType.CASH_ANOMALY,
                "BANK_DUPLICATE": ExceptionType.BANK_DUPLICATE,
            }
            exc_type = exc_type_map.get(s_type, ExceptionType.OTHER)

            # Build synthetic bounded dossier representing ground truth
            import uuid

            exc_uuid = uuid.uuid4()
            comp_uuid = uuid.uuid4()
            valid_records = {p_id} | set(related_ids)
            valid_evs = {f"{item.get('primary_record_type', 'record').lower()}:{p_id}"}
            for rid in related_ids:
                valid_evs.add(f"record:{rid}")
                valid_evs.add(f"payment:{rid}")
                valid_evs.add(f"invoice:{rid}")
                valid_evs.add(f"purchase_order:{rid}")
                valid_evs.add(f"goods_receipt:{rid}")

            related_records = [
                {
                    "node_id": f"record:{rid}",
                    "node_type": "payment" if s_type == "PAYMENT_FRAGMENTATION" else "record",
                    "record_id": rid,
                    "label": f"Related {rid}",
                    "properties": {},
                }
                for rid in related_ids
            ]

            dossier = EvidenceDossier(
                exception_id=exc_uuid,
                company_id=comp_uuid,
                exception_type=exc_type,
                severity=ExceptionSeverity.HIGH if impact > 50000 else ExceptionSeverity.MEDIUM,
                financial_impact=impact,
                currency="USD",
                valid_record_ids=valid_records,
                valid_evidence_ids=valid_evs,
                primary_record={
                    "node_id": f"{item.get('primary_record_type', 'record').lower()}:{p_id}",
                    "node_type": item.get("primary_record_type", "record").lower(),
                    "record_id": p_id,
                    "label": item.get("title", s_id),
                    "properties": {"impact": str(impact)},
                },
                related_records=related_records,
                ranked_nodes=[{"node_id": f"node:{p_id}", "score": 1.0, "label": s_id}],
                graph_edges=[],
                markdown_dossier=(
                    f"# Scenario {s_id}: {item.get('title')}\n"
                    f"Description: {item.get('description')}"
                ),
            )

            req = InvestigationRequest(
                exception_id=exc_uuid,
                company_id=comp_uuid,
                dossier=dossier,
            )

            finding = await provider.generate_finding(req)

            # Validate citations
            from app.investigation.calibration import ConfidenceCalibrator
            from app.investigation.citation_validator import CitationValidator

            val = CitationValidator().validate_finding(finding, dossier)
            calibrated = ConfidenceCalibrator().calibrate(finding, dossier)

            actual_action = finding.recommendation.action.value
            actual_rc = finding.root_cause_analysis.likely_cause.lower()

            action_match = actual_action == expected_action
            rc_match = (
                (expected_rc in actual_rc)
                or (actual_rc in expected_rc)
                or (s_type.lower() in actual_rc)
            )

            if action_match:
                matched_actions += 1
            if rc_match:
                matched_root_causes += 1

            total_citations += val.total_citations
            hallucinated_citations += len(val.hallucinated_citations)
            confidence_sum += calibrated

            details.append(
                {
                    "scenario_id": s_id,
                    "scenario_type": s_type,
                    "expected_action": expected_action,
                    "actual_action": actual_action,
                    "action_match": action_match,
                    "expected_root_cause": item.get("expected_root_cause"),
                    "actual_root_cause": finding.root_cause_analysis.likely_cause,
                    "rc_match": rc_match,
                    "citations_valid": val.is_valid,
                    "hallucinations_count": len(val.hallucinated_citations),
                    "calibrated_confidence": str(calibrated),
                }
            )

        action_acc = (Decimal(matched_actions) / Decimal(total)).quantize(Decimal("0.0001"))
        rc_acc = (Decimal(matched_root_causes) / Decimal(total)).quantize(Decimal("0.0001"))
        hal_rate = (
            (Decimal(hallucinated_citations) / Decimal(total_citations)).quantize(Decimal("0.0001"))
            if total_citations > 0
            else Decimal("0.0000")
        )
        avg_conf = (confidence_sum / Decimal(total)).quantize(Decimal("0.0001"))

        return InvestigationEvaluationReport(
            total_scenarios=total,
            evaluated_scenarios=total,
            successful_investigations=total,
            action_accuracy=action_acc,
            root_cause_accuracy=rc_acc,
            hallucination_rate=hal_rate,
            avg_calibrated_confidence=avg_conf,
            scenario_details=details,
        )
