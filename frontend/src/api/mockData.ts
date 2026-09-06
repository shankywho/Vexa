import { Company } from '../types/company';
import { CloseRun, CloseTask, ClosePolicy, ClosePackage } from '../types/closeRun';
import { ExceptionRecord } from '../types/exception';
import { FinancialEvidenceGraph } from '../types/evidenceGraph';
import { AuditEvent } from '../types/audit';
import { BenchmarkRunSummary } from '../types/benchmark';
import { DemoTrace } from '../types/demo';

export const MOCK_COMPANY: Company = {
  id: 'abf0fca7-983d-5216-bbde-71a6678ca5e8',
  name: 'NovaScale AI',
  legal_name: 'NovaScale AI Technologies Inc.',
  tax_id: 'US-EIN-94-3829104',
  base_currency: 'USD',
  fiscal_year_end: '2026-12-31',
  active_close_runs: 1,
  total_transactions: 12480,
};

export const MOCK_COMPANIES: Company[] = [
  MOCK_COMPANY,
  {
    id: 'f1e2d3c4-b5a6-7890-1234-56789abcdef0',
    name: 'Apex Global Logistics',
    legal_name: 'Apex Global Logistics LLC',
    tax_id: 'US-EIN-12-8472910',
    base_currency: 'EUR',
    fiscal_year_end: '2026-12-31',
    active_close_runs: 0,
    total_transactions: 8520,
  },
  {
    id: 'c7d8e9f0-1a2b-3c4d-5e6f-7a8b9c0d1e2f',
    name: 'Quantis BioVentures',
    legal_name: 'Quantis BioVentures Corp',
    tax_id: 'US-EIN-88-2947103',
    base_currency: 'USD',
    fiscal_year_end: '2026-06-30',
    active_close_runs: 0,
    total_transactions: 4190,
  }
];

export const MOCK_CLOSE_RUN: CloseRun = {
  id: '341cfa78-09fd-499b-ae0d-399485211be9',
  company_id: MOCK_COMPANY.id,
  period_start: '2026-03-01',
  period_end: '2026-03-31',
  status: 'WAITING_FOR_HUMAN',
  version: 4,
  started_at: '2026-04-01T08:00:00Z',
  created_at: '2026-04-01T07:45:00Z',
  updated_at: '2026-04-01T08:14:22Z',
  tasks_completed: 8,
  total_tasks: 10,
  blocking_exceptions_count: 2,
  total_financial_exposure: '1834000.00',
  close_summary: JSON.stringify({
    period: 'March 2026',
    reconciled_volume: '$42,850,210.45',
    variance_unresolved: '$1,834,000.00',
    autonomous_rate: '85.7%'
  })
};

export const MOCK_CLOSE_RUNS: CloseRun[] = [
  MOCK_CLOSE_RUN,
  {
    id: 'a123b456-c789-0123-4567-89abcdef0123',
    company_id: MOCK_COMPANY.id,
    period_start: '2026-02-01',
    period_end: '2026-02-28',
    status: 'CLOSED',
    version: 12,
    started_at: '2026-03-01T08:00:00Z',
    completed_at: '2026-03-02T14:30:00Z',
    created_at: '2026-03-01T07:30:00Z',
    tasks_completed: 10,
    total_tasks: 10,
    blocking_exceptions_count: 0,
    total_financial_exposure: '0.00',
  },
  {
    id: 'f987e654-d321-0987-6543-21fedcba9876',
    company_id: MOCK_COMPANY.id,
    period_start: '2026-01-01',
    period_end: '2026-01-31',
    status: 'CLOSED',
    version: 10,
    started_at: '2026-02-01T08:00:00Z',
    completed_at: '2026-02-02T18:15:00Z',
    created_at: '2026-02-01T07:45:00Z',
    tasks_completed: 10,
    total_tasks: 10,
    blocking_exceptions_count: 0,
    total_financial_exposure: '0.00',
  }
];

export const MOCK_CLOSE_TASKS: CloseTask[] = [
  {
    id: 'task-1',
    close_run_id: MOCK_CLOSE_RUN.id,
    task_type: 'INVOICE_VALIDATION',
    status: 'COMPLETED',
    started_at: '2026-04-01T08:00:02Z',
    completed_at: '2026-04-01T08:01:15Z',
    duration_ms: 73000,
    result_summary: 'Validated 4,210 vendor invoices against PO registries and active tax brackets.',
  },
  {
    id: 'task-2',
    close_run_id: MOCK_CLOSE_RUN.id,
    task_type: 'PAYMENT_RECONCILIATION',
    status: 'COMPLETED',
    started_at: '2026-04-01T08:01:16Z',
    completed_at: '2026-04-01T08:03:02Z',
    duration_ms: 106000,
    result_summary: 'Matched 3,980 disbursements. Flagged 1 severe payment fragmentation pattern.',
  },
  {
    id: 'task-3',
    close_run_id: MOCK_CLOSE_RUN.id,
    task_type: 'BANK_RECONCILIATION',
    status: 'COMPLETED',
    started_at: '2026-04-01T08:03:03Z',
    completed_at: '2026-04-01T08:04:40Z',
    duration_ms: 97000,
    result_summary: '100% bank statement balance reconciled across 6 institutional accounts.',
  },
  {
    id: 'task-4',
    close_run_id: MOCK_CLOSE_RUN.id,
    task_type: 'AP_RECONCILIATION',
    status: 'COMPLETED',
    started_at: '2026-04-01T08:04:41Z',
    completed_at: '2026-04-01T08:06:12Z',
    duration_ms: 91000,
    result_summary: 'Subledger tied to General Ledger with $384,000 quantity variance staged for correction.',
  },
  {
    id: 'task-5',
    close_run_id: MOCK_CLOSE_RUN.id,
    task_type: 'AR_RECONCILIATION',
    status: 'COMPLETED',
    started_at: '2026-04-01T08:06:13Z',
    completed_at: '2026-04-01T08:07:30Z',
    duration_ms: 77000,
    result_summary: 'Accounts receivable aged and verified. Bad debt reserve within tolerance.',
  },
  {
    id: 'task-6',
    close_run_id: MOCK_CLOSE_RUN.id,
    task_type: 'VARIANCE_ANALYSIS',
    status: 'COMPLETED',
    started_at: '2026-04-01T08:07:31Z',
    completed_at: '2026-04-01T08:09:10Z',
    duration_ms: 99000,
    result_summary: 'Financial analyst agent completed period-over-period budget-to-actual analytics.',
  },
  {
    id: 'task-7',
    close_run_id: MOCK_CLOSE_RUN.id,
    task_type: 'ACCRUAL_REVIEW',
    status: 'COMPLETED',
    started_at: '2026-04-01T08:09:11Z',
    completed_at: '2026-04-01T08:10:45Z',
    duration_ms: 94000,
    result_summary: 'Evaluated unbilled goods receipts; auto-accrued $14,250 in delivery-in-transit.',
  },
  {
    id: 'task-8',
    close_run_id: MOCK_CLOSE_RUN.id,
    task_type: 'EXCEPTION_REVIEW',
    status: 'COMPLETED',
    started_at: '2026-04-01T08:10:46Z',
    completed_at: '2026-04-01T08:14:00Z',
    duration_ms: 194000,
    result_summary: 'Evaluated 28 exceptions: 20 auto-resolved, 5 staged for controller, 3 escalated to CFO.',
  },
  {
    id: 'task-9',
    close_run_id: MOCK_CLOSE_RUN.id,
    task_type: 'FINAL_VERIFICATION',
    status: 'BLOCKED',
    result_summary: 'Blocked: 2 high-materiality items pending CFO & Controller authorizations ($1,834,000 at risk).',
  },
  {
    id: 'task-10',
    close_run_id: MOCK_CLOSE_RUN.id,
    task_type: 'CLOSE_PACKAGE',
    status: 'PENDING',
    result_summary: 'Awaiting completion of Final Verification.',
  },
];

export const MOCK_POLICY: ClosePolicy = {
  policy_version_id: 'pol_v2_2026_enterprise',
  max_auto_resolution_amount: '50000.00',
  materiality_threshold: '100000.00',
  min_confidence: '0.9500',
  approval_timeout_hours: 24,
  required_approvers_material: ['CFO', 'CONTROLLER']
};

export const MOCK_EXCEPTIONS: ExceptionRecord[] = [
  {
    id: 'ex-frag-001',
    company_id: MOCK_COMPANY.id,
    close_run_id: MOCK_CLOSE_RUN.id,
    type: 'PAYMENT_FRAGMENTATION',
    severity: 'CRITICAL',
    status: 'ESCALATED',
    autonomy_level: 'LEVEL_1_RECOMMEND',
    title: 'Severe Payment Fragmentation Detected (Vendor: HyperScale Infra)',
    description: 'Invoice #INV-2026-881 for $1,450,000.00 was satisfied through 14 fragmented disbursements of exactly $100,000 plus $50,000 over a 48-hour window, bypassing $100k internal control thresholds.',
    financial_impact: '1450000.00',
    currency: 'USD',
    detected_at: '2026-04-01T08:02:15Z',
    assigned_to: 'cfo@novascale.ai',
    root_cause: 'Deliberate invoice structuring to evade single-disbursement board approval limits ($100k). High fraud risk indicator.',
    suggested_action: 'ESCALATE to CFO immediately. Place hold on pending vendor disbursements and request executive audit confirmation.',
    raw_confidence: '0.9840',
    calibrated_confidence: '0.9420',
    evidence_count: 16,
    investigation_model: 'Mistral (codestral-latest)',
    verification_model: 'Groq (qwen3.8-27b)',
    verification_status: 'PRESERVED',
    calculation_proof: {
      formula: 'Sum(Disbursements 1..14) + Final Check',
      variables: {
        'Sub-Disbursement Count': 14,
        'Amount per Chunk': '$100,000.00',
        'Residual Balance': '$50,000.00',
        'Original Invoice Total': '$1,450,000.00'
      },
      expected: '$1,450,000.00',
      actual: '$1,450,000.00',
      variance: '$0.00 (Structural Anomaly)',
      is_material: true
    },
    citations: [
      { citation_id: 'cit-inv-881', record_type: 'Invoice', record_id: 'INV-2026-881', document_ref: 'ERP-AP-INV-881', verified_in_db: true },
      { citation_id: 'cit-po-881', record_type: 'PurchaseOrder', record_id: 'PO-2026-440', document_ref: 'ERP-PO-440', verified_in_db: true },
      { citation_id: 'cit-pay-batch', record_type: 'PaymentBatch', record_id: 'PAY-BATCH-991', document_ref: 'ACH-BATCH-991', verified_in_db: true }
    ],
    staged_action: {
      action_type: 'HOLD_PAYMENTS_AND_ESCALATE',
      description: 'Freezes active ACH release queue for HyperScale Infra and registers CFO incident ticket #SOX-SEC-01.',
      amount: '1450000.00',
      currency: 'USD',
      staged_by: 'investigation_agent',
      staged_at: '2026-04-01T08:03:00Z'
    }
  },
  {
    id: 'ex-po-002',
    company_id: MOCK_COMPANY.id,
    close_run_id: MOCK_CLOSE_RUN.id,
    type: 'PO_MISMATCH',
    severity: 'HIGH',
    status: 'STAGED',
    autonomy_level: 'LEVEL_2_STAGE',
    title: 'PO Quantity Variance: NovaScale AI GPU Server Ingestion',
    description: 'Vendor billed for 1,000 units @ $1,600/unit ($1,600,000.00), but Goods Receipt confirmed delivery of only 760 units. 240 units unreceived.',
    financial_impact: '384000.00',
    currency: 'USD',
    detected_at: '2026-04-01T08:04:12Z',
    assigned_to: 'controller@novascale.ai',
    root_cause: 'Vendor advance billing ahead of physical fulfillment. Warehouse confirmed receipt of 760 units on GR-902.',
    suggested_action: 'STAGE compensating debit memo of $384,000.00 against AP and hold payment differential.',
    raw_confidence: '0.9700',
    calibrated_confidence: '0.9150',
    evidence_count: 5,
    investigation_model: 'Mistral (codestral-latest)',
    verification_model: 'Groq (qwen3.8-27b)',
    verification_status: 'PRESERVED',
    calculation_proof: {
      formula: '(Invoiced_Qty - Received_Qty) * Unit_Price',
      variables: {
        'Invoiced Quantity': 1000,
        'Received Quantity': 760,
        'Shortfall Units': 240,
        'Unit Contract Price': '$1,600.00'
      },
      expected: '$1,216,000.00',
      actual: '$1,600,000.00',
      variance: '$384,000.00 Overbilled',
      is_material: true
    },
    citations: [
      { citation_id: 'cit-inv-902', record_type: 'Invoice', record_id: 'INV-2026-902', document_ref: 'INV-902-GPU', verified_in_db: true },
      { citation_id: 'cit-po-902', record_type: 'PurchaseOrder', record_id: 'PO-2026-771', document_ref: 'PO-771-H100', verified_in_db: true },
      { citation_id: 'cit-gr-902', record_type: 'GoodsReceipt', record_id: 'GR-2026-104', document_ref: 'WH-GR-104', verified_in_db: true }
    ],
    staged_action: {
      action_type: 'AP_DEBIT_MEMO',
      description: 'Issue short-pay authorization of $384,000.00 and stage journal entry debiting AP clearing and crediting accrued inventory.',
      debit_account: '2010-Accounts-Payable',
      credit_account: '1410-Accrued-Inventory',
      amount: '384000.00',
      currency: 'USD',
      staged_by: 'accountant@novascale.ai',
      staged_at: '2026-04-01T08:08:20Z'
    }
  },
  {
    id: 'ex-clean-003',
    company_id: MOCK_COMPANY.id,
    close_run_id: MOCK_CLOSE_RUN.id,
    type: 'OTHER',
    severity: 'LOW',
    status: 'RESOLVED',
    autonomy_level: 'LEVEL_3_AUTO_RESOLVE',
    title: 'Clean 6-Way Multi-Currency Transaction (FX Rounding)',
    description: 'EUR to USD currency conversion difference of $0.42 on Cloudflare Enterprise licensing contract.',
    financial_impact: '0.42',
    currency: 'USD',
    detected_at: '2026-04-01T08:01:40Z',
    root_cause: 'Cent-rounding variance in ECB spot conversion rate vs bank settlement fee.',
    suggested_action: 'AUTO-RESOLVE: Book $0.42 to Foreign Exchange Gain/Loss (Control FX-01).',
    raw_confidence: '0.9990',
    calibrated_confidence: '0.9950',
    evidence_count: 6,
    investigation_model: 'Deterministic Rule Engine',
    verification_model: 'Deterministic Rule Engine',
    verification_status: 'PRESERVED'
  },
  {
    id: 'ex-dup-004',
    company_id: MOCK_COMPANY.id,
    close_run_id: MOCK_CLOSE_RUN.id,
    type: 'DUPLICATE_INVOICE',
    severity: 'MEDIUM',
    status: 'RESOLVED',
    autonomy_level: 'LEVEL_3_AUTO_RESOLVE',
    title: 'Duplicate Software Subscription Invoice (Slack Technologies)',
    description: 'Duplicate bill submitted for $12,450.00 matching Invoice #SLK-8812 previously settled via corporate card.',
    financial_impact: '12450.00',
    currency: 'USD',
    detected_at: '2026-04-01T08:05:10Z',
    root_cause: 'Vendor automated re-billing following payment gateway sync delay.',
    suggested_action: 'AUTO-RESOLVE: Void duplicate invoice and link payment voucher #PV-410 to master entry.',
    raw_confidence: '0.9940',
    calibrated_confidence: '0.9780',
    evidence_count: 4,
    investigation_model: 'Mistral (codestral-latest)',
    verification_model: 'Groq (qwen3.8-27b)',
    verification_status: 'PRESERVED'
  }
];

export const MOCK_EVIDENCE_GRAPH: FinancialEvidenceGraph = {
  nodes: [
    { id: 'node-vendor', type: 'vendor', label: 'HyperScale Infra Corp', properties: { gstin: 'US-884920', risk_score: 'HIGH' }, pagerank_score: 0.95 },
    { id: 'node-inv', type: 'invoice', label: 'INV-2026-881 ($1,450,000)', amount: '1450000.00', currency: 'USD', pagerank_score: 1.0 },
    { id: 'node-po', type: 'purchase_order', label: 'PO-2026-440 ($1,450,000)', amount: '1450000.00', currency: 'USD', pagerank_score: 0.88 },
    { id: 'node-pay-1', type: 'payment', label: 'ACH #1 ($100,000)', amount: '100000.00', currency: 'USD', pagerank_score: 0.65 },
    { id: 'node-pay-2', type: 'payment', label: 'ACH #2 ($100,000)', amount: '100000.00', currency: 'USD', pagerank_score: 0.65 },
    { id: 'node-pay-3', type: 'payment', label: 'ACH #3 ($100,000)', amount: '100000.00', currency: 'USD', pagerank_score: 0.65 },
    { id: 'node-pay-4', type: 'payment', label: 'ACH #4 ($100,000)', amount: '100000.00', currency: 'USD', pagerank_score: 0.65 },
    { id: 'node-bank', type: 'bank_account', label: 'SVB Operating #9012', properties: { bank: 'Silicon Valley Bank' }, pagerank_score: 0.72 },
    { id: 'node-gl', type: 'gl_account', label: '2010 Accounts Payable', properties: { balance: '$18,420,100' }, pagerank_score: 0.81 }
  ],
  edges: [
    { id: 'e1', source: 'node-vendor', target: 'node-inv', type: 'BILLED_ON', label: 'ISSUED_BY' },
    { id: 'e2', source: 'node-po', target: 'node-inv', type: 'GOVERNED_BY', label: 'MATCHES_PO' },
    { id: 'e3', source: 'node-inv', target: 'node-pay-1', type: 'PAID_BY', label: 'FRAGMENT_1' },
    { id: 'e4', source: 'node-inv', target: 'node-pay-2', type: 'PAID_BY', label: 'FRAGMENT_2' },
    { id: 'e5', source: 'node-inv', target: 'node-pay-3', type: 'PAID_BY', label: 'FRAGMENT_3' },
    { id: 'e6', source: 'node-inv', target: 'node-pay-4', type: 'PAID_BY', label: 'FRAGMENT_4' },
    { id: 'e7', source: 'node-bank', target: 'node-pay-1', type: 'POSTED_TO', label: 'DEBITED_FROM' },
    { id: 'e8', source: 'node-inv', target: 'node-gl', type: 'POSTED_TO', label: 'SUBLEDGER_POST' }
  ]
};

export const MOCK_AUDIT_EVENTS: AuditEvent[] = [
  {
    id: 'audit-001',
    timestamp: '2026-04-01T08:00:01Z',
    company_id: MOCK_COMPANY.id,
    close_run_id: MOCK_CLOSE_RUN.id,
    event_type: 'CLOSE_RUN_STATE_CHANGE',
    actor: 'controller@novascale.ai',
    actor_type: 'CONTROLLER',
    control_id: 'CLOSE-01',
    decision: 'START_CLOSE',
    reason: 'Initiated March 2026 month-end closing cycle for NovaScale AI.',
    is_reversal: false,
    reversible: false
  },
  {
    id: 'audit-002',
    timestamp: '2026-04-01T08:02:16Z',
    company_id: MOCK_COMPANY.id,
    close_run_id: MOCK_CLOSE_RUN.id,
    exception_id: 'ex-frag-001',
    event_type: 'EXCEPTION_DETECTED',
    actor: 'investigation_agent',
    actor_type: 'AGENT',
    agent_name: 'CFO Investigation Agent',
    prompt_version_id: 'prom_inv_v2.1',
    policy_version_id: 'pol_v2_2026_enterprise',
    control_id: 'AP-03',
    financial_impact: '1450000.00',
    currency: 'USD',
    confidence: '0.9420',
    reason: 'Identified 14 structured disbursements under $100k threshold.',
    is_reversal: false,
    reversible: false
  },
  {
    id: 'audit-003',
    timestamp: '2026-04-01T08:08:20Z',
    company_id: MOCK_COMPANY.id,
    close_run_id: MOCK_CLOSE_RUN.id,
    exception_id: 'ex-po-002',
    event_type: 'ACTION_STAGED',
    actor: 'accountant@novascale.ai',
    actor_type: 'USER',
    control_id: 'PROC-04',
    financial_impact: '384000.00',
    currency: 'USD',
    reason: 'Staged debit memo entry for 240 unreceived GPU server units.',
    is_reversal: false,
    reversible: true
  },
  {
    id: 'audit-004',
    timestamp: '2026-04-01T08:09:45Z',
    company_id: MOCK_COMPANY.id,
    close_run_id: MOCK_CLOSE_RUN.id,
    exception_id: 'ex-dup-004',
    event_type: 'APPROVAL',
    actor: 'verification_agent',
    actor_type: 'AGENT',
    control_id: 'AP-09',
    financial_impact: '12450.00',
    currency: 'USD',
    confidence: '0.9780',
    decision: 'AUTO_RESOLVED',
    reason: 'Voided duplicate Slack subscription bill against verified payment card voucher.',
    is_reversal: false,
    reversible: true
  }
];

export const MOCK_BENCHMARK_SUMMARY: BenchmarkRunSummary = {
  id: 'bench-run-2026-04',
  run_timestamp: '2026-04-01T06:00:00Z',
  total_scenarios: 35,
  evaluated_scenarios: 35,
  action_accuracy: '1.0000',
  root_cause_accuracy: '1.0000',
  hallucination_rate: '0.0000',
  avg_latency_ms: 1420,
  total_cost_usd: '0.0248',
  calibration_report: {
    expected_calibration_error: '0.0182',
    brier_score: '0.0210',
    reliability_curve: [
      { confidence: 0.65, accuracy: 0.64 },
      { confidence: 0.75, accuracy: 0.76 },
      { confidence: 0.85, accuracy: 0.84 },
      { confidence: 0.92, accuracy: 0.91 },
      { confidence: 0.98, accuracy: 0.99 }
    ],
    buckets: [
      { bucket_min: 0.6, bucket_max: 0.7, sample_count: 3, mean_predicted_confidence: 0.65, empirical_accuracy: 0.66, calibration_error: 0.01 },
      { bucket_min: 0.7, bucket_max: 0.8, sample_count: 5, mean_predicted_confidence: 0.75, empirical_accuracy: 0.74, calibration_error: 0.01 },
      { bucket_min: 0.8, bucket_max: 0.9, sample_count: 9, mean_predicted_confidence: 0.85, empirical_accuracy: 0.86, calibration_error: 0.01 },
      { bucket_min: 0.9, bucket_max: 1.0, sample_count: 18, mean_predicted_confidence: 0.96, empirical_accuracy: 0.98, calibration_error: 0.02 }
    ]
  },
  scenario_details: [
    {
      scenario_id: 'SCENARIO-001',
      scenario_type: 'PAYMENT_FRAGMENTATION',
      title: 'Payment Fragmentation Scheme (14 sub-100k payments)',
      expected_action: 'ESCALATE',
      actual_action: 'ESCALATE',
      action_matched: true,
      expected_root_cause: 'fragmentation',
      actual_root_cause: 'payment fragmentation structuring',
      root_cause_matched: true,
      citations_valid: true,
      hallucinations_count: 0,
      raw_confidence: '0.9800',
      calibrated_confidence: '0.9400',
      latency_ms: 1820,
      financial_impact: '1450000.00'
    },
    {
      scenario_id: 'SCENARIO-002',
      scenario_type: 'PO_MISMATCH',
      title: '3-Way Match Quantity Variance (240 units unreceived)',
      expected_action: 'STAGE',
      actual_action: 'STAGE',
      action_matched: true,
      expected_root_cause: 'quantity mismatch',
      actual_root_cause: '240 units unreceived exceeds tolerance',
      root_cause_matched: true,
      citations_valid: true,
      hallucinations_count: 0,
      raw_confidence: '0.9700',
      calibrated_confidence: '0.9100',
      latency_ms: 1350,
      financial_impact: '384000.00'
    },
    {
      scenario_id: 'SCENARIO-003',
      scenario_type: 'OTHER',
      title: 'Clean 6-Way Multi-Currency Reconciliation',
      expected_action: 'AUTO_RESOLVE',
      actual_action: 'AUTO_RESOLVE',
      action_matched: true,
      expected_root_cause: 'clean',
      actual_root_cause: 'clean transaction within variance limit',
      root_cause_matched: true,
      citations_valid: true,
      hallucinations_count: 0,
      raw_confidence: '0.9990',
      calibrated_confidence: '0.9950',
      latency_ms: 890,
      financial_impact: '0.42'
    },
    {
      scenario_id: 'SCENARIO-004',
      scenario_type: 'DUPLICATE_INVOICE',
      title: 'Identical Subledger Duplicate Invoice Submission',
      expected_action: 'AUTO_RESOLVE',
      actual_action: 'AUTO_RESOLVE',
      action_matched: true,
      expected_root_cause: 'duplicate invoice',
      actual_root_cause: 'duplicate invoice matching existing settled bill',
      root_cause_matched: true,
      citations_valid: true,
      hallucinations_count: 0,
      raw_confidence: '0.9900',
      calibrated_confidence: '0.9800',
      latency_ms: 1120,
      financial_impact: '12450.00'
    },
    {
      scenario_id: 'SCENARIO-005',
      scenario_type: 'VENDOR_BANK_CHANGE_ANOMALY',
      title: 'Unverified Vendor Routing Number Modification',
      expected_action: 'ESCALATE',
      actual_action: 'ESCALATE',
      action_matched: true,
      expected_root_cause: 'bank change without dual authorization',
      actual_root_cause: 'unverified offshore bank modification',
      root_cause_matched: true,
      citations_valid: true,
      hallucinations_count: 0,
      raw_confidence: '0.9650',
      calibrated_confidence: '0.9200',
      latency_ms: 1490,
      financial_impact: '210000.00'
    }
  ]
};

export const MOCK_DEMO_TRACES: DemoTrace[] = [
  {
    trace_id: 'trace-golden-01',
    scenario_id: 'SCENARIO-001',
    title: 'Golden Demo 1: Payment Fragmentation ($1.45M Structured Payments)',
    description: 'Autonomous detection of 14 disbursements structured under $100k, forensic graph assembly, citation validation, and CFO escalation.',
    duration_ms: 45000,
    frames_count: 42
  },
  {
    trace_id: 'trace-golden-02',
    scenario_id: 'SCENARIO-002',
    title: 'Golden Demo 2: PO Quantity Mismatch ($384k Unreceived Servers)',
    description: '3-way reconciliation detects 240 missing server units, stages compensating journal entry, and routes to Controller for sign-off.',
    duration_ms: 32000,
    frames_count: 28
  },
  {
    trace_id: 'trace-golden-03',
    scenario_id: 'SCENARIO-003',
    title: 'Golden Demo 3: Zero-Touch 6-Way Multi-Currency Auto-Resolution',
    description: 'Automated 10-pass reconciliation clears cross-border transactions and auto-adjusts FX rounding variance under SOX control catalog.',
    duration_ms: 18000,
    frames_count: 16
  }
];
