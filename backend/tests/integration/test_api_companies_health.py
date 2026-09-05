"""API integration tests for the foundation endpoints."""

from __future__ import annotations

import uuid

from httpx import AsyncClient


async def test_health_endpoint(client: AsyncClient) -> None:
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert body["environment"] == "development"


async def test_company_crud_flow(client: AsyncClient) -> None:
    # Create
    resp = await client.post(
        "/api/companies",
        json={"name": "NovaScale AI", "base_currency": "INR", "fiscal_year_end": "03-31"},
    )
    assert resp.status_code == 201
    company = resp.json()
    assert company["name"] == "NovaScale AI"
    assert company["base_currency"] == "INR"
    company_id = uuid.UUID(company["id"])

    # Get by id
    resp = await client.get(f"/api/companies/{company_id}")
    assert resp.status_code == 200
    assert resp.json()["legal_name"] is None

    # List
    resp = await client.get("/api/companies")
    assert resp.status_code == 200
    assert any(c["id"] == company["id"] for c in resp.json())

    # Unknown company -> 404
    resp = await client.get(f"/api/companies/{uuid.uuid4()}")
    assert resp.status_code == 404


async def test_company_validation(client: AsyncClient) -> None:
    resp = await client.post("/api/companies", json={"name": ""})
    assert resp.status_code == 422
