"""Citation validator for CFO Investigation Agent claims (spec sections 10, 11, 21-25).

Guarantees zero hallucinated citations:
Every FACT and INFERENCE must cite record IDs or evidence IDs that strictly
exist within the bounded EvidenceDossier. Any ungrounded or fabricated citation
is flagged and penalizes the finding.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.investigation.types import EvidenceDossier, InvestigationFinding


@dataclass(frozen=True)
class CitationValidationResult:
    """Outcome of validating all citations in an investigation finding."""

    is_valid: bool
    total_citations: int
    valid_citations: int
    hallucinated_citations: list[str] = field(default_factory=list)
    unsupported_claims: list[str] = field(default_factory=list)
    citation_accuracy: float = 1.0


class CitationValidator:
    """Validates citations in findings against the bounded EvidenceDossier."""

    UUID_REGEX = re.compile(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        re.IGNORECASE,
    )

    def validate_citation(self, citation: str, dossier: EvidenceDossier) -> bool:
        """Verify whether a cited identifier exists in the bounded dossier."""
        if not citation:
            return False
        clean = citation.strip()
        if dossier.is_valid_citation(clean):
            return True

        # Check if citation contains a UUID that exists in dossier
        uuids = self.UUID_REGEX.findall(clean)
        for u in uuids:
            if dossier.is_valid_citation(u.lower()):
                return True

        # Check prefixed forms e.g. "invoice:<uuid>" -> check "<uuid>"
        if ":" in clean:
            prefix, part = clean.split(":", 1)
            if dossier.is_valid_citation(part):
                return True

        return False

    def validate_finding(
        self, finding: InvestigationFinding, dossier: EvidenceDossier
    ) -> CitationValidationResult:
        """Validate all facts, inferences, and textual citations in a finding."""
        all_citations: list[str] = []
        hallucinations: list[str] = []
        unsupported: list[str] = []

        # 1. Validate Facts
        for idx, fact in enumerate(finding.facts):
            fact_citations = []
            if fact.evidence_id:
                fact_citations.append(fact.evidence_id)
            if fact.record_id:
                fact_citations.append(fact.record_id)

            if not fact_citations:
                unsupported.append(f"Fact #{idx + 1} '{fact.statement}' lacks citation")
                continue

            for cit in fact_citations:
                all_citations.append(cit)
                if not self.validate_citation(cit, dossier):
                    hallucinations.append(cit)
                    unsupported.append(f"Fact #{idx + 1} cites unknown identifier '{cit}'")

        # 2. Validate Inferences
        for idx, inf in enumerate(finding.inferences):
            if not inf.supported_by_evidence_ids:
                unsupported.append(
                    f"Inference #{idx + 1} '{inf.statement}' has no supporting evidence IDs"
                )
                continue

            for cit in inf.supported_by_evidence_ids:
                all_citations.append(cit)
                if not self.validate_citation(cit, dossier):
                    hallucinations.append(cit)
                    unsupported.append(f"Inference #{idx + 1} cites unknown identifier '{cit}'")

        total = len(all_citations)
        invalid_count = len(hallucinations)
        valid_count = total - invalid_count
        accuracy = (valid_count / total) if total > 0 else (1.0 if not unsupported else 0.0)
        is_valid = (invalid_count == 0) and (len(unsupported) == 0)

        return CitationValidationResult(
            is_valid=is_valid,
            total_citations=total,
            valid_citations=valid_count,
            hallucinated_citations=sorted(list(set(hallucinations))),
            unsupported_claims=unsupported,
            citation_accuracy=accuracy,
        )
