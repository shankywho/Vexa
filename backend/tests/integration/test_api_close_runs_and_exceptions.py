"""Integration tests for Close-Runs, Exceptions, Agent-Runs API and SSE stream."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.generator import seed_financial_transactions
from app.data.seed import seed_company
from app.db.models.agent import AgentRun, AgentStep
from app.db.models.close_run import CloseRun
from app.db.models.exception import ExceptionAction, ExceptionRecord
from app.domain.enums import (
    AgentRunStatus,
    AutonomyLevel,
    CloseRunStatus,
    CloseTaskStatus,
    CloseTaskType,
    ExceptionSeverity,
    ExceptionStatus,
    ExceptionType,
)


@pytest.mark.asyncio
async def test_close_runs_crud_and_workflow_api(client: AsyncClient, client_session: AsyncSession):
    # 1. Create company
    resp = await client.post(
        "/api/companies",
        json={"name": "CloseRun Corp", "base_currency": "USD"},
    )
    assert resp.status_code == 201
    comp = resp.json()
    comp_id = comp["id"]
    headers = {"X-Company-Id": comp_id}

    # 2. POST /api/close-runs
    resp = await client.post(
        "/api/close-runs",
        headers=headers,
        json={"period_start": "2024-01-01", "period_end": "2024-01-31"},
    )
    assert resp.status_code == 201
    run_data = resp.json()
    close_run_id = run_data["id"]
    assert run_data["status"] == "CREATED"
    assert run_data["version"] == 1

    # 3. GET /api/close-runs
    resp = await client.get("/api/close-runs", headers=headers)
    assert resp.status_code == 200
    runs = resp.json()
    assert any(r["id"] == close_run_id for r in runs)

    # 4. GET /api/close-runs/{id}
    resp = await client.get(f"/api/close-runs/{close_run_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == close_run_id

    # 5. GET /api/close-runs/{id}/tasks
    resp = await client.get(f"/api/close-runs/{close_run_id}/tasks", headers=headers)
    assert resp.status_code == 200
    tasks = resp.json()
    assert len(tasks) == 10  # 10 default tasks
    assert all(t["status"] == "PENDING" for t in tasks)

    # 6. POST /api/close-runs/{id}/start
    resp = await client.post(f"/api/close-runs/{close_run_id}/start", headers=headers)
    assert resp.status_code == 200
    started_run = resp.json()
    assert started_run["status"] in ("RECONCILING", "INVESTIGATING", "WAITING_FOR_HUMAN", "READY_TO_CLOSE", "BLOCKED")

    # 7. GET /api/close-runs/{id}/tasks after start
    resp = await client.get(f"/api/close-runs/{close_run_id}/tasks", headers=headers)
    assert resp.status_code == 200
    updated_tasks = resp.json()
    assert any(t["status"] in ("COMPLETED", "IN_PROGRESS", "PENDING", "BLOCKED") for t in updated_tasks)

    # 8. GET /api/close-runs/{id}/exceptions
    resp = await client.get(f"/api/close-runs/{close_run_id}/exceptions", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

    # 9. GET /api/close-runs/{id}/package
    resp = await client.get(f"/api/close-runs/{close_run_id}/package", headers=headers)
    assert resp.status_code == 200
    pkg = resp.json()
    assert pkg["close_run_id"] == close_run_id
    assert "tasks" in pkg
    assert "readiness" in pkg

    # 10. GET /api/close-runs/{id}/audit
    resp = await client.get(f"/api/close-runs/{close_run_id}/audit", headers=headers)
    assert resp.status_code == 200
    audit_events = resp.json()
    assert len(audit_events) > 0

    # 11. GET /api/close-runs/{id}/stream (SSE stream)
    resp = await client.get(f"/api/close-runs/{close_run_id}/stream", headers=headers)
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
    assert "data:" in resp.text
    assert "connected" in resp.text


@pytest.mark.asyncio
async def test_exceptions_and_actions_api_flow(client: AsyncClient, client_session: AsyncSession):
    # 1. Seed company & financial data
    comp_resp = await client.post(
        "/api/companies",
        json={"name": "Exceptions Corp", "base_currency": "USD"},
    )
    comp_id = uuid.UUID(comp_resp.json()["id"])
    headers = {"X-Company-Id": str(comp_id)}

    # 2. Create close run
    cr_resp = await client.post(
        "/api/close-runs",
        headers=headers,
        json={"period_start": "2024-01-01", "period_end": "2024-01-31"},
    )
    cr_id = uuid.UUID(cr_resp.json()["id"])

    # 3. Insert a test exception in DB
    exc = ExceptionRecord(
        company_id=comp_id,
        close_run_id=cr_id,
        type=ExceptionType.PAYMENT_FRAGMENTATION,
        severity=ExceptionSeverity.CRITICAL,
        status=ExceptionStatus.OPEN,
        financial_impact=Decimal("24000.00"),
        currency="USD",
        autonomy_level=AutonomyLevel.STAGE,
        root_cause="Suspicious payment fragmentation below threshold",
        recommended_action="Escalate to CFO and block vendor payments",
    )
    client_session.add(exc)
    await client_session.flush()

    # Stage an action on this exception
    act = ExceptionAction(
        exception_id=exc.id,
        action_type="STAGE_JOURNAL_ENTRY",
        status="STAGED",
        payload_json='{"memo": "Adjust fragmentation", "amount": "24000.00"}',
        actor="action_agent",
    )
    client_session.add(act)
    await client_session.flush()

    # 4. GET /api/exceptions/{id}
    resp = await client.get(f"/api/exceptions/{exc.id}", headers=headers)
    assert resp.status_code == 200
    exc_data = resp.json()
    assert exc_data["id"] == str(exc.id)
    assert exc_data["financial_impact"] == "24000.00"
    assert exc_data["type"] == "PAYMENT_FRAGMENTATION"

    # 5. GET /api/exceptions/{id}/evidence
    resp = await client.get(f"/api/exceptions/{exc.id}/evidence", headers=headers)
    assert resp.status_code == 200
    ev_data = resp.json()
    assert ev_data["exception_id"] == str(exc.id)
    assert "dossier" in ev_data

    # 6. POST /api/exceptions/{id}/approve
    resp = await client.post(
        f"/api/exceptions/{exc.id}/approve",
        headers=headers,
        json={"actor": "controller_alice", "notes": "Approved staged adjustment"},
    )
    assert resp.status_code == 200
    appr_data = resp.json()
    assert appr_data["status"] == "EXECUTED"
    assert appr_data["actor"] == "controller_alice"

    # 7. POST /api/exceptions/{id}/reverse (Spec 13.2 Rollback Path)
    resp = await client.post(
        f"/api/exceptions/{exc.id}/reverse",
        headers=headers,
        json={"reason": "Auditor requested rollback of adjustment", "reversed_by": "cfo_carol"},
    )
    assert resp.status_code == 200
    rev_data = resp.json()
    assert rev_data["action_type"] == "REVERSAL"
    assert rev_data["status"] == "REVERSED"
    assert rev_data["actor"] == "cfo_carol"

    # Verify exception status reopened after reversal
    resp = await client.get(f"/api/exceptions/{exc.id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "REOPENED"

    # 8. POST /api/exceptions/{id}/escalate
    resp = await client.post(
        f"/api/exceptions/{exc.id}/escalate",
        headers=headers,
        json={"target_role": "CFO", "reason": "High fraud risk", "actor": "controller_alice"},
    )
    assert resp.status_code == 200
    esc_data = resp.json()
    assert esc_data["action_type"] == "MARK_EXCEPTION_ESCALATED"

    # Verify exception status is ESCALATED
    resp = await client.get(f"/api/exceptions/{exc.id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ESCALATED"

    # 9. POST /api/exceptions/{id}/resolve
    resp = await client.post(
        f"/api/exceptions/{exc.id}/resolve",
        headers=headers,
        json={"actor": "cfo_carol", "notes": "Fraud investigation concluded with vendor"},
    )
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["action_type"] == "MARK_EXCEPTION_RESOLVED"

    # Verify exception status is RESOLVED
    resp = await client.get(f"/api/exceptions/{exc.id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "RESOLVED"

    # 10. POST /api/exceptions/{id}/reject
    resp = await client.post(
        f"/api/exceptions/{exc.id}/reject",
        headers=headers,
        json={"actor": "auditor_dave", "notes": "Additional inquiry required"},
    )
    assert resp.status_code == 200
    rej_data = resp.json()
    assert rej_data["status"] == "EXECUTED"

    # Verify returned to OPEN
    resp = await client.get(f"/api/exceptions/{exc.id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "OPEN"


@pytest.mark.asyncio
async def test_agent_runs_api(client: AsyncClient, client_session: AsyncSession):
    # 1. Setup company
    comp_resp = await client.post(
        "/api/companies",
        json={"name": "AgentRuns Corp", "base_currency": "USD"},
    )
    comp_id = uuid.UUID(comp_resp.json()["id"])
    headers = {"X-Company-Id": str(comp_id)}

    # 2. Create an AgentRun and AgentSteps in DB
    run = AgentRun(
        company_id=comp_id,
        agent_name="cfo_investigation_agent",
        status=AgentRunStatus.COMPLETED,
        prompt_version_id="prompt-v1",
        model="gpt-4o",
        latency_ms=850,
        total_tokens=520,
        cost_usd=Decimal("0.0025"),
    )
    client_session.add(run)
    await client_session.flush()

    step1 = AgentStep(
        agent_run_id=run.id,
        step_number=1,
        step_type="dossier_inspection",
        tool_name="EvidenceDossierBuilder",
        input_json='{"test": true}',
        output_json='{"nodes": 4}',
        status="COMPLETED",
        latency_ms=120,
        citations_valid=True,
    )
    step2 = AgentStep(
        agent_run_id=run.id,
        step_number=2,
        step_type="reasoning_generation",
        tool_name="LLMProvider",
        input_json='{"prompt": "analyze"}',
        output_json='{"analysis": "complete"}',
        status="COMPLETED",
        latency_ms=730,
        citations_valid=True,
    )
    client_session.add_all([step1, step2])
    await client_session.flush()

    # 3. GET /api/agent-runs/{id}
    resp = await client.get(f"/api/agent-runs/{run.id}", headers=headers)
    assert resp.status_code == 200
    run_data = resp.json()
    assert run_data["id"] == str(run.id)
    assert run_data["agent_name"] == "cfo_investigation_agent"
    assert run_data["status"] == "COMPLETED"
    assert len(run_data["steps"]) == 2

    # 4. GET /api/agent-runs/{id}/steps
    resp = await client.get(f"/api/agent-runs/{run.id}/steps", headers=headers)
    assert resp.status_code == 200
    steps_data = resp.json()
    assert len(steps_data) == 2
    assert steps_data[0]["step_type"] == "dossier_inspection"
    assert steps_data[1]["step_type"] == "reasoning_generation"
