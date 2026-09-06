export type AuditEventType =
  | 'CLOSE_RUN_STATE_CHANGE'
  | 'CLOSE_TASK_STATE_CHANGE'
  | 'RECONCILIATION_PASS'
  | 'EXCEPTION_DETECTED'
  | 'INVESTIGATION_COMPLETED'
  | 'VERIFICATION_COMPLETED'
  | 'ACTION_STAGED'
  | 'APPROVAL'
  | 'REJECTION'
  | 'REVERSAL'
  | 'POLICY_CHANGE'
  | 'DEMO_MODE_TOGGLE';

export type ActorType = 'USER' | 'AGENT' | 'CONTROLLER' | 'SYSTEM';

export interface AuditEvent {
  id: string;
  timestamp: string;
  company_id: string;
  close_run_id?: string;
  exception_id?: string;
  action_id?: string;
  reversal_action_id?: string;
  event_type: AuditEventType;
  actor: string;
  actor_type: ActorType;
  agent_name?: string;
  policy_version_id?: string;
  prompt_version_id?: string;
  decision?: string;
  reason?: string;
  control_id?: string;
  financial_impact?: string;
  currency?: string;
  confidence?: string;
  is_reversal: boolean;
  reversible: boolean;
  metadata?: Record<string, unknown>;
}

export interface ReversalAction {
  id: string;
  original_action_id: string;
  exception_id: string;
  company_id: string;
  executed_by: string;
  executed_at: string;
  reason: string;
  reversal_entry?: {
    debit_account: string;
    credit_account: string;
    amount: string;
    currency: string;
  };
}
