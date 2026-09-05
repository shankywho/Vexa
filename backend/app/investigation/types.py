"""Typed contracts for the CFO Investigation Agent (spec sections 10, 11, 13, 21-25).

Explicitly distinguishes:
- FACT: Directly observable from verified evidence records.
- INFERENCE: Logical deduction derived from facts.
- UNCERTAINTY: Ambiguities, unknown intent, or missing data points.
- RECOMMENDATION: Concrete governance or operational next steps.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import (
    ExceptionSeverity,
    ExceptionType,
    Role,
)


class ClaimType(StrEnum):
    """Epistemological classification of investigation claims."""

    FACT = "FACT"
    INFERENCE = "INFERENCE"
    UNCERTAINTY = "UNCERTAINTY"
    RECOMMENDATION = "RECOMMENDATION"


class FindingStatus(StrEnum):
    """High-level outcome status of the exception investigation."""

    COMPLETED = "COMPLETED"
    ESCALATED = "ESCALATED"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    AMBIGUOUS = "AMBIGUOUS"
    FAILED = "FAILED"


class AutonomyAction(StrEnum):
    """Recommended autonomy action according to spec section 11."""

    AUTO_RESOLVE = "AUTO_RESOLVE"
    STAGE = "STAGE"
    ESCALATE = "ESCALATE"
    REFUSE = "REFUSE"


class Fact(BaseModel):
    """A factual claim directly grounded in a verified evidence record."""

    model_config = ConfigDict(frozen=True)

    statement: str
    evidence_id: str
    record_type: str
    record_id: str
    is_verified: bool = True


class Inference(BaseModel):
    """A logical deduction derived from one or more verified facts."""

    model_config = ConfigDict(frozen=True)

    statement: str
    supported_by_evidence_ids: list[str] = Field(default_factory=list)
    confidence: Decimal = Field(default=Decimal("1.0000"))


class RootCauseAnalysis(BaseModel):
    """Structured root-cause evaluation for an exception."""

    model_config = ConfigDict(frozen=True)

    primary_category: str
    summary: str
    likely_cause: str
    is_genuine_discrepancy: bool
    is_timing_or_operational: bool


class InvestigationRecommendation(BaseModel):
    """CFO-office recommended action and controller governance checklist."""

    model_config = ConfigDict(frozen=True)

    action: AutonomyAction
    target_role: Role
    recommended_action: str
    should_block_close: bool
    should_escalate_to_cfo: bool
    controller_review_checklist: list[str] = Field(default_factory=list)


class EvidenceDossier(BaseModel):
    """Bounded financial evidence dossier supplied to the Investigation Agent."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    exception_id: uuid.UUID
    company_id: uuid.UUID
    close_run_id: uuid.UUID | None = None
    exception_type: ExceptionType
    severity: ExceptionSeverity
    financial_impact: Decimal
    currency: str = "USD"
    valid_record_ids: set[str] = Field(default_factory=set)
    valid_evidence_ids: set[str] = Field(default_factory=set)
    primary_record: dict[str, Any] = Field(default_factory=dict)
    related_records: list[dict[str, Any]] = Field(default_factory=list)
    ranked_nodes: list[dict[str, Any]] = Field(default_factory=list)
    graph_edges: list[dict[str, Any]] = Field(default_factory=list)
    markdown_dossier: str = ""
    invoices: list[Any] = Field(default_factory=list)
    purchase_orders: list[Any] = Field(default_factory=list)
    goods_receipts: list[Any] = Field(default_factory=list)
    payments: list[Any] = Field(default_factory=list)
    bank_transactions: list[Any] = Field(default_factory=list)
    journal_entries: list[Any] = Field(default_factory=list)

    def is_valid_citation(self, citation_id: str) -> bool:
        """Verify whether a cited record or evidence ID exists in the bounded dossier."""
        clean_id = str(citation_id).strip()
        return clean_id in self.valid_record_ids or clean_id in self.valid_evidence_ids


class InvestigationRequest(BaseModel):
    """Typed request initiating an exception investigation."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    exception_id: uuid.UUID
    company_id: uuid.UUID
    close_run_id: uuid.UUID | None = None
    dossier: EvidenceDossier
    policy: Any = None
    questions: list[str] = Field(
        default_factory=lambda: [
            "Why was this exception triggered?",
            "Which records support the finding?",
            "Is this a genuine financial discrepancy or a timing/operational issue?",
            "What is the likely root cause?",
            "What evidence is missing?",
            "Should this block the close?",
            "Should this be escalated?",
            "What should a controller review?",
        ]
    )
    prompt_version_id: str = "cfo-investigator-v1"
    model: str = "vexa-cfo-analyst-v1"
    timeout_seconds: float = 10.0
    max_retries: int = 2


class InvestigationFinding(BaseModel):
    """Structured, evidence-backed finding produced by the Investigation Agent."""

    exception_id: uuid.UUID
    exception_type: ExceptionType
    finding_status: FindingStatus
    facts: list[Fact] = Field(default_factory=list)
    inferences: list[Inference] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    root_cause_analysis: RootCauseAnalysis
    recommendation: InvestigationRecommendation
    raw_confidence: Decimal = Field(default=Decimal("0.9500"))
    calibrated_confidence: Decimal = Field(default=Decimal("0.9500"))
    all_citations_valid: bool = True
    hallucinated_citations: list[str] = Field(default_factory=list)
    has_unsupported_claims: bool = False
    answers_to_questions: dict[str, str] = Field(default_factory=dict)
    executive_summary: str = ""
    markdown_dossier: str = ""
    agent_run_id: uuid.UUID | None = None

    @property
    def cited_record_ids(self) -> list[str]:
        """List of all unique record IDs cited in facts."""
        seen: set[str] = set()
        res: list[str] = []
        for f in self.facts:
            if f.record_id and f.record_id not in seen:
                seen.add(f.record_id)
                res.append(f.record_id)
        return res

    def to_dict(self) -> dict[str, Any]:
        """Convert finding to JSON-serializable dictionary."""
        return {
            "exception_id": str(self.exception_id),
            "exception_type": self.exception_type.value,
            "finding_status": self.finding_status.value,
            "facts": [f.model_dump() for f in self.facts],
            "inferences": [
                {
                    "statement": inf.statement,
                    "supported_by_evidence_ids": inf.supported_by_evidence_ids,
                    "confidence": str(inf.confidence),
                }
                for inf in self.inferences
            ],
            "uncertainties": self.uncertainties,
            "missing_evidence": self.missing_evidence,
            "root_cause_analysis": self.root_cause_analysis.model_dump(),
            "recommendation": {
                "action": self.recommendation.action.value,
                "target_role": self.recommendation.target_role.value,
                "recommended_action": self.recommendation.recommended_action,
                "should_block_close": self.recommendation.should_block_close,
                "should_escalate_to_cfo": self.recommendation.should_escalate_to_cfo,
                "controller_review_checklist": self.recommendation.controller_review_checklist,
            },
            "raw_confidence": str(self.raw_confidence),
            "calibrated_confidence": str(self.calibrated_confidence),
            "all_citations_valid": self.all_citations_valid,
            "hallucinated_citations": self.hallucinated_citations,
            "has_unsupported_claims": self.has_unsupported_claims,
            "answers_to_questions": self.answers_to_questions,
            "executive_summary": self.executive_summary,
            "markdown_dossier": self.markdown_dossier,
            "agent_run_id": str(self.agent_run_id) if self.agent_run_id else None,
        }
