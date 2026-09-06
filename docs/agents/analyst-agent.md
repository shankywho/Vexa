# Financial Analyst Agent Specification

The Financial Analyst Agent performs aggregate accounting analytics across general ledger balances, cash velocity, burn rate, and accrual timing.

---

## 1. Responsibilities & Tools

* **Primary Function:** High-level financial reporting, period-over-period variance analysis, and executive close summaries.
* **Deterministic Tool Boundaries:** The agent performs **zero mental arithmetic**. It executes calculations through typed tools in [`FinancialAnalystTools`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-7/backend/app/analyst/tools.py):
  - `calculate_account_variances()`: Period-over-period account shift calculations.
  - `calculate_cash_summary()`: Operating, investing, and financing cash movements.
  - `review_accrual_candidates()`: Unbilled goods receipts and amortizations.

---

## 2. Output Schema: `FinancialAnalysisReport`

Defined in [`app/analyst/types.py`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-7/backend/app/analyst/types.py):
* **Period Details:** Start date, end date, company ID.
* **Account Variances:** List of account shifts with `prior_balance`, `current_balance`, `variance_amount`, `percentage_change`, and `is_material`.
* **Cash Movement:** Net burn rate, total inflows, total outflows.
* **Accruals Summary:** Total GRNI candidates and recommended adjusting entries.
* **Executive Narrative:** Synthesized executive summary for the CFO.

---

## 3. Relevant Tests

* Integration Tests: [`tests/integration/test_analyst_and_benchmarks.py`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-7/backend/tests/integration/test_analyst_and_benchmarks.py).
