export type CloseRunStatus =
  | 'CREATED'
  | 'INGESTING'
  | 'RECONCILING'
  | 'INVESTIGATING'
  | 'VERIFYING'
  | 'WAITING_FOR_HUMAN'
  | 'RESOLVING'
  | 'FINAL_VERIFICATION'
  | 'READY_TO_CLOSE'
  | 'CLOSED'
  | 'BLOCKED'
  | 'FAILED'
  | 'RUNNING';

export type CloseTaskType =
  | 'INVOICE_VALIDATION'
  | 'PAYMENT_RECONCILIATION'
  | 'BANK_RECONCILIATION'
  | 'AP_RECONCILIATION'
  | 'AR_RECONCILIATION'
  | 'VARIANCE_ANALYSIS'
  | 'ACCRUAL_REVIEW'
  | 'EXCEPTION_REVIEW'
  | 'FINAL_VERIFICATION'
  | 'CLOSE_PACKAGE';

export type CloseTaskStatus = 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'FAILED' | 'BLOCKED';

export interface CloseTask {
  id: string;
  close_run_id: string;
  task_type: CloseTaskType;
  status: CloseTaskStatus;
  started_at?: string;
  completed_at?: string;
  duration_ms?: number;
  result_summary?: string;
  error_message?: string;
  metrics?: Record<string, unknown>;
  name?: string;
  confidenceScore?: number;
}

export interface CloseRun {
  id: string;
  company_id?: string;
  companyId?: string;
  period_start?: string;
  period_end?: string;
  period?: string;
  status: CloseRunStatus;
  version: number;
  started_at?: string;
  startedAt?: string;
  completed_at?: string;
  completedAt?: string;
  created_at?: string;
  updated_at?: string;
  close_summary?: string;
  tasks_completed?: number;
  completedTasks?: number;
  total_tasks?: number;
  totalTasks?: number;
  blocking_exceptions_count?: number;
  exceptionsCount?: number;
  total_financial_exposure?: string;
  reconciledVolume?: number;
}

export interface ClosePolicy {
  policy_version_id?: string;
  max_auto_resolution_amount: string;
  materiality_threshold: string;
  min_confidence: string;
  approval_timeout_hours: number;
  required_approvers_material: string[];
}

export interface CloseReadiness {
  is_ready: boolean;
  close_completion_percentage: number;
  open_exceptions: number;
  blocking_exceptions: number;
  financial_impact_at_risk: string;
  blockers: string[];
  tasks_status: Record<string, string>;
}

export interface ClosePackage {
  close_run_id: string;
  company_id: string;
  period_start: string;
  period_end: string;
  status: string;
  generated_at: string;
  readiness: CloseReadiness;
  tasks: Record<string, unknown>[];
  exceptions_summary: {
    total: number;
    auto_resolved: number;
    human_approved: number;
    reopened: number;
    net_adjustment_total: string;
  };
  certified_by?: string;
  certification_hash?: string;
}
