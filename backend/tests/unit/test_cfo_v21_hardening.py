"""Comprehensive tests for Vexa Backend v2.1 — CFO Capability & Safety Hardening.

Covers:
1. Vendor bank account change anomaly detection & evidence graph edges
2. Data ingestion gap detection & close workflow readiness blocking
3. Investigation agent circuit breaker (hard step limit & wall-clock timeout)
4. Human correction / outcome recording loop, override statistics & policy tuning candidates
5. Per-account materiality policy (variance % of balance, per-account overrides, zero/negative guards)
6. SOX control-ID deterministic tagging & audit event filtering
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.action.correction_service import HumanCorrectionService
from app.action.service import ActionService
from app.audit.controls import SoxControl, map_to_control_id
from app.audit.service import AuditService
from app.close_workflow.types import ClosePolicy
from app.db.models.banking import BankAccount, BankTransaction, Payment
from app.db.models.counterparty import Vendor
from app.db.models.exception import ExceptionRecord
from app.db.models.ledger import JournalEntry
from app.db.models.tenancy import Company
from app.domain.enums import (
    AuditEventType,
    AutonomyLevel,
    BankTransactionDirection,
    CloseTaskType,
    DocumentStatus,
    ExceptionSeverity,
    ExceptionStatus,
    ExceptionType,
    Role,
)
from app.evidence_graph.builder import FinancialEvidenceGraphBuilder
from app.evidence_graph.types import EdgeType, EvidenceNode, NodeType
from app.investigation.agent import (
    CFOInvestigationAgent,
    InvestigationCircuitBreakerTripped,
)
from app.investigation.llm_provider import MockLLMProvider
from app.investigation.types import (
    AutonomyAction,
    EvidenceDossier,
    FindingStatus,
    InvestigationFinding,
    InvestigationRecommendation,
    InvestigationRequest,
    RootCauseAnalysis,
)
from app.reconciliation.config import ReconciliationConfig
from app.reconciliation.rules import (
    detect_data_ingestion_gaps,
    detect_vendor_bank_change_anomalies,
)
from app.reconciliation.schemas import ReconciliationType
from app.verification.engine import PolicyGateVerifier

# ---------------------------------------------------------------------------
# Helpers & Fixtures
# ---------------------------------------------------------------------------


async def _create_test_company(db: AsyncSession, name: str = "CFO Test Co") -> Company:
    company = Company(name=name, base_currency="USD", is_active=True)
    db.add(company)
    await db.flush()
    return company


def _create_test_dossier(exc: ExceptionRecord, company_id: uuid.UUID) -> EvidenceDossier:
    p_id = str(uuid.uuid4())
    return EvidenceDossier(
        exception_id=exc.id,
        company_id=company_id,
        exception_type=exc.type,
        severity=exc.severity,
        financial_impact=exc.financial_impact,
        currency="USD",
        valid_record_ids={p_id, str(exc.id)},
        valid_evidence_ids={f"invoice:{p_id}", f"exception:{exc.id}"},
        primary_record={
            "node_id": f"invoice:{p_id}",
            "node_type": "invoice",
            "record_id": p_id,
            "label": "Test Invoice",
            "properties": {},
        },
        ranked_nodes=[{"node_id": f"invoice:{p_id}", "score": 1.0, "label": "Inv"}],
    )


# ---------------------------------------------------------------------------
# 1. Vendor Bank Account Change Anomaly Detection & Evidence Graph Edges
# ---------------------------------------------------------------------------


def test_vendor_bank_change_anomaly_rule() -> None:
    """Detect payment to vendor whose bank account changed within 7-day window."""
    company_id = uuid.uuid4()
    old_account_id = uuid.uuid4()
    new_account_id = uuid.uuid4()
    vendor_id = uuid.uuid4()

    vendor = Vendor(
        id=vendor_id,
        company_id=company_id,
        name="Apex Industrial",
        bank_account_id=new_account_id,
        previous_bank_account_id=old_account_id,
        bank_account_changed_at=datetime(2026, 3, 10, 10, 0, tzinfo=timezone.utc),
    )

    # Payment made on 2026-03-12 (2 days after bank account change -> within 7 day window)
    payment = Payment(
        id=uuid.uuid4(),
        company_id=company_id,
        beneficiary_reference="PMT-9901",
        vendor_id=vendor_id,
        bank_account_id=new_account_id,
        payment_date=date(2026, 3, 12),
        amount=Decimal("75000.00"),
        currency="USD",
        status=DocumentStatus.POSTED,
    )

    config = ReconciliationConfig(vendor_bank_change_window_days=7)
    results = detect_vendor_bank_change_anomalies(
        vendors=[vendor],
        payments=[payment],
        config=config,
    )

    assert len(results) == 1
    anomaly = results[0]
    assert anomaly.reconciliation_type == ReconciliationType.VENDOR_BANK_CHANGE
    assert anomaly.exception_type == ExceptionType.VENDOR_BANK_CHANGE_ANOMALY
    assert anomaly.financial_impact == Decimal("75000.00")
    assert "Apex Industrial" in anomaly.deterministic_reason
    assert "only 2 day(s) after vendor's bank account was modified" in anomaly.deterministic_reason
    assert len(anomaly.matched_records) == 3


@pytest.mark.asyncio
async def test_vendor_bank_change_evidence_graph_edges(db: AsyncSession) -> None:
    """Verify evidence graph constructs VENDOR_PREVIOUS_BANK_ACCOUNT and ACCOUNT_CHANGED_TO edges."""
    company = await _create_test_company(db, name="Evidence Graph Vendor Co")

    old_acct = BankAccount(
        company_id=company.id,
        account_name="Old Vendor Bank Acct",
        account_number="****8888",
        currency="USD",
    )
    new_acct = BankAccount(
        company_id=company.id,
        account_name="New Vendor Bank Acct",
        account_number="****9999",
        currency="USD",
    )
    db.add_all([old_acct, new_acct])
    await db.flush()

    vendor = Vendor(
        company_id=company.id,
        name="Global Cyber Logistics",
        bank_account_id=new_acct.id,
        previous_bank_account_id=old_acct.id,
        bank_account_changed_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
    )
    db.add(vendor)
    await db.flush()

    builder = FinancialEvidenceGraphBuilder(db, company.id)
    graph = await builder.build()

    vendor_node_id = EvidenceNode.make_id(NodeType.VENDOR, vendor.id)
    old_acct_node_id = EvidenceNode.make_id(NodeType.BANK_ACCOUNT, old_acct.id)
    new_acct_node_id = EvidenceNode.make_id(NodeType.BANK_ACCOUNT, new_acct.id)

    assert vendor_node_id in graph.nodes
    assert old_acct_node_id in graph.nodes
    assert new_acct_node_id in graph.nodes

    # Edge: vendor -> previous bank account
    prev_edges = graph.get_edges_by_type(EdgeType.VENDOR_PREVIOUS_BANK_ACCOUNT)
    assert any(
        e.source_id == vendor_node_id and e.target_id == old_acct_node_id for e in prev_edges
    )

    # Edge: previous bank account -> new bank account
    changed_edges = graph.get_edges_by_type(EdgeType.ACCOUNT_CHANGED_TO)
    assert any(
        e.source_id == old_acct_node_id and e.target_id == new_acct_node_id for e in changed_edges
    )


def test_vendor_bank_change_policy_gate_forces_cfo_escalation() -> None:
    """Vendor bank change anomaly must NEVER auto-resolve and must escalate to CFO."""
    policy = ClosePolicy(
        max_auto_resolution_amount=Decimal("100000.00"),
        min_confidence=Decimal("0.80"),
    )
    verifier = PolicyGateVerifier()

    exc = ExceptionRecord(
        id=uuid.uuid4(),
        company_id=uuid.uuid4(),
        type=ExceptionType.VENDOR_BANK_CHANGE_ANOMALY,
        severity=ExceptionSeverity.CRITICAL,
        financial_impact=Decimal("45000.00"),
        currency="USD",
        status=ExceptionStatus.OPEN,
    )

    finding = InvestigationFinding(
        exception_id=exc.id,
        exception_type=exc.type,
        finding_status=FindingStatus.COMPLETED,
        root_cause_analysis=RootCauseAnalysis(
            primary_category="VENDOR_BANK_CHANGE_ANOMALY",
            summary="Bank account changed right before payment",
            likely_cause="Potential phishing or legitimate update requiring authorization",
            is_genuine_discrepancy=True,
            is_timing_or_operational=False,
        ),
        recommendation=InvestigationRecommendation(
            action=AutonomyAction.AUTO_RESOLVE,  # LLM attempted to auto-resolve!
            target_role=Role.CONTROLLER,
            recommended_action="Approve payment",
            should_block_close=False,
            should_escalate_to_cfo=False,
        ),
    )

    autonomy, violations = verifier.evaluate_policy(
        exception=exc,
        finding=finding,
        calibrated_confidence=Decimal("0.95"),
        policy=policy,
        calculation_valid=True,
        evidence_complete=True,
    )

    # Policy gate MUST override LLM attempt to auto-resolve
    assert autonomy == AutonomyLevel.RECOMMEND
    assert autonomy != AutonomyLevel.EXECUTE


# ---------------------------------------------------------------------------
# 2. Data Ingestion Gap Detection & Close Readiness Blocking
# ---------------------------------------------------------------------------


def test_data_ingestion_gap_detection_rules() -> None:
    """Detect bank feed date gaps >= 5 business days and missing sequential journal entries."""
    company_id = uuid.uuid4()
    bank_acct_id = uuid.uuid4()

    # Bank transactions with a 6-business-day gap: 2026-03-02 (Monday) to 2026-03-11 (Wednesday)
    tx1 = BankTransaction(
        id=uuid.uuid4(),
        company_id=company_id,
        bank_account_id=bank_acct_id,
        transaction_date=date(2026, 3, 2),
        amount=Decimal("1200.00"),
        currency="USD",
        direction=BankTransactionDirection.CREDIT,
        reference="DEP-001",
        status=DocumentStatus.POSTED,
    )
    tx2 = BankTransaction(
        id=uuid.uuid4(),
        company_id=company_id,
        bank_account_id=bank_acct_id,
        transaction_date=date(2026, 3, 11),
        amount=Decimal("1500.00"),
        currency="USD",
        direction=BankTransactionDirection.CREDIT,
        reference="DEP-002",
        status=DocumentStatus.POSTED,
    )

    # Journal entries with sequence gap: JE-00101, JE-00102, JE-00105 (missing 103, 104)
    je1 = JournalEntry(
        id=uuid.uuid4(),
        company_id=company_id,
        reference="JE-00101",
        entry_date=date(2026, 3, 2),
        status=DocumentStatus.POSTED,
    )
    je2 = JournalEntry(
        id=uuid.uuid4(),
        company_id=company_id,
        reference="JE-00102",
        entry_date=date(2026, 3, 3),
        status=DocumentStatus.POSTED,
    )
    je3 = JournalEntry(
        id=uuid.uuid4(),
        company_id=company_id,
        reference="JE-00105",
        entry_date=date(2026, 3, 5),
        status=DocumentStatus.POSTED,
    )

    results = detect_data_ingestion_gaps(
        bank_transactions=[tx1, tx2],
        journal_entries=[je1, je2, je3],
        config=ReconciliationConfig(),
    )

    assert len(results) >= 2
    types = [r.reconciliation_type for r in results]
    assert all(t == ReconciliationType.DATA_INGESTION_GAP for t in types)

    # Check bank gap message
    bank_gaps = [r for r in results if r.source_record_type == "BANK_TRANSACTION"]
    assert len(bank_gaps) == 1
    assert "between 2026-03-02 and 2026-03-11" in bank_gaps[0].deterministic_reason

    # Check sequence gap message
    je_gaps = [r for r in results if r.source_record_type == "JOURNAL_ENTRY"]
    assert len(je_gaps) == 1
    assert "Discontinuity in journal entry sequence numbering" in je_gaps[0].deterministic_reason


def test_data_ingestion_gap_blocks_close_policy() -> None:
    """Unresolved data ingestion gap is in blocking_exception_types and blocks close readiness."""
    policy = ClosePolicy()
    assert ExceptionType.DATA_INGESTION_GAP in policy.blocking_exception_types
    assert ExceptionType.VENDOR_BANK_CHANGE_ANOMALY in policy.blocking_exception_types

    verifier = PolicyGateVerifier()
    exc = ExceptionRecord(
        id=uuid.uuid4(),
        company_id=uuid.uuid4(),
        type=ExceptionType.DATA_INGESTION_GAP,
        severity=ExceptionSeverity.CRITICAL,
        financial_impact=Decimal("0.00"),
        currency="USD",
        status=ExceptionStatus.OPEN,
    )

    finding = InvestigationFinding(
        exception_id=exc.id,
        exception_type=exc.type,
        finding_status=FindingStatus.COMPLETED,
        root_cause_analysis=RootCauseAnalysis(
            primary_category="DATA_INGESTION_GAP",
            summary="Missing 4 business days of bank statements",
            likely_cause="Bank feed API outage",
            is_genuine_discrepancy=True,
            is_timing_or_operational=False,
        ),
        recommendation=InvestigationRecommendation(
            action=AutonomyAction.AUTO_RESOLVE,
            target_role=Role.CONTROLLER,
            recommended_action="Ignore feed outage",
            should_block_close=False,
            should_escalate_to_cfo=False,
        ),
    )

    autonomy, violations = verifier.evaluate_policy(
        exception=exc,
        finding=finding,
        calibrated_confidence=Decimal("0.95"),
        policy=policy,
        calculation_valid=True,
        evidence_complete=True,
    )
    assert autonomy == AutonomyLevel.RECOMMEND
    assert autonomy != AutonomyLevel.EXECUTE


# ---------------------------------------------------------------------------
# 3. Investigation Agent Circuit Breaker (Hard Step Limit & Wall-Clock Timeout)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_investigation_circuit_breaker_step_limit(db: AsyncSession) -> None:
    """Agent must trip circuit breaker and terminate cleanly when exceeding step limit."""
    company = await _create_test_company(db, name="Circuit Breaker Step Co")
    audit_service = AuditService(db, company.id)

    exc = ExceptionRecord(
        company_id=company.id,
        type=ExceptionType.PO_MISMATCH,
        severity=ExceptionSeverity.HIGH,
        financial_impact=Decimal("1500.00"),
        currency="USD",
        status=ExceptionStatus.OPEN,
    )
    db.add(exc)
    await db.flush()

    dossier = _create_test_dossier(exc, company.id)
    agent = CFOInvestigationAgent(db, company.id, audit_service=audit_service)

    # Request configured with hard step limit of 2 (normal pipeline has 5 steps)
    req = InvestigationRequest(
        exception_id=exc.id,
        company_id=company.id,
        dossier=dossier,
        max_agent_steps=2,
        max_investigation_seconds=30.0,
    )

    with pytest.raises(InvestigationCircuitBreakerTripped) as exc_info:
        await agent.investigate(req)

    assert exc_info.value.reason == "STEP_LIMIT"
    assert exc_info.value.steps == 2
    assert "exceeded maximum step limit" in str(exc_info.value)

    # Verify audit event was logged with structured circuit breaker info
    events = await audit_service.list(limit=10)
    failed_events = [e for e in events if e.decision == "FAILED"]
    assert len(failed_events) >= 1
    assert "STEP_LIMIT" in failed_events[0].metadata_


@pytest.mark.asyncio
async def test_investigation_circuit_breaker_timeout(db: AsyncSession) -> None:
    """Agent must trip circuit breaker and terminate cleanly when exceeding wall-clock timeout."""
    company = await _create_test_company(db, name="Circuit Breaker Timeout Co")
    audit_service = AuditService(db, company.id)

    exc = ExceptionRecord(
        company_id=company.id,
        type=ExceptionType.PO_MISMATCH,
        severity=ExceptionSeverity.HIGH,
        financial_impact=Decimal("2500.00"),
        currency="USD",
        status=ExceptionStatus.OPEN,
    )
    db.add(exc)
    await db.flush()

    dossier = _create_test_dossier(exc, company.id)

    # Provider with 0.20s delay, exceeding 0.05s timeout
    slow_provider = MockLLMProvider(delay_seconds=0.20)
    agent = CFOInvestigationAgent(
        db, company.id, provider=slow_provider, audit_service=audit_service
    )

    # Request configured with 0.05s timeout
    req = InvestigationRequest(
        exception_id=exc.id,
        company_id=company.id,
        dossier=dossier,
        max_agent_steps=15,
        max_investigation_seconds=0.05,
    )

    with pytest.raises(InvestigationCircuitBreakerTripped) as exc_info:
        await agent.investigate(req)

    assert exc_info.value.reason == "TIMEOUT"
    assert "exceeded wall-clock timeout" in str(exc_info.value)

    # Verify audit event was logged
    events = await audit_service.list(limit=10)
    timeout_events = [e for e in events if e.decision == "TIMED_OUT"]
    assert len(timeout_events) >= 1
    assert "TIMEOUT" in timeout_events[0].metadata_


# ---------------------------------------------------------------------------
# 4. Human Correction / Outcome Recording Loop & Override Statistics
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_human_correction_recording_and_stats(db: AsyncSession) -> None:
    """Record human review actions, calculate override statistics, and flag tuning candidates."""
    company = await _create_test_company(db, name="Correction Loop Co")
    correction_svc = HumanCorrectionService(db, company.id)

    # Create parent exceptions in DB to satisfy foreign key constraint
    exc1 = ExceptionRecord(
        company_id=company.id,
        type=ExceptionType.PO_MISMATCH,
        severity=ExceptionSeverity.MEDIUM,
        financial_impact=Decimal("500.00"),
        currency="USD",
        status=ExceptionStatus.OPEN,
    )
    exc2 = ExceptionRecord(
        company_id=company.id,
        type=ExceptionType.DUPLICATE_INVOICE,
        severity=ExceptionSeverity.HIGH,
        financial_impact=Decimal("2500.00"),
        currency="USD",
        status=ExceptionStatus.OPEN,
    )
    db.add_all([exc1, exc2])
    await db.flush()

    # Record 6 corrections for PO_MISMATCH: 4 overrides, 2 agrees (override rate 4/6 = 66.7% > 20%)
    for i in range(6):
        is_override = i < 4
        await correction_svc.record_correction(
            exception_id=exc1.id,
            original_decision="AUTO_RESOLVE" if is_override else "STAGE",
            human_decision="REJECT" if is_override else "APPROVE",
            original_confidence=Decimal("0.95"),
            calibrated_confidence=Decimal("0.95"),
            exception_type=ExceptionType.PO_MISMATCH.value,
            reviewer_role=Role.CONTROLLER.value,
            actor=f"reviewer_{i}@vexacfo.ai",
            reason=f"Review test {i}",
        )

    # Record 2 corrections for DUPLICATE_INVOICE: 0 overrides
    for j in range(2):
        await correction_svc.record_correction(
            exception_id=exc2.id,
            original_decision="STAGE",
            human_decision="APPROVE",
            original_confidence=Decimal("0.75"),
            calibrated_confidence=Decimal("0.75"),
            exception_type=ExceptionType.DUPLICATE_INVOICE.value,
            reviewer_role=Role.CFO.value,
            actor="cfo@vexacfo.ai",
            reason="Confirmed duplicate",
        )

    stats = await correction_svc.get_override_statistics()

    # Total: 8 reviews, 4 overrides -> 50.0% override rate
    assert stats.overall.total_decisions == 8
    assert stats.overall.overrides == 4
    assert stats.overall.override_rate == 0.5

    # By exception type
    assert ExceptionType.PO_MISMATCH.value in stats.by_exception_type
    po_stats = stats.by_exception_type[ExceptionType.PO_MISMATCH.value]
    assert po_stats.total_decisions == 6
    assert po_stats.overrides == 4
    assert round(po_stats.override_rate, 2) == 0.67

    # Tuning candidate: PO_MISMATCH has >= 5 samples and > 20% override rate
    assert f"exception_type:{ExceptionType.PO_MISMATCH.value}" in stats.tuning_candidates
    assert f"exception_type:{ExceptionType.DUPLICATE_INVOICE.value}" not in stats.tuning_candidates

    # By confidence bucket
    assert "HIGH (>=0.95)" in stats.by_confidence_bucket
    assert stats.by_confidence_bucket["HIGH (>=0.95)"].total_decisions == 6
    assert stats.by_confidence_bucket["HIGH (>=0.95)"].overrides == 4


@pytest.mark.asyncio
async def test_action_service_creates_human_correction(db: AsyncSession) -> None:
    """ActionService approve/reject methods persist HumanCorrection records."""
    company = await _create_test_company(db, name="Action Service Correction Co")
    action_svc = ActionService(db, company.id)

    exc = ExceptionRecord(
        company_id=company.id,
        type=ExceptionType.PO_MISMATCH,
        severity=ExceptionSeverity.MEDIUM,
        financial_impact=Decimal("1200.00"),
        currency="USD",
        status=ExceptionStatus.OPEN,
        confidence=Decimal("0.85"),
        recommended_action="Review vendor pricing agreement",
    )
    db.add(exc)
    await db.flush()

    # Controller reviews and approves
    await action_svc.approve_exception(
        exception_id=exc.id,
        actor="controller-user-1",
        notes="Approved pricing exception after vendor discussion",
    )

    # Verify HumanCorrection record was created
    corrections = await action_svc.correction_service.list_corrections(exception_id=exc.id)
    assert len(corrections) == 1
    assert corrections[0].exception_id == exc.id
    assert corrections[0].human_decision == "APPROVED"


# ---------------------------------------------------------------------------
# 5. Per-Account Materiality Policy Support
# ---------------------------------------------------------------------------


def test_per_account_materiality_relative_threshold() -> None:
    """PolicyGateVerifier evaluates variance as % of balance and flags when exceeding relative materiality."""
    # Policy with 1.0% relative materiality threshold
    policy = ClosePolicy(
        max_auto_resolution_amount=Decimal("10000.00"),
        materiality_threshold=Decimal("5000.00"),
        materiality_pct_of_account_balance=Decimal("1.0"),
    )
    verifier = PolicyGateVerifier()

    exc = ExceptionRecord(
        id=uuid.uuid4(),
        company_id=uuid.uuid4(),
        type=ExceptionType.PO_MISMATCH,
        severity=ExceptionSeverity.MEDIUM,
        financial_impact=Decimal("150.00"),  # $150 variance
        currency="USD",
        status=ExceptionStatus.OPEN,
    )

    finding = InvestigationFinding(
        exception_id=exc.id,
        exception_type=exc.type,
        finding_status=FindingStatus.COMPLETED,
        root_cause_analysis=RootCauseAnalysis(
            primary_category="PO_MISMATCH",
            summary="Small variance",
            likely_cause="Freight fee difference",
            is_genuine_discrepancy=True,
            is_timing_or_operational=False,
        ),
        recommendation=InvestigationRecommendation(
            action=AutonomyAction.AUTO_RESOLVE,
            target_role=Role.CONTROLLER,
            recommended_action="Auto-adjust freight variance",
            should_block_close=False,
            should_escalate_to_cfo=False,
        ),
    )

    # Case A: Account balance is $10,000 -> $150 variance is 1.5% > 1.0% threshold!
    autonomy_a, violations_a = verifier.evaluate_policy(
        exception=exc,
        finding=finding,
        calibrated_confidence=Decimal("0.96"),
        policy=policy,
        calculation_valid=True,
        evidence_complete=True,
        account_balance=Decimal("10000.00"),
        account_code="6010",
    )
    assert autonomy_a == AutonomyLevel.STAGE
    assert any("exceeding relative materiality threshold" in v for v in violations_a)

    # Case B: Account balance is $50,000 -> $150 variance is 0.3% <= 1.0% threshold -> passes!
    autonomy_b, violations_b = verifier.evaluate_policy(
        exception=exc,
        finding=finding,
        calibrated_confidence=Decimal("0.96"),
        policy=policy,
        calculation_valid=True,
        evidence_complete=True,
        account_balance=Decimal("50000.00"),
        account_code="6010",
    )
    assert autonomy_b == AutonomyLevel.EXECUTE
    assert len(violations_b) == 0


def test_per_account_materiality_override_and_zero_balance_guards() -> None:
    """Test specific per-account absolute thresholds and clean fallback when account balance is 0 or negative."""
    # Account 1010 has a strict $200 threshold
    policy = ClosePolicy(
        max_auto_resolution_amount=Decimal("10000.00"),
        materiality_threshold=Decimal("5000.00"),
        materiality_pct_of_account_balance=Decimal("1.0"),
        account_materiality_thresholds={
            "1010": Decimal("200.00"),
        },
    )
    verifier = PolicyGateVerifier()

    exc = ExceptionRecord(
        id=uuid.uuid4(),
        company_id=uuid.uuid4(),
        type=ExceptionType.PO_MISMATCH,
        severity=ExceptionSeverity.MEDIUM,
        financial_impact=Decimal("350.00"),  # $350 variance exceeds the $200 per-account threshold
        currency="USD",
        status=ExceptionStatus.OPEN,
    )

    finding = InvestigationFinding(
        exception_id=exc.id,
        exception_type=exc.type,
        finding_status=FindingStatus.COMPLETED,
        root_cause_analysis=RootCauseAnalysis(
            primary_category="PO_MISMATCH",
            summary="Variance check",
            likely_cause="Rate adjustment",
            is_genuine_discrepancy=True,
            is_timing_or_operational=False,
        ),
        recommendation=InvestigationRecommendation(
            action=AutonomyAction.AUTO_RESOLVE,
            target_role=Role.CONTROLLER,
            recommended_action="Auto resolve",
            should_block_close=False,
            should_escalate_to_cfo=False,
        ),
    )

    # 1. Account 1010 has explicit threshold of $200 -> $350 exceeds it
    autonomy_strict, violations_strict = verifier.evaluate_policy(
        exception=exc,
        finding=finding,
        calibrated_confidence=Decimal("0.96"),
        policy=policy,
        calculation_valid=True,
        evidence_complete=True,
        account_balance=Decimal("100000.00"),
        account_code="1010",
    )
    assert autonomy_strict == AutonomyLevel.STAGE
    assert any(
        "exceeds max_auto_resolution_amount threshold of 200.00" in v for v in violations_strict
    )

    # 2. Account with 0 balance -> safely skips relative check without ZeroDivisionError
    autonomy_zero, violations_zero = verifier.evaluate_policy(
        exception=exc,
        finding=finding,
        calibrated_confidence=Decimal("0.96"),
        policy=policy,
        calculation_valid=True,
        evidence_complete=True,
        account_balance=Decimal("0.00"),
        account_code="2020",
    )
    # Passed because $350 is below global auto resolution amount $10,000 and global materiality $5,000
    assert autonomy_zero == AutonomyLevel.EXECUTE
    assert len(violations_zero) == 0


# ---------------------------------------------------------------------------
# 6. SOX Control-ID Tagging & Audit Event Filtering
# ---------------------------------------------------------------------------


def test_sox_control_mapping_deterministic() -> None:
    """Verify deterministic SOX control ID mapping for all major operational and financial categories."""
    assert map_to_control_id(exception_type=ExceptionType.PO_MISMATCH) == SoxControl.PROC_04
    assert map_to_control_id(exception_type=ExceptionType.DUPLICATE_PAYMENT) == SoxControl.AP_03
    assert map_to_control_id(exception_type=ExceptionType.DUPLICATE_INVOICE) == SoxControl.AP_03
    assert (
        map_to_control_id(exception_type=ExceptionType.VENDOR_BANK_CHANGE_ANOMALY)
        == SoxControl.AP_07
    )
    assert map_to_control_id(exception_type=ExceptionType.BANK_GL_MISMATCH) == SoxControl.BANK_01
    assert map_to_control_id(exception_type=ExceptionType.GL_MAPPING_ERROR) == SoxControl.GL_02
    assert map_to_control_id(exception_type=ExceptionType.DATA_INGESTION_GAP) == SoxControl.CLOSE_01
    assert map_to_control_id(exception_type=ExceptionType.AR_MISMATCH) == SoxControl.REV_01
    assert map_to_control_id(exception_type=ExceptionType.ACCRUAL_ANOMALY) == SoxControl.EXP_01
    assert map_to_control_id(task_type=CloseTaskType.BANK_RECONCILIATION) == SoxControl.BANK_01
    assert map_to_control_id(task_type=CloseTaskType.CLOSE_PACKAGE) == SoxControl.CLOSE_01
    assert map_to_control_id(event_type="CLOSE_RUN_FINALIZED") == SoxControl.CLOSE_01


@pytest.mark.asyncio
async def test_audit_service_sox_control_tagging_and_filter(db: AsyncSession) -> None:
    """AuditService tags events with control_id and supports filtering by control_id."""
    company = await _create_test_company(db, name="SOX Audit Co")
    service = AuditService(db, company_id=company.id)

    # 1. Event without explicit control_id -> auto-mapped to PROC-04 for PO_MISMATCH
    evt1 = await service.record(
        event_type=AuditEventType.EXCEPTION_DECISION,
        actor="system",
        actor_type="SYSTEM",
        decision="STAGE",
        reason="PO price variance detected",
        metadata_={"exception_type": ExceptionType.PO_MISMATCH.value},
    )
    assert evt1.control_id == SoxControl.PROC_04.value

    # 2. Event with explicit control_id -> preserved
    evt2 = await service.record(
        event_type=AuditEventType.EXCEPTION_DECISION,
        actor="cfo@vexacfo.ai",
        actor_type="HUMAN",
        decision="OVERRIDE",
        reason="CFO manual approval under AP-07",
        control_id=SoxControl.AP_07.value,
        metadata_={"exception_type": ExceptionType.VENDOR_BANK_CHANGE_ANOMALY.value},
    )
    assert evt2.control_id == SoxControl.AP_07.value

    # 3. Close task event with task_type -> auto-mapped to CLOSE-01
    evt3 = await service.record(
        event_type=AuditEventType.CLOSE_TASK_STATE_CHANGE,
        actor="system",
        actor_type="SYSTEM",
        decision="COMPLETE",
        reason="Close package generation complete",
        metadata_={"task_type": CloseTaskType.CLOSE_PACKAGE.value},
    )
    assert evt3.control_id == SoxControl.CLOSE_01.value

    # 4. Test filtering by control_id in AuditService.list
    proc04_events = await service.list(control_id=SoxControl.PROC_04.value)
    assert len(proc04_events) == 1
    assert proc04_events[0].id == evt1.id

    ap07_events = await service.list(control_id=SoxControl.AP_07.value)
    assert len(ap07_events) == 1
    assert ap07_events[0].id == evt2.id

    close01_events = await service.list(control_id=SoxControl.CLOSE_01.value)
    assert len(close01_events) == 1
    assert close01_events[0].id == evt3.id
