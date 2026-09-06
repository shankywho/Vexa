# Action Agent Specification

The Action Agent executes approved accounting adjustments, stages draft journal entries, drafts vendor inquiry letters, and manages audit trails under strict corporate governance.

---

## 1. Responsibilities & Hard Safety Rules

* **Primary Function:** Enact decisions authorized by the Verification Agent or confirmed by human reviewers.
* **Strict Prohibitions:**
  - **NO AUTONOMOUS MONEY MOVEMENT:** Cannot execute bank disbursements, wires, ACH transfers, or debit authorizations.
  - **NO IRREVERSIBLE MUTATIONS:** Every executed entry has an explicit compensating reversal pathway via [`ReversalEngine`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/action/reversal.py).

---

## 2. Tools & Capabilities

Implemented in [`ActionTools`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/action/tools.py):
* **`stage_journal_entry()`**: Creates a draft compensating journal entry in `DRAFT` status.
* **`draft_vendor_email()`**: Creates a draft clarification email for Accounts Payable review.
* **`create_review_task()`**: Enqueues an internal review ticket assigned to the Controller.
* **`mark_exception_resolved()`**: Formally updates exception status to `RESOLVED` or `AUTO_RESOLVED`.
* **`mark_exception_escalated()`**: Updates exception status to `ESCALATED` and notifies the CFO.

---

## 3. Relevant Tests

* Unit Tests: [`tests/unit/test_action_agent_and_reversal.py`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/tests/unit/test_action_agent_and_reversal.py).
* Integration Tests: [`tests/integration/test_verification_action_reversal_flow.py`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/tests/integration/test_verification_action_reversal_flow.py).
