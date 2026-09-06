# LLM Safety & Guardrails

Vexa wraps all machine learning interactions in strict safety guardrails to ensure production reliability, zero hallucinations, and institutional audit compliance.

---

## 1. Provider Abstraction & Fallback Architecture

The [`LLMProvider`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-7/backend/app/investigation/llm_provider.py) interface isolates model providers from the rest of the application:
* **Supported Providers:**
  - `deterministic` (Default local rules provider; zero network dependency)
  - `openai` (`gpt-4o` with JSON schema enforcement)
  - `anthropic` (Claude 3.5 Sonnet)
  - `gemini` (Gemini 1.5 Pro)
  - `custom` (Internal fine-tuned finance endpoints)

### Deterministic Fallback Invariant
If an external LLM request encounters a network error, HTTP 5xx error, or exceeds the 30.0-second timeout, the system automatically falls back to [`DeterministicInvestigationProvider`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-7/backend/app/investigation/llm_provider.py#L48). This guarantees that a close run will **never** freeze or fail due to external API outages.

---

## 2. Citation Validation (Zero Hallucinations)

The [`CitationValidator`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-7/backend/app/investigation/citation_validator.py) checks every identifier cited in agent reasoning against the bounded dossier whitelist:
* Every fact must cite a real `record_id` or `evidence_id`.
* Any citation not present in `valid_record_ids` is flagged as a hallucination.
* Findings with hallucinated citations are disqualified from autonomous execution and penalized by 0.50 points in confidence calibration.

---

## 3. Version Tracking & Reproducibility

Every prompt template is assigned an immutable version identifier (e.g. `cfo-investigator-v2`, `financial-analyst-v1`).
* When an agent executes, `prompt_version_id` is written into the `agent_runs` table and referenced in all associated `audit_events`.
* Auditors can inspect historical decisions knowing the exact prompt, policy configuration, and model parameters that produced them.
