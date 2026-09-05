"""Trace recorder capturing live runs into replayable fixtures (spec section 37)."""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.agent import AgentRun, AgentStep
from app.db.models.close_run import CloseRun, CloseTask
from app.db.models.demo import DemoTrace

logger = logging.getLogger(__name__)


class TraceRecorder:
    """Records live close runs into structured demo traces."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def record_from_close_run(
        self,
        close_run_id: uuid.UUID,
        scenario_key: str,
        title: str,
        description: str | None = None,
        is_golden: bool = False,
    ) -> DemoTrace:
        """Capture all execution steps, tasks, and audit events from a close run."""
        close_run = await self.session.get(CloseRun, close_run_id)
        if close_run is None:
            raise ValueError(f"Close run {close_run_id} not found")

        events: list[dict[str, Any]] = []

        # 1. Close run start event
        events.append(
            {
                "offset_ms": 0,
                "event": "close_run_started",
                "close_run_id": str(close_run_id),
                "status": close_run.status.value,
            }
        )

        # 2. Tasks
        task_stmt = (
            select(CloseTask)
            .where(CloseTask.close_run_id == close_run_id)
            .order_by(CloseTask.created_at.asc())
        )
        tasks = (await self.session.scalars(task_stmt)).all()
        for idx, t in enumerate(tasks):
            events.append(
                {
                    "offset_ms": 100 * (idx + 1),
                    "event": "task_update",
                    "task_id": str(t.id),
                    "task_type": t.task_type.value,
                    "status": t.status.value,
                    "summary": t.result_summary,
                }
            )

        # 3. Agent runs and steps
        agent_stmt = (
            select(AgentRun)
            .where(AgentRun.close_run_id == close_run_id)
            .order_by(AgentRun.created_at.asc())
        )
        runs = (await self.session.scalars(agent_stmt)).all()
        step_offset = len(events) * 100
        for r in runs:
            events.append(
                {
                    "offset_ms": step_offset,
                    "event": "agent_run_started",
                    "agent_run_id": str(r.id),
                    "agent_name": r.agent_name,
                }
            )
            step_offset += 50

            step_stmt = (
                select(AgentStep)
                .where(AgentStep.agent_run_id == r.id)
                .order_by(AgentStep.step_number.asc())
            )
            steps = (await self.session.scalars(step_stmt)).all()
            for s in steps:
                output = None
                if s.output_json:
                    try:
                        output = json.loads(s.output_json)
                    except Exception:
                        output = s.output_json
                events.append(
                    {
                        "offset_ms": step_offset,
                        "event": "agent_step",
                        "step_id": str(s.id),
                        "agent_run_id": str(r.id),
                        "step_number": s.step_number,
                        "step_type": s.step_type,
                        "tool_name": s.tool_name,
                        "status": s.status,
                        "latency_ms": s.latency_ms,
                        "citations_valid": s.citations_valid,
                        "output": output,
                    }
                )
                step_offset += s.latency_ms or 50

        total_duration = step_offset + 200
        events.append(
            {
                "offset_ms": total_duration,
                "event": "completed",
                "close_run_id": str(close_run_id),
                "status": close_run.status.value,
            }
        )

        trace = DemoTrace(
            company_id=close_run.company_id,
            scenario_key=scenario_key,
            title=title,
            description=description,
            events_json=json.dumps(events),
            total_steps=len(events),
            total_duration_ms=total_duration,
            is_golden=is_golden,
        )
        self.session.add(trace)
        await self.session.flush()
        return trace


def get_golden_trace_definitions() -> list[dict[str, Any]]:
    """Return hard-coded golden traces for the 3 core demo scenarios (Sections 22-24)."""
    return [
        {
            "scenario_key": "PAYMENT_FRAGMENTATION",
            "title": "Scenario 1: Payment Fragmentation Below Threshold (Fraud / Policy Evasion)",
            "description": (
                "Vendor invoices split into $48,000 and $49,000 increments to bypass the "
                "$50,000 controller approval policy. Investigation traverses graph to find "
                "10 structured settlements. Verifier flags policy conflict; recommended action "
                "is CFO ESCALATION."
            ),
            "events": [
                {"offset_ms": 0, "event": "connected", "status": "INVESTIGATING"},
                {
                    "offset_ms": 100,
                    "event": "task_update",
                    "task_type": "BANK_RECONCILIATION",
                    "status": "COMPLETED",
                },
                {
                    "offset_ms": 200,
                    "event": "task_update",
                    "task_type": "AP_RECONCILIATION",
                    "status": "COMPLETED",
                },
                {
                    "offset_ms": 300,
                    "event": "agent_run_started",
                    "agent_name": "cfo_investigation_agent",
                    "exception_type": "PAYMENT_FRAGMENTATION",
                },
                {
                    "offset_ms": 450,
                    "event": "agent_step",
                    "step_number": 1,
                    "step_type": "dossier_inspection",
                    "tool_name": "EvidenceDossierBuilder",
                    "status": "COMPLETED",
                    "citations_valid": True,
                    "output": {"valid_records_count": 11, "ranked_nodes_count": 11},
                },
                {
                    "offset_ms": 750,
                    "event": "agent_step",
                    "step_number": 2,
                    "step_type": "reasoning_generation",
                    "tool_name": "LLMProvider",
                    "status": "COMPLETED",
                    "citations_valid": True,
                    "output": {
                        "likely_cause": (
                            "Fragmented settlement pattern to evade single-transaction "
                            "authorization threshold"
                        )
                    },
                },
                {
                    "offset_ms": 850,
                    "event": "agent_step",
                    "step_number": 3,
                    "step_type": "citation_validation",
                    "tool_name": "CitationValidator",
                    "status": "COMPLETED",
                    "citations_valid": True,
                    "output": {"hallucinations": 0, "all_valid": True},
                },
                {
                    "offset_ms": 950,
                    "event": "agent_step",
                    "step_number": 4,
                    "step_type": "confidence_calibration",
                    "tool_name": "ConfidenceCalibrator",
                    "status": "COMPLETED",
                    "citations_valid": True,
                    "output": {"raw_confidence": "0.9800", "calibrated_confidence": "0.9400"},
                },
                {
                    "offset_ms": 1100,
                    "event": "agent_finding",
                    "agent_name": "cfo_investigation_agent",
                    "action": "ESCALATE",
                    "target_role": "CFO",
                    "financial_impact": "1450000.00",
                },
                {
                    "offset_ms": 1250,
                    "event": "verification_complete",
                    "agent_name": "verification_agent",
                    "verified": True,
                    "recommended_autonomy": "ESCALATE",
                    "policy_violations": ["Single-transaction approval threshold evaded"],
                },
                {
                    "offset_ms": 1400,
                    "event": "action_executed",
                    "action_type": "MARK_EXCEPTION_ESCALATED",
                    "status": "EXECUTED",
                    "assigned_to": "CFO",
                },
                {"offset_ms": 1500, "event": "completed", "status": "WAITING_FOR_HUMAN"},
            ],
        },
        {
            "scenario_key": "PO_MISMATCH",
            "title": "Scenario 2: Purchase Order Quantity Mismatch ($24,000 Overbilling)",
            "description": (
                "Invoice billed 120 units at $1,200 ($144,000) against PO and Goods Receipt for "
                "100 units ($120,000). Verifier confirms $24,000 calculation discrepancy. Action "
                "agent stages adjusting journal entry and drafts vendor discrepancy letter, "
                "awaiting human approval."
            ),
            "events": [
                {"offset_ms": 0, "event": "connected", "status": "INVESTIGATING"},
                {
                    "offset_ms": 100,
                    "event": "task_update",
                    "task_type": "INVOICE_VALIDATION",
                    "status": "COMPLETED",
                },
                {
                    "offset_ms": 250,
                    "event": "agent_run_started",
                    "agent_name": "cfo_investigation_agent",
                    "exception_type": "PO_MISMATCH",
                },
                {
                    "offset_ms": 400,
                    "event": "agent_step",
                    "step_number": 1,
                    "step_type": "dossier_inspection",
                    "tool_name": "EvidenceDossierBuilder",
                    "status": "COMPLETED",
                    "citations_valid": True,
                    "output": {"invoice_qty": 120, "po_qty": 100, "received_qty": 100},
                },
                {
                    "offset_ms": 650,
                    "event": "agent_step",
                    "step_number": 2,
                    "step_type": "reasoning_generation",
                    "tool_name": "LLMProvider",
                    "status": "COMPLETED",
                    "citations_valid": True,
                    "output": {
                        "likely_cause": (
                            "Invoice quantity exceeds authorized PO quantity "
                            "by 20 units ($24,000.00)"
                        )
                    },
                },
                {
                    "offset_ms": 800,
                    "event": "verification_complete",
                    "agent_name": "verification_agent",
                    "verified": True,
                    "recommended_autonomy": "STAGE",
                    "calculations_verified": True,
                },
                {
                    "offset_ms": 950,
                    "event": "action_executed",
                    "action_type": "STAGE_JOURNAL_ENTRY",
                    "status": "STAGED",
                    "amount": "24000.00",
                },
                {
                    "offset_ms": 1100,
                    "event": "action_executed",
                    "action_type": "DRAFT_VENDOR_EMAIL",
                    "status": "STAGED",
                    "vendor": "Acme Industrial Supplies",
                },
                {"offset_ms": 1250, "event": "completed", "status": "WAITING_FOR_HUMAN"},
            ],
        },
        {
            "scenario_key": "CLEAN_TRANSACTION",
            "title": "Scenario 3: Clean 6-Way Reconciled Transaction ($0 Variance)",
            "description": (
                "Standard procurement order with exact matching between Purchase Order, "
                "Goods Receipt, Vendor Invoice, Bank Statement, Payment, and General Ledger line. "
                "Autonomously verified and resolved."
            ),
            "events": [
                {"offset_ms": 0, "event": "connected", "status": "RECONCILING"},
                {
                    "offset_ms": 100,
                    "event": "task_update",
                    "task_type": "BANK_RECONCILIATION",
                    "status": "COMPLETED",
                },
                {
                    "offset_ms": 200,
                    "event": "task_update",
                    "task_type": "PAYMENT_RECONCILIATION",
                    "status": "COMPLETED",
                },
                {
                    "offset_ms": 300,
                    "event": "verification_complete",
                    "agent_name": "verification_agent",
                    "verified": True,
                    "recommended_autonomy": "AUTO_RESOLVE",
                    "confidence": "0.9800",
                    "calibrated_confidence": "0.9800",
                },
                {
                    "offset_ms": 400,
                    "event": "action_executed",
                    "action_type": "MARK_EXCEPTION_RESOLVED",
                    "status": "EXECUTED",
                    "auto_resolved": True,
                },
                {"offset_ms": 500, "event": "completed", "status": "READY_TO_CLOSE"},
            ],
        },
    ]


async def seed_golden_traces(session: AsyncSession) -> list[DemoTrace]:
    """Ensure the 3 golden traces exist in the database for instant replay."""
    traces: list[DemoTrace] = []
    definitions = get_golden_trace_definitions()

    for defn in definitions:
        existing = await session.scalar(
            select(DemoTrace).where(DemoTrace.scenario_key == defn["scenario_key"])
        )
        if existing is not None:
            traces.append(existing)
            continue

        events = defn["events"]
        total_duration = events[-1]["offset_ms"] if events else 0
        trace = DemoTrace(
            scenario_key=defn["scenario_key"],
            title=defn["title"],
            description=defn["description"],
            events_json=json.dumps(events),
            total_steps=len(events),
            total_duration_ms=total_duration,
            is_golden=True,
        )
        session.add(trace)
        traces.append(trace)

    await session.flush()
    return traces
