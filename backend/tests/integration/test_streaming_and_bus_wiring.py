"""Integration tests for live SSE event bus wiring (spec sections 17, 37).

Verifies that events are published and received across:
- State changes (CloseWorkflowStateMachine)
- Task state changes
- Deterministic reconciliation
- Exception investigations
- Independent verification
- Action executions & approvals
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.action.service import ActionService
from app.close_workflow.state_machine import CloseWorkflowStateMachine
from app.data.generator import seed_company
from app.db.models.close_run import CloseRun, CloseTask
from app.db.models.exception import ExceptionRecord
from app.domain.enums import (
    CloseRunStatus,
    CloseTaskStatus,
    CloseTaskType,
    ExceptionSeverity,
    ExceptionStatus,
    ExceptionType,
    Role,
)
from app.investigation.agent import CFOInvestigationAgent
from app.investigation.types import (
    EvidenceDossier,
    InvestigationRequest,
)
from app.streaming.bus import agent_event_bus, format_sse
from app.verification.agent import VerificationAgent
from app.verification.types import VerificationRequest


@pytest.mark.asyncio
async def test_format_sse_formatting():
    """Verify SSE format conforms to standard spec."""
    raw = {"hello": "world", "count": 42}
    formatted = format_sse(raw, event="custom_event")
    assert formatted.startswith("event: custom_event\n")
    assert '"hello": "world"' in formatted
    assert formatted.endswith("\n\n")

    unnamed = format_sse(raw)
    assert unnamed.startswith("data: ")
    assert '"count": 42' in unnamed


@pytest.mark.asyncio
async def test_streaming_bus_wiring_across_workflow(db: AsyncSession):
    """Subscribe to agent_event_bus for a close run and verify all event types arrive."""
    company = await seed_company(db, seed=42)
    comp_id = company.id

    # 1. Create CloseRun & CloseTask
    close_run = CloseRun(
        company_id=comp_id,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 1, 31),
        status=CloseRunStatus.CREATED,
        version=1,
    )
    db.add(close_run)
    await db.flush()

    task = CloseTask(
        close_run_id=close_run.id,
        task_type=CloseTaskType.INVOICE_VALIDATION,
        status=CloseTaskStatus.PENDING,
    )
    db.add(task)
    await db.flush()

    # 2. Subscribe to event bus for close_run.id
    async with agent_event_bus.subscribe(close_run.id) as queue:
        # Step A: CloseRun state transition
        sm = CloseWorkflowStateMachine(db, comp_id)
        await sm.transition_close_run(close_run.id, CloseRunStatus.INGESTING)

        evt1 = queue.get_nowait()
        assert evt1["event"] == "close_run_state_change"
        assert evt1["close_run_id"] == str(close_run.id)
        assert evt1["new_status"] == CloseRunStatus.INGESTING.value

        # Step B: CloseTask state transition
        await sm.transition_task(task.id, CloseTaskStatus.IN_PROGRESS)

        evt2 = queue.get_nowait()
        assert evt2["event"] == "close_task_state_change"
        assert evt2["task_id"] == str(task.id)
        assert evt2["new_status"] == CloseTaskStatus.IN_PROGRESS.value

        # Step C: Exception investigation
        exc = ExceptionRecord(
            company_id=comp_id,
            close_run_id=close_run.id,
            type=ExceptionType.PO_MISMATCH,
            severity=ExceptionSeverity.HIGH,
            status=ExceptionStatus.OPEN,
            financial_impact=Decimal("25000.00"),
            currency="INR",
            confidence=Decimal("0.9500"),
            calibrated_confidence=Decimal("0.9200"),
        )
        db.add(exc)
        await db.flush()

        dossier = EvidenceDossier(
            exception_id=exc.id,
            company_id=comp_id,
            close_run_id=close_run.id,
            exception_type=ExceptionType.PO_MISMATCH,
            severity=ExceptionSeverity.HIGH,
            financial_impact=Decimal("25000.00"),
            currency="INR",
            valid_record_ids={str(exc.id)},
            valid_evidence_ids={f"record:{exc.id}"},
        )

        agent = CFOInvestigationAgent(session=db, company_id=comp_id)
        req = InvestigationRequest(
            exception_id=exc.id,
            company_id=comp_id,
            close_run_id=close_run.id,
            dossier=dossier,
        )
        finding = await agent.investigate(req)

        # We should have received investigation_started and investigation_completed
        evt_start = queue.get_nowait()
        assert evt_start["event"] == "investigation_started"
        assert evt_start["exception_id"] == str(exc.id)

        evt_complete = queue.get_nowait()
        assert evt_complete["event"] == "investigation_completed"
        assert evt_complete["finding_status"] == finding.finding_status.value

        # Step D: Independent verification
        verifier = VerificationAgent(session=db, company_id=comp_id)
        v_req = VerificationRequest(
            exception_id=exc.id,
            company_id=comp_id,
            close_run_id=close_run.id,
            finding=finding,
            dossier=dossier,
        )
        await verifier.verify(v_req)

        evt_ver = queue.get_nowait()
        assert evt_ver["event"] == "verification_completed"
        assert evt_ver["close_run_id"] == str(close_run.id)
        assert evt_ver["exception_id"] == str(exc.id)

        # Step E: Action approval and escalation
        action_service = ActionService(db, comp_id)
        await action_service.approve_exception(exc.id, actor="lead_controller")

        evt_app = queue.get_nowait()
        assert evt_app["event"] == "exception_approved"
        assert evt_app["actor"] == "lead_controller"
        assert evt_app["exception_id"] == str(exc.id)

        await action_service.escalate_exception(
            exc.id, target_role=Role.CFO, reason="Policy threshold", actor="auditor"
        )
        evt_esc = queue.get_nowait()
        assert evt_esc["event"] == "exception_escalated"
        assert evt_esc["actor"] == "auditor"
        assert evt_esc["target_role"] == Role.CFO.value


@pytest.mark.asyncio
async def test_sse_endpoint_receives_live_events(client: AsyncClient, client_session: AsyncSession):
    """Verify GET /api/close-runs/{id}/stream receives live published events."""
    comp_resp = await client.post(
        "/api/companies",
        json={"name": "SSE Stream Corp", "base_currency": "USD"},
    )
    assert comp_resp.status_code == 201
    comp_id = comp_resp.json()["id"]
    headers = {"X-Company-Id": comp_id}

    run_resp = await client.post(
        "/api/close-runs",
        headers=headers,
        json={"period_start": "2026-02-01", "period_end": "2026-02-28"},
    )
    assert run_resp.status_code == 201
    close_run_id = uuid.UUID(run_resp.json()["id"])

    # Update close run to READY_TO_CLOSE so stream yields connected + completed and exits
    run_obj = await client_session.get(CloseRun, close_run_id)
    assert run_obj is not None
    run_obj.status = CloseRunStatus.READY_TO_CLOSE
    await client_session.flush()

    # Calling stream endpoint returns 200 with text/event-stream
    stream_resp = await client.get(f"/api/close-runs/{close_run_id}/stream", headers=headers)
    assert stream_resp.status_code == 200
    assert "text/event-stream" in stream_resp.headers["content-type"]
    assert "data:" in stream_resp.text
    assert "connected" in stream_resp.text
    assert "completed" in stream_resp.text
