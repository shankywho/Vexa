import React, { useState, useEffect, useRef } from 'react';
import { useCloseRun } from '../../context/CloseRunContext';
import { CloseRunEventStream } from '../../api/sse';
import { Terminal, Radio, Pause, Play, Download, ShieldCheck, Zap } from 'lucide-react';

interface AgentStepLog {
  id: string;
  timestamp: string;
  agent_name: string;
  provider: string;
  tool: string;
  status: string;
  latency_ms: number;
  tokens_used: number;
  detail: string;
}

export const AgentTelemetryPage: React.FC = () => {
  const { activeRun } = useCloseRun();
  const [logs, setLogs] = useState<AgentStepLog[]>([
    {
      id: 'step-1',
      timestamp: '08:00:15',
      agent_name: 'Reconciliation Agent',
      provider: 'Groq (qwen3.8-27b)',
      tool: 'reconcile_bank_to_ledger',
      status: 'MATCHED',
      latency_ms: 120,
      tokens_used: 342,
      detail: 'Reconciled 1,420 bank statement rows with $0.00 cash variance.',
    },
    {
      id: 'step-2',
      timestamp: '08:02:18',
      agent_name: 'CFO Investigation Agent',
      provider: 'Mistral (codestral-latest)',
      tool: 'traverse_financial_graph',
      status: 'ANOMALY_FOUND',
      latency_ms: 410,
      tokens_used: 820,
      detail: 'Traversed 16 graph nodes for Invoice #INV-2026-881. Detected 14 structured payments of $100,000.',
    },
    {
      id: 'step-3',
      timestamp: '08:02:45',
      agent_name: 'Verification Agent',
      provider: 'Groq (qwen3.8-27b)',
      tool: 'verify_independent_reasoning',
      status: 'PRESERVED',
      latency_ms: 180,
      tokens_used: 410,
      detail: 'Cross-model verification guarantee PRESERVED. Independent review confirms payment fragmentation.',
    },
    {
      id: 'step-4',
      timestamp: '08:05:12',
      agent_name: 'Financial Analyst Agent',
      provider: 'Groq (qwen3.8-27b)',
      tool: 'calculate_account_variances',
      status: 'COMPLETED',
      latency_ms: 240,
      tokens_used: 512,
      detail: 'Budget variance analysis completed. Net cash flow variance: +$1.34M favorable.',
    },
  ]);

  const [isFollowing, setIsFollowing] = useState(true);
  const terminalEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const stream = new CloseRunEventStream(activeRun.id);
    const unsubscribe = stream.subscribe((event, data) => {
      if (event === 'agent_step') {
        setLogs((prev) => [
          ...prev,
          {
            id: data.step_id || `step-${Date.now()}`,
            timestamp: new Date().toLocaleTimeString(),
            agent_name: data.agent_name || 'Autonomous Agent',
            provider: data.provider || 'Groq / Mistral',
            tool: data.tool || 'execute_tool',
            status: data.status || 'OK',
            latency_ms: data.latency_ms || 200,
            tokens_used: data.tokens_used || 350,
            detail: data.detail || 'Executed tool pass.',
          },
        ]);
      }
    });

    stream.connect();
    return () => {
      unsubscribe();
      stream.disconnect();
    };
  }, [activeRun.id]);

  useEffect(() => {
    if (isFollowing) {
      terminalEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, isFollowing]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', width: '100%' }}>
      {/* Top Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h2 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 800, color: 'var(--color-neutral-950)' }}>
            Real-Time Agent Telemetry Stream
          </h2>
          <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-neutral-500)', marginTop: '0.15rem' }}>
            Live SSE telemetry bus broadcasting agent steps, multi-model verification, and token metrics.
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <button
            onClick={() => setIsFollowing(!isFollowing)}
            className="btn-secondary"
            style={{ fontSize: 'var(--font-size-xs)' }}
          >
            {isFollowing ? <Pause size={14} /> : <Play size={14} />}
            {isFollowing ? 'Pause Auto-Scroll' : 'Resume Auto-Scroll'}
          </button>
        </div>
      </div>

      {/* Terminal Display */}
      <div
        style={{
          background: 'var(--color-neutral-1000)',
          borderRadius: 'var(--radius-md)',
          border: '1px solid rgba(255, 255, 255, 0.12)',
          boxShadow: 'var(--shadow-xl)',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          height: '520px',
        }}
      >
        {/* Terminal Title Bar */}
        <div
          style={{
            background: '#1a1a1a',
            padding: '0.65rem 1rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#ef4444' }} />
            <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#f59e0b' }} />
            <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#22c55e' }} />
            <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-neutral-300)', marginLeft: '0.5rem' }}>
              vexa-telemetry-bus: /api/close-runs/{activeRun.id}/stream
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--color-accent-400)', fontSize: '0.72rem', fontWeight: 700 }}>
            <Radio size={12} className="animate-pulse-glow" />
            <span>SSE CONNECTED</span>
          </div>
        </div>

        {/* Terminal Output Body */}
        <div
          className="font-mono"
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '1.25rem',
            display: 'flex',
            flexDirection: 'column',
            gap: '0.85rem',
            fontSize: '0.82rem',
            lineHeight: 1.6,
          }}
        >
          {logs.map((log) => (
            <div
              key={log.id}
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: '1rem',
                borderBottom: '1px solid rgba(255, 255, 255, 0.04)',
                paddingBottom: '0.65rem',
              }}
            >
              <span style={{ color: 'var(--color-neutral-500)', flexShrink: 0 }}>[{log.timestamp}]</span>
              <span
                style={{
                  color: 'var(--color-primary-400)',
                  fontWeight: 700,
                  flexShrink: 0,
                  minWidth: '180px',
                }}
              >
                {log.agent_name}
              </span>
              <span
                style={{
                  background: 'rgba(255, 255, 255, 0.1)',
                  color: '#ffffff',
                  padding: '0.1rem 0.45rem',
                  borderRadius: 'var(--radius-xs)',
                  fontSize: '0.7rem',
                  flexShrink: 0,
                }}
              >
                {log.provider}
              </span>
              <span style={{ color: 'var(--color-secondary-400)', flexShrink: 0 }}>
                {log.tool}()
              </span>
              <span style={{ color: '#e5e5e5', flex: 1 }}>{log.detail}</span>
              <span style={{ color: 'var(--color-neutral-500)', fontSize: '0.72rem', flexShrink: 0 }}>
                {log.latency_ms}ms • {log.tokens_used} tok
              </span>
            </div>
          ))}
          <div ref={terminalEndRef} />
        </div>
      </div>
    </div>
  );
};
