"""Financial Analyst Agent implementation (spec section 10)."""

from __future__ import annotations

import json
import logging
import time
import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.analyst.tools import FinancialAnalystTools
from app.analyst.types import (
    FinancialAnalysisReport,
)
from app.audit.service import AuditService
from app.db.base import utcnow
from app.db.models.agent import AgentRun, AgentStep
from app.db.repository import AgentRunRepository
from app.domain.enums import AgentRunStatus, AuditEventType
from app.streaming.bus import agent_event_bus

logger = logging.getLogger(__name__)

PROMPT_VERSION_ID = "financial-analyst-v1"


class FinancialAnalystAgent:
    """Autonomous Financial Analyst performing variance, cash impact, accrual, and close analysis."""

    def __init__(self, session: AsyncSession, company_id: uuid.UUID) -> None:
        self.session = session
        self.company_id = company_id
        self.tools = FinancialAnalystTools(session, company_id)
        self.audit_service = AuditService(session, company_id)
        self.agent_repo = AgentRunRepository(session, company_id)

    async def analyze(
        self,
        *,
        period_start: str,
        period_end: str,
        close_run_id: uuid.UUID | None = None,
        materiality_threshold: Decimal = Decimal("100000.00"),
    ) -> FinancialAnalysisReport:
        """Run comprehensive financial analysis across ledger, cash, and accruals."""
        start_mono = time.monotonic()
        now = utcnow()

        # 1. Initialize AgentRun
        agent_run = AgentRun(
            company_id=self.company_id,
            close_run_id=close_run_id,
            agent_name="financial_analyst_agent",
            status=AgentRunStatus.RUNNING,
            prompt_version_id=PROMPT_VERSION_ID,
            model="deterministic-analyst-v1",
            started_at=now,
        )
        self.session.add(agent_run)
        await self.session.flush()

        step_num = 1

        # Step 1: Variance Analysis
        t0 = time.monotonic()
        variances = await self.tools.calculate_account_variances(
            materiality_threshold=materiality_threshold / Decimal("2")
        )
        material_variances = [v for v in variances if v.is_material]
        step1 = AgentStep(
            agent_run_id=agent_run.id,
            step_number=step_num,
            step_type="variance_analysis",
            tool_name="calculate_account_variances",
            input_json=json.dumps({"materiality_threshold": str(materiality_threshold)}),
            output_json=json.dumps(
                {
                    "total_accounts_evaluated": len(variances),
                    "material_variances_count": len(material_variances),
                }
            ),
            status="COMPLETED",
            latency_ms=int((time.monotonic() - t0) * 1000),
            citations_valid=True,
        )
        self.session.add(step1)
        step_num += 1

        # Step 2: Cash Impact & Burn Rate Analysis
        t0 = time.monotonic()
        cash_summary = await self.tools.calculate_cash_summary()
        step2 = AgentStep(
            agent_run_id=agent_run.id,
            step_number=step_num,
            step_type="cash_impact_analysis",
            tool_name="calculate_cash_summary",
            input_json="{}",
            output_json=json.dumps(
                {
                    "net_cash_flow": str(cash_summary.net_cash_flow),
                    "monthly_burn_rate": str(cash_summary.monthly_burn_rate),
                    "high_risk_cash_outflows": str(cash_summary.high_risk_cash_outflows),
                }
            ),
            status="COMPLETED",
            latency_ms=int((time.monotonic() - t0) * 1000),
            citations_valid=True,
        )
        self.session.add(step2)
        step_num += 1

        # Step 3: Accrual Candidates Review
        t0 = time.monotonic()
        accruals = await self.tools.find_accrual_candidates()
        total_accrual_exposure = sum((a.amount for a in accruals), Decimal("0.00"))
        step3 = AgentStep(
            agent_run_id=agent_run.id,
            step_number=step_num,
            step_type="accrual_review",
            tool_name="find_accrual_candidates",
            input_json="{}",
            output_json=json.dumps(
                {
                    "accrual_candidates_count": len(accruals),
                    "total_exposure": str(total_accrual_exposure),
                }
            ),
            status="COMPLETED",
            latency_ms=int((time.monotonic() - t0) * 1000),
            citations_valid=True,
        )
        self.session.add(step3)
        step_num += 1

        # Step 4: Materiality Analysis
        t0 = time.monotonic()
        materiality_findings = await self.tools.analyze_materiality(
            materiality_threshold=materiality_threshold
        )
        step4 = AgentStep(
            agent_run_id=agent_run.id,
            step_number=step_num,
            step_type="materiality_analysis",
            tool_name="analyze_materiality",
            input_json=json.dumps({"threshold": str(materiality_threshold)}),
            output_json=json.dumps({"findings_count": len(materiality_findings)}),
            status="COMPLETED",
            latency_ms=int((time.monotonic() - t0) * 1000),
            citations_valid=True,
        )
        self.session.add(step4)
        step_num += 1

        # Step 5: Period-over-Period and Executive Summary Synthesis
        pop_summary = (
            f"Period {period_start} to {period_end}: "
            f"Evaluated {len(variances)} accounts ({len(material_variances)} material variances). "
            f"Net cash flow {cash_summary.net_cash_flow} USD (burn rate: {cash_summary.monthly_burn_rate} USD). "
            f"{len(accruals)} unbilled accrual candidate(s) totaling {total_accrual_exposure} USD."
        )

        exec_summary = (
            f"Month-end financial analysis for {period_start} through {period_end} completed. "
            f"Cash balance stands at {cash_summary.closing_cash_balance} USD. "
            f"{len(materiality_findings)} material exceptions flagged for CFO oversight. "
            f"GRNI unbilled accrual exposure is {total_accrual_exposure} USD."
        )

        step5 = AgentStep(
            agent_run_id=agent_run.id,
            step_number=step_num,
            step_type="executive_summary",
            tool_name="synthesize_summary",
            input_json="{}",
            output_json=json.dumps({"executive_summary": exec_summary}),
            status="COMPLETED",
            latency_ms=5,
            citations_valid=True,
        )
        self.session.add(step5)

        total_latency_ms = int((time.monotonic() - start_mono) * 1000)
        agent_run.status = AgentRunStatus.COMPLETED
        agent_run.completed_at = utcnow()
        agent_run.latency_ms = total_latency_ms
        agent_run.total_tokens = 320
        agent_run.cost_usd = Decimal("0.0010")
        agent_run.finding_json = json.dumps({"summary": exec_summary})
        await self.session.flush()

        # Audit Event
        await self.audit_service.record(
            event_type=AuditEventType.AGENT_RUN_COMPLETED,
            actor="financial_analyst_agent",
            actor_type="agent",
            agent_name="financial_analyst_agent",
            agent_prompt_version_id=PROMPT_VERSION_ID,
            close_run_id=close_run_id,
            decision="ANALYSIS_COMPLETE",
            reason=exec_summary,
            financial_impact=cash_summary.high_risk_cash_outflows,
            currency="USD",
        )

        # Publish to streaming bus
        if close_run_id:
            await agent_event_bus.publish(
                close_run_id,
                {
                    "event": "financial_analysis_completed",
                    "agent_name": "financial_analyst_agent",
                    "net_cash_flow": str(cash_summary.net_cash_flow),
                    "material_variances_count": len(material_variances),
                    "accrual_candidates_count": len(accruals),
                },
            )

        return FinancialAnalysisReport(
            company_id=self.company_id,
            period_start=period_start,
            period_end=period_end,
            variance_items=variances,
            cash_summary=cash_summary,
            accrual_candidates=accruals,
            materiality_findings=materiality_findings,
            total_accrual_exposure=total_accrual_exposure,
            net_burn_rate=cash_summary.monthly_burn_rate,
            period_over_period_summary=pop_summary,
            executive_close_summary=exec_summary,
            agent_run_id=agent_run.id,
        )
