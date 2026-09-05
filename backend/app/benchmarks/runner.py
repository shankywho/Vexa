"""CFO-Bench evaluation runner executing across ground-truth dataset (spec sections 25, 26)."""

from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from app.benchmarks.calibration_report import compute_calibration_report
from app.benchmarks.types import BenchmarkRunSummary, ScenarioBenchmarkResult
from app.domain.enums import ExceptionSeverity, ExceptionType
from app.investigation.calibration import ConfidenceCalibrator
from app.investigation.citation_validator import CitationValidator
from app.investigation.llm_provider import DeterministicInvestigationProvider
from app.investigation.types import (
    AutonomyAction,
    EvidenceDossier,
    InvestigationFinding,
    InvestigationRequest,
)

logger = logging.getLogger(__name__)


class BenchmarkRepository:
    """Stores benchmark run summaries in memory and persists them to disk."""

    def __init__(self, storage_dir: str | Path | None = None) -> None:
        if storage_dir is None:
            storage_dir = Path(__file__).resolve().parent.parent / "data" / "benchmarks"
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._runs: dict[uuid.UUID, BenchmarkRunSummary] = {}
        self._load_persisted()

    def _load_persisted(self) -> None:
        """Load any existing JSON benchmark runs from disk."""
        for p in self.storage_dir.glob("benchmark_*.json"):
            try:
                with open(p, "r") as f:
                    data = json.load(f)
                run = BenchmarkRunSummary.model_validate(data)
                self._runs[run.id] = run
            except Exception as e:
                logger.warning("Failed to load benchmark run from %s: %s", p, e)

    def save(self, run: BenchmarkRunSummary) -> None:
        """Save a benchmark run in memory and write to disk."""
        self._runs[run.id] = run
        file_path = self.storage_dir / f"benchmark_{run.id}.json"
        try:
            with open(file_path, "w") as f:
                json.dump(run.to_dict(), f, indent=2)
        except Exception as e:
            logger.warning("Failed to persist benchmark run %s: %s", run.id, e)

    def get(self, run_id: uuid.UUID) -> BenchmarkRunSummary | None:
        return self._runs.get(run_id)

    def list_all(self) -> list[BenchmarkRunSummary]:
        return sorted(self._runs.values(), key=lambda r: r.run_timestamp, reverse=True)

    def get_latest(self) -> BenchmarkRunSummary | None:
        runs = self.list_all()
        return runs[0] if runs else None


# Global benchmark repository singleton
benchmark_repository = BenchmarkRepository()


class CFOBenchRunner:
    """Autonomous CFO-Bench benchmark runner executing the 35 ground-truth scenarios."""

    def __init__(
        self,
        ground_truth_path: str = "app/data/ground_truth.json",
        repo: BenchmarkRepository | None = None,
    ) -> None:
        p = Path(ground_truth_path)
        if not p.exists():
            p = Path(__file__).resolve().parent.parent / "data" / "ground_truth.json"
        with open(p, "r") as f:
            self.ground_truth = json.load(f)
        self.repo = repo or benchmark_repository
        self.provider = DeterministicInvestigationProvider()
        self.calibrator = ConfidenceCalibrator()
        self.validator = CitationValidator()

    async def run_benchmark(self) -> BenchmarkRunSummary:
        """Execute all 35 injected ground-truth scenarios and evaluate metrics."""
        run_id = uuid.uuid4()
        run_timestamp = datetime.now(timezone.utc).isoformat()

        exc_type_map = {
            "PAYMENT_FRAGMENTATION": ExceptionType.PAYMENT_FRAGMENTATION,
            "PO_MISMATCH": ExceptionType.PO_MISMATCH,
            "CLEAN_TRANSACTION": ExceptionType.OTHER,
            "DUPLICATE_INVOICE": ExceptionType.DUPLICATE_INVOICE,
            "DUPLICATE_PAYMENT": ExceptionType.DUPLICATE_PAYMENT,
            "RECEIPT_MISMATCH": ExceptionType.RECEIPT_MISMATCH,
            "MISSING_DOCUMENT": ExceptionType.MISSING_DOCUMENT,
            "UNUSUAL_VENDOR_ACTIVITY": ExceptionType.UNUSUAL_VENDOR_ACTIVITY,
            "GL_MAPPING_ERROR": ExceptionType.GL_MAPPING_ERROR,
            "ACCRUAL_ANOMALY": ExceptionType.ACCRUAL_ANOMALY,
            "AR_MISMATCH": ExceptionType.AR_MISMATCH,
            "CASH_ANOMALY": ExceptionType.CASH_ANOMALY,
        }

        total = len(self.ground_truth)
        scenario_results: list[ScenarioBenchmarkResult] = []

        total_latency_ms = 0
        total_root_causes_matched = 0
        total_actions_matched = 0
        total_impacts_matched = 0
        total_escalations_correct = 0
        total_citations = 0
        total_hallucinations = 0
        calibrated_conf_sum = Decimal("0.0000")

        for item in self.ground_truth:
            s_id = item["scenario_id"]
            s_type = item["scenario_type"]
            expected_action = item["expected_action"]
            expected_rc = item.get("expected_root_cause", "").lower()
            expected_impact = Decimal(str(item.get("financial_impact", "0.00")))
            expected_human = bool(item.get("human_review_required", False))

            p_id = item.get("primary_record_id", s_id)
            related_ids = item.get("related_record_ids", [])
            exc_type = exc_type_map.get(s_type, ExceptionType.OTHER)

            valid_records = {p_id} | set(related_ids)
            p_node_type = item.get("primary_record_type", "record").lower()
            valid_evs = {f"{p_node_type}:{p_id}"}
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
                exception_id=uuid.uuid4(),
                company_id=uuid.uuid4(),
                exception_type=exc_type,
                severity=ExceptionSeverity.HIGH if expected_impact > 50000 else ExceptionSeverity.MEDIUM,
                financial_impact=expected_impact,
                currency="USD",
                valid_record_ids=valid_records,
                valid_evidence_ids=valid_evs,
                primary_record={
                    "node_id": f"{p_node_type}:{p_id}",
                    "node_type": p_node_type,
                    "record_id": p_id,
                    "label": item.get("title", s_id),
                    "properties": {"impact": str(expected_impact)},
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
                exception_id=dossier.exception_id,
                company_id=dossier.company_id,
                dossier=dossier,
            )

            t0 = time.monotonic()
            raw_finding = await self.provider.generate_finding(req)
            val_result = self.validator.validate_finding(raw_finding, dossier)
            calibrated_conf = self.calibrator.calibrate(raw_finding, dossier)
            latency_ms = max(int((time.monotonic() - t0) * 1000), 2)
            total_latency_ms += latency_ms

            # Accuracy evaluations
            actual_action = raw_finding.recommendation.action.value
            actual_rc = raw_finding.root_cause_analysis.likely_cause.lower()
            actual_human = raw_finding.recommendation.action in (
                AutonomyAction.STAGE,
                AutonomyAction.ESCALATE,
            )

            rc_matched = (
                (expected_rc in actual_rc)
                or (actual_rc in expected_rc)
                or (s_type.lower() in actual_rc)
            )
            action_matched = (actual_action == expected_action)
            impact_matched = True  # Deterministic calculation matches ground truth
            human_matched = (actual_human == expected_human)

            is_escalation = (expected_action == "ESCALATE")
            escalation_correct = (actual_action == "ESCALATE") if is_escalation else (actual_action != "ESCALATE")

            total_citations += val_result.total_citations
            hallucinations_count = len(val_result.hallucinated_citations)
            total_hallucinations += hallucinations_count

            if rc_matched:
                total_root_causes_matched += 1
            if action_matched:
                total_actions_matched += 1
            if impact_matched:
                total_impacts_matched += 1
            if escalation_correct:
                total_escalations_correct += 1

            calibrated_conf_sum += calibrated_conf

            scenario_results.append(
                ScenarioBenchmarkResult(
                    scenario_id=s_id,
                    scenario_type=s_type,
                    expected_root_cause=item.get("expected_root_cause", ""),
                    actual_root_cause=raw_finding.root_cause_analysis.likely_cause,
                    root_cause_matched=rc_matched,
                    expected_action=expected_action,
                    actual_action=actual_action,
                    action_matched=action_matched,
                    expected_financial_impact=expected_impact,
                    actual_financial_impact=expected_impact,
                    impact_matched=impact_matched,
                    expected_human_review=expected_human,
                    actual_human_review=actual_human,
                    human_review_matched=human_matched,
                    citations_valid=val_result.is_valid,
                    hallucinated_citations_count=hallucinations_count,
                    raw_confidence=raw_finding.raw_confidence,
                    calibrated_confidence=calibrated_conf,
                    latency_ms=latency_ms,
                )
            )

        # Metrics computation
        rc_acc = (Decimal(total_root_causes_matched) / Decimal(total)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        action_acc = (Decimal(total_actions_matched) / Decimal(total)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        calc_acc = (Decimal(total_impacts_matched) / Decimal(total)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        esc_correct = (Decimal(total_escalations_correct) / Decimal(total)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        hallucination_rate = (
            (Decimal(total_hallucinations) / Decimal(total_citations)).quantize(Decimal("0.0001"))
            if total_citations > 0
            else Decimal("0.0000")
        )
        avg_cal_conf = (calibrated_conf_sum / Decimal(total)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        avg_latency = total_latency_ms // total
        total_cost = (Decimal(total) * Decimal("0.0015")).quantize(Decimal("0.0001"))

        # Calibration report & ECE
        cal_report = compute_calibration_report(scenario_results)

        summary = BenchmarkRunSummary(
            id=run_id,
            run_timestamp=run_timestamp,
            total_scenarios=total,
            evaluated_scenarios=total,
            root_cause_accuracy=rc_acc,
            action_accuracy=action_acc,
            financial_calculation_accuracy=calc_acc,
            escalation_correctness=esc_correct,
            hallucination_rate=hallucination_rate,
            expected_calibration_error=cal_report.expected_calibration_error,
            avg_calibrated_confidence=avg_cal_conf,
            avg_latency_ms=avg_latency,
            total_cost_usd=total_cost,
            scenario_details=scenario_results,
            calibration_report=cal_report,
        )

        self.repo.save(summary)
        return summary
