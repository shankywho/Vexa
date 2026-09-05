"""CFO Investigation Agent module (Phase 6).

Empowers Vexa to autonomously investigate financial exceptions like a CFO-office
analyst using bounded evidence dossiers from the Financial Evidence Graph,
producing evidence-backed findings and recommendations.
"""

from __future__ import annotations

from app.investigation.agent import CFOInvestigationAgent
from app.investigation.calibration import ConfidenceCalibrator
from app.investigation.citation_validator import CitationValidationResult, CitationValidator
from app.investigation.dossier_builder import EvidenceDossierBuilder
from app.investigation.evaluation import InvestigationEvaluationReport, InvestigationEvaluator
from app.investigation.llm_provider import (
    DeterministicInvestigationProvider,
    FallbackLLMProvider,
    LLMProvider,
    MockLLMProvider,
)
from app.investigation.prompt import (
    CFO_INVESTIGATOR_SYSTEM_PROMPT,
    PROMPT_VERSION_ID,
    format_investigation_user_prompt,
)
from app.investigation.service import InvestigationService
from app.investigation.types import (
    AutonomyAction,
    ClaimType,
    EvidenceDossier,
    Fact,
    FindingStatus,
    Inference,
    InvestigationFinding,
    InvestigationRecommendation,
    InvestigationRequest,
    RootCauseAnalysis,
)

__all__ = [
    "CFOInvestigationAgent",
    "ConfidenceCalibrator",
    "CitationValidator",
    "CitationValidationResult",
    "EvidenceDossierBuilder",
    "InvestigationEvaluationReport",
    "InvestigationEvaluator",
    "LLMProvider",
    "DeterministicInvestigationProvider",
    "FallbackLLMProvider",
    "MockLLMProvider",
    "PROMPT_VERSION_ID",
    "CFO_INVESTIGATOR_SYSTEM_PROMPT",
    "format_investigation_user_prompt",
    "InvestigationService",
    "AutonomyAction",
    "ClaimType",
    "EvidenceDossier",
    "Fact",
    "FindingStatus",
    "Inference",
    "InvestigationFinding",
    "InvestigationRecommendation",
    "InvestigationRequest",
    "RootCauseAnalysis",
]
