import React from 'react';
import { SteppedBarChart } from '../../components/common/SteppedBarChart';
import { FloatingTargetCard } from '../../components/common/FloatingTargetCard';
import { useCloseRun } from '../../context/CloseRunContext';
import {
  ArrowUpRight,
  ArrowRight,
  TrendingUp,
  Sparkles,
  AlertTriangle,
  ShieldAlert,
  CheckCircle2,
  Clock,
} from 'lucide-react';

interface CloseRunOverviewPageProps {
  onNavigateTab: (tabId: string) => void;
}

export const CloseRunOverviewPage: React.FC<CloseRunOverviewPageProps> = ({ onNavigateTab }) => {
  const { activeRun } = useCloseRun();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', width: '100%' }}>
      {/* Hero Visual Section (Apple Material Principles & Optical Hierarchy) */}
      <div
        className="surface-card"
        style={{
          padding: '2.25rem 2.5rem',
          borderRadius: 'var(--radius-xl)',
          background: 'var(--material-surface)',
          border: '1px solid rgba(0, 0, 0, 0.05)',
          boxShadow: 'var(--shadow-card)',
          position: 'relative',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          gap: '1.5rem',
        }}
      >
        {/* Top Split: Big Financial Headline on Left, Floating Target Card on Right */}
        <div className="hero-split-grid">
          {/* Left Column: Big Headline + Stepped Bar Graph */}
          <div style={{ minWidth: 0, width: '100%', display: 'flex', flexDirection: 'column' }}>
            <div
              style={{
                fontSize: '0.72rem',
                color: 'var(--color-neutral-400)',
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
              }}
            >
              Reconciled Balance & Volume
            </div>

            {/* Huge Financial Headline (Apple Optical Sizing & Tracking) */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem', marginTop: '0.35rem' }}>
              <div
                className="font-mono"
                style={{
                  fontFamily: "'Urbanist', var(--font-family-mono)",
                  fontSize: 'clamp(2.4rem, 3.8vw, 3.6rem)',
                  fontWeight: 600,
                  color: 'var(--color-neutral-950)',
                  lineHeight: 1.05,
                  letterSpacing: '-0.035em',
                }}
              >
                $1,342,567
              </div>
              <div
                style={{
                  background: 'rgba(52, 199, 89, 0.12)',
                  color: '#1b8a3e',
                  border: '1px solid rgba(52, 199, 89, 0.22)',
                  padding: '0.22rem 0.65rem',
                  borderRadius: 'var(--radius-full)',
                  fontSize: '0.74rem',
                  fontWeight: 700,
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.25rem',
                }}
              >
                <TrendingUp size={13} strokeWidth={2.5} />
                <span>+21%</span>
              </div>
            </div>

            <div
              style={{
                fontSize: '0.82rem',
                color: 'var(--color-neutral-500)',
                marginTop: '0.45rem',
                lineHeight: 1.5,
                maxWidth: '560px',
              }}
            >
              Autonomous 10-pass reconciliation cleared 12,480 journal line items with mathematical determinism.
            </div>

            {/* Stepped Layered Rounded Bar Graph Visual */}
            <div style={{ marginTop: '1.75rem', width: '100%', minWidth: 0 }}>
              <SteppedBarChart />
            </div>
          </div>

          {/* Right Column: Floating Target Card (from reference design) */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', minWidth: 0 }}>
            <FloatingTargetCard onViewApprovals={() => onNavigateTab('approvals')} />
          </div>
        </div>
      </div>

      {/* Period-Over-Period Variance & Analyst Summary (Apple Executive Split Cards) */}
      <div className="executive-split-grid">
        {/* Executive Close Summary Box (Financial Analyst Agent Synthesis) */}
        <div
          className="surface-card"
          style={{
            padding: '1.85rem 2rem',
            borderRadius: 'var(--radius-xl)',
            background: 'var(--material-surface)',
            border: '1px solid rgba(0, 0, 0, 0.05)',
            boxShadow: 'var(--shadow-card)',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            gap: '1.25rem',
          }}
        >
          <div>
            {/* Header: Glowing Squircle Badge + Title + Verified Pill */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <div
                  style={{
                    width: '36px',
                    height: '36px',
                    borderRadius: '10px',
                    background: 'linear-gradient(135deg, #ff4e26 0%, #fe2f01 100%)',
                    boxShadow: '0 4px 14px rgba(254, 47, 1, 0.32)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#ffffff',
                    flexShrink: 0,
                  }}
                >
                  <Sparkles size={18} />
                </div>
                <div>
                  <div
                    style={{
                      fontFamily: 'var(--font-family-headings)',
                      fontSize: '1rem',
                      fontWeight: 600,
                      color: 'var(--color-neutral-950)',
                      letterSpacing: '-0.01em',
                    }}
                  >
                    Financial Analyst Synthesis
                  </div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--color-neutral-400)', fontWeight: 500 }}>
                    Autonomous Agent • 10-Pass Deterministic Run
                  </div>
                </div>
              </div>

              <div
                style={{
                  background: 'rgba(52, 199, 89, 0.12)',
                  color: '#1b8a3e',
                  border: '1px solid rgba(52, 199, 89, 0.22)',
                  padding: '0.22rem 0.65rem',
                  borderRadius: 'var(--radius-full)',
                  fontSize: '0.7rem',
                  fontWeight: 700,
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
                    background: '#34c759',
                    boxShadow: '0 0 6px rgba(52, 199, 89, 0.6)',
                  }}
                />
                <span>Verified Analysis</span>
              </div>
            </div>

            {/* Narrative Synthesis Body */}
            <div
              style={{
                fontSize: '0.84rem',
                color: 'var(--color-neutral-700)',
                lineHeight: 1.6,
                letterSpacing: '-0.005em',
              }}
            >
              The March 2026 books reflect strong net operating cash balance of{' '}
              <strong style={{ color: 'var(--color-neutral-950)', fontWeight: 600 }}>$14.2M</strong>. Automated subledger
              reconciliation completed 10 deterministic passes with zero unmitigated balance sheet variances. 2 material items
              require human authorization before formal CFO closure.
            </div>

            {/* Mini Exception Callout Squircles */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                gap: '0.75rem',
                marginTop: '1rem',
              }}
            >
              {/* Item 1: Payment Fragmentation */}
              <div
                style={{
                  background: 'rgba(255, 59, 48, 0.04)',
                  border: '1px solid rgba(255, 59, 48, 0.16)',
                  borderRadius: 'var(--radius-md)',
                  padding: '0.75rem 0.95rem',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.2rem',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: '#ff3b30' }}>
                  <ShieldAlert size={13} strokeWidth={2.5} />
                  <span style={{ fontSize: '0.68rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                    CFO Escalation
                  </span>
                </div>
                <div
                  className="font-mono"
                  style={{
                    fontFamily: "'Urbanist', var(--font-family-mono)",
                    fontSize: '1rem',
                    fontWeight: 600,
                    color: 'var(--color-neutral-950)',
                    letterSpacing: '-0.01em',
                  }}
                >
                  $1,450,000
                </div>
                <div style={{ fontSize: '0.7rem', color: 'var(--color-neutral-500)' }}>
                  Payment Fragmentation • HyperScale
                </div>
              </div>

              {/* Item 2: Quantity Discrepancy */}
              <div
                style={{
                  background: 'rgba(255, 149, 0, 0.04)',
                  border: '1px solid rgba(255, 149, 0, 0.16)',
                  borderRadius: 'var(--radius-md)',
                  padding: '0.75rem 0.95rem',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.2rem',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: '#b25000' }}>
                  <AlertTriangle size={13} strokeWidth={2.5} />
                  <span style={{ fontSize: '0.68rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                    Staged Review
                  </span>
                </div>
                <div
                  className="font-mono"
                  style={{
                    fontFamily: "'Urbanist', var(--font-family-mono)",
                    fontSize: '1rem',
                    fontWeight: 600,
                    color: 'var(--color-neutral-950)',
                    letterSpacing: '-0.01em',
                  }}
                >
                  $384,000
                </div>
                <div style={{ fontSize: '0.7rem', color: 'var(--color-neutral-500)' }}>
                  Quantity Discrepancy • GPU Hardware
                </div>
              </div>
            </div>
          </div>

          {/* Bottom Tactile Action Buttons */}
          <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.5rem', flexWrap: 'wrap' }}>
            <button
              onClick={() => onNavigateTab('tasks')}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.45rem',
                padding: '0.55rem 1.15rem',
                borderRadius: 'var(--radius-full)',
                background: 'var(--color-neutral-950)',
                color: '#ffffff',
                fontSize: '0.78rem',
                fontWeight: 600,
                boxShadow: '0 3px 10px rgba(0, 0, 0, 0.15)',
                transition: 'all 160ms var(--ease-spring-ui)',
                cursor: 'pointer',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'translateY(-1px)';
                e.currentTarget.style.boxShadow = '0 5px 16px rgba(0, 0, 0, 0.2)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = '0 3px 10px rgba(0, 0, 0, 0.15)';
              }}
            >
              <span>View 10-Task Pipeline</span>
              <ArrowRight size={13} />
            </button>

            <button
              onClick={() => onNavigateTab('telemetry')}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.45rem',
                padding: '0.55rem 1.15rem',
                borderRadius: 'var(--radius-full)',
                background: '#ffffff',
                color: 'var(--color-neutral-800)',
                border: '1px solid rgba(0, 0, 0, 0.1)',
                fontSize: '0.78rem',
                fontWeight: 600,
                boxShadow: '0 1px 3px rgba(0, 0, 0, 0.04)',
                transition: 'all 160ms var(--ease-spring-ui)',
                cursor: 'pointer',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'translateY(-1px)';
                e.currentTarget.style.backgroundColor = 'var(--color-neutral-50)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.backgroundColor = '#ffffff';
              }}
            >
              <span>Inspect Agent Logs</span>
              <ArrowUpRight size={13} />
            </button>
          </div>
        </div>

        {/* Subledger Health Status Card */}
        <div
          className="surface-card"
          style={{
            padding: '1.85rem 2rem',
            borderRadius: 'var(--radius-xl)',
            background: 'var(--material-surface)',
            border: '1px solid rgba(0, 0, 0, 0.05)',
            boxShadow: 'var(--shadow-card)',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            gap: '1rem',
          }}
        >
          <div>
            {/* Header: Title + Subledger Count Badge */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
              <div>
                <div
                  style={{
                    fontFamily: 'var(--font-family-headings)',
                    fontSize: '1rem',
                    fontWeight: 600,
                    color: 'var(--color-neutral-950)',
                    letterSpacing: '-0.01em',
                  }}
                >
                  Subledger Reconciliation Status
                </div>
                <div style={{ fontSize: '0.7rem', color: 'var(--color-neutral-400)', fontWeight: 500 }}>
                  Continuous Multi-Domain Balancing
                </div>
              </div>

              <div
                style={{
                  background: 'rgba(120, 120, 128, 0.08)',
                  color: 'var(--color-neutral-600)',
                  padding: '0.22rem 0.65rem',
                  borderRadius: 'var(--radius-full)',
                  fontSize: '0.7rem',
                  fontWeight: 600,
                  letterSpacing: '0.02em',
                }}
              >
                4 Domains
              </div>
            </div>

            {/* List of 4 Subledgers */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
              {[
                {
                  domain: 'Bank to Cash Ledger',
                  status: 'MATCHED',
                  volume: '$42,850,210.45',
                  variance: '$0.00',
                  badgeBg: 'rgba(52, 199, 89, 0.12)',
                  badgeColor: '#1b8a3e',
                  badgeBorder: 'rgba(52, 199, 89, 0.22)',
                  icon: <CheckCircle2 size={11} strokeWidth={2.5} />,
                },
                {
                  domain: 'Accounts Payable (AP)',
                  status: 'VARIANCE (STAGED)',
                  volume: '$18,420,100.00',
                  variance: '($384,000.00)',
                  badgeBg: 'rgba(255, 149, 0, 0.12)',
                  badgeColor: '#b25000',
                  badgeBorder: 'rgba(255, 149, 0, 0.22)',
                  icon: <Clock size={11} strokeWidth={2.5} />,
                },
                {
                  domain: 'Disbursements & ACH',
                  status: 'CFO ESCALATION',
                  volume: '$12,940,000.00',
                  variance: '($1,450,000.00)',
                  badgeBg: 'rgba(255, 59, 48, 0.12)',
                  badgeColor: '#d70015',
                  badgeBorder: 'rgba(255, 59, 48, 0.22)',
                  icon: <ShieldAlert size={11} strokeWidth={2.5} />,
                },
                {
                  domain: 'Accounts Receivable (AR)',
                  status: 'MATCHED',
                  volume: '$11,490,110.00',
                  variance: '$0.00',
                  badgeBg: 'rgba(52, 199, 89, 0.12)',
                  badgeColor: '#1b8a3e',
                  badgeBorder: 'rgba(52, 199, 89, 0.22)',
                  icon: <CheckCircle2 size={11} strokeWidth={2.5} />,
                },
              ].map((sub, i) => (
                <div
                  key={i}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '0.65rem 0.85rem',
                    background: 'rgba(0, 0, 0, 0.02)',
                    border: '1px solid rgba(0, 0, 0, 0.04)',
                    borderRadius: 'var(--radius-md)',
                    transition: 'background-color 160ms var(--ease-spring-ui), transform 160ms var(--ease-spring-ui)',
                  }}
                >
                  <div>
                    <div style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--color-neutral-900)' }}>
                      {sub.domain}
                    </div>
                    <div
                      className="font-mono"
                      style={{
                        fontFamily: "'Urbanist', var(--font-family-mono)",
                        fontSize: '0.7rem',
                        color: 'var(--color-neutral-400)',
                        fontVariantNumeric: 'tabular-nums',
                      }}
                    >
                      Vol: {sub.volume}
                    </div>
                  </div>

                  <div style={{ textAlign: 'right', display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.15rem' }}>
                    <div
                      style={{
                        background: sub.badgeBg,
                        color: sub.badgeColor,
                        border: `1px solid ${sub.badgeBorder}`,
                        borderRadius: 'var(--radius-full)',
                        padding: '0.15rem 0.5rem',
                        fontSize: '0.65rem',
                        fontWeight: 700,
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '0.25rem',
                        letterSpacing: '0.02em',
                      }}
                    >
                      {sub.icon}
                      <span>{sub.status}</span>
                    </div>
                    <div
                      className="font-mono"
                      style={{
                        fontFamily: "'Urbanist', var(--font-family-mono)",
                        fontSize: '0.82rem',
                        fontWeight: 600,
                        color: sub.variance === '$0.00' ? 'var(--color-neutral-400)' : sub.badgeColor,
                        fontVariantNumeric: 'tabular-nums',
                      }}
                    >
                      {sub.variance === '$0.00' ? '$0.00' : sub.variance}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Hairline Divider & Bottom Metric */}
          <div style={{ borderTop: '1px solid rgba(0, 0, 0, 0.06)', paddingTop: '0.75rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '0.72rem', color: 'var(--color-neutral-400)', fontWeight: 500 }}>
              Reconciled Match Rate
            </span>
            <span
              className="font-mono"
              style={{
                fontFamily: "'Urbanist', var(--font-family-mono)",
                fontSize: '0.85rem',
                fontWeight: 700,
                color: '#1b8a3e',
                fontVariantNumeric: 'tabular-nums',
              }}
            >
              94.8% Straight-Through
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
