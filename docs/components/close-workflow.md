# Close Workflow Component Deep Dive

The Close Workflow component orchestrates the month-end closing process, managing task sequencing, state machine concurrency, task executors, and close readiness gates.

---

## 1. Package Structure

Located at [`backend/app/close_workflow/`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/close_workflow/):

```
app/close_workflow/
├── __init__.py
├── controller.py        # CloseWorkflowController (DAG execution & orchestration)
├── dependencies.py      # TaskDependencyResolver (Topological sorting & readiness)
├── executor.py          # CloseTaskExecutor (Per-task specialized runners)
├── readiness.py         # CloseReadinessEvaluator (Pre-close checklist & blocking rules)
├── routing.py           # CloseRoutingEngine (Exception routing to specialized agents)
├── state_machine.py     # CloseWorkflowStateMachine (CAS transitions & audit emission)
└── types.py             # ClosePolicy, CloseRunContext, and evaluation types
```

---

## 2. Core Subsystem Classes

### 2.1 `TaskDependencyResolver`
Enforces a Directed Acyclic Graph (DAG) across the 10 close tasks:
```python
DEFAULT_TASK_DEPENDENCIES = {
    CloseTaskType.INVOICE_VALIDATION: [],
    CloseTaskType.PAYMENT_RECONCILIATION: [CloseTaskType.INVOICE_VALIDATION],
    CloseTaskType.BANK_RECONCILIATION: [CloseTaskType.PAYMENT_RECONCILIATION],
    CloseTaskType.AP_RECONCILIATION: [
        CloseTaskType.INVOICE_VALIDATION,
        CloseTaskType.PAYMENT_RECONCILIATION,
    ],
    CloseTaskType.AR_RECONCILIATION: [CloseTaskType.BANK_RECONCILIATION],
    CloseTaskType.VARIANCE_ANALYSIS: [
        CloseTaskType.INVOICE_VALIDATION,
        CloseTaskType.PAYMENT_RECONCILIATION,
    ],
    CloseTaskType.ACCRUAL_REVIEW: [
        CloseTaskType.INVOICE_VALIDATION,
        CloseTaskType.AP_RECONCILIATION,
    ],
    CloseTaskType.EXCEPTION_REVIEW: [
        CloseTaskType.INVOICE_VALIDATION,
        CloseTaskType.PAYMENT_RECONCILIATION,
        CloseTaskType.BANK_RECONCILIATION,
        CloseTaskType.AP_RECONCILIATION,
        CloseTaskType.AR_RECONCILIATION,
        CloseTaskType.VARIANCE_ANALYSIS,
        CloseTaskType.ACCRUAL_REVIEW,
    ],
    CloseTaskType.FINAL_VERIFICATION: [CloseTaskType.EXCEPTION_REVIEW],
    CloseTaskType.CLOSE_PACKAGE: [CloseTaskType.FINAL_VERIFICATION],
}
```

* **`validate_dag()`**: Kahn's algorithm cycle detection upon initialization.
* **`get_execution_order()`**: Deterministic topological sort order for sequential or staged execution.
* **`get_ready_tasks(statuses)`**: Returns `PENDING` tasks whose prerequisites are 100% `COMPLETED`.
* **`get_blocked_tasks(statuses)`**: Returns `PENDING` tasks with any `FAILED` or `BLOCKED` prerequisite.

### 2.2 `CloseWorkflowStateMachine`
Executes atomic Compare-And-Swap (CAS) state changes on database rows:
* **Legal Transitions Map:** Enforces allowed transitions defined in [`ALLOWED_CLOSE_RUN_TRANSITIONS`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/close_workflow/state_machine.py#L26).
* **CAS Concurrency Guard:** Updates require matching current `version` integer. If modified concurrently, raises `CloseRunError`.
* **Audit & Streaming Hook:** Each transition immediately records an immutable `AuditEvent` and publishes a `close_run_state_change` event to the SSE bus.

### 2.3 `CloseTaskExecutor`
Specialized task runner executing the domain logic for each task type:
* **`INVOICE_VALIDATION`**: Checks unapproved invoices and PO references.
* **`PAYMENT_RECONCILIATION`**: Matches payments to bills; flags unapplied payments.
* **`BANK_RECONCILIATION`**: Matches bank feeds to disbursements; reconciles cash.
* **`AP_RECONCILIATION`**: 3-way matching and vendor balance reconciliation.
* **`AR_RECONCILIATION`**: Remittance matching; customer short-payment detection.
* **`VARIANCE_ANALYSIS`**: Invokes [`FinancialAnalystAgent`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/analyst/agent.py) to identify balance sheet shifts.
* **`ACCRUAL_REVIEW`**: Reviews unbilled receipts (GRNI) and prepaid amortization.
* **`EXCEPTION_REVIEW`**: Coordinates [`CFOInvestigationAgent`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/investigation/agent.py) and [`VerificationEngine`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/verification/engine.py).
* **`FINAL_VERIFICATION`**: Validates close completeness via [`CloseReadinessEvaluator`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/close_workflow/readiness.py).
* **`CLOSE_PACKAGE`**: Compiles the sealed close package JSON artifact.

---

## 3. Configuration & Policy: `ClosePolicy`

Policy rules governing the close run are defined in [`app/close_workflow/types.py`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/close_workflow/types.py#L12):

```python
class ClosePolicy(BaseModel):
    max_auto_resolution_amount: Decimal = Decimal("50000.00")
    min_confidence: Decimal = Decimal("0.9500")
    materiality_threshold: Decimal = Decimal("50000.00")
    materiality_pct_of_account_balance: Decimal | None = Decimal("5.0")
    account_materiality_thresholds: dict[str, Decimal] = {}
    require_human_for_vendor_bank_change: bool = True
    require_human_for_cash_anomaly: bool = True
    require_human_for_payment_fragmentation: bool = True
    allow_autonomous_money_movement: bool = False  # Hard invariant: NEVER True
```
