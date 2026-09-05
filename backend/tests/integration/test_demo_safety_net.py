"""Integration tests for Demo Safety Net: Live/Replay mode and Trace Player (spec section 37)."""

from __future__ import annotations

import json
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.agent import AgentRun, AgentStep
from app.db.models.close_run import CloseRun, CloseTask
from app.demo.mode import demo_mode_manager
from app.domain.enums import AgentRunStatus, CloseRunStatus, CloseTaskStatus, CloseTaskType


@pytest.mark.asyncio
async def test_demo_mode_toggle(client: AsyncClient):
    # Ensure fresh state
    demo_mode_manager.reset()

    # 1. Default mode is LIVE
    resp = await client.get("/api/demo/mode")
    assert resp.status_code == 200
    assert resp.json() == {"mode": "LIVE", "close_run_id": None}

    # 2. Toggle global mode to REPLAY
    resp = await client.post("/api/demo/mode", json={"mode": "REPLAY"})
    assert resp.status_code == 200
    assert resp.json() == {"mode": "REPLAY", "close_run_id": None}

    # Verify global mode is now REPLAY
    resp = await client.get("/api/demo/mode")
    assert resp.status_code == 200
    assert resp.json()["mode"] == "REPLAY"

    # 3. Toggle specific close run to LIVE
    cr_id = uuid.uuid4()
    resp = await client.post("/api/demo/mode", json={"mode": "LIVE", "close_run_id": str(cr_id)})
    assert resp.status_code == 200
    assert resp.json() == {"mode": "LIVE", "close_run_id": str(cr_id)}

    # Verify run-specific query returns LIVE
    resp = await client.get(f"/api/demo/mode?close_run_id={cr_id}")
    assert resp.status_code == 200
    assert resp.json()["mode"] == "LIVE"

    # Verify other run falls back to global REPLAY
    other_cr_id = uuid.uuid4()
    resp = await client.get(f"/api/demo/mode?close_run_id={other_cr_id}")
    assert resp.status_code == 200
    assert resp.json()["mode"] == "REPLAY"

    # 4. Invalid mode returns 400
    resp = await client.post("/api/demo/mode", json={"mode": "TURBO_SPEED"})
    assert resp.status_code == 400

    # Reset
    demo_mode_manager.reset()


@pytest.mark.asyncio
async def test_golden_traces_seeded_and_retrieved(
    client: AsyncClient, client_session: AsyncSession
):
    # 1. Create company
    comp_resp = await client.post(
        "/api/companies",
        json={"name": "Demo Safety Net Corp", "base_currency": "USD"},
    )
    assert comp_resp.status_code == 201
    comp_id = comp_resp.json()["id"]
    headers = {"X-Company-Id": comp_id}

    # 2. GET /api/demo/traces (should auto-seed the 3 golden traces)
    resp = await client.get("/api/demo/traces", headers=headers)
    assert resp.status_code == 200
    traces = resp.json()
    assert len(traces) >= 3

    scenario_keys = {t["scenario_key"] for t in traces}
    assert "PAYMENT_FRAGMENTATION" in scenario_keys
    assert "PO_MISMATCH" in scenario_keys
    assert "CLEAN_TRANSACTION" in scenario_keys

    golden_frag = next(t for t in traces if t["scenario_key"] == "PAYMENT_FRAGMENTATION")
    assert golden_frag["is_golden"] is True
    assert golden_frag["total_steps"] > 0
    assert len(golden_frag["events"]) > 0

    # 3. Filter by scenario_key
    resp = await client.get("/api/demo/traces?scenario_key=PAYMENT_FRAGMENTATION", headers=headers)
    assert resp.status_code == 200
    filtered = resp.json()
    assert len(filtered) == 1
    assert filtered[0]["scenario_key"] == "PAYMENT_FRAGMENTATION"

    # 4. GET /api/demo/traces/{id}
    trace_id = golden_frag["id"]
    resp = await client.get(f"/api/demo/traces/{trace_id}", headers=headers)
    assert resp.status_code == 200
    trace_detail = resp.json()
    assert trace_detail["id"] == trace_id
    assert trace_detail["title"] == golden_frag["title"]
    assert len(trace_detail["events"]) == golden_frag["total_steps"]


@pytest.mark.asyncio
async def test_trace_recorder_and_player_stream(client: AsyncClient, client_session: AsyncSession):
    # 1. Create company
    comp_resp = await client.post(
        "/api/companies",
        json={"name": "TraceRecorder Corp", "base_currency": "USD"},
    )
    comp_id = uuid.UUID(comp_resp.json()["id"])
    headers = {"X-Company-Id": str(comp_id)}

    from datetime import date

    # 2. Create CloseRun, CloseTask, and AgentRun with steps in DB
    close_run = CloseRun(
        company_id=comp_id,
        period_start=date(2024, 3, 1),
        period_end=date(2024, 3, 31),
        status=CloseRunStatus.INVESTIGATING,
        version=1,
    )
    client_session.add(close_run)
    await client_session.flush()

    task = CloseTask(
        close_run_id=close_run.id,
        task_type=CloseTaskType.BANK_RECONCILIATION,
        status=CloseTaskStatus.COMPLETED,
        result_summary="Reconciled 50 transactions",
    )
    client_session.add(task)

    agent_run = AgentRun(
        company_id=comp_id,
        close_run_id=close_run.id,
        agent_name="cfo_investigation_agent",
        status=AgentRunStatus.COMPLETED,
        prompt_version_id="prompt-v1",
        model="gpt-4o",
        latency_ms=450,
    )
    client_session.add(agent_run)
    await client_session.flush()

    step = AgentStep(
        agent_run_id=agent_run.id,
        step_number=1,
        step_type="dossier_inspection",
        tool_name="EvidenceDossierBuilder",
        output_json='{"records_found": 8}',
        status="COMPLETED",
        latency_ms=150,
        citations_valid=True,
    )
    client_session.add(step)
    await client_session.flush()

    # 3. POST /api/demo/record
    record_payload = {
        "close_run_id": str(close_run.id),
        "scenario_key": "REHEARSAL_REPLAY_1",
        "title": "Captured Rehearsal Run 1",
        "description": "Recorded from live close run rehearsal",
        "is_golden": False,
    }
    resp = await client.post("/api/demo/record", headers=headers, json=record_payload)
    assert resp.status_code == 201
    recorded_trace = resp.json()
    assert recorded_trace["scenario_key"] == "REHEARSAL_REPLAY_1"
    assert recorded_trace["total_steps"] >= 4  # started + task + agent_run + step + completed
    assert recorded_trace["is_golden"] is False

    trace_id = recorded_trace["id"]

    # 4. Stream recorded trace directly via GET /api/demo/traces/{id}/stream
    async with client.stream(
        "GET",
        f"/api/demo/traces/{trace_id}/stream?simulate_delay=false&playback_speed=10.0",
        headers=headers,
    ) as stream_resp:
        assert stream_resp.status_code == 200
        events: list[dict] = []
        async for line in stream_resp.aiter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))

        assert len(events) >= 4
        assert events[0]["event"] == "close_run_started"
        assert any(e.get("event") == "task_update" for e in events)
        assert any(e.get("event") == "agent_step" for e in events)
        assert events[-1]["event"] == "completed"


@pytest.mark.asyncio
async def test_close_run_stream_in_replay_mode(client: AsyncClient, client_session: AsyncSession):
    demo_mode_manager.reset()

    # 1. Setup company and close run
    comp_resp = await client.post(
        "/api/companies",
        json={"name": "ReplaySafetyNet Corp", "base_currency": "USD"},
    )
    comp_id = comp_resp.json()["id"]
    headers = {"X-Company-Id": comp_id}

    cr_resp = await client.post(
        "/api/close-runs",
        headers=headers,
        json={"period_start": "2024-04-01", "period_end": "2024-04-30"},
    )
    assert cr_resp.status_code == 201
    close_run_id = cr_resp.json()["id"]

    # 2. Toggle demo mode to REPLAY for this specific close run
    resp = await client.post(
        "/api/demo/mode",
        json={"mode": "REPLAY", "close_run_id": close_run_id},
    )
    assert resp.status_code == 200
    assert resp.json()["mode"] == "REPLAY"

    # 3. Connect to GET /api/close-runs/{id}/stream
    # Since REPLAY mode is active, TracePlayer replays golden trace transparently!
    async with client.stream(
        "GET",
        f"/api/close-runs/{close_run_id}/stream?simulate_delay=false&playback_speed=10.0",
        headers=headers,
    ) as stream_resp:
        assert stream_resp.status_code == 200
        events: list[dict] = []
        async for line in stream_resp.aiter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))

        assert len(events) > 0
        # Replayed events have close_run_id matching the requested run
        assert events[0].get("close_run_id") == close_run_id
        # Sequence contains expected steps
        step_types = [e.get("step_type") for e in events if "step_type" in e]
        assert "dossier_inspection" in step_types

    # Reset
    demo_mode_manager.reset()
