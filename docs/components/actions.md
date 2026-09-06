# Actions & Human Review Component Deep Dive

The Actions subsystem executes permitted adjustments, stages proposals for Controller review, manages human escalations, and provides a 1-click reversal rollback path.

---

## 1. Package Structure

Located at [`backend/app/action/`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/action/):

```
app/action/
├── __init__.py
├── agent.py               # ActionAgent (Coordinates permitted actions)
├── correction_service.py  # HumanCorrectionService (Tracks human overrides & statistics)
├── reversal.py            # ReversalEngine (Compensating reversal entries)
├── service.py             # ActionService (Approvals, rejections, reversals)
├── tools.py               # ActionTools (Compensating journal entry & email staging)
└── types.py               # ActionType, ActionResult, ReversalResult
```

---

## 2. Hard Invariant: Zero Autonomous Money Movement

Vexa is strictly prohibited from disbursing funds or initiating transactions on external banking networks. Permitted action types in [`app.action.types.ActionType`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/action/types.py#L9) are strictly bounded to internal adjustments:
* `MARK_EXCEPTION_RESOLVED`: Closes exception after verified match or compensating entry.
* `STAGE_JOURNAL_ENTRY`: Stages draft adjusting entry in `GL_DRAFT` state for human review.
* `DRAFT_VENDOR_EMAIL`: Stages inquiry text for accounts payable clerk review.
* `CREATE_REVIEW_TASK`: Assigns investigation task to an internal accountant.
* `MARK_EXCEPTION_ESCALATED`: Formally routes exception to CFO or Controller.

---

## 3. The Distinction: Recommend vs Stage vs Execute

* **Agent Recommends:** The Investigation Agent formulates an action recommendation within its finding (e.g. suggesting an accrual adjustment).
* **System Stages:** If verification assigns `AutonomyLevel.STAGE`, the system stages the action payload in the database with status `STAGED`. No financial state changes take effect until a human approves.
* **Human Approves:** When a Controller calls `POST /api/exceptions/{id}/approve`, the staged action status transitions to `EXECUTED`, and the exception transitions to `RESOLVED`.
* **System Executes:** If verification assigns `AutonomyLevel.EXECUTE` (immaterial, high confidence, verified arithmetic), the action transitions directly to `EXECUTED` without human delay.

---

## 4. Reversal Engine & Rollback Path

If an action was executed or approved erroneously, an authorized reviewer can reverse it via `POST /api/exceptions/{id}/reverse`.

The [`ReversalEngine`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/action/reversal.py) guarantees:
1. **Zero Row Deletion:** Historical rows are never deleted.
2. **Reversal Record:** Inserts a new `ReversalAction` row linking to `ExceptionAction.id` with timestamp, reviewer ID, and business rationale.
3. **Exception Reopening:** The exception status transitions back to `REOPENED`, and `resolved_at` is cleared.
4. **Downstream Voiding:** Staged draft entries or draft emails are marked `VOID`.
5. **Dual Audit Logging:** Emits two immutable audit events: `REVERSAL` and `EXCEPTION_REOPENED`.

---

## 5. Human Correction & Policy Tuning Loop

The [`HumanCorrectionService`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/action/correction_service.py) records every human intervention where a human reviewer's final decision differs from the system recommendation.

### Override Statistics
Metrics are aggregated across three views via `GET /api/exceptions/corrections/stats`:
* **Overall Override Rate:** Total human overrides divided by total human decisions.
* **By Exception Type:** Override rate per exception category (e.g. `PO_MISMATCH` vs `DUPLICATE_INVOICE`).
* **By Confidence Bucket:** Override rates partitioned into `HIGH (>=0.95)`, `MEDIUM (0.80-0.94)`, and `LOW (<0.80)`.

### Advisory Policy Tuning Candidates
If an exception category or confidence bucket exhibits:
$$\text{Total Decisions} \ge 5 \quad \text{and} \quad \text{Override Rate} > 20\%$$
the service tags it as an **Advisory Tuning Candidate** (`tuning_candidates: ["exception_type:PO_MISMATCH"]`).

> **Important:** Tuning candidates are strictly advisory metrics displayed to administrators. The system never modifies corporate policies autonomously without human governance approval.
