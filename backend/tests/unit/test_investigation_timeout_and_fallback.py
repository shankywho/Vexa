"""Unit tests for investigation provider timeout and automatic fallback (spec section 5.2)."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

from app.domain.enums import ExceptionSeverity, ExceptionType
from app.investigation.llm_provider import (
    DeterministicInvestigationProvider,
    FallbackLLMProvider,
    MockLLMProvider,
)
from app.investigation.types import (
    EvidenceDossier,
    InvestigationRequest,
)


@pytest.fixture
def dummy_request() -> InvestigationRequest:
    exc_id = uuid.uuid4()
    comp_id = uuid.uuid4()
    p_id = str(uuid.uuid4())
    dossier = EvidenceDossier(
        exception_id=exc_id,
        company_id=comp_id,
        exception_type=ExceptionType.PO_MISMATCH,
        severity=ExceptionSeverity.HIGH,
        financial_impact=Decimal("5000.00"),
        currency="USD",
        valid_record_ids={p_id, str(exc_id)},
        valid_evidence_ids={f"invoice:{p_id}", f"exception:{exc_id}"},
        primary_record={
            "node_id": f"invoice:{p_id}",
            "node_type": "invoice",
            "record_id": p_id,
            "label": "Invoice test",
            "properties": {},
        },
        ranked_nodes=[{"node_id": f"invoice:{p_id}", "score": 1.0, "label": "Inv"}],
    )
    return InvestigationRequest(
        exception_id=exc_id,
        company_id=comp_id,
        dossier=dossier,
        timeout_seconds=0.1,  # tight timeout
    )


@pytest.mark.asyncio
async def test_fallback_provider_on_timeout(dummy_request: InvestigationRequest):
    # Primary provider sleeps for 0.5s, exceeding 0.1s timeout
    slow_primary = MockLLMProvider(delay_seconds=0.5)
    fallback = DeterministicInvestigationProvider()

    provider = FallbackLLMProvider(
        primary_provider=slow_primary,
        fallback_provider=fallback,
    )

    # Should not raise TimeoutError; falls back seamlessly to deterministic provider
    finding = await provider.generate_finding(dummy_request)
    assert finding is not None
    assert finding.exception_id == dummy_request.exception_id
    assert finding.recommendation is not None
    assert finding.root_cause_analysis is not None


@pytest.mark.asyncio
async def test_fallback_provider_on_runtime_error(dummy_request: InvestigationRequest):
    # Primary provider raises network/API error
    failing_primary = MockLLMProvider(raise_error=RuntimeError("LLM API endpoint unavailable"))
    fallback = DeterministicInvestigationProvider()

    provider = FallbackLLMProvider(
        primary_provider=failing_primary,
        fallback_provider=fallback,
    )

    finding = await provider.generate_finding(dummy_request)
    assert finding is not None
    assert finding.exception_id == dummy_request.exception_id
    assert finding.recommendation is not None


@pytest.mark.asyncio
async def test_mock_llm_provider_injects_hallucination(dummy_request: InvestigationRequest):
    mock = MockLLMProvider(inject_hallucination=True)
    finding = await mock.generate_finding(dummy_request)

    # Verify hallucinated record was appended
    fake_facts = [f for f in finding.facts if "fake-hallucinated-id" in f.record_id]
    assert len(fake_facts) == 1
