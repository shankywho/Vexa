# Benchmarks API Reference

Endpoints for triggering evaluation runs against the 35 ground-truth scenarios and inspecting calibration reports. Router: [`backend/app/api/routes/benchmarks.py`](../../backend/app/api/routes/benchmarks.py).

---

## Endpoints

### 1. List Benchmark Runs
`GET /api/benchmarks`
* **Description:** Lists historical benchmark evaluation runs and aggregate metrics.
* **Response:** Array of [`BenchmarkRunSummary`](../../backend/app/benchmarks/types.py).

### 2. Execute Benchmark Run
`POST /api/benchmarks/run` (Status: `201 Created`)
* **Description:** Triggers an immediate evaluation run across all 35 ground-truth scenarios.
* **Response:** `BenchmarkRunSummary`.
* **Example Response:**
  ```json
  {
    "id": "2daecf70-d867-4e31-97ad-9d8995fc04df",
    "total_scenarios": 35,
    "evaluated_scenarios": 35,
    "root_cause_accuracy": "1.0000",
    "action_accuracy": "1.0000",
    "financial_calculation_accuracy": "1.0000",
    "escalation_correctness": "1.0000",
    "hallucination_rate": "0.0000",
    "expected_calibration_error": "0.0135",
    "avg_calibrated_confidence": "0.9654",
    "avg_latency_ms": 12
  }
  ```

### 3. Get Confidence Calibration Report
`GET /api/benchmarks/calibration`
* **Description:** Retrieves the latest calibration breakdown across confidence buckets ($[0.9-1.0]$, $[0.8-0.9]$, etc.) and the empirical Expected Calibration Error (ECE).
* **Response:** [`ConfidenceCalibrationReport`](../../backend/app/domain/schemas.py).

### 4. Get Benchmark Run by ID
`GET /api/benchmarks/{id}`
* **Description:** Retrieves detailed scenario-by-scenario results for a specific historical benchmark run.
* **Response:** `BenchmarkRunSummary`.
