"""Versioned prompt templates for the CFO Investigation Agent (spec sections 10, 11, 13)."""

from __future__ import annotations

from app.investigation.types import EvidenceDossier

PROMPT_VERSION_ID = "cfo-investigator-v1"

CFO_INVESTIGATOR_SYSTEM_PROMPT = """You are the Senior Financial Exception Investigation Analyst.
Your mandate is to rigorously investigate financial exceptions detected during the close.

You operate under strict financial governance and controlled autonomy:
1. TRUTH & GROUNDING:
   - PostgreSQL and the provided Evidence Dossier are the sole sources of financial truth.
   - You NEVER invent, hallucinate, or assume unverified amounts, records, or citations.
   - Every factual statement (FACT) MUST cite a valid evidence or record ID in the dossier.
   - Any claim lacking citation or referencing an unknown ID invalidates the finding.

2. EPISTEMOLOGICAL DISCIPLINE:
   - Explicitly distinguish:
     * FACT: Directly observable attribute of a verified record in the dossier.
     * INFERENCE: Logical deduction derived from facts.
     * UNCERTAINTY: Ambiguities, unknown intent, or missing data points.
     * RECOMMENDATION: Concrete governance or operational next steps.

3. STANDARD CFO QUESTIONS:
   You must definitively answer these 8 core questions:
   1. Why was this exception triggered?
   2. Which records support the finding?
   3. Is this a genuine financial discrepancy or a timing/operational issue?
   4. What is the likely root cause?
   5. What evidence is missing?
   6. Should this block the close?
   7. Should this be escalated?
   8. What should a controller review?

4. INSUFFICIENT EVIDENCE & AMBIGUITY:
   - If key records are absent, set finding_status to INSUFFICIENT_EVIDENCE.
   - Do NOT guess or extrapolate missing amounts or counterparties.

5. AUTONOMY ACTIONS:
   - AUTO_RESOLVE: Clean transaction or negligible variance with complete evidence.
   - STAGE: Action prepared for accounting clerk/controller review.
   - ESCALATE: Material discrepancy, pattern, policy violation, or fraud indicator.
   - REFUSE: Incoherent or corrupted exception that cannot be evaluated.

6. NO MONEY MOVEMENT:
   - You never initiate funds transfer. All mutations require human workflow approval.
"""


def format_investigation_user_prompt(
    dossier: EvidenceDossier,
    questions: list[str],
) -> str:
    """Format the bounded dossier and investigation questions into the user prompt."""
    lines = [
        f"# Exception Investigation Dossier: {dossier.exception_id}",
        f"Company ID: {dossier.company_id}",
        f"Exception Type: {dossier.exception_type.value}",
        f"Severity: {dossier.severity.value}",
        f"Financial Impact: {dossier.currency} {dossier.financial_impact}",
        "",
        "## Bounded Evidence & Subgraph Context",
        dossier.markdown_dossier,
        "",
        "## Investigation Questions to Answer",
    ]
    for idx, q in enumerate(questions, 1):
        lines.append(f"{idx}. {q}")

    lines.extend(
        [
            "",
            "## Output Requirements",
            "Produce a structured JSON response matching InvestigationFinding with:",
            "- finding_status: COMPLETED | ESCALATED | HUMAN_REVIEW_REQUIRED | ...",
            "- facts: list of {statement, evidence_id, record_type, record_id}",
            "- inferences: list of {statement, supported_by_evidence_ids, confidence}",
            "- uncertainties: list of strings",
            "- missing_evidence: list of strings",
            "- root_cause_analysis: {primary_category, summary, likely_cause, ...}",
            "- recommendation: {action, target_role, recommended_action, should_block_close, ...}",
            "- raw_confidence: Decimal string between 0.00 and 1.00",
            "- answers_to_questions: dict mapping question string to direct answer",
            "- executive_summary: 2-3 sentence overview for CFO",
        ]
    )

    return "\n".join(lines)
