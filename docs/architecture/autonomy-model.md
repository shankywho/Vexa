# Controlled Autonomy Model

Vexa implements a multi-tier autonomy model that balances computational efficiency with institutional fiduciary controls. The system replaces all-or-nothing automation with a graduated framework based on risk, financial impact, and evidence completeness.

---

## 1. The 4 Autonomy Levels

Defined in [`app.domain.enums.AutonomyLevel`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-8/backend/app/domain/enums.py#L100):

```
                               ┌─────────────────────────────┐
                               │ Level 3: EXECUTE            │
                               │ Autonomous resolution       │
                               └──────────────▲──────────────┘
                                              │ (Low risk, high confidence,
                                              │  complete evidence, <= $50k)
                               ┌──────────────┴──────────────┐
                               │ Level 2: STAGE              │
                               │ Action staged for approval  │
                               └──────────────▲──────────────┘
                                              │ (Standard discrepancy,
                                              │  moderate variance)
                               ┌──────────────┴──────────────┐
                               │ Level 1: RECOMMEND          │
                               │ Human investigation required│
                               └──────────────▲──────────────┘
                                              │ (Material risk, fraud signal,
                                              │  or policy conflict)
                               ┌──────────────┴──────────────┐
                               │ Level 0: OBSERVE            │
                               │ Logged; no action proposed  │
                               └─────────────────────────────┘
```

### Level 0: OBSERVE
* **Behavior:** Flags an anomaly or data discrepancy; logs telemetry; executes zero mutations; proposes zero actions.
* **Triggered When:** Evidence is severely incomplete, independent calculation fails, or citations are ungrounded.

### Level 1: RECOMMEND (CFO Escalation)
* **Behavior:** Performs root-cause analysis; formulates a detailed forensic dossier; routes the exception directly to the CFO or Head of Internal Audit.
* **Triggered When:** High-risk indicators are present:
  - Vendor bank account modification prior to payment (`AP-07`).
  - Payment fragmentation or structuring patterns (`AP-03`).
  - Cash balance anomalies or unrecorded bank transactions (`BANK-01`).
  - Data ingestion gaps or GL sequence discontinuities (`CLOSE-01`).

### Level 2: STAGE (Controller Review)
* **Behavior:** Automatically generates all required remedial artifacts (e.g. drafting correcting journal entries or vendor inquiries), but places them in a pending approval queue.
* **Triggered When:** Routine procurement or billing discrepancies that exceed the auto-resolution materiality threshold ($50,000) or have moderate calibrated confidence (0.80 – 0.94).
* **Execution:** Actions remain in `STAGED` status until explicitly approved via `POST /api/exceptions/{id}/approve` by an authorized Controller.

### Level 3: EXECUTE (Autonomous Resolution)
* **Behavior:** Autonomously executes safe compensating adjustments, marks the exception resolved, and generates audit events without manual intervention.
* **Triggered When:**
  - Independent calculation verification is 100% valid (`diff <= 0.01`).
  - Evidence completeness is 100% verified with zero hallucinated citations.
  - Financial impact is below the absolute materiality cap ($\le \$50,000.00$).
  - Financial impact is below relative account balance thresholds.
  - Calibrated confidence is $\ge 0.9500$.
  - Zero hard escalation flags.

---

## 2. Decision Resolution Matrix

| Scenario / Exception Type | Impact Range | Calibrated Confidence | Evidence Status | Assigned Autonomy Level | Final System Action |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Clean 6-Way Matched Transaction** | $0.00 | $\ge 0.95$ | Complete | **Level 3: EXECUTE** | Auto-resolve; zero human touch. |
| **Small Immaterial Fee Variance** | $\le \$50,000$ | $\ge 0.95$ | Complete | **Level 3: EXECUTE** | Auto-resolve via draft adjusting entry. |
| **PO / Invoice Quantity Mismatch** | $> \$50,000$ | $\ge 0.95$ | Complete | **Level 2: STAGE** | Stage debit memo; await Controller OK. |
| **Timing Difference (Unbilled GRNI)**| $> \$50,000$ | $\ge 0.90$ | Complete | **Level 2: STAGE** | Stage month-end accrual entry. |
| **Missing Document (Unattached PO)** | Any | $< 0.80$ | Incomplete | **Level 2: STAGE** | Stage inquiry to procurement owner. |
| **Vendor Bank Account Change** | Any | Any | Any | **Level 1: RECOMMEND** | Hard escalation to CFO (fraud review). |
| **Payment Fragmentation (Structuring)**| Any | Any | Any | **Level 1: RECOMMEND** | Hard escalation to CFO (compliance review). |
| **Arithmetic Verification Discrepancy**| Any | Any | Any | **Level 0: OBSERVE** | Block autonomous action; log audit alert. |

---

## 3. Human-in-the-Loop Governance

Human review is a first-class operational workflow in Vexa, not an exceptional error state:
1. **Controller Queue:** Standard staged actions (`Level 2`) populate the Controller dashboard. Approving an exception automatically executes the staged payloads.
2. **CFO Escalations:** Material or anomalous issues (`Level 1`) require explicit sign-off with documented business rationale.
3. **Audit Immutability:** When a human approves, rejects, or escalates an item, their user ID, role, timestamp, and review notes are bound into an immutable `AuditEvent`.
4. **Advisory Policy Tuning:** The system computes human override rates against agent suggestions across confidence buckets. If an exception category exhibits $>20\%$ human overrides over 5+ decisions, it is flagged as an advisory policy tuning candidate.
