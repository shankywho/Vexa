"""API integration tests for policy configuration and close certification endpoints."""

from __future__ import annotations

import uuid
from httpx import AsyncClient


async def test_policies_get_and_update(client: AsyncClient) -> None:
    # Create company first
    comp_resp = await client.post(
        "/api/companies",
        json={"name": "Policy Corp", "base_currency": "USD"},
    )
    assert comp_resp.status_code == 201
    comp_id = comp_resp.json()["id"]
    headers = {"X-Company-Id": comp_id}

    # 1. Get default policy
    resp = await client.get("/api/policies", headers=headers)
    assert resp.status_code == 200
    policy = resp.json()
    assert policy["max_auto_resolution_amount"] == "50000.00"
    assert policy["materiality_threshold"] == "100000.00"
    assert policy["min_confidence"] in ("0.95", "0.9500")

    # 2. Update policy
    update_resp = await client.post(
        "/api/policies",
        headers=headers,
        json={
            "max_auto_resolution_amount": "75000.00",
            "materiality_threshold": "150000.00",
            "min_confidence": "0.98",
        },
    )
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["max_auto_resolution_amount"] == "75000.00"
    assert updated["materiality_threshold"] == "150000.00"
    assert updated["min_confidence"] == "0.98"

    # 3. Verify get returns updated policy
    resp2 = await client.get("/api/policies", headers=headers)
    assert resp2.status_code == 200
    assert resp2.json()["max_auto_resolution_amount"] == "75000.00"


async def test_certify_close_run_flow(client: AsyncClient) -> None:
    # Create company first
    comp_resp = await client.post(
        "/api/companies",
        json={"name": "Certify Corp", "base_currency": "USD"},
    )
    assert comp_resp.status_code == 201
    comp_id = comp_resp.json()["id"]
    headers = {"X-Company-Id": comp_id}

    # Create close run
    create_resp = await client.post(
        "/api/close-runs",
        headers=headers,
        json={"period_start": "2026-03-01", "period_end": "2026-03-31"},
    )
    assert create_resp.status_code in (200, 201)
    run_id = create_resp.json()["id"]

    # Certify close run
    certify_resp = await client.post(
        f"/api/close-runs/{run_id}/certify",
        headers=headers,
        json={
            "officer_name": "Alexandra Wright, CPA (CFO)",
            "notes": "Board audit committee sign-off",
        },
    )
    assert certify_resp.status_code == 200
    certified_data = certify_resp.json()
    assert certified_data["status"] == "CLOSED"
