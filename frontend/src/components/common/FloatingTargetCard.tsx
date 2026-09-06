import React, { useState } from 'react';
import { ArrowRight } from 'lucide-react';

interface FloatingTargetCardProps {
  onViewApprovals?: () => void;
}

export const FloatingTargetCard: React.FC<FloatingTargetCardProps> = ({ onViewApprovals }) => {
  const [activeSegment, setActiveSegment] = useState<'run' | 'qtd' | 'ytd'>('run');

  const data = {
    run: {
      title: 'Close Targets & Readiness',
      amount: '$1,834,000.00',
      subtitle: 'Financial Exposure Pending Resolution',
      autoResolved: '$50,240.42',
      stagedItems: '5 entries',
      materialRisk: '2 Blockers',
      totalClosed: '$41,016,210.45',
      progress1: 70, // Auto-resolved
      progress2: 20, // Staged
      progress3: 10, // Escalated
    },
    qtd: {
      title: 'Q1 2026 Close Portfolio',
      amount: '$128,490,000.00',
      subtitle: 'Aggregated Q1 Ledger Volume',
      autoResolved: '$148,920.00',
      stagedItems: '14 entries',
      materialRisk: '0 Blockers',
      totalClosed: '$128,490,000.00',
      progress1: 85,
      progress2: 12,
      progress3: 3,
    },
    ytd: {
      title: 'Fiscal Year 2026 Audit',
      amount: '$492,100,000.00',
      subtitle: 'Cumulative Enterprise Balance',
      autoResolved: '$412,800.00',
      stagedItems: '28 entries',
      materialRisk: '0 Blockers',
      totalClosed: '$492,100,000.00',
      progress1: 92,
      progress2: 6,
      progress3: 2,
    },
  }[activeSegment];

  return (
    <div
      className="surface-card"
      style={{
        width: '100%',
        maxWidth: '340px',
        padding: '1.5rem 1.6rem',
        borderRadius: 'var(--radius-xl)',
        background: 'rgba(255, 255, 255, 0.92)',
        backdropFilter: 'blur(20px) saturate(180%)',
        WebkitBackdropFilter: 'blur(20px) saturate(180%)',
        border: '1px solid rgba(0, 0, 0, 0.07)',
        boxShadow: 'var(--shadow-card)',
        display: 'flex',
        flexDirection: 'column',
        gap: '1.15rem',
        boxSizing: 'border-box',
      }}
    >
      {/* Header with Title & Apple Segmented Control */}
      <div>
        <div
          style={{
            fontSize: '0.92rem',
            fontWeight: 600,
            color: 'var(--color-neutral-900)',
            marginBottom: '0.75rem',
            letterSpacing: '-0.01em',
            fontFamily: 'var(--font-family-headings)',
          }}
        >
          {data.title}
        </div>

        {/* Apple Segmented Control (Light Track + Elevated White Active Pill) */}
        <div
          style={{
            background: 'rgba(120, 120, 128, 0.08)',
            borderRadius: 'var(--radius-full)',
            padding: '3px',
            display: 'flex',
            alignItems: 'center',
            gap: '2px',
          }}
        >
          {(['run', 'qtd', 'ytd'] as const).map((seg) => {
            const isActive = activeSegment === seg;
            const labels = { run: 'Current Run', qtd: 'QTD', ytd: 'YTD' };
            return (
              <button
                key={seg}
                onClick={() => setActiveSegment(seg)}
                style={{
                  flex: 1,
                  padding: '0.35rem 0.5rem',
                  borderRadius: 'var(--radius-full)',
                  fontSize: '0.73rem',
                  fontWeight: isActive ? 600 : 500,
                  background: isActive ? '#ffffff' : 'transparent',
                  color: isActive ? 'var(--color-neutral-950)' : 'var(--color-neutral-500)',
                  boxShadow: isActive ? '0 1px 4px rgba(0, 0, 0, 0.08), 0 2px 6px rgba(0, 0, 0, 0.04)' : 'none',
                  transition: 'all 160ms var(--ease-spring-ui)',
                  textAlign: 'center',
                }}
              >
                {labels[seg]}
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Bold Metric */}
      <div>
        <div
          className="font-mono"
          style={{
            fontFamily: "'Urbanist', var(--font-family-mono)",
            fontSize: '1.75rem',
            fontWeight: 600,
            color: 'var(--color-neutral-950)',
            lineHeight: 1.15,
            letterSpacing: '-0.025em',
          }}
        >
          {data.amount}
        </div>
        <div
          style={{
            fontSize: '0.72rem',
            color: 'var(--color-neutral-400)',
            marginTop: '0.2rem',
            fontWeight: 500,
            letterSpacing: '0.01em',
          }}
        >
          {data.subtitle}
        </div>
      </div>

      {/* Apple Segmented Multi-Color Progress Bar */}
      <div style={{ display: 'flex', gap: '3px', height: '6px', width: '100%', borderRadius: '9999px', overflow: 'hidden' }}>
        <div
          style={{
            flex: data.progress1,
            background: '#ff9500',
            borderRadius: '9999px',
            transition: 'flex 240ms var(--ease-spring-ui)',
          }}
        />
        <div
          style={{
            flex: data.progress2,
            background: '#34c759',
            borderRadius: '9999px',
            transition: 'flex 240ms var(--ease-spring-ui)',
          }}
        />
        <div
          style={{
            flex: data.progress3,
            background: '#ff3b30',
            borderRadius: '9999px',
            transition: 'flex 240ms var(--ease-spring-ui)',
          }}
        />
      </div>

      {/* Breakdown Items with Apple Ambient Glow Indicators */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem', fontSize: '0.78rem' }}>
        {/* Auto-Resolved */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.55rem', color: 'var(--color-neutral-600)' }}>
            <span
              style={{
                width: '7px',
                height: '7px',
                borderRadius: '50%',
                background: '#ff9500',
                boxShadow: '0 0 8px rgba(255, 149, 0, 0.4)',
                flexShrink: 0,
              }}
            />
            <span>Auto-Resolved</span>
          </div>
          <span
            className="font-mono"
            style={{
              fontFamily: "'Urbanist', var(--font-family-mono)",
              fontWeight: 600,
              color: 'var(--color-neutral-900)',
              fontVariantNumeric: 'tabular-nums',
            }}
          >
            {data.autoResolved}
          </span>
        </div>

        {/* Staged for Controller */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.55rem', color: 'var(--color-neutral-600)' }}>
            <span
              style={{
                width: '7px',
                height: '7px',
                borderRadius: '50%',
                background: '#34c759',
                boxShadow: '0 0 8px rgba(52, 199, 89, 0.4)',
                flexShrink: 0,
              }}
            />
            <span>Staged for Controller</span>
          </div>
          <span
            className="font-mono"
            style={{
              fontFamily: "'Urbanist', var(--font-family-mono)",
              fontWeight: 600,
              color: 'var(--color-neutral-900)',
              fontVariantNumeric: 'tabular-nums',
            }}
          >
            {data.stagedItems}
          </span>
        </div>

        {/* CFO Critical Blockers */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.55rem', color: 'var(--color-neutral-600)' }}>
            <span
              style={{
                width: '7px',
                height: '7px',
                borderRadius: '50%',
                background: '#ff3b30',
                boxShadow: '0 0 8px rgba(255, 59, 48, 0.4)',
                flexShrink: 0,
              }}
            />
            <span>CFO Critical Blockers</span>
          </div>
          <span
            className="font-mono"
            style={{
              fontFamily: "'Urbanist', var(--font-family-mono)",
              fontWeight: 700,
              color: '#ff3b30',
              fontVariantNumeric: 'tabular-nums',
            }}
          >
            {data.materialRisk}
          </span>
        </div>
      </div>

      {/* Translucent Hairline Divider */}
      <div style={{ height: '1px', background: 'rgba(0, 0, 0, 0.06)' }} />

      {/* Bottom Total Reconciled Volume */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontSize: '0.73rem', fontWeight: 500, color: 'var(--color-neutral-400)' }}>
          Net Reconciled Volume:
        </span>
        <span
          className="font-mono"
          style={{
            fontFamily: "'Urbanist', var(--font-family-mono)",
            fontSize: '0.98rem',
            fontWeight: 600,
            color: 'var(--color-neutral-950)',
            letterSpacing: '-0.01em',
            fontVariantNumeric: 'tabular-nums',
          }}
        >
          {data.totalClosed}
        </span>
      </div>

      {/* Tactile Obsidian Pill Button */}
      {onViewApprovals && (
        <button
          onClick={onViewApprovals}
          style={{
            width: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '0.45rem',
            padding: '0.65rem 1rem',
            borderRadius: 'var(--radius-full)',
            background: 'var(--color-neutral-950)',
            color: '#ffffff',
            fontSize: '0.78rem',
            fontWeight: 600,
            letterSpacing: '0.01em',
            boxShadow: '0 3px 12px rgba(0, 0, 0, 0.16)',
            transition: 'transform 160ms var(--ease-spring-ui), background-color 160ms var(--ease-spring-ui), box-shadow 160ms var(--ease-spring-ui)',
            cursor: 'pointer',
            marginTop: '0.2rem',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = 'translateY(-1px)';
            e.currentTarget.style.boxShadow = '0 6px 18px rgba(0, 0, 0, 0.22)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = 'translateY(0)';
            e.currentTarget.style.boxShadow = '0 3px 12px rgba(0, 0, 0, 0.16)';
          }}
          onMouseDown={(e) => {
            e.currentTarget.style.transform = 'scale(0.98)';
          }}
          onMouseUp={(e) => {
            e.currentTarget.style.transform = 'translateY(-1px)';
          }}
        >
          <span>Review Pending Approvals (2)</span>
          <ArrowRight size={14} />
        </button>
      )}
    </div>
  );
};
