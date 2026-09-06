import React from 'react';
import { useCloseRun } from '../../context/CloseRunContext';
import { MetricCard } from '../common/MetricCard';
import {
  AlertOctagon,
  Clock,
  CheckCircle2,
  Lock,
  Play,
  TrendingUp,
  GitFork,
  AlertTriangle,
  Coins,
  ShieldAlert,
  ShieldCheck,
} from 'lucide-react';

interface CloseRunShellProps {
  activeTab: string;
  onSelectTab: (tabId: string) => void;
  children: React.ReactNode;
}

export const CloseRunShell: React.FC<CloseRunShellProps> = ({ onSelectTab, children }) => {
  const { activeRun, startRun } = useCloseRun();

  const renderStatusBanner = () => {
    switch (activeRun.status) {
      case 'BLOCKED':
        return (
          <div
            style={{
              background: '#fef2f2',
              border: '1px solid #fecaca',
              borderRadius: 'var(--radius-sm)',
              padding: '0.85rem 1.25rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: '1.25rem',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', color: '#991b1b' }}>
              <AlertOctagon size={20} />
              <div>
                <span style={{ fontWeight: 800 }}>Month-End Close BLOCKED: </span>
                <span>2 high-materiality anomalies pending CFO & Controller sign-offs ($1,834,000 at risk).</span>
              </div>
            </div>
            <button onClick={() => onSelectTab('approvals')} className="btn-primary" style={{ padding: '0.4rem 1rem' }}>
              Review Blocker Approvals →
            </button>
          </div>
        );

      case 'WAITING_FOR_HUMAN':
        return (
          <div
            style={{
              background: '#fffbeb',
              border: '1px solid #fde68a',
              borderRadius: 'var(--radius-sm)',
              padding: '0.85rem 1.25rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: '1.25rem',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', color: '#92400e' }}>
              <Clock size={20} />
              <div>
                <span style={{ fontWeight: 800 }}>Action Staged & Waiting for Human Review: </span>
                <span>Reconciliation completed. 2 staged proposals require Controller & CFO approval to advance.</span>
              </div>
            </div>
            <button onClick={() => onSelectTab('approvals')} className="btn-primary" style={{ padding: '0.4rem 1rem' }}>
              Review Staged Items →
            </button>
          </div>
        );

      case 'READY_TO_CLOSE':
        return (
          <div
            style={{
              background: '#f0fdf4',
              border: '1px solid #bbf7d0',
              borderRadius: 'var(--radius-sm)',
              padding: '0.85rem 1.25rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: '1.25rem',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', color: '#166534' }}>
              <CheckCircle2 size={20} />
              <div>
                <span style={{ fontWeight: 800 }}>Books Ready to Close (100% Reconciled): </span>
                <span>All 10 close tasks finished with zero unmitigated material exceptions.</span>
              </div>
            </div>
            <button onClick={() => onSelectTab('package')} className="btn-primary" style={{ padding: '0.4rem 1rem' }}>
              Certify & Sign Off →
            </button>
          </div>
        );

      case 'CLOSED':
        return (
          <div
            style={{
              background: '#eff6ff',
              border: '1px solid #bfdbfe',
              borderRadius: 'var(--radius-sm)',
              padding: '0.85rem 1.25rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: '1.25rem',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', color: '#1e40af' }}>
              <Lock size={20} />
              <div>
                <span style={{ fontWeight: 800 }}>Period Locked & Closed: </span>
                <span>Certified by CFO on {new Date(activeRun.completed_at || activeRun.updated_at || '').toLocaleDateString()}. Immutable audit archive sealed.</span>
              </div>
            </div>
            <button onClick={() => onSelectTab('package')} className="btn-secondary" style={{ padding: '0.4rem 1rem' }}>
              Download Certified PDF
            </button>
          </div>
        );

      case 'CREATED':
        return (
          <div
            style={{
              background: '#fafafa',
              border: '1px solid var(--color-neutral-300)',
              borderRadius: 'var(--radius-sm)',
              padding: '0.85rem 1.25rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: '1.25rem',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', color: 'var(--color-neutral-800)' }}>
              <Play size={20} color="var(--color-primary-500)" />
              <div>
                <span style={{ fontWeight: 800 }}>Close Run Initialized: </span>
                <span>Ledger transactions and bank feeds ready for autonomous ingestion.</span>
              </div>
            </div>
            <button onClick={startRun} className="btn-primary" style={{ padding: '0.4rem 1rem' }}>
              Start Month-End Close →
            </button>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', width: '100%' }}>
      {/* 1. Contextual Run Header Strip (Apple Design: Top Master Workspace Banner) */}
      <div
        className="surface-card"
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0.75rem 1.4rem',
          borderRadius: 'var(--radius-lg)',
          background: 'var(--material-surface)',
          border: '1px solid rgba(0, 0, 0, 0.05)',
          boxShadow: 'var(--shadow-card)',
          boxSizing: 'border-box',
          width: '100%',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem', flexWrap: 'wrap' }}>
          <span
            style={{
              fontFamily: 'var(--font-family-headings)',
              fontSize: '0.98rem',
              fontWeight: 700,
              color: 'var(--color-neutral-950)',
              letterSpacing: '-0.01em',
            }}
          >
            {activeRun.period || 'March 2026 Close'}
          </span>
          <span style={{ width: '4px', height: '4px', borderRadius: '50%', background: 'rgba(0, 0, 0, 0.15)' }} />
          <span
            className="font-mono"
            style={{
              fontFamily: "'Urbanist', var(--font-family-mono)",
              fontSize: '0.75rem',
              fontWeight: 600,
              color: 'var(--color-neutral-500)',
            }}
          >
            Run #{activeRun.id.slice(0, 8)}
          </span>
          <span style={{ width: '4px', height: '4px', borderRadius: '50%', background: 'rgba(0, 0, 0, 0.15)' }} />
          <span style={{ fontSize: '0.75rem', color: 'var(--color-neutral-500)', fontWeight: 500 }}>
            Cut-off:{' '}
            {new Date(activeRun.period_end || activeRun.updated_at || '2026-03-31').toLocaleDateString('en-US', {
              month: 'short',
              day: 'numeric',
              year: 'numeric',
            })}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span
            style={{
              fontSize: '0.72rem',
              fontWeight: 700,
              padding: '0.22rem 0.65rem',
              borderRadius: 'var(--radius-full)',
              background:
                activeRun.status === 'BLOCKED'
                  ? 'rgba(255, 59, 48, 0.12)'
                  : activeRun.status === 'READY_TO_CLOSE'
                  ? 'rgba(52, 199, 89, 0.12)'
                  : activeRun.status === 'CLOSED'
                  ? 'rgba(0, 122, 255, 0.12)'
                  : 'rgba(255, 149, 0, 0.12)',
              color:
                activeRun.status === 'BLOCKED'
                  ? '#d70015'
                  : activeRun.status === 'READY_TO_CLOSE'
                  ? '#1b8a3e'
                  : activeRun.status === 'CLOSED'
                  ? '#0062cc'
                  : '#b25000',
              border: `1px solid ${
                activeRun.status === 'BLOCKED'
                  ? 'rgba(255, 59, 48, 0.22)'
                  : activeRun.status === 'READY_TO_CLOSE'
                  ? 'rgba(52, 199, 89, 0.22)'
                  : activeRun.status === 'CLOSED'
                  ? 'rgba(0, 122, 255, 0.22)'
                  : 'rgba(255, 149, 0, 0.22)'
              }`,
              letterSpacing: '0.02em',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.35rem',
            }}
          >
            <span
              style={{
                width: '6px',
                height: '6px',
                borderRadius: '50%',
                background:
                  activeRun.status === 'BLOCKED'
                    ? '#ff3b30'
                    : activeRun.status === 'READY_TO_CLOSE'
                    ? '#34c759'
                    : activeRun.status === 'CLOSED'
                    ? '#007aff'
                    : '#ff9500',
              }}
            />
            <span>{activeRun.status.replace(/_/g, ' ')}</span>
          </span>

          <span
            style={{
              fontSize: '0.72rem',
              color: 'var(--color-neutral-400)',
              fontWeight: 600,
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.3rem',
            }}
          >
            <ShieldCheck size={13} color="var(--color-accent-600)" />
            <span>SOX 404 Controlled</span>
          </span>
        </div>
      </div>

      {/* 2. Dynamic Status Alert Banner */}
      {renderStatusBanner()}

      {/* 3. Top 5 Metric Cards Strip (Apple Design: strictly identical dimensions, squircle radius, ambient glow disks) */}
      <div className="metrics-strip-5">
        <div className="stagger-1 animate-fade-in" style={{ display: 'flex', minWidth: 0, height: '100%' }}>
          <MetricCard
            title="Close Readiness"
            value="82.4%"
            subtext="8/10 tasks"
            trend="↑ +14%"
            trendPositive={true}
            diskColor="primary"
            icon={<TrendingUp size={22} />}
          />
        </div>
        <div className="stagger-2 animate-fade-in" style={{ display: 'flex', minWidth: 0, height: '100%' }}>
          <MetricCard
            title="Task Execution"
            value="8 / 10"
            subtext="1 Blocked, 1 Pending"
            diskColor="secondary"
            icon={<GitFork size={22} />}
          />
        </div>
        <div className="stagger-3 animate-fade-in" style={{ display: 'flex', minWidth: 0, height: '100%' }}>
          <MetricCard
            title="Exception Triage"
            value="28 Total"
            subtext="20 Auto, 5 Staged"
            diskColor="accent"
            icon={<AlertTriangle size={22} />}
          />
        </div>
        <div className="stagger-4 animate-fade-in" style={{ display: 'flex', minWidth: 0, height: '100%' }}>
          <MetricCard
            title="Exposure At Risk"
            value="$1,834,000"
            subtext="2 Sign-offs"
            trend="Critical"
            trendPositive={false}
            diskColor="primary"
            icon={<ShieldAlert size={22} />}
          />
        </div>
        <div className="stagger-5 animate-fade-in" style={{ display: 'flex', minWidth: 0, height: '100%' }}>
          <MetricCard
            title="AI Expenditure"
            value="$0.0248"
            subtext="Mistral + Gemini"
            diskColor="neutral"
            icon={<Coins size={22} />}
          />
        </div>
      </div>

      {/* 4. Nested Page Content */}
      <div style={{ minWidth: 0 }}>{children}</div>
    </div>
  );
};
