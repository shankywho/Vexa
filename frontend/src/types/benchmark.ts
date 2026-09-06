export interface ScenarioBenchmarkResult {
  scenario_id: string;
  scenario_type: string;
  title: string;
  expected_action: string;
  actual_action: string;
  action_matched: boolean;
  expected_root_cause: string;
  actual_root_cause: string;
  root_cause_matched: boolean;
  citations_valid: boolean;
  hallucinations_count: number;
  raw_confidence: string;
  calibrated_confidence: string;
  latency_ms: number;
  financial_impact: string;
}

export interface CalibrationBucket {
  bucket_min: number;
  bucket_max: number;
  sample_count: number;
  mean_predicted_confidence: number;
  empirical_accuracy: number;
  calibration_error: number;
}

export interface CalibrationReport {
  expected_calibration_error: string;
  brier_score: string;
  buckets: CalibrationBucket[];
  reliability_curve: { confidence: number; accuracy: number }[];
}

export interface BenchmarkRunSummary {
  id: string;
  run_timestamp: string;
  total_scenarios: number;
  evaluated_scenarios: number;
  action_accuracy: string;
  root_cause_accuracy: string;
  hallucination_rate: string;
  avg_latency_ms: number;
  total_cost_usd: string;
  calibration_report: CalibrationReport;
  scenario_details: ScenarioBenchmarkResult[];
}
