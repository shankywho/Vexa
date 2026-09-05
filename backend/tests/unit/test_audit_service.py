"""Audit-service foundation tests (spec section 13)."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import (
    AuditService,
    deploy_agent_prompt_version,
    deploy_policy_version,
    parse_json_column,
)
from app.db.models.tenancy import Company
from app.domain.enums import AuditEventType


async def _company(db: AsyncSession) -> Company:
    company = Company(name="Audit Co", base_currency="USD", is_active=True)
    db.add(company)
    await db.flush()
    return company


async def test_record_audit_event_with_version_refs(db: AsyncSession) -> None:
    company = await _company(db)
    service = AuditService(db, company_id=company.id)

    await deploy_policy_version(db, version_id="policy-v2", policy_config={"min_confidence": 0.95})
    await deploy_agent_prompt_version(
        db, agent_name="investigator", version_id="investigator-v3", prompt_config={"system": "..."}
    )

    event = await service.record(
        event_type=AuditEventType.EXCEPTION_DECISION,
        actor="investigator",
        actor_type="AGENT",
        agent_name="investigator",
        agent_prompt_version_id="investigator-v3",
        policy_version_id="policy-v2",
        decision="ESCALATE",
        reason="Invoice quantity exceeds received quantity",
        financial_impact=Decimal("384000.00"),
        currency="INR",
        confidence=Decimal("0.97"),
        calibrated_confidence=Decimal("0.90"),
        evidence_ids=["INV-821", "PO-4421"],
        metadata_={"tool_calls": [{"name": "calculate_variance"}]},
    )

    assert event.company_id == company.id
    assert event.agent_prompt_version_id == "investigator-v3"
    assert event.policy_version_id == "policy-v2"
    assert parse_json_column(event.evidence_ids) == ["INV-821", "PO-4421"]
    assert parse_json_column(event.metadata_)["tool_calls"][0]["name"] == "calculate_variance"


async def test_list_audit_events_is_tenant_scoped(db: AsyncSession) -> None:
    company_a = await _company(db)
    company_b = Company(name="Other Co", base_currency="USD", is_active=True)
    db.add(company_b)
    await db.flush()

    await AuditService(db, company_id=company_a.id).record(
        event_type=AuditEventType.SYSTEM, reason="a"
    )
    await AuditService(db, company_id=company_b.id).record(
        event_type=AuditEventType.SYSTEM, reason="b"
    )

    events_a = await AuditService(db, company_id=company_a.id).list()
    assert len(events_a) == 1
    assert events_a[0].reason == "a"


async def test_audit_events_are_append_only(db: AsyncSession) -> None:
    company = await _company(db)
    service = AuditService(db, company_id=company.id)
    await service.record(event_type=AuditEventType.SYSTEM, reason="first")
    await service.record(event_type=AuditEventType.SYSTEM, reason="second")

    events = await service.list()
    assert [e.reason for e in events] == ["second", "first"]
