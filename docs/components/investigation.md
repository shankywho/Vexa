# Investigation Subsystem Deep Dive

The Investigation subsystem provides autonomous forensic reasoning over financial exceptions. It constructs bounded evidence dossiers, generates root-cause hypotheses, validates factual citations, and calibrates confidence scores.

---

## 1. Package Structure

Located at [`backend/app/investigation/`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-7/backend/app/investigation/):

```
app/investigation/
├── __init__.py
├── agent.py               # CFOInvestigationAgent (Core investigator & circuit breakers)
├── calibration.py         # ConfidenceCalibrator (Empirical accuracy bucket mapper)
├── citation_validator.py  # CitationValidator (Hallucination detector & citation verifier)
├── dossier_builder.py     # EvidenceDossierBuilder (Extracts bounded context from graph)
├── evaluation.py          # InvestigationEvaluator (Compares findings with ground truth)
├── llm_provider.py        # LLMProvider abstraction (OpenAI, Gemini, Anthropic, Deterministic)
├── prompt.py              # Versioned system prompts & JSON output schemas
├── service.py             # InvestigationService (Application entry point)
└── types.py               # Pydantic schemas (InvestigationRequest, Finding, Dossier)
```

---

## 2. Dossier Construction: `EvidenceDossierBuilder`

To prevent agents from hallucinating nonexistent records or searching unbounded database state, [`EvidenceDossierBuilder`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-7/backend/app/investigation/dossier_builder.py) builds a frozen `EvidenceDossier`:
1. **Primary Entity Extraction:** Retrieves the record directly tied to the exception (`Invoice`, `Payment`, `BankTransaction`, etc.).
2. **Graph Traversal:** Extracts 2-hop to 4-hop neighboring nodes and directed edges from [`FinancialEvidenceGraph`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-7/backend/app/evidence_graph/graph.py).
3. **Whitelist Formulation:** Builds two immutable sets:
   - `valid_record_ids`: Set of all raw database UUIDs present in the subgraph.
   - `valid_evidence_ids`: Set of all typed node IDs (e.g. `invoice:44a1-b8...`).
4. **Markdown Serialization:** Generates a structured markdown digest representing the financial state for LLM ingestion.

---

## 3. The Investigation Finding Contract

The agent generates a structured [`InvestigationFinding`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-7/backend/app/investigation/types.py#L76):

```json
{
  "finding_id": "8f56e6d1-12c8-4796-98ec-923f03b2241e",
  "exception_id": "b182ef0a-3132-482a-a9fb-10b2d6da6194",
  "finding_status": "CONFIRMED_ANOMALY",
  "executive_summary": "Invoice INV-042 totals 1,000 units, but warehouse Goods Receipt GR-088 confirms delivery of only 760 units.",
  "root_cause_analysis": {
    "category": "VENDOR_OVERBILLING",
    "likely_cause": "Vendor billed for full purchase order quantity prior to shipment delivery.",
    "contributing_factors": ["Warehouse partial fulfillment", "Automated EDI bill ingestion"]
  },
  "facts": [
    {
      "statement": "Purchase order PO-441 authorized 800 units @ $1,600.",
      "record_id": "po:4410",
      "evidence_id": "purchase_order:4410"
    },
    {
      "statement": "Goods receipt GR-088 confirms receipt of 760 units on 2026-08-28.",
      "record_id": "gr:0880",
      "evidence_id": "goods_receipt:0880"
    }
  ],
  "inferences": [
    {
      "statement": "Billed excess represents 240 unreceived units valued at $384,000.",
      "supported_by_evidence_ids": ["invoice:0420", "goods_receipt:0880"]
    }
  ],
  "recommendation": {
    "action": "STAGE",
    "should_escalate_to_cfo": true,
    "rationale": "Discrepancy of $384,000 exceeds materiality cap ($50,000); draft debit memo staged for Controller."
  },
  "raw_confidence": "0.9800",
  "calibrated_confidence": "0.9800",
  "all_citations_valid": true,
  "hallucinated_citations": []
}
```

---

## 4. Citation Hallucination Guard

The [`CitationValidator`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-7/backend/app/investigation/citation_validator.py) checks every identifier in `facts` and `inferences` against `dossier.valid_record_ids` and `dossier.valid_evidence_ids`:
* **Valid:** The ID is confirmed as an actual database record present in the dossier.
* **Hallucinated:** If the model invents a synthetic ID (e.g. `INV-FAKE-999`), it is captured in `hallucinated_citations`.
* **Penalty:** An invalid citation drops `all_citations_valid` to `False`, applies a `0.50` penalty in [`ConfidenceCalibrator`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-7/backend/app/investigation/calibration.py), and automatically fails Independent Verification Gate 2.

---

## 5. Model Provider Abstraction & Deterministic Fallback

The system isolates model interaction behind the [`LLMProvider`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-7/backend/app/investigation/llm_provider.py) interface:
* **`DeterministicInvestigationProvider`**: 100% deterministic local rules provider evaluating ground truth scenarios without external API calls (default for unit testing and offline development).
* **`OpenAIInvestigationProvider`**: Structured JSON model calls using `gpt-4o`.
* **Automatic Fallback:** If an external LLM request times out ($>30\text{s}$) or encounters network dropouts, the system falls back to the deterministic provider to guarantee completion without blocking the close workflow.
