"""Independent Verification Agent module (Phase 7).

Verifies investigation findings, reproduces calculations independently,
enforces policy gates, and validates confidence calibration.
"""

from __future__ import annotations

from app.verification.agent import VERIFIER_PROMPT_VERSION_ID, VerificationAgent
from app.verification.engine import (
    EvidenceCompletenessVerifier,
    IndependentCalculationVerifier,
    PolicyGateVerifier,
)
from app.verification.service import VerificationService
from app.verification.types import VerificationRequest, VerificationResult

__all__ = [
    "VerificationAgent",
    "VerificationService",
    "VerificationRequest",
    "VerificationResult",
    "IndependentCalculationVerifier",
    "EvidenceCompletenessVerifier",
    "PolicyGateVerifier",
    "VERIFIER_PROMPT_VERSION_ID",
]
