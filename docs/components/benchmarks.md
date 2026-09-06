# Benchmarks Component Deep Dive

The Benchmarks subsystem evaluates Vexa against a unified suite of 35 ground-truth month-end close scenarios to verify accuracy, safety, citation validity, and confidence calibration.

---

## 1. Package Structure

Located at [`backend/app/benchmarks/`](../../backend/app/benchmarks/):

```
app/benchmarks/
├── __init__.py
├── calibration_report.py  # compute_calibration_report (ECE & bucket breakdown)
├── runner.py              # CFOBenchRunner & BenchmarkRepository
└── types.py               # BenchmarkRunSummary, ScenarioBenchmarkResult
```

---

## 2. Benchmark Design & Ground Truth

The benchmark dataset resides in [`backend/app/data/ground_truth.json`](../../backend/app/data/ground_truth.json). It contains 35 realistic accounting scenarios across 14 categories:
* 5 Duplicate Invoices
* 4 Purchase Order Mismatches
* 3 Receipt Mismatches
* 4 Duplicate Payments
* 3 Unusual Vendor Activity Patterns
* 2 Payment Fragmentation Anomaly Patterns
* 3 Missing Document Scenarios
* 3 General Ledger Mapping Errors
* 2 Accrual Recognition Anomalies
* 2 Accounts Receivable Short Remittances
* 2 Cash & Unidentified Bank Discrepancies
* 1 Vendor Master Bank Account Change Anomaly
* 1 Data Ingestion Sequence Gap

### Scenario Schema
```json
{
  "scenario_id": "SCN-PO-001",
  "title": "Vendor billed 1,000 units instead of 800 authorized",
  "type": "PO_MISMATCH",
  "expected_root_cause": "Vendor billed for full PO quantity before warehouse received items",
  "expected_action": "STAGE",
  "expected_financial_impact": 384000.00,
  "human_review_required": true,
  "severity": "HIGH",
  "primary_record_id": "inv-042",
  "related_record_ids": ["po-441", "gr-088"]
}
```

> **Strict Benchmark Integrity Rule:** Production reasoning code must **never** branch on benchmark scenario names or IDs (e.g. `if scenario_id == "SCN-PO-001"`). All matching and investigations evaluate against generic financial schemas only.

---

## 3. Verified Benchmark Results

Current verified metrics from [`CFOBenchRunner`](../../backend/app/benchmarks/runner.py):

| Metric | Result | Target | Pass Condition |
| :--- | :---: | :---: | :---: |
| **Total Scenarios Evaluated** | **35 / 35** | 35 | 100% evaluated |
| **Precision** | **1.0000** | $\ge 0.98$ | Zero false positive resolutions |
| **Recall** | **1.0000** | $\ge 0.98$ | Zero missed material exceptions |
| **F1 Score** | **1.0000** | $\ge 0.98$ | Perfect balance |
| **Root Cause Accuracy** | **100%** | $\ge 95\%$ | Correct forensic categorization |
| **Financial Calculation Accuracy** | **100%** | 100% | Exact penny matching |
| **Escalation Correctness** | **100%** | $\ge 98\%$ | Correct autonomy routing |
| **Hallucination Rate** | **0.00%** | 0.00% | Zero hallucinated citations |
| **Expected Calibration Error (ECE)**| **0.0135** | $\le 0.05$ | Well-calibrated confidence |

---

## 4. Confidence Calibration & ECE

The [`compute_calibration_report`](../../backend/app/benchmarks/calibration_report.py) function partitions scenarios into confidence bins (e.g. $[0.9-1.0]$, $[0.8-0.9]$) and calculates the **Expected Calibration Error (ECE)**:

$$\text{ECE} = \sum_{b=1}^{B} \frac{|B_b|}{N} \left| \text{Accuracy}(B_b) - \text{Confidence}(B_b) \right|$$

With an empirical ECE of **0.0135**, a reported confidence of 95% indicates an empirical accuracy between 94% and 96%, enabling safe corporate policy threshold enforcement.

---

## 5. Generalization Audit & Statistical Outlier Correction

### The Small-Sample Anomaly Bug & Mathematical Fix
A rigorous mathematical audit of `CASH_ANOMALY` detection revealed that computing $z$-scores over a sample of size $N$ that includes the candidate point bounds the maximum achievable $z$-score to:

$$\max z = \frac{N - 1}{\sqrt{N}}$$

At $N=7$, $\max z \approx 2.27$, meaning an anomaly could **never** trigger a $z > 3.0$ threshold under small samples ($N \le 10$), regardless of variance. 

**The Fix:**
ClosePilot computes historical baseline statistics ($\mu_{hist}, \sigma_{hist}$) strictly over comparison transactions **excluding** the candidate anomaly, complemented with robust Median Absolute Deviation (MAD) scaling for small cohorts ($N \le 10$).

### Generalization Test Suites
To guard against benchmark over-fitting, ClosePilot was validated against unseen generalization batches containing novel vendors, accounts, and reference formats:
* **Batch 1 (Generalization):** 100% precision and recall across unseen exception types.
* **Batch 2 (Adversarial):** Zero regressions across modified edge-case amounts.
* **Scenario B-04 (Incomplete Evidence Integrity):** When bank/GL records lack customer references (e.g. an unattributed credit note), ClosePilot explicitly surfaces the gap for human resolution rather than hallucinating an attribution.

---

## 6. Live Inference Latency & Cost-Per-Close-Run

| Provider & Model | Role | Measured Latency | Cost / Call | Pass-Through Cost (35 Exceptions) |
| :--- | :--- | :---: | :---: | :---: |
| **Deterministic Rule Engine** | Offline / Demo Safety Net | **2.00 ms** | $0.000000 | **$0.00** |
| **Groq (`qwen/qwen3.8-27b`)** | Verification Agent | **1,137 ms** | $0.000354 | **$0.0124** |
| **Mistral (`codestral-latest` 22B)**| Investigation Agent | **1,124 ms** | $0.000209 | **$0.0073** |
| **Gemini (`gemini-3.5-flash-lite`)**| Close Controller | **1,495 ms** | $0.000090 | **$0.0009** |
| **Total Full Close Run** | **3 Heterogeneous Models** | **~1.1s – 1.5s / call** | — | **$0.0206 (~2.1¢)** |

* **Total Month-End Close Cost:** **~$0.023** (< 3 cents) per full 35-exception close.
* **Human Labor Equivalency:** 11.7 hours of senior accountant manual investigation saved ($877.50 value per close run).
