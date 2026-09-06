export type ExceptionType =
  | 'PAYMENT_FRAGMENTATION'
  | 'PO_MISMATCH'
  | 'DUPLICATE_INVOICE'
  | 'DUPLICATE_PAYMENT'
  | 'RECEIPT_MISMATCH'
  | 'MISSING_DOCUMENT'
  | 'UNUSUAL_VENDOR_ACTIVITY'
  | 'GL_MAPPING_ERROR'
  | 'ACCRUAL_ANOMALY'
  | 'AR_MISMATCH'
  | 'CASH_ANOMALY'
  | 'VENDOR_BANK_CHANGE_ANOMALY'
  | 'DATA_INGESTION_GAP'
  | 'BANK_DUPLICATE'
  | 'OTHER';

export type ExceptionSeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

export type ExceptionStatus =
  | 'OPEN'
  | 'INVESTIGATING'
  | 'VERIFYING'
  | 'STAGED'
  | 'APPROVED'
  | 'RESOLVED'
  | 'REJECTED'
  | 'ESCALATED'
  | 'REOPENED';

export type AutonomyLevel =
  | 'LEVEL_3_AUTO_RESOLVE'
  | 'LEVEL_2_STAGE'
  | 'LEVEL_1_RECOMMEND'
  | 'LEVEL_0_OBSERVE';

export interface EvidenceItem {
  id: string;
  node_id: string;
  node_type: string;
  label: string;
  record_id?: string;
  amount?: string;
  currency?: string;
  properties?: Record<string, unknown>;
  relevance_score?: number;
}

export interface CalculationProof {
  formula: string;
  variables: Record<string, string | number>;
  expected: string;
  actual: string;
  variance: string;
  is_material: boolean;
}

export interface CitationReference {
  citation_id: string;
  record_type: string;
  record_id: string;
  document_ref: string;
  verified_in_db: boolean;
}

export interface ExceptionRecord {
  id: string;
  company_id: string;
  close_run_id?: string;
  type: ExceptionType;
  severity: ExceptionSeverity;
  status: ExceptionStatus;
  autonomy_level?: AutonomyLevel;
  title: string;
  description: string;
  financial_impact: string;
  currency: string;
  detected_at: string;
  assigned_to?: string;
  root_cause?: string;
  suggested_action?: string;
  raw_confidence?: string;
  calibrated_confidence?: string;
  evidence_count?: number;
  evidence?: EvidenceItem[];
  citations?: CitationReference[];
  calculation_proof?: CalculationProof;
  staged_action?: {
    action_type: string;
    description: string;
    debit_account?: string;
    credit_account?: string;
    amount: string;
    currency: string;
    staged_by?: string;
    staged_at?: string;
  };
  investigation_model?: string;
  verification_model?: string;
  verification_status?: 'PRESERVED' | 'COMPROMISED' | 'SKIPPED';
  recommended_action?: string;
  confidence?: number;
  metadata_?: Record<string, unknown>;
  created_at?: string;
  updated_at?: string;
  resolved_at?: string;
  source_invoice_id?: string;
  source_po_id?: string;
  source_payment_id?: string;
  source_bank_txn_id?: string;
}

export type Exception = ExceptionRecord;

export interface ActionResponse {
  action_id: string;
  exception_id: string;
  action_type: string;
  status: string;
  message?: string;
  payload?: Record<string, unknown>;
  actor: string;
  executed_at: string;
}
