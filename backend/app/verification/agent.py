"""Independent Verification Agent (Agent 5, spec section 10, 12, 12.1)."""

from __future__ import annotations

import json
import time
import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import AuditService
from app.db.base import utcnow
from app.db.models.agent import AgentRun, AgentStep
from app.db.repository import ExceptionRepository
from app.domain.enums import AgentRunStatus, AuditEventType
from app.verification.engine import (
    EvidenceCompletenessVerifier,
    IndependentCalculationVerifier,
    PolicyGateVerifier,
)
from app.verification.types import VerificationRequest, VerificationResult

VERIFIER_PROMPT_VERSION_ID = "verifier-v1"


class VerificationAgent:
    """Independent verification agent that verifies investigation findings against DB evidence."""

    def __init__(self, session: AsyncSession, company_id: uuid.UUID) -> None:
        self.session = session
        self.company_id = company_id
        self.calc_verifier = IndependentCalculationVerifier()
        self.evidence_verifier = EvidenceCompletenessVerifier()
        self.policy_verifier = PolicyGateVerifier()
        self.exc_repo = ExceptionRepository(session, company_id)
        self.audit_service = AuditService(session, company_id)

    async def verify(self, request: VerificationRequest) -> VerificationResult:
        """Execute independent verification of an investigation finding."""
        start_time = time.perf_counter()
        started_at = utcnow()

        # 1. Load exception record
        exception = await self.exc_repo.get_by_id(request.exception_id)
        if not exception:
            raise ValueError(
                f"Exception {request.exception_id} not found for company {self.company_id}"
            )

        # 2. Initialize AgentRun
        run = AgentRun(
            company_id=self.company_id,
            close_run_id=request.close_run_id or exception.close_run_id,
            exception_id=request.exception_id,
            agent_name="verification_agent",
            status=AgentRunStatus.RUNNING,
            prompt_version_id=VERIFIER_PROMPT_VERSION_ID,
            model="deterministic_verifier",
            started_at=started_at,
        )
        self.session.add(run)
        await self.session.flush()

        await self.audit_service.record_event(
            event_type=AuditEventType.AGENT_RUN_STARTED,
            actor="verification_agent",
            entity_type="exception",
            entity_id=request.exception_id,
            payload={
                "run_id": str(run.id),
                "prompt_version_id": VERIFIER_PROMPT_VERSION_ID,
                "exception_type": str(request.dossier.exception_type),
            },
        )

        steps: list[AgentStep] = []
        step_number = 1

        # Step 1: Dossier and Claim Extraction
        s1_start = time.perf_counter()
        s1 = AgentStep(
            agent_run_id=run.id,
            step_number=step_number,
            step_type="dossier_inspection",
            tool_name="inspect_claims",
            input_json=json.dumps({"exception_id": str(request.exception_id)}, default=str),
            output_json=json.dumps(
                {
                    "claimed_cause": request.finding.root_cause_analysis.likely_cause,
                    "claimed_action": str(request.finding.recommendation.action),
                    "raw_confidence": str(request.finding.raw_confidence),
                    "facts_count": len(request.finding.facts),
                },
                default=str,
            ),
            status="COMPLETED",
            latency_ms=int((time.perf_counter() - s1_start) * 1000),
            citations_valid=request.finding.all_citations_valid,
        )
        steps.append(s1)
        step_number += 1

        # Step 2: Independent Calculation Reproduction
        s2_start = time.perf_counter()
        calc_valid, recalc_impact, var_diff, calc_errors = self.calc_verifier.verify_calculations(
            finding=request.finding,
            dossier=request.dossier,
            exception=exception,
        )
        s2 = AgentStep(
            agent_run_id=run.id,
            step_number=step_number,
            step_type="independent_calculation_reproduction",
            tool_name="recalculate_variance",
            input_json=json.dumps(
                {"financial_impact": str(exception.financial_impact)}, default=str
            ),
            output_json=json.dumps(
                {
                    "recalculated_impact": str(recalc_impact),
                    "variance_diff": str(var_diff),
                    "calculation_valid": calc_valid,
                    "errors": calc_errors,
                },
                default=str,
            ),
            status="COMPLETED" if calc_valid else "FAILED",
            latency_ms=int((time.perf_counter() - s2_start) * 1000),
            citations_valid=True,
            error_message=calc_errors[0] if calc_errors else None,
        )
        steps.append(s2)
        step_number += 1

        # Step 3: Evidence Completeness Validation
        s3_start = time.perf_counter()
        evidence_complete, missing_evidence = self.evidence_verifier.verify_evidence(
            dossier=request.dossier,
            finding=request.finding,
        )
        s3 = AgentStep(
            agent_run_id=run.id,
            step_number=step_number,
            step_type="evidence_completeness_validation",
            tool_name="verify_evidence_integrity",
            input_json=json.dumps(
                {"citations_count": len(request.finding.cited_record_ids)}, default=str
            ),
            output_json=json.dumps(
                {
                    "evidence_complete": evidence_complete,
                    "missing_evidence": missing_evidence,
                    "hallucinations_count": len(request.finding.hallucinated_citations),
                },
                default=str,
            ),
            status="COMPLETED" if evidence_complete else "FAILED",
            latency_ms=int((time.perf_counter() - s3_start) * 1000),
            citations_valid=evidence_complete,
            error_message=missing_evidence[0] if missing_evidence else None,
        )
        steps.append(s3)
        step_number += 1

        # Step 4: Policy Gate Evaluation
        s4_start = time.perf_counter()
        recommended_autonomy, policy_violations = self.policy_verifier.evaluate_policy(
            exception=exception,
            finding=request.finding,
            calibrated_confidence=request.finding.calibrated_confidence,
            policy=request.policy,
            calculation_valid=calc_valid,
            evidence_complete=evidence_complete,
        )
        s4 = AgentStep(
            agent_run_id=run.id,
            step_number=step_number,
            step_type="policy_gate_evaluation",
            tool_name="evaluate_close_policy",
            input_json=json.dumps(
                {
                    "max_auto_amount": str(request.policy.max_auto_resolution_amount),
                    "min_confidence": str(request.policy.min_confidence),
                },
                default=str,
            ),
            output_json=json.dumps(
                {
                    "recommended_autonomy": str(recommended_autonomy),
                    "policy_violations": policy_violations,
                },
                default=str,
            ),
            status="COMPLETED",
            latency_ms=int((time.perf_counter() - s4_start) * 1000),
            citations_valid=True,
        )
        steps.append(s4)
        step_number += 1

        # Step 5: Confidence Calibration Verification
        s5_start = time.perf_counter()
        calibrated_conf = request.finding.calibrated_confidence
        # Double-check calibration: if calculation errors or missing evidence, penalize
        if not calc_valid or not evidence_complete:
            calibrated_conf = min(calibrated_conf, Decimal("0.4000"))

        s5 = AgentStep(
            agent_run_id=run.id,
            step_number=step_number,
            step_type="confidence_calibration_verification",
            tool_name="verify_calibrated_confidence",
            input_json=json.dumps(
                {"raw_confidence": str(request.finding.raw_confidence)}, default=str
            ),
            output_json=json.dumps(
                {
                    "calibrated_confidence": str(calibrated_conf),
                    "min_confidence_met": calibrated_conf >= request.policy.min_confidence,
                },
                default=str,
            ),
            status="COMPLETED",
            latency_ms=int((time.perf_counter() - s5_start) * 1000),
            citations_valid=True,
        )
        steps.append(s5)

        # 3. Formulate VerificationResult
        is_verified = calc_valid and evidence_complete and len(policy_violations) == 0
        total_latency_ms = int((time.perf_counter() - start_time) * 1000)

        result = VerificationResult(
            exception_id=request.exception_id,
            verified=is_verified,
            confidence=request.finding.raw_confidence,
            calibrated_confidence=calibrated_conf,
            missing_evidence=missing_evidence,
            calculation_errors=calc_errors,
            policy_violations=policy_violations,
            recommended_autonomy=recommended_autonomy,
            reproduction_valid=calc_valid,
            evidence_complete=evidence_complete,
            calculation_valid=calc_valid,
            recalculated_impact=recalc_impact,
            variance_diff=var_diff,
            notes=(
                f"Verified: {is_verified}. Autonomy: {recommended_autonomy}. "
                f"Calculations: {'PASS' if calc_valid else 'FAIL'}. "
                f"Evidence: {'PASS' if evidence_complete else 'FAIL'}."
            ),
        )

        # 4. Save steps and finalize AgentRun
        self.session.add_all(steps)
        run.status = AgentRunStatus.COMPLETED
        run.completed_at = utcnow()
        run.latency_ms = total_latency_ms
        run.finding_json = result.model_dump_json()
        await self.session.flush()

        # 5. Audit Event
        await self.audit_service.record_event(
            event_type=AuditEventType.AGENT_RUN_COMPLETED,
            actor="verification_agent",
            entity_type="exception",
            entity_id=request.exception_id,
            payload={
                "run_id": str(run.id),
                "verified": is_verified,
                "recommended_autonomy": str(recommended_autonomy),
                "calibrated_confidence": str(calibrated_conf),
                "latency_ms": total_latency_ms,
            },
        )

        close_run_id = request.close_run_id or exception.close_run_id
        if close_run_id:
            try:
                from app.streaming.bus import agent_event_bus

                await agent_event_bus.publish(
                    close_run_id,
                    {
                        "event": "verification_completed",
                        "close_run_id": str(close_run_id),
                        "exception_id": str(request.exception_id),
                        "agent_run_id": str(run.id),
                        "verified": is_verified,
                        "recommended_autonomy": str(recommended_autonomy),
                        "calibrated_confidence": str(calibrated_conf),
                        "latency_ms": total_latency_ms,
                    },
                )
            except Exception:
                pass

        return result
