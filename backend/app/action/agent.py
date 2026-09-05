"""Action Agent (Agent 6, spec section 10, 11)."""

from __future__ import annotations

import json
import time
import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.action.tools import ActionTools
from app.action.types import ActionResult, ActionType
from app.audit.service import AuditService
from app.db.models.agent import AgentRun, AgentStep
from app.db.repository import ExceptionRepository
from app.db.base import utcnow
from app.domain.enums import AgentRunStatus, AuditEventType, AutonomyLevel, Role
from app.investigation.types import AutonomyAction, InvestigationFinding
from app.verification.types import VerificationResult

ACTION_AGENT_PROMPT_VERSION_ID = "action-v1"


class ActionAgent:
    """Autonomous Action Agent executing policy-controlled, auditable finance actions."""

    def __init__(self, session: AsyncSession, company_id: uuid.UUID) -> None:
        self.session = session
        self.company_id = company_id
        self.tools = ActionTools(session, company_id)
        self.exc_repo = ExceptionRepository(session, company_id)
        self.audit_service = AuditService(session, company_id)

    async def execute_for_verification(
        self,
        exception_id: uuid.UUID,
        finding: InvestigationFinding,
        verification: VerificationResult,
    ) -> list[ActionResult]:
        """Execute safe actions based on independent verification output."""
        start_time = time.perf_counter()
        started_at = utcnow()

        exception = await self.exc_repo.get_by_id(exception_id)
        if not exception:
            raise ValueError(f"Exception {exception_id} not found for company {self.company_id}")

        # 1. Initialize AgentRun
        run = AgentRun(
            company_id=self.company_id,
            close_run_id=exception.close_run_id,
            exception_id=exception_id,
            agent_name="action_agent",
            status=AgentRunStatus.RUNNING,
            prompt_version_id=ACTION_AGENT_PROMPT_VERSION_ID,
            model="deterministic_action_router",
            started_at=started_at,
        )
        self.session.add(run)
        await self.session.flush()

        steps: list[AgentStep] = []
        step_number = 1
        actions_taken: list[ActionResult] = []

        # Step 1: Evaluate Autonomy Level Gate
        s1_start = time.perf_counter()
        autonomy = verification.recommended_autonomy
        s1 = AgentStep(
            agent_run_id=run.id,
            step_number=step_number,
            step_type="autonomy_level_evaluation",
            tool_name="evaluate_autonomy_gate",
            input_json=json.dumps(
                {
                    "verified": verification.verified,
                    "recommended_autonomy": str(autonomy),
                    "calibrated_confidence": str(verification.calibrated_confidence),
                },
                default=str,
            ),
            output_json=json.dumps(
                {
                    "permitted_level": str(autonomy),
                    "autonomous_execution_allowed": autonomy == AutonomyLevel.EXECUTE,
                },
                default=str,
            ),
            status="COMPLETED",
            latency_ms=int((time.perf_counter() - s1_start) * 1000),
            citations_valid=True,
        )
        steps.append(s1)
        step_number += 1

        # Step 2: Action Execution
        s2_start = time.perf_counter()

        # Branch 1: Level 3 EXECUTE (Clean / safe / auto-resolvable)
        if autonomy == AutonomyLevel.EXECUTE and verification.verified:
            act = await self.tools.mark_exception_resolved(
                exception_id=exception_id,
                resolution_note=finding.recommendation.recommended_action or "Auto-resolved: verified clean match within tolerances.",
                actor="action_agent",
                auto_resolved=True,
            )
            actions_taken.append(act)

        # Branch 2: Level 2 STAGE (Discrepancy staging: draft email, stage JE, review task)
        elif autonomy == AutonomyLevel.STAGE:
            cause_lower = finding.root_cause_analysis.likely_cause.lower()

            if "exceeds" in cause_lower or "mismatch" in cause_lower or "price" in cause_lower:
                draft_act = await self.tools.draft_vendor_email(
                    exception_id=exception_id,
                    vendor_name="Vendor Operations",
                    subject=f"Discrepancy Notice: Exception {exception_id}",
                    body=finding.executive_summary,
                )
                actions_taken.append(draft_act)

            elif "receipt" in cause_lower or "accrual" in cause_lower:
                je_act = await self.tools.stage_journal_entry(
                    exception_id=exception_id,
                    memo=f"Accrual adjustment for {finding.root_cause_analysis.likely_cause}",
                    lines=[
                        {"account": "Operating Expense", "debit": str(exception.financial_impact)},
                        {"account": "Accrued Liabilities", "credit": str(exception.financial_impact)},
                    ],
                    currency=exception.currency,
                )
                actions_taken.append(je_act)

            task_act = await self.tools.create_review_task(
                exception_id=exception_id,
                title=f"Review exception {exception.type}",
                description=finding.root_cause_analysis.summary,
                assigned_to=Role.CONTROLLER,
            )
            actions_taken.append(task_act)

        # Branch 3: Level 0 / Level 1 ESCALATE (CFO Escalation or Unverified)
        else:
            esc_reason = finding.root_cause_analysis.likely_cause
            if not verification.verified:
                esc_reason = f"Verification failed: {', '.join(verification.calculation_errors + verification.missing_evidence + verification.policy_violations)}"

            esc_act = await self.tools.mark_exception_escalated(
                exception_id=exception_id,
                escalation_reason=esc_reason,
                target_role=Role.CFO,
            )
            actions_taken.append(esc_act)

            task_act = await self.tools.create_review_task(
                exception_id=exception_id,
                title=f"CFO ESCALATION: {exception.type}",
                description=esc_reason,
                assigned_to=Role.CFO,
            )
            actions_taken.append(task_act)

        s2 = AgentStep(
            agent_run_id=run.id,
            step_number=step_number,
            step_type="action_dispatch",
            tool_name="execute_permitted_actions",
            input_json=json.dumps({"actions_count": len(actions_taken)}, default=str),
            output_json=json.dumps([a.model_dump() for a in actions_taken], default=str),
            status="COMPLETED",
            latency_ms=int((time.perf_counter() - s2_start) * 1000),
            citations_valid=True,
        )
        steps.append(s2)

        # 3. Finalize run and steps
        self.session.add_all(steps)
        total_latency_ms = int((time.perf_counter() - start_time) * 1000)
        run.status = AgentRunStatus.COMPLETED
        run.completed_at = utcnow()
        run.latency_ms = total_latency_ms
        run.finding_json = json.dumps([a.model_dump() for a in actions_taken], default=str)
        await self.session.flush()

        await self.audit_service.record_event(
            event_type=AuditEventType.AGENT_RUN_COMPLETED,
            actor="action_agent",
            entity_type="exception",
            entity_id=exception_id,
            payload={
                "run_id": str(run.id),
                "actions_executed": [a.action_type for a in actions_taken],
                "latency_ms": total_latency_ms,
            },
        )

        return actions_taken
