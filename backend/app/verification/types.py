"""Type definitions for the Independent Verification Agent (spec section 10/12/39)."""

from __future__ import annotations

import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.close_workflow.types import ClosePolicy
from app.domain.enums import AutonomyLevel
from app.investigation.types import EvidenceDossier, InvestigationFinding


class VerificationRequest(BaseModel):
    """Input payload for independent verification of an investigation finding."""

    model_config = ConfigDict(frozen=True)

    exception_id: uuid.UUID
    company_id: uuid.UUID
    close_run_id: uuid.UUID | None = None
    finding: InvestigationFinding
    dossier: EvidenceDossier
    policy: ClosePolicy = Field(default_factory=ClosePolicy)


class VerificationResult(BaseModel):
    """Structured output of independent verification (spec section 10).

    Matches the canonical spec schema:
    {
      "verified": true,
      "confidence": 0.96,
      "calibrated_confidence": 0.91,
      "missing_evidence": [],
      "calculation_errors": [],
      "policy_violations": [],
      "recommended_autonomy": "AUTO_RESOLVE"
    }
    """

    model_config = ConfigDict(frozen=True)

    exception_id: uuid.UUID
    verified: bool
    confidence: Decimal = Field(default=Decimal("1.0000"))
    calibrated_confidence: Decimal = Field(default=Decimal("1.0000"))
    missing_evidence: list[str] = Field(default_factory=list)
    calculation_errors: list[str] = Field(default_factory=list)
    policy_violations: list[str] = Field(default_factory=list)
    recommended_autonomy: AutonomyLevel
    reproduction_valid: bool = True
    evidence_complete: bool = True
    calculation_valid: bool = True
    recalculated_impact: Decimal | None = None
    variance_diff: Decimal = Field(default=Decimal("0.00"))
    notes: str = ""
