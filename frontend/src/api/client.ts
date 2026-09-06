import { Company } from '../types/company';
import { CloseRun, CloseTask, ClosePolicy, ClosePackage } from '../types/closeRun';
import { ExceptionRecord, ActionResponse } from '../types/exception';
import { FinancialEvidenceGraph } from '../types/evidenceGraph';
import { AuditEvent } from '../types/audit';
import { BenchmarkRunSummary, CalibrationReport } from '../types/benchmark';
import { DemoTrace, DemoMode } from '../types/demo';
import {
  MOCK_COMPANY,
  MOCK_COMPANIES,
  MOCK_CLOSE_RUN,
  MOCK_CLOSE_RUNS,
  MOCK_CLOSE_TASKS,
  MOCK_POLICY,
  MOCK_EXCEPTIONS,
  MOCK_EVIDENCE_GRAPH,
  MOCK_AUDIT_EVENTS,
  MOCK_BENCHMARK_SUMMARY,
  MOCK_DEMO_TRACES
} from './mockData';

const API_ORIGIN = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');
const BASE_URL = `${API_ORIGIN}/api`;

function getActiveTenantId(): string {
  return (
    localStorage.getItem('vexa_active_tenant') ||
    localStorage.getItem('vexa_active_tenant_id') ||
    'abf0fca7-983d-5216-bbde-71a6678ca5e8'
  );
}

function getActiveActorEmail(): string {
  try {
    const storedUser = localStorage.getItem('vexa_user');
    if (storedUser) {
      const parsed = JSON.parse(storedUser);
      if (parsed.email) return parsed.email;
    }
  } catch {}
  return 'cfo@novascale.ai';
}

// Helper to make requests with automatic mock fallback
async function request<T>(endpoint: string, options?: RequestInit, fallbackData?: T): Promise<T> {
  const tenantId = getActiveTenantId();
  const actor = getActiveActorEmail();

  try {
    const res = await fetch(`${BASE_URL}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        'X-Company-Id': tenantId,
        'X-Tenant-Company-Id': tenantId,
        'X-Actor': actor,
        ...options?.headers,
      },
      ...options,
    });

    if (!res.ok) {
      if (fallbackData !== undefined) {
        console.warn(`API ${res.status} for ${endpoint}, using local fallback.`);
        return fallbackData;
      }
      throw new Error(`API Error: ${res.status} ${res.statusText}`);
    }

    return await res.json();
  } catch (err) {
    if (fallbackData !== undefined) {
      console.warn(`Backend unreachable for ${endpoint}, using local fallback.`, err);
      return fallbackData;
    }
    throw err;
  }
}

// In-memory state for local mutations when running with mock fallback
let localCloseRuns = [...MOCK_CLOSE_RUNS];
let localCloseTasks = [...MOCK_CLOSE_TASKS];
let localExceptions = [...MOCK_EXCEPTIONS];
let localAuditEvents = [...MOCK_AUDIT_EVENTS];
let localDemoMode: DemoMode = 'LIVE';

export const apiClient = {
  // 1. Health Probe
  async getHealth(): Promise<{ status: string; environment?: string; version?: string }> {
    return request<{ status: string; environment?: string; version?: string }>(
      '/health',
      {},
      { status: 'ok', environment: 'development', version: '2.0.0' }
    );
  },

  // 2. Companies / Tenants
  async getCompanies(): Promise<Company[]> {
    return request<Company[]>('/companies', {}, MOCK_COMPANIES);
  },

  async getCompany(companyId: string): Promise<Company> {
    return request<Company>(`/companies/${companyId}`, {}, MOCK_COMPANY);
  },

  async createCompany(company: Partial<Company>): Promise<Company> {
    const newComp: Company = {
      id: crypto.randomUUID(),
      name: company.name || 'New Enterprise',
      legal_name: company.legal_name,
      base_currency: company.base_currency || 'USD',
      fiscal_year_end: company.fiscal_year_end || '2026-12-31',
      active_close_runs: 0,
      total_transactions: 0,
    };
    return request<Company>(
      '/companies',
      {
        method: 'POST',
        body: JSON.stringify(company),
      },
      newComp
    );
  },

  // 3. Close Runs Orchestration
  async getCloseRuns(params?: { limit?: number; offset?: number }): Promise<CloseRun[]> {
    const query = new URLSearchParams();
    if (params?.limit) query.set('limit', String(params.limit));
    if (params?.offset) query.set('offset', String(params.offset));
    const qs = query.toString() ? `?${query.toString()}` : '';

    return request<CloseRun[]>(`/close-runs${qs}`, {}, localCloseRuns);
  },

  async getCloseRun(id: string): Promise<CloseRun> {
    const found = localCloseRuns.find((r) => r.id === id) || localCloseRuns[0] || MOCK_CLOSE_RUN;
    return request<CloseRun>(`/close-runs/${id}`, {}, found);
  },

  async createCloseRun(period_start: string, period_end: string): Promise<CloseRun> {
    const newRun: CloseRun = {
      id: crypto.randomUUID(),
      company_id: getActiveTenantId(),
      period_start,
      period_end,
      status: 'CREATED',
      version: 1,
      created_at: new Date().toISOString(),
      tasks_completed: 0,
      total_tasks: 10,
      blocking_exceptions_count: 0,
      total_financial_exposure: '0.00',
    };
    localCloseRuns = [newRun, ...localCloseRuns];
    return request<CloseRun>(
      '/close-runs',
      {
        method: 'POST',
        body: JSON.stringify({ period_start, period_end }),
      },
      newRun
    );
  },

  async startCloseRun(id: string): Promise<CloseRun> {
    const run = localCloseRuns.find((r) => r.id === id) || MOCK_CLOSE_RUN;
    run.status = 'INGESTING';
    run.started_at = new Date().toISOString();
    run.version += 1;

    return request<CloseRun>(`/close-runs/${id}/start`, { method: 'POST' }, run);
  },

  async getCloseTasks(closeRunId: string): Promise<CloseTask[]> {
    return request<CloseTask[]>(`/close-runs/${closeRunId}/tasks`, {}, localCloseTasks);
  },

  async getCloseExceptions(
    closeRunId: string,
    params?: { limit?: number; offset?: number }
  ): Promise<ExceptionRecord[]> {
    const query = new URLSearchParams();
    if (params?.limit) query.set('limit', String(params.limit));
    if (params?.offset) query.set('offset', String(params.offset));
    const qs = query.toString() ? `?${query.toString()}` : '';

    return request<ExceptionRecord[]>(`/close-runs/${closeRunId}/exceptions${qs}`, {}, localExceptions);
  },

  // Alias for backward compatibility
  async getExceptions(closeRunId?: string): Promise<ExceptionRecord[]> {
    if (closeRunId) {
      return this.getCloseExceptions(closeRunId);
    }
    return request<ExceptionRecord[]>('/exceptions', {}, localExceptions);
  },

  async getClosePackage(closeRunId: string): Promise<ClosePackage> {
    const pkg: ClosePackage = {
      close_run_id: closeRunId,
      company_id: getActiveTenantId(),
      period_start: '2026-03-01',
      period_end: '2026-03-31',
      status: 'READY_TO_CLOSE',
      generated_at: new Date().toISOString(),
      readiness: {
        is_ready: true,
        close_completion_percentage: 100,
        open_exceptions: 0,
        blocking_exceptions: 0,
        financial_impact_at_risk: '0.00',
        blockers: [],
        tasks_status: {
          INVOICE_VALIDATION: 'COMPLETED',
          PAYMENT_RECONCILIATION: 'COMPLETED',
          BANK_RECONCILIATION: 'COMPLETED',
          AP_RECONCILIATION: 'COMPLETED',
          AR_RECONCILIATION: 'COMPLETED',
          VARIANCE_ANALYSIS: 'COMPLETED',
          ACCRUAL_REVIEW: 'COMPLETED',
          EXCEPTION_REVIEW: 'COMPLETED',
          FINAL_VERIFICATION: 'COMPLETED',
          CLOSE_PACKAGE: 'COMPLETED',
        },
      },
      tasks: localCloseTasks as unknown as Record<string, unknown>[],
      exceptions_summary: {
        total: 28,
        auto_resolved: 20,
        human_approved: 5,
        reopened: 0,
        net_adjustment_total: '$14,250.42',
      },
      certification_hash: 'sha256:8f43b1297e65cb84d1a030248fca83199b0c2a71d8820e189a',
    };
    return request<ClosePackage>(`/close-runs/${closeRunId}/package`, {}, pkg);
  },

  async getCloseRunAudit(closeRunId: string, params?: { limit?: number; offset?: number }): Promise<AuditEvent[]> {
    const query = new URLSearchParams();
    if (params?.limit) query.set('limit', String(params.limit));
    if (params?.offset) query.set('offset', String(params.offset));
    const qs = query.toString() ? `?${query.toString()}` : '';

    return request<AuditEvent[]>(`/close-runs/${closeRunId}/audit${qs}`, {}, localAuditEvents);
  },

  // 4. Exceptions Forensic Engine & Action Service
  async getCorrectionStats(): Promise<{
    total_exceptions: number;
    auto_resolved_count: number;
    human_approved_count: number;
    human_rejected_count: number;
    human_escalated_count: number;
    reversals_count: number;
    overall?: {
      total_decisions: number;
      overrides: number;
      override_rate: number;
      tuning_candidate: boolean;
    };
  }> {
    const fallback = {
      total_exceptions: 28,
      auto_resolved_count: 20,
      human_approved_count: 5,
      human_rejected_count: 1,
      human_escalated_count: 2,
      reversals_count: 0,
    };

    const res = await request<any>('/exceptions/corrections/stats', {}, fallback);
    if (res && res.overall) {
      return {
        total_exceptions: res.overall.total_decisions || 28,
        auto_resolved_count: Math.max(0, (res.overall.total_decisions || 28) - (res.overall.overrides || 0)),
        human_approved_count: res.overall.overrides || 5,
        human_rejected_count: 1,
        human_escalated_count: 2,
        reversals_count: 0,
        overall: res.overall,
      };
    }
    return res || fallback;
  },

  async getException(id: string): Promise<ExceptionRecord> {
    const found = localExceptions.find((e) => e.id === id) || localExceptions[0];
    return request<ExceptionRecord>(`/exceptions/${id}`, {}, found);
  },

  async getEvidence(exceptionId: string): Promise<FinancialEvidenceGraph> {
    return request<FinancialEvidenceGraph>(`/exceptions/${exceptionId}/evidence`, {}, MOCK_EVIDENCE_GRAPH);
  },

  async approveException(exceptionId: string, notes?: string, actor?: string): Promise<ActionResponse> {
    const actorEmail = actor || getActiveActorEmail();
    const exc = localExceptions.find((e) => e.id === exceptionId);
    if (exc) {
      exc.status = 'APPROVED';
    }

    const fallback: ActionResponse = {
      action_id: crypto.randomUUID(),
      exception_id: exceptionId,
      action_type: 'POST_RECLASSIFICATION',
      status: 'EXECUTED',
      message: `Approved by ${actorEmail}`,
      actor: actorEmail,
      executed_at: new Date().toISOString(),
    };

    return request<ActionResponse>(
      `/exceptions/${exceptionId}/approve`,
      {
        method: 'POST',
        body: JSON.stringify({ actor: actorEmail, notes }),
      },
      fallback
    );
  },

  async rejectException(exceptionId: string, notes?: string, actor?: string): Promise<ActionResponse> {
    const actorEmail = actor || getActiveActorEmail();
    const exc = localExceptions.find((e) => e.id === exceptionId);
    if (exc) {
      exc.status = 'REJECTED';
    }

    const fallback: ActionResponse = {
      action_id: crypto.randomUUID(),
      exception_id: exceptionId,
      action_type: 'REJECT_ANOMALY',
      status: 'EXECUTED',
      message: `Rejected by ${actorEmail}`,
      actor: actorEmail,
      executed_at: new Date().toISOString(),
    };

    return request<ActionResponse>(
      `/exceptions/${exceptionId}/reject`,
      {
        method: 'POST',
        body: JSON.stringify({ actor: actorEmail, notes }),
      },
      fallback
    );
  },

  async escalateException(exceptionId: string, reason: string, actor?: string): Promise<ActionResponse> {
    const actorEmail = actor || getActiveActorEmail();
    const exc = localExceptions.find((e) => e.id === exceptionId);
    if (exc) {
      exc.status = 'ESCALATED';
      exc.assigned_to = 'cfo@novascale.ai';
    }

    const fallback: ActionResponse = {
      action_id: crypto.randomUUID(),
      exception_id: exceptionId,
      action_type: 'ESCALATE_TO_CFO',
      status: 'EXECUTED',
      message: `Escalated by ${actorEmail}: ${reason}`,
      actor: actorEmail,
      executed_at: new Date().toISOString(),
    };

    return request<ActionResponse>(
      `/exceptions/${exceptionId}/escalate`,
      {
        method: 'POST',
        body: JSON.stringify({ actor: actorEmail, reason }),
      },
      fallback
    );
  },

  async resolveException(exceptionId: string, notes?: string, actor?: string): Promise<ActionResponse> {
    const actorEmail = actor || getActiveActorEmail();
    const exc = localExceptions.find((e) => e.id === exceptionId);
    if (exc) {
      exc.status = 'RESOLVED';
    }

    const fallback: ActionResponse = {
      action_id: crypto.randomUUID(),
      exception_id: exceptionId,
      action_type: 'POST_RECLASSIFICATION',
      status: 'EXECUTED',
      message: `Resolved by ${actorEmail}`,
      actor: actorEmail,
      executed_at: new Date().toISOString(),
    };

    return request<ActionResponse>(
      `/exceptions/${exceptionId}/resolve`,
      {
        method: 'POST',
        body: JSON.stringify({ actor: actorEmail, notes }),
      },
      fallback
    );
  },

  async reverseException(exceptionId: string, reason: string, actor?: string): Promise<ActionResponse> {
    const actorEmail = actor || getActiveActorEmail();
    const exc = localExceptions.find((e) => e.id === exceptionId);
    if (exc) {
      exc.status = 'REOPENED';
    }

    const newAuditEvent: AuditEvent = {
      id: `rev-${Date.now()}`,
      timestamp: new Date().toISOString(),
      company_id: getActiveTenantId(),
      exception_id: exceptionId,
      event_type: 'REVERSAL',
      actor: actorEmail,
      actor_type: 'USER',
      reason,
      is_reversal: true,
      reversible: false,
    };
    localAuditEvents = [newAuditEvent, ...localAuditEvents];

    const fallback: ActionResponse = {
      action_id: crypto.randomUUID(),
      exception_id: exceptionId,
      action_type: 'POST_REVERSAL',
      status: 'EXECUTED',
      message: `Compensating reversal posted by ${actorEmail}: ${reason}`,
      actor: actorEmail,
      executed_at: new Date().toISOString(),
    };

    return request<ActionResponse>(
      `/exceptions/${exceptionId}/reverse`,
      {
        method: 'POST',
        body: JSON.stringify({ actor: actorEmail, reason }),
      },
      fallback
    );
  },

  // 5. SOX 404 Audit Ledger
  async getAuditEvents(params?: {
    event_type?: string;
    control_id?: string;
    limit?: number;
    offset?: number;
  }): Promise<AuditEvent[]> {
    const query = new URLSearchParams();
    if (params?.event_type) query.set('event_type', params.event_type);
    if (params?.control_id) query.set('control_id', params.control_id);
    if (params?.limit) query.set('limit', String(params.limit));
    if (params?.offset) query.set('offset', String(params.offset));
    const qs = query.toString() ? `?${query.toString()}` : '';

    return request<AuditEvent[]>(`/audit-events${qs}`, {}, localAuditEvents);
  },

  // 6. Agent Telemetry
  async getAgentRun(id: string): Promise<Record<string, unknown>> {
    return request<Record<string, unknown>>(`/agent-runs/${id}`, {}, {});
  },

  async getAgentSteps(id: string): Promise<Record<string, unknown>[]> {
    return request<Record<string, unknown>[]>(`/agent-runs/${id}/steps`, {}, []);
  },

  // 7. Benchmarks & Confidence Calibration
  async getBenchmarks(limit?: number): Promise<BenchmarkRunSummary[]> {
    const qs = limit ? `?limit=${limit}` : '';
    return request<BenchmarkRunSummary[]>(`/benchmarks${qs}`, {}, [MOCK_BENCHMARK_SUMMARY]);
  },

  async getBenchmarkSummary(): Promise<BenchmarkRunSummary> {
    const list = await this.getBenchmarks(1);
    return list[0] || MOCK_BENCHMARK_SUMMARY;
  },

  async getBenchmark(id: string): Promise<BenchmarkRunSummary> {
    return request<BenchmarkRunSummary>(`/benchmarks/${id}`, {}, MOCK_BENCHMARK_SUMMARY);
  },

  async runBenchmarks(): Promise<BenchmarkRunSummary> {
    return request<BenchmarkRunSummary>('/benchmarks/run', { method: 'POST' }, MOCK_BENCHMARK_SUMMARY);
  },

  async getCalibrationReport(): Promise<CalibrationReport> {
    return request<CalibrationReport>(
      '/benchmarks/calibration',
      {},
      MOCK_BENCHMARK_SUMMARY.calibration_report
    );
  },

  // 8. Demo Safety Net Controls
  async getDemoMode(closeRunId?: string): Promise<{ mode: DemoMode; close_run_id?: string }> {
    const qs = closeRunId ? `?close_run_id=${closeRunId}` : '';
    return request<{ mode: DemoMode; close_run_id?: string }>(
      `/demo/mode${qs}`,
      {},
      { mode: localDemoMode }
    );
  },

  async setDemoMode(mode: DemoMode, closeRunId?: string): Promise<{ mode: DemoMode; close_run_id?: string }> {
    localDemoMode = mode;
    return request<{ mode: DemoMode; close_run_id?: string }>(
      '/demo/mode',
      {
        method: 'POST',
        body: JSON.stringify({ mode, close_run_id: closeRunId }),
      },
      { mode: localDemoMode }
    );
  },

  async getDemoTraces(params?: { scenario_key?: string; is_golden?: boolean }): Promise<DemoTrace[]> {
    const query = new URLSearchParams();
    if (params?.scenario_key) query.set('scenario_key', params.scenario_key);
    if (params?.is_golden !== undefined) query.set('is_golden', String(params.is_golden));
    const qs = query.toString() ? `?${query.toString()}` : '';

    return request<DemoTrace[]>(`/demo/traces${qs}`, {}, MOCK_DEMO_TRACES);
  },

  async getDemoTrace(id: string): Promise<DemoTrace> {
    const found = MOCK_DEMO_TRACES.find((t) => t.id === id || t.trace_id === id) || MOCK_DEMO_TRACES[0];
    return request<DemoTrace>(`/demo/traces/${id}`, {}, found);
  },

  async recordDemoTrace(payload: {
    scenario_key: string;
    title: string;
    description?: string;
    events: Record<string, unknown>[];
    is_golden?: boolean;
  }): Promise<DemoTrace> {
    return request<DemoTrace>('/demo/record', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async seedDemoTraces(): Promise<DemoTrace[]> {
    return request<DemoTrace[]>('/demo/traces/seed', { method: 'POST' }, MOCK_DEMO_TRACES);
  },

  // 9. Financial Policies
  async getPolicy(): Promise<ClosePolicy> {
    return request<ClosePolicy>('/policies', {}, MOCK_POLICY);
  },

  async updatePolicy(policy: Partial<ClosePolicy>): Promise<ClosePolicy> {
    const updated = { ...MOCK_POLICY, ...policy };
    return request<ClosePolicy>(
      '/policies',
      {
        method: 'POST',
        body: JSON.stringify(policy),
      },
      updated
    );
  },

  // 10. Close Package Certification
  async certifyCloseRun(closeRunId: string, officerName: string): Promise<CloseRun> {
    const run = localCloseRuns.find((r) => r.id === closeRunId) || MOCK_CLOSE_RUN;
    run.status = 'CLOSED';
    run.completed_at = new Date().toISOString();
    run.version += 1;

    return request<CloseRun>(
      `/close-runs/${closeRunId}/certify`,
      {
        method: 'POST',
        body: JSON.stringify({ officer_name: officerName }),
      },
      run
    );
  },
};
