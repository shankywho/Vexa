export type SSECallback = (event: string, data: any) => void;

const API_ORIGIN = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');

export class CloseRunEventStream {
  private eventSource: EventSource | null = null;
  private listeners: Set<SSECallback> = new Set();
  private mockInterval: any = null;
  private isConnected = false;

  constructor(private closeRunId: string, private useMockFallback = true) {}

  public subscribe(callback: SSECallback): () => void {
    this.listeners.add(callback);
    return () => this.listeners.delete(callback);
  }

  public connect(): void {
    if (this.isConnected) return;

    try {
      const companyId = localStorage.getItem('vexa_active_tenant_id') || 'abf0fca7-983d-5216-bbde-71a6678ca5e8';
      this.eventSource = new EventSource(`${API_ORIGIN}/api/close-runs/${this.closeRunId}/stream?company_id=${companyId}`);

      this.eventSource.onopen = () => {
        this.isConnected = true;
        this.emit('connected', { status: 'LIVE_STREAM_ACTIVE' });
      };

      this.eventSource.addEventListener('close_run_state_change', (e) => {
        try {
          const data = JSON.parse(e.data);
          this.emit('close_run_state_change', data);
        } catch {}
      });

      this.eventSource.addEventListener('close_task_state_change', (e) => {
        try {
          const data = JSON.parse(e.data);
          this.emit('close_task_state_change', data);
        } catch {}
      });

      this.eventSource.addEventListener('agent_step', (e) => {
        try {
          const data = JSON.parse(e.data);
          this.emit('agent_step', data);
        } catch {}
      });

      this.eventSource.addEventListener('actions_executed', (e) => {
        try {
          const data = JSON.parse(e.data);
          this.emit('actions_executed', data);
        } catch {}
      });

      this.eventSource.onerror = () => {
        if (this.eventSource) {
          this.eventSource.close();
          this.eventSource = null;
        }
        this.isConnected = false;
        if (this.useMockFallback) {
          this.startMockSimulation();
        }
      };
    } catch {
      if (this.useMockFallback) {
        this.startMockSimulation();
      }
    }
  }

  public disconnect(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
    if (this.mockInterval) {
      clearInterval(this.mockInterval);
      this.mockInterval = null;
    }
    this.isConnected = false;
  }

  private emit(event: string, data: any): void {
    this.listeners.forEach((listener) => listener(event, data));
  }

  private startMockSimulation(): void {
    if (this.mockInterval) return;

    const simulatedSteps = [
      {
        agent: 'Reconciliation Agent',
        provider: 'Groq (qwen3.8-27b)',
        tool: 'reconcile_bank_to_ledger',
        status: 'MATCHED',
        tokens: 342,
        latency_ms: 120,
        message: 'Reconciled 1,420 bank records against cash subledger.',
      },
      {
        agent: 'CFO Investigation Agent',
        provider: 'Mistral (codestral-latest)',
        tool: 'traverse_financial_graph',
        status: 'ANOMALY_FOUND',
        tokens: 685,
        latency_ms: 380,
        message: 'Traversing 16 nodes for Invoice #INV-2026-881: 14 sub-100k payment clusters identified.',
      },
      {
        agent: 'Verification Agent',
        provider: 'Groq (qwen3.8-27b)',
        tool: 'verify_calculations_and_citations',
        status: 'PRESERVED',
        tokens: 412,
        latency_ms: 190,
        message: 'Citation check: 100% database references valid. Calibrated confidence 0.9420.',
      },
      {
        agent: 'Financial Analyst Agent',
        provider: 'Groq (qwen3.8-27b)',
        tool: 'calculate_account_variances',
        status: 'COMPLETED',
        tokens: 520,
        latency_ms: 220,
        message: 'Account 2010 Accounts Payable variance within materiality threshold.',
      },
    ];

    let stepIndex = 0;
    this.emit('connected', { status: 'SIMULATED_REPLAY_ACTIVE' });

    this.mockInterval = setInterval(() => {
      const step = simulatedSteps[stepIndex % simulatedSteps.length];
      this.emit('agent_step', {
        step_id: `step-${Date.now()}`,
        timestamp: new Date().toISOString(),
        agent_name: step.agent,
        provider: step.provider,
        tool: step.tool,
        status: step.status,
        latency_ms: step.latency_ms,
        tokens_used: step.tokens,
        detail: step.message,
      });
      stepIndex++;
    }, 4000);
  }
}

export class DemoTraceEventStream {
  private eventSource: EventSource | null = null;
  private listeners: Set<SSECallback> = new Set();
  private isConnected = false;

  constructor(private traceId: string, private speed = 1) {}

  public subscribe(callback: SSECallback): () => void {
    this.listeners.add(callback);
    return () => this.listeners.delete(callback);
  }

  public connect(): void {
    if (this.isConnected) return;

    try {
      const companyId = localStorage.getItem('vexa_active_tenant_id') || 'abf0fca7-983d-5216-bbde-71a6678ca5e8';
      this.eventSource = new EventSource(`${API_ORIGIN}/api/demo/traces/${this.traceId}/stream?playback_speed=${this.speed}&company_id=${companyId}`);

      this.eventSource.onopen = () => {
        this.isConnected = true;
        this.emit('connected', { status: 'DEMO_TRACE_STREAM_ACTIVE' });
      };

      this.eventSource.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data);
          this.emit('frame', data);
        } catch {}
      };

      this.eventSource.onerror = () => {
        if (this.eventSource) {
          this.eventSource.close();
          this.eventSource = null;
        }
        this.isConnected = false;
      };
    } catch {}
  }

  public disconnect(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
    this.isConnected = false;
  }

  private emit(event: string, data: any): void {
    this.listeners.forEach((listener) => listener(event, data));
  }
}

