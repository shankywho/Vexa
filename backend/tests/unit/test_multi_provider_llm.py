"""Unit tests for ClosePilot multi-provider LLM support (Groq, Mistral, Gemini).

Validates:
1. LLMProvider interface and concrete adapters (GroqProvider, MistralProvider, GeminiProvider)
2. Native structured JSON mode and schema deserialization
3. Token usage and cost metadata capture per provider
4. Read-only zero arithmetic authority and citation validation preservation
5. Agent-to-provider routing and fallback mechanics (missing credentials, timeout, API failure)
6. Verification independence guarantee (startup ConfigurationError and runtime penalty)
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from pydantic import BaseModel

from app.config import (
    ConfigurationError,
    Settings,
    validate_routing_independence,
)
from app.db.models.procurement import Invoice, PurchaseOrder
from app.domain.enums import ExceptionSeverity, ExceptionType, Role
from app.investigation.llm_provider import (
    DeterministicInvestigationProvider,
    FallbackLLMProvider,
    GeminiProvider,
    GroqProvider,
    MistralProvider,
    MockLLMProvider,
    get_provider_for_agent,
)
from app.investigation.types import (
    AutonomyAction,
    EvidenceDossier,
    Fact,
    FindingStatus,
    InvestigationFinding,
    InvestigationRecommendation,
    InvestigationRequest,
    RootCauseAnalysis,
)
from app.verification.agent import VerificationAgent
from app.verification.types import VerificationRequest


class SampleResponseSchema(BaseModel):
    summary: str
    risk_score: Decimal
    recommended_flag: bool = True


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
        financial_impact=Decimal("12500.00"),
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
        timeout_seconds=5.0,
    )


# =====================================================================
# 1. GroqProvider Tests
# =====================================================================

@pytest.mark.asyncio
async def test_groq_provider_generate_structured(monkeypatch):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {"summary": "Groq analysis passed", "risk_score": "0.8500", "recommended_flag": True}
                    )
                }
            }
        ],
        "usage": {
            "prompt_tokens": 120,
            "completion_tokens": 45,
            "total_tokens": 165,
        },
    }
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post.return_value = mock_resp

    monkeypatch.setattr(httpx, "AsyncClient", lambda *args, **kwargs: mock_client)

    provider = GroqProvider(api_key="groq-test-key", model="llama-3.3-70b-versatile")
    result = await provider.generate_structured(
        prompt="Analyze variance",
        response_schema=SampleResponseSchema,
    )

    assert isinstance(result, SampleResponseSchema)
    assert result.summary == "Groq analysis passed"
    assert result.risk_score == Decimal("0.8500")

    # Verify request payload
    call_kwargs = mock_client.post.call_args
    assert "https://api.groq.com/openai/v1/chat/completions" in call_kwargs[0][0]
    payload = call_kwargs[1]["json"]
    assert payload["model"] == "llama-3.3-70b-versatile"
    assert payload["response_format"] == {"type": "json_object"}
    assert payload["temperature"] == 0.0
    assert call_kwargs[1]["headers"]["Authorization"] == "Bearer groq-test-key"

    # Verify metadata and cost
    meta = provider.last_call_metadata
    assert meta is not None
    assert meta.provider == "groq"
    assert meta.model == "llama-3.3-70b-versatile"
    assert meta.input_tokens == 120
    assert meta.output_tokens == 45
    assert meta.cost_usd > Decimal("0.000000")


# =====================================================================
# 2. MistralProvider Tests
# =====================================================================

@pytest.mark.asyncio
async def test_mistral_provider_generate_structured(monkeypatch):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {"summary": "Mistral analysis passed", "risk_score": "0.4200", "recommended_flag": False}
                    )
                }
            }
        ],
        "usage": {
            "prompt_tokens": 200,
            "completion_tokens": 80,
            "total_tokens": 280,
        },
    }
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post.return_value = mock_resp

    monkeypatch.setattr(httpx, "AsyncClient", lambda *args, **kwargs: mock_client)

    provider = MistralProvider(api_key="mistral-test-key", model="mistral-large-latest")
    result = await provider.generate_structured(
        prompt="Analyze variance",
        response_schema=SampleResponseSchema,
    )

    assert isinstance(result, SampleResponseSchema)
    assert result.summary == "Mistral analysis passed"
    assert result.risk_score == Decimal("0.4200")

    call_kwargs = mock_client.post.call_args
    assert "https://api.mistral.ai/v1/chat/completions" in call_kwargs[0][0]
    payload = call_kwargs[1]["json"]
    assert payload["model"] == "mistral-large-latest"
    assert payload["response_format"] == {"type": "json_object"}
    assert call_kwargs[1]["headers"]["Authorization"] == "Bearer mistral-test-key"

    meta = provider.last_call_metadata
    assert meta is not None
    assert meta.provider == "mistral"
    assert meta.input_tokens == 200
    assert meta.output_tokens == 80
    assert meta.cost_usd > Decimal("0.000000")


# =====================================================================
# 3. GeminiProvider Tests
# =====================================================================

@pytest.mark.asyncio
async def test_gemini_provider_generate_structured(monkeypatch):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps(
                                {"summary": "Gemini analysis passed", "risk_score": "0.1500", "recommended_flag": True}
                            )
                        }
                    ]
                }
            }
        ],
        "usageMetadata": {
            "promptTokenCount": 350,
            "candidatesTokenCount": 90,
            "totalTokenCount": 440,
        },
    }
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post.return_value = mock_resp

    monkeypatch.setattr(httpx, "AsyncClient", lambda *args, **kwargs: mock_client)

    provider = GeminiProvider(api_key="gemini-test-key", model="gemini-2.0-flash")
    result = await provider.generate_structured(
        prompt="Analyze variance",
        response_schema=SampleResponseSchema,
    )

    assert isinstance(result, SampleResponseSchema)
    assert result.summary == "Gemini analysis passed"
    assert result.risk_score == Decimal("0.1500")

    call_kwargs = mock_client.post.call_args
    assert "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent" in call_kwargs[0][0]
    payload = call_kwargs[1]["json"]
    assert payload["generationConfig"]["responseMimeType"] == "application/json"
    assert call_kwargs[1]["headers"]["x-goog-api-key"] == "gemini-test-key"

    meta = provider.last_call_metadata
    assert meta is not None
    assert meta.provider == "gemini"
    assert meta.input_tokens == 350
    assert meta.output_tokens == 90
    assert meta.cost_usd > Decimal("0.000000")


# =====================================================================
# 4. Zero Arithmetic Authority & Citation Validation across Providers
# =====================================================================

@pytest.mark.asyncio
async def test_provider_zero_arithmetic_authority(dummy_request, monkeypatch):
    p_id = list(dummy_request.dossier.valid_record_ids)[0]
    raw_llm_json = {
        "finding_status": "COMPLETED",
        "root_cause_analysis": {
            "primary_category": "PROCUREMENT_DISCREPANCY",
            "summary": "Mismatch",
            "likely_cause": "Unit price variance",
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
            "target_role": "CONTROLLER",
            "recommended_action": "Stage adjusting entry",
            "should_block_close": False,
            "should_escalate_to_cfo": False,
            "controller_review_checklist": [],
        },
        "raw_confidence": "0.9500",
        "financial_impact": "999999999.00",  # LLM attempted hallucinated impact
        "currency": "EUR",  # LLM attempted hallucinated currency
        "executive_summary": "Summary",
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": json.dumps(raw_llm_json)}}]
    }
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post.return_value = mock_resp

    monkeypatch.setattr(httpx, "AsyncClient", lambda *args, **kwargs: mock_client)

    provider = MistralProvider(api_key="test-key")
    finding = await provider.generate_finding(dummy_request)

    # Dossier ground truth must be strictly preserved
    assert dummy_request.dossier.financial_impact == Decimal("12500.00")
    assert dummy_request.dossier.currency == "USD"
    assert finding.exception_id == dummy_request.dossier.exception_id
    assert finding.exception_type == dummy_request.dossier.exception_type
    assert finding.provider_name == "mistral"


# =====================================================================
# 5. Routing and Fallback Mechanics
# =====================================================================

def test_get_provider_fallback_when_keys_missing(caplog):
    settings = Settings(
        groq_api_key=None,
        mistral_api_key=None,
        gemini_api_key=None,
    )
    with caplog.at_level(logging.WARNING):
        provider = get_provider_for_agent("investigation_agent", settings)

    assert isinstance(provider, DeterministicInvestigationProvider)
    assert provider.provider_name == "deterministic"
    assert "Primary provider 'mistral' has no credentials configured" in caplog.text


def test_get_provider_secondary_fallback_when_primary_missing(caplog):
    settings = Settings(
        mistral_api_key=None,
        groq_api_key="gsk-test",
    )
    with caplog.at_level(logging.WARNING):
        provider = get_provider_for_agent("investigation_agent", settings)

    # Secondary groq is wrapped in FallbackLLMProvider with deterministic fallback
    assert isinstance(provider, FallbackLLMProvider)
    assert provider.primary_provider.provider_name == "groq"
    assert provider.fallback_provider.provider_name == "deterministic"
    assert "Primary provider 'mistral' has no credentials configured for agent 'investigation_agent'. Falling back to 'groq'" in caplog.text


@pytest.mark.asyncio
async def test_fallback_llm_provider_runtime_failover(dummy_request):
    failing_primary = MockLLMProvider(raise_error=RuntimeError("Groq 503 Overloaded"))
    fallback = DeterministicInvestigationProvider()

    chained = FallbackLLMProvider(
        primary_provider=failing_primary,
        fallback_provider=fallback,
        agent_name="investigation_agent",
    )

    finding = await chained.generate_finding(dummy_request)
    assert finding is not None
    assert finding.exception_id == dummy_request.exception_id
    assert finding.provider_name == "deterministic"


# =====================================================================
# 6. Verification Independence Guarantee
# =====================================================================

def test_startup_independence_violation_in_production():
    routing_collision = {
        "investigation_agent": {"primary": "groq", "fallback": "gemini"},
        "verification_agent": {"primary": "groq", "fallback": "gemini"},
    }
    with pytest.raises(ConfigurationError) as exc_info:
        validate_routing_independence(routing_collision, environment="production", strict=True)
    assert "cannot share primary provider 'groq'" in str(exc_info.value)


@pytest.mark.asyncio
async def test_runtime_verification_independence_compromised(monkeypatch, caplog):
    session = MagicMock()
    session.flush = AsyncMock()
    comp_id = uuid.uuid4()
    exc_id = uuid.uuid4()

    mock_exc = MagicMock()
    mock_exc.id = exc_id
    mock_exc.close_run_id = uuid.uuid4()
    mock_exc.company_id = comp_id
    mock_exc.financial_impact = Decimal("0.00")
    mock_exc.created_at = None

    exc_repo_mock = AsyncMock()
    exc_repo_mock.get_by_id.return_value = mock_exc

    inv_id = uuid.uuid4()
    po_id = uuid.uuid4()
    inv = Invoice(
        id=inv_id,
        company_id=comp_id,
        vendor_id=uuid.uuid4(),
        invoice_number="INV-001",
        total=Decimal("0.00"),
        currency="USD",
    )
    po = PurchaseOrder(
        id=po_id,
        company_id=comp_id,
        vendor_id=uuid.uuid4(),
        po_number="PO-001",
        total=Decimal("0.00"),
        currency="USD",
    )

    finding = InvestigationFinding(
        exception_id=exc_id,
        exception_type=ExceptionType.PO_MISMATCH,
        finding_status=FindingStatus.COMPLETED,
        root_cause_analysis=RootCauseAnalysis(
            primary_category="PROCUREMENT_DISCREPANCY",
            summary="Variance",
            likely_cause="Variance detected",
            is_genuine_discrepancy=True,
            is_timing_or_operational=False,
        ),
        facts=[
            Fact(
                statement="Invoice record",
                evidence_id=f"invoice:{inv_id}",
                record_type="invoice",
                record_id=str(inv_id),
            ),
            Fact(
                statement="PO record",
                evidence_id=f"purchase_order:{po_id}",
                record_type="purchase_order",
                record_id=str(po_id),
            ),
        ],
        recommendation=InvestigationRecommendation(
            action=AutonomyAction.STAGE,
            target_role=Role.CONTROLLER,
            recommended_action="Review",
            should_block_close=False,
            should_escalate_to_cfo=False,
        ),
        raw_confidence=Decimal("0.9500"),
        calibrated_confidence=Decimal("0.9500"),
        provider_name="groq",  # Investigation agent used groq
    )

    dossier = EvidenceDossier(
        exception_id=exc_id,
        company_id=comp_id,
        exception_type=ExceptionType.PO_MISMATCH,
        severity=ExceptionSeverity.MEDIUM,
        financial_impact=Decimal("0.00"),
        currency="USD",
        invoices=[inv],
        purchase_orders=[po],
        valid_record_ids={str(inv_id), str(po_id)},
    )

    req = VerificationRequest(
        exception_id=exc_id,
        company_id=comp_id,
        finding=finding,
        dossier=dossier,
    )

    # Verification agent ALSO configured with groq
    verifier_provider = MockLLMProvider()
    verifier_provider.provider_name = "groq"

    verifier = VerificationAgent(session=session, company_id=comp_id, provider=verifier_provider)
    verifier.exc_repo = exc_repo_mock

    with caplog.at_level(logging.WARNING):
        res = await verifier.verify(req)

    assert res.independence_compromised is True
    # Penalty applied: calibrated confidence reduced from 0.9500 to 0.8500
    assert res.calibrated_confidence == Decimal("0.8500")
    assert "WARNING: Verification independence compromised — both investigation and verification used groq" in caplog.text


@pytest.mark.asyncio
async def test_runtime_verification_independence_preserved(monkeypatch):
    session = MagicMock()
    session.flush = AsyncMock()
    comp_id = uuid.uuid4()
    exc_id = uuid.uuid4()

    mock_exc = MagicMock()
    mock_exc.id = exc_id
    mock_exc.close_run_id = uuid.uuid4()
    mock_exc.company_id = comp_id
    mock_exc.financial_impact = Decimal("0.00")
    mock_exc.created_at = None

    exc_repo_mock = AsyncMock()
    exc_repo_mock.get_by_id.return_value = mock_exc

    inv_id = uuid.uuid4()
    po_id = uuid.uuid4()
    inv = Invoice(
        id=inv_id,
        company_id=comp_id,
        vendor_id=uuid.uuid4(),
        invoice_number="INV-002",
        total=Decimal("0.00"),
        currency="USD",
    )
    po = PurchaseOrder(
        id=po_id,
        company_id=comp_id,
        vendor_id=uuid.uuid4(),
        po_number="PO-002",
        total=Decimal("0.00"),
        currency="USD",
    )

    finding = InvestigationFinding(
        exception_id=exc_id,
        exception_type=ExceptionType.PO_MISMATCH,
        finding_status=FindingStatus.COMPLETED,
        root_cause_analysis=RootCauseAnalysis(
            primary_category="PROCUREMENT_DISCREPANCY",
            summary="Variance",
            likely_cause="Variance detected",
            is_genuine_discrepancy=True,
            is_timing_or_operational=False,
        ),
        facts=[
            Fact(
                statement="Invoice record",
                evidence_id=f"invoice:{inv_id}",
                record_type="invoice",
                record_id=str(inv_id),
            ),
            Fact(
                statement="PO record",
                evidence_id=f"purchase_order:{po_id}",
                record_type="purchase_order",
                record_id=str(po_id),
            ),
        ],
        recommendation=InvestigationRecommendation(
            action=AutonomyAction.STAGE,
            target_role=Role.CONTROLLER,
            recommended_action="Review",
            should_block_close=False,
            should_escalate_to_cfo=False,
        ),
        raw_confidence=Decimal("0.9500"),
        calibrated_confidence=Decimal("0.9500"),
        provider_name="mistral",  # Investigation agent used mistral
    )

    dossier = EvidenceDossier(
        exception_id=exc_id,
        company_id=comp_id,
        exception_type=ExceptionType.PO_MISMATCH,
        severity=ExceptionSeverity.MEDIUM,
        financial_impact=Decimal("0.00"),
        currency="USD",
        invoices=[inv],
        purchase_orders=[po],
        valid_record_ids={str(inv_id), str(po_id)},
    )

    req = VerificationRequest(
        exception_id=exc_id,
        company_id=comp_id,
        finding=finding,
        dossier=dossier,
    )

    # Verification agent configured with groq (distinct provider!)
    verifier_provider = MockLLMProvider()
    verifier_provider.provider_name = "groq"

    verifier = VerificationAgent(session=session, company_id=comp_id, provider=verifier_provider)
    verifier.exc_repo = exc_repo_mock

    res = await verifier.verify(req)
    assert res.independence_compromised is False
    assert res.calibrated_confidence == Decimal("0.9500")


# =====================================================================
# 7. Wire Credentials Test Status
# =====================================================================

def test_wire_credentials_status():
    keys = {
        "groq": os.environ.get("GROQ_API_KEY") or os.environ.get("VEXA_GROQ_API_KEY"),
        "mistral": os.environ.get("MISTRAL_API_KEY") or os.environ.get("VEXA_MISTRAL_API_KEY"),
        "gemini": os.environ.get("GEMINI_API_KEY") or os.environ.get("VEXA_GEMINI_API_KEY"),
    }
    for provider_name, key in keys.items():
        if not key:
            print(f"{provider_name.upper()}: NOT TESTED — missing credentials")
        else:
            print(f"{provider_name.upper()}: CREDENTIAL PRESENT")
