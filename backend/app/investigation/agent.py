"""CFO Investigation Agent orchestrating bounded dossier investigation.

Coordinates:
1. Dossier inspection & bounded scope enforcement
2. Reasoning provider invocation (Deterministic, LLM, or Fallback)
3. Citation validation against bounded EvidenceDossier
4. Confidence calibration against ground-truth benchmarks
5. Controlled autonomy & policy enforcement
6. PostgreSQL AgentRun and AgentStep recording
7. Versioned AuditEvent trail emission
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import AuditService
from app.db.models.agent import AgentRun, AgentStep
from app.db.repository import AgentRunRepository, ExceptionRepository
from app.domain.enums import AgentRunStatus, AuditEventType, ExceptionStatus
from app.investigation.calibration import ConfidenceCalibrator
from app.investigation.citation_validator import CitationValidator
from app.investigation.llm_provider import (
    LLMProvider,
    get_default_llm_provider,
)
from app.investigation.types import (
    AutonomyAction,
    FindingStatus,
    InvestigationFinding,
    InvestigationRequest,
)

logger = logging.getLogger(__name__)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class InvestigationCircuitBreakerTripped(RuntimeError):
    """Raised when investigation agent circuit breaker trips (step limit or timeout)."""

    def __init__(self, message: str, reason: str, steps: int, elapsed_seconds: float) -> None:
        super().__init__(message)
        self.reason = reason
        self.steps = steps
        self.elapsed_seconds = elapsed_seconds


class CFOInvestigationAgent:
    """CFO-office autonomous investigation agent for financial exceptions."""

    def __init__(
        self,
        session: AsyncSession,
        company_id: uuid.UUID,
        provider: LLMProvider | None = None,
        calibrator: ConfidenceCalibrator | None = None,
        validator: CitationValidator | None = None,
        audit_service: AuditService | None = None,
    ) -> None:
        self.session = session
        self.company_id = company_id
        self.provider = provider or get_default_llm_provider()
        self.calibrator = calibrator or ConfidenceCalibrator()
        self.validator = validator or CitationValidator()
        self.audit_service = audit_service or AuditService(session, company_id)
        self.agent_repo = AgentRunRepository(session, company_id)
        self.exc_repo = ExceptionRepository(session, company_id)

    async def investigate(self, request: InvestigationRequest) -> InvestigationFinding:
        """Execute a full investigated analysis of a financial exception."""
        started_at = utcnow()
        start_mono = time.monotonic()
        dossier = request.dossier

        # 1. Create AgentRun record in database
        agent_run = AgentRun(
            company_id=self.company_id,
            close_run_id=request.close_run_id,
            exception_id=request.exception_id,
            agent_name="cfo_investigation_agent",
            status=AgentRunStatus.RUNNING,
            prompt_version_id=request.prompt_version_id,
            model=request.model,
            started_at=started_at,
        )
        self.session.add(agent_run)
        await self.session.flush()

        # 2. Emit AGENT_RUN_STARTED audit event
        try:
            await self.audit_service.record(
                event_type=AuditEventType.AGENT_RUN_STARTED,
                actor="cfo_investigation_agent",
                actor_type="agent",
                agent_name="cfo_investigation_agent",
                agent_prompt_version_id=request.prompt_version_id,
                close_run_id=request.close_run_id,
                exception_id=request.exception_id,
                decision="INVESTIGATING",
                reason=f"Started autonomous investigation of exception {request.exception_id}",
                financial_impact=dossier.financial_impact,
                metadata_={
                    "agent_run_id": str(agent_run.id),
                    "exception_type": dossier.exception_type.value,
                    "valid_records_count": len(dossier.valid_record_ids),
                },
            )
        except Exception as audit_err:
            logger.warning("Failed to record AGENT_RUN_STARTED audit event: %s", audit_err)

        if request.close_run_id:
            try:
                from app.streaming.bus import agent_event_bus

                await agent_event_bus.publish(
                    request.close_run_id,
                    {
                        "event": "investigation_started",
                        "close_run_id": str(request.close_run_id),
                        "exception_id": str(request.exception_id),
                        "agent_run_id": str(agent_run.id),
                        "exception_type": dossier.exception_type.value,
                        "financial_impact": str(dossier.financial_impact),
                    },
                )
            except Exception as bus_err:
                logger.warning("Failed to publish investigation_started to SSE bus: %s", bus_err)

        max_steps = getattr(request, "max_agent_steps", 15) or 15
        max_seconds = (
            getattr(request, "max_investigation_seconds", 30.0)
            or getattr(request, "timeout_seconds", 30.0)
            or 30.0
        )

        step_num = 1

        def check_step_limit() -> None:
            if step_num > max_steps:
                raise InvestigationCircuitBreakerTripped(
                    f"Circuit breaker tripped: Investigation exceeded maximum step limit of {max_steps} steps.",
                    reason="STEP_LIMIT",
                    steps=step_num - 1,
                    elapsed_seconds=time.monotonic() - start_mono,
                )

        try:
            async with asyncio.timeout(max_seconds):
                # Step 1: Dossier Inspection & Bounded Scope
                check_step_limit()
                step_start = time.monotonic()
                dossier_summary = {
                    "valid_record_ids_count": len(dossier.valid_record_ids),
                    "valid_evidence_ids_count": len(dossier.valid_evidence_ids),
                    "ranked_nodes_count": len(dossier.ranked_nodes),
                    "edges_count": len(dossier.graph_edges),
                }
                step_1 = AgentStep(
                    agent_run_id=agent_run.id,
                    step_number=step_num,
                    step_type="dossier_inspection",
                    tool_name="EvidenceDossierBuilder",
                    input_json=json.dumps({"exception_id": str(request.exception_id)}),
                    output_json=json.dumps(dossier_summary),
                    status="COMPLETED",
                    latency_ms=int((time.monotonic() - step_start) * 1000),
                    citations_valid=True,
                )
                self.session.add(step_1)
                step_num += 1

                # Step 2: Reasoning Generation
                check_step_limit()
                step_start = time.monotonic()
                raw_finding = await self.provider.generate_finding(request)
                raw_finding.agent_run_id = agent_run.id
                step_2 = AgentStep(
                    agent_run_id=agent_run.id,
                    step_number=step_num,
                    step_type="reasoning_generation",
                    tool_name="LLMProvider",
                    input_json=json.dumps({"prompt_version_id": request.prompt_version_id}),
                    output_json=json.dumps(
                        {
                            "finding_status": raw_finding.finding_status.value,
                            "facts_count": len(raw_finding.facts),
                            "inferences_count": len(raw_finding.inferences),
                            "raw_confidence": str(raw_finding.raw_confidence),
                        }
                    ),
                    status="COMPLETED",
                    latency_ms=int((time.monotonic() - step_start) * 1000),
                )
                self.session.add(step_2)
                step_num += 1

                # Step 3: Citation Validation
                check_step_limit()
                step_start = time.monotonic()
                val_result = self.validator.validate_finding(raw_finding, dossier)
                raw_finding.all_citations_valid = val_result.is_valid
                raw_finding.hallucinated_citations = val_result.hallucinated_citations
                raw_finding.has_unsupported_claims = len(val_result.unsupported_claims) > 0

                step_3 = AgentStep(
                    agent_run_id=agent_run.id,
                    step_number=step_num,
                    step_type="citation_validation",
                    tool_name="CitationValidator",
                    input_json=json.dumps({"total_citations": val_result.total_citations}),
                    output_json=json.dumps(
                        {
                            "is_valid": val_result.is_valid,
                            "valid_citations": val_result.valid_citations,
                            "hallucinations": val_result.hallucinated_citations,
                            "unsupported": val_result.unsupported_claims,
                        }
                    ),
                    status="COMPLETED" if val_result.is_valid else "CITATION_FLAGGED",
                    latency_ms=int((time.monotonic() - step_start) * 1000),
                    citations_valid=val_result.is_valid,
                )
                self.session.add(step_3)
                step_num += 1

                # Step 4: Confidence Calibration
                check_step_limit()
                step_start = time.monotonic()
                calibrated = self.calibrator.calibrate(raw_finding, dossier)
                raw_finding.calibrated_confidence = calibrated

                step_4 = AgentStep(
                    agent_run_id=agent_run.id,
                    step_number=step_num,
                    step_type="confidence_calibration",
                    tool_name="ConfidenceCalibrator",
                    input_json=json.dumps({"raw_confidence": str(raw_finding.raw_confidence)}),
                    output_json=json.dumps({"calibrated_confidence": str(calibrated)}),
                    status="COMPLETED",
                    latency_ms=int((time.monotonic() - step_start) * 1000),
                )
                self.session.add(step_4)
                step_num += 1

                # Step 5: Policy Governance Check
                check_step_limit()
                step_start = time.monotonic()
                final_finding = self._apply_policy_overrides(raw_finding, request)
                step_5 = AgentStep(
                    agent_run_id=agent_run.id,
                    step_number=step_num,
                    step_type="governance_policy_check",
                    tool_name="PolicyEngine",
                    input_json=json.dumps(
                        {
                            "min_confidence": str(
                                getattr(request.policy, "min_confidence", Decimal("0.95"))
                                if request.policy
                                else Decimal("0.95")
                            ),
                            "max_auto_resolution_amount": str(
                                getattr(
                                    request.policy,
                                    "max_auto_resolution_amount",
                                    Decimal("50000.00"),
                                )
                                if request.policy
                                else Decimal("50000.00")
                            ),
                        }
                    ),
                    output_json=json.dumps(
                        {
                            "action": final_finding.recommendation.action.value,
                            "finding_status": final_finding.finding_status.value,
                        }
                    ),
                    status="COMPLETED",
                    latency_ms=int((time.monotonic() - step_start) * 1000),
                )
                self.session.add(step_5)

                # Complete AgentRun
                completed_at = utcnow()
                total_latency_ms = int((time.monotonic() - start_mono) * 1000)
                agent_run.status = AgentRunStatus.COMPLETED
                agent_run.completed_at = completed_at
                agent_run.latency_ms = total_latency_ms
                agent_run.total_tokens = 480 + (len(dossier.ranked_nodes) * 45)
                agent_run.cost_usd = Decimal("0.0015")
                agent_run.finding_json = json.dumps(final_finding.to_dict())

                # Update Exception record in DB
                exception = await self.exc_repo.get(request.exception_id)
                if exception:
                    exception.root_cause = final_finding.root_cause_analysis.likely_cause
                    exception.recommended_action = final_finding.recommendation.recommended_action
                    if final_finding.recommendation.action == AutonomyAction.AUTO_RESOLVE:
                        exception.status = ExceptionStatus.RESOLVED
                    elif final_finding.recommendation.action == AutonomyAction.ESCALATE:
                        exception.status = ExceptionStatus.ESCALATED
                    else:
                        exception.status = ExceptionStatus.INVESTIGATING

                await self.session.flush()

                # Emit AGENT_RUN_COMPLETED audit event
                try:
                    await self.audit_service.record(
                        event_type=AuditEventType.AGENT_RUN_COMPLETED,
                        actor="cfo_investigation_agent",
                        actor_type="agent",
                        agent_name="cfo_investigation_agent",
                        agent_prompt_version_id=request.prompt_version_id,
                        close_run_id=request.close_run_id,
                        exception_id=request.exception_id,
                        decision=final_finding.recommendation.action.value,
                        reason=final_finding.root_cause_analysis.likely_cause,
                        financial_impact=dossier.financial_impact,
                        confidence=final_finding.raw_confidence,
                        calibrated_confidence=final_finding.calibrated_confidence,
                        evidence_ids=list(dossier.valid_record_ids)[:15],
                        metadata_={
                            "agent_run_id": str(agent_run.id),
                            "citations_valid": final_finding.all_citations_valid,
                            "status": final_finding.finding_status.value,
                        },
                    )
                except Exception as audit_err:
                    logger.warning(
                        "Failed to record AGENT_RUN_COMPLETED audit event: %s", audit_err
                    )

                if request.close_run_id:
                    try:
                        from app.streaming.bus import agent_event_bus

                        await agent_event_bus.publish(
                            request.close_run_id,
                            {
                                "event": "investigation_completed",
                                "close_run_id": str(request.close_run_id),
                                "exception_id": str(request.exception_id),
                                "agent_run_id": str(agent_run.id),
                                "finding_status": final_finding.finding_status.value,
                                "action": final_finding.recommendation.action.value,
                                "likely_cause": final_finding.root_cause_analysis.likely_cause,
                                "financial_impact": str(dossier.financial_impact),
                                "calibrated_confidence": str(final_finding.calibrated_confidence),
                            },
                        )
                    except Exception as bus_err:
                        logger.warning(
                            "Failed to publish investigation_completed to SSE bus: %s", bus_err
                        )

                return final_finding

        except Exception as exc:
            logger.exception("Investigation failed for exception %s: %s", request.exception_id, exc)
            completed_at = utcnow()
            elapsed_sec = time.monotonic() - start_mono
            elapsed_ms = int(elapsed_sec * 1000)

            is_timeout = isinstance(exc, (TimeoutError, asyncio.TimeoutError)) or (
                isinstance(exc, InvestigationCircuitBreakerTripped) and exc.reason == "TIMEOUT"
            )
            term_reason = getattr(exc, "reason", "TIMEOUT" if is_timeout else "EXECUTION_ERROR")
            steps_completed = getattr(exc, "steps", step_num - 1)

            agent_run.status = AgentRunStatus.TIMED_OUT if is_timeout else AgentRunStatus.FAILED
            agent_run.completed_at = completed_at
            agent_run.error_message = str(exc)
            agent_run.latency_ms = elapsed_ms
            await self.session.flush()

            # Record structured audit log with step count, elapsed time, termination reason
            try:
                await self.audit_service.record(
                    event_type=AuditEventType.AGENT_RUN_COMPLETED,
                    actor="cfo_investigation_agent",
                    actor_type="agent",
                    agent_name="cfo_investigation_agent",
                    agent_prompt_version_id=request.prompt_version_id,
                    close_run_id=request.close_run_id,
                    exception_id=request.exception_id,
                    decision="TIMED_OUT" if is_timeout else "FAILED",
                    reason=str(exc),
                    financial_impact=dossier.financial_impact,
                    metadata_={
                        "agent_run_id": str(agent_run.id),
                        "status": agent_run.status.value,
                        "step_count": steps_completed,
                        "elapsed_seconds": round(elapsed_sec, 3),
                        "termination_reason": term_reason,
                        "error": str(exc),
                    },
                )
            except Exception as audit_err:
                logger.warning("Failed to record failure audit: %s", audit_err)

            if request.close_run_id:
                try:
                    from app.streaming.bus import agent_event_bus

                    await agent_event_bus.publish(
                        request.close_run_id,
                        {
                            "event": "investigation_failed",
                            "close_run_id": str(request.close_run_id),
                            "exception_id": str(request.exception_id),
                            "agent_run_id": str(agent_run.id),
                            "error": str(exc),
                            "termination_reason": term_reason,
                            "step_count": steps_completed,
                            "elapsed_seconds": round(elapsed_sec, 3),
                        },
                    )
                except Exception as bus_err:
                    logger.warning("Failed to publish investigation_failed to SSE bus: %s", bus_err)

            if is_timeout and not isinstance(exc, InvestigationCircuitBreakerTripped):
                raise InvestigationCircuitBreakerTripped(
                    f"Circuit breaker tripped: Investigation exceeded wall-clock timeout of {max_seconds}s.",
                    reason="TIMEOUT",
                    steps=steps_completed,
                    elapsed_seconds=elapsed_sec,
                ) from exc

            raise

    def _apply_policy_overrides(
        self,
        finding: InvestigationFinding,
        request: InvestigationRequest,
    ) -> InvestigationFinding:
        """Apply deterministic policy constraints (spec sections 11, 12)."""
        policy = request.policy
        impact = request.dossier.financial_impact
        rec = finding.recommendation

        # If citations were invalid, demote to HUMAN_REVIEW_REQUIRED and REFUSE/ESCALATE
        if not finding.all_citations_valid or finding.hallucinated_citations:
            return finding.model_copy(
                update={
                    "finding_status": FindingStatus.HUMAN_REVIEW_REQUIRED,
                    "recommendation": rec.model_copy(
                        update={
                            "action": AutonomyAction.REFUSE,
                            "recommended_action": (
                                "Refuse autonomous action due to invalid or ungrounded citation."
                            ),
                            "should_block_close": True,
                        }
                    ),
                }
            )

        high_impact_human = getattr(policy, "high_impact_requires_human", True) if policy else True
        max_auto = (
            getattr(policy, "max_auto_resolution_amount", Decimal("50000.00"))
            if policy
            else Decimal("50000.00")
        )
        min_confidence = (
            getattr(policy, "min_confidence", Decimal("0.95")) if policy else Decimal("0.95")
        )

        # High impact requires human review
        if high_impact_human and impact > max_auto:
            if rec.action == AutonomyAction.AUTO_RESOLVE:
                finding = finding.model_copy(
                    update={
                        "finding_status": FindingStatus.HUMAN_REVIEW_REQUIRED,
                        "recommendation": rec.model_copy(
                            update={
                                "action": AutonomyAction.STAGE,
                                "recommended_action": (
                                    f"Stage for human review: amount ({impact}) exceeds "
                                    f"auto-resolution limit ({max_auto})."
                                ),
                                "should_block_close": True,
                            }
                        ),
                    }
                )

        # Calibrated confidence below threshold requires human review
        if finding.calibrated_confidence < min_confidence:
            if rec.action == AutonomyAction.AUTO_RESOLVE:
                finding = finding.model_copy(
                    update={
                        "finding_status": FindingStatus.HUMAN_REVIEW_REQUIRED,
                        "recommendation": rec.model_copy(
                            update={
                                "action": AutonomyAction.STAGE,
                                "recommended_action": (
                                    f"Stage for human review: calibrated confidence "
                                    f"({finding.calibrated_confidence}) is below threshold "
                                    f"({min_confidence})."
                                ),
                                "should_block_close": True,
                            }
                        ),
                    }
                )

        return finding
