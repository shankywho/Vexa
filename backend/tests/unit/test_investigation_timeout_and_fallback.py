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


@pytest.mark.asyncio
async def test_real_llm_provider_structured_output_and_zero_arithmetic_authority(
    dummy_request: InvestigationRequest, monkeypatch
):
    import json
    from unittest.mock import AsyncMock, MagicMock

    import httpx

    from app.investigation.llm_provider import RealLLMInvestigationProvider

    p_id = list(dummy_request.dossier.valid_record_ids)[0]
    canned_llm_json = {
        "exception_id": str(dummy_request.exception_id),
        "finding_status": "COMPLETED",
        "primary_root_cause_category": "PROCUREMENT_DISCREPANCY",
        "root_cause_analysis": {
            "primary_category": "PROCUREMENT_DISCREPANCY",
            "summary": "PO and invoice mismatch",
            "likely_cause": "Unit price mismatch",
            "is_genuine_discrepancy": True,
            "is_timing_or_operational": False,
        },
        "facts": [
            {
                "statement": "Invoice verified",
                "evidence_id": f"invoice:{p_id}",
                "record_type": "invoice",
                "record_id": p_id,
            }
        ],
        "inferences": [],
        "uncertainties": [],
        "missing_evidence": [],
        "recommendation": {
            "action": "STAGE",
            "target_role": "ACCOUNTANT",
            "recommended_action": "Stage adjusting entry",
            "should_block_close": False,
            "should_escalate_to_cfo": False,
            "controller_review_checklist": [],
        },
        "raw_confidence": "0.9500",
        "financial_impact": "99999999.00",  # Attempted arithmetic hallucination
        "currency": "EUR",
        "executive_summary": "Summary",
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": json.dumps(canned_llm_json)}}]
    }
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post.return_value = mock_resp

    monkeypatch.setattr(httpx, "AsyncClient", lambda *args, **kwargs: mock_client)

    real_provider = RealLLMInvestigationProvider(api_key="test-key", model="gpt-4o")
    finding = await real_provider.generate_finding(dummy_request)

    # Zero arithmetic authority: LLM does not set financial impact on finding; dossier retains source of truth
    assert dummy_request.dossier.financial_impact == Decimal("5000.00")
    assert dummy_request.dossier.currency == "USD"
    assert finding.finding_status.value == "COMPLETED"
    assert finding.exception_type == dummy_request.dossier.exception_type
    assert finding.exception_id == dummy_request.exception_id


@pytest.mark.asyncio
async def test_real_llm_provider_citation_hallucination_triggers_fallback(
    dummy_request: InvestigationRequest, monkeypatch
):
    import json
    from unittest.mock import AsyncMock, MagicMock

    import httpx

    from app.investigation.llm_provider import FallbackLLMProvider, RealLLMInvestigationProvider

    canned_llm_hallu = {
        "exception_id": str(dummy_request.exception_id),
        "finding_status": "COMPLETED",
        "primary_root_cause_category": "PROCUREMENT_DISCREPANCY",
        "root_cause_analysis": {
            "primary_category": "PROCUREMENT_DISCREPANCY",
            "summary": "Summary",
            "likely_cause": "Cause",
            "is_genuine_discrepancy": True,
            "is_timing_or_operational": False,
        },
        "facts": [
            {
                "statement": "Hallucinated invoice citation",
                "evidence_id": "invoice:00000000-0000-0000-0000-999999999999",
                "record_type": "invoice",
                "record_id": "00000000-0000-0000-0000-999999999999",
            }
        ],
        "inferences": [],
        "uncertainties": [],
        "missing_evidence": [],
        "recommendation": {
            "action": "STAGE",
            "target_role": "ACCOUNTANT",
            "recommended_action": "Stage adjusting entry",
            "should_block_close": False,
            "should_escalate_to_cfo": False,
            "controller_review_checklist": [],
        },
        "raw_confidence": "0.9500",
        "financial_impact": "5000.00",
        "currency": "USD",
        "executive_summary": "Summary",
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": json.dumps(canned_llm_hallu)}}]
    }
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post.return_value = mock_resp

    monkeypatch.setattr(httpx, "AsyncClient", lambda *args, **kwargs: mock_client)

    real_provider = RealLLMInvestigationProvider(api_key="test-key", model="gpt-4o")
    fallback_wrapper = FallbackLLMProvider(primary_provider=real_provider)

    # Hallucinated citation should cause primary provider to fail and safely fall back
    finding = await fallback_wrapper.generate_finding(dummy_request)
    assert finding is not None
    assert finding.exception_id == dummy_request.exception_id
    # Ensure finding came from deterministic fallback (no hallucinated citations)
    fake_facts = [f for f in finding.facts if "999999999999" in f.record_id]
    assert len(fake_facts) == 0
