import React, { useState } from 'react';
import type { ExceptionRecord, ExceptionSeverity, ExceptionStatus } from '../../types/exception';
import { MOCK_EXCEPTIONS } from '../../api/mockData';
import { useCloseRun } from '../../context/CloseRunContext';
import { AlertTriangle, ArrowRight, Filter, ShieldAlert, Sparkles, CheckCircle2 } from 'lucide-react';

interface ExceptionsWorkbenchPageProps {
  onSelectException: (id: string) => void;
}

export const ExceptionsWorkbenchPage: React.FC<ExceptionsWorkbenchPageProps> = ({ onSelectException }) => {
  const { exceptions: contextExceptions } = useCloseRun();
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');

  const sourceExceptions = contextExceptions && contextExceptions.length > 0 ? contextExceptions : MOCK_EXCEPTIONS;

  const filtered = sourceExceptions.filter((exc) => {
    if (severityFilter !== 'ALL' && exc.severity !== severityFilter) return false;
    if (statusFilter !== 'ALL' && exc.status !== statusFilter) return false;
    return true;
  });

  const getSeverityBadge = (severity: ExceptionSeverity) => {
    switch (severity) {
      case 'CRITICAL':
        return <span style={{ background: '#fee2e2', color: '#b91c1c', padding: '0.15rem 0.5rem', borderRadius: 'var(--radius-full)', fontSize: '0.68rem', fontWeight: 800 }}>CRITICAL</span>;
      case 'HIGH':
        return <span style={{ background: '#ffedd5', color: '#c2410c', padding: '0.15rem 0.5rem', borderRadius: 'var(--radius-full)', fontSize: '0.68rem', fontWeight: 800 }}>HIGH</span>;
      case 'MEDIUM':
        return <span style={{ background: '#fef3c7', color: '#b45309', padding: '0.15rem 0.5rem', borderRadius: 'var(--radius-full)', fontSize: '0.68rem', fontWeight: 800 }}>MEDIUM</span>;
      default:
        return <span style={{ background: 'var(--color-neutral-200)', color: 'var(--color-neutral-700)', padding: '0.15rem 0.5rem', borderRadius: 'var(--radius-full)', fontSize: '0.68rem', fontWeight: 800 }}>LOW</span>;
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', width: '100%' }}>
      {/* Header & Filter Matrix */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h2 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 800, color: 'var(--color-neutral-950)' }}>
            Exceptions & Forensic Triage Workbench
          </h2>
          <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-neutral-500)', marginTop: '0.15rem' }}>
            Autonomous anomaly detection grounded in the Financial Evidence Graph with zero hallucinated citations.
          </div>
        </div>

        {/* Filters */}
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', background: '#ffffff', border: '1px solid var(--color-neutral-200)', borderRadius: 'var(--radius-full)', padding: '0.3rem 0.75rem' }}>
            <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-neutral-400)', fontWeight: 700 }}>Severity:</span>
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              style={{ border: 'none', background: 'transparent', outline: 'none', fontSize: 'var(--font-size-xs)', fontWeight: 700 }}
            >
              <option value="ALL">All Severities</option>
              <option value="CRITICAL">Critical</option>
              <option value="HIGH">High</option>
              <option value="MEDIUM">Medium</option>
              <option value="LOW">Low</option>
            </select>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', background: '#ffffff', border: '1px solid var(--color-neutral-200)', borderRadius: 'var(--radius-full)', padding: '0.3rem 0.75rem' }}>
            <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-neutral-400)', fontWeight: 700 }}>Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              style={{ border: 'none', background: 'transparent', outline: 'none', fontSize: 'var(--font-size-xs)', fontWeight: 700 }}
            >
              <option value="ALL">All Statuses</option>
              <option value="ESCALATED">Escalated</option>
              <option value="STAGED">Staged</option>
              <option value="RESOLVED">Resolved</option>
            </select>
          </div>
        </div>
      </div>

      {/* Exception Cards List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {filtered.map((exc) => (
          <div
            key={exc.id}
            className="surface-card"
            style={{
              padding: '1.5rem',
              borderRadius: 'var(--radius-md)',
              display: 'flex',
              flexDirection: 'column',
              gap: '1rem',
              cursor: 'pointer',
            }}
            onClick={() => onSelectException(exc.id)}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', marginBottom: '0.35rem' }}>
                  {getSeverityBadge(exc.severity)}
                  <span style={{ fontSize: '0.72rem', fontWeight: 800, color: 'var(--color-neutral-500)', fontFamily: 'var(--font-family-mono)' }}>
                    {exc.type}
                  </span>
                  <span
                    style={{
                      fontSize: '0.68rem',
                      fontWeight: 700,
                      padding: '0.15rem 0.5rem',
                      borderRadius: 'var(--radius-full)',
                      background: exc.status === 'RESOLVED' ? '#dcfce7' : exc.status === 'STAGED' ? '#fef3c7' : '#fee2e2',
                      color: exc.status === 'RESOLVED' ? '#15803d' : exc.status === 'STAGED' ? '#b45309' : '#b91c1c',
                    }}
                  >
                    {exc.status}
                  </span>
                </div>

                <div style={{ fontSize: 'var(--font-size-md)', fontWeight: 800, color: 'var(--color-neutral-950)' }}>
                  {exc.title}
                </div>
                <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-neutral-600)', marginTop: '0.35rem', lineHeight: 1.5, maxWidth: '820px' }}>
                  {exc.description}
                </div>
              </div>

              {/* Financial Impact Box */}
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-neutral-500)', fontWeight: 600 }}>
                  Financial Exposure
                </div>
                <div
                  className="font-mono"
                  style={{
                    fontSize: 'var(--font-size-lg)',
                    fontWeight: 800,
                    color: Number(exc.financial_impact) > 100000 ? 'var(--color-primary-600)' : 'var(--color-neutral-900)',
                  }}
                >
                  ${Number(exc.financial_impact).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                </div>
              </div>
            </div>

            {/* Bottom Meta Bar: Calibrated Confidence, Models, and Deep Link */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                paddingTop: '0.85rem',
                borderTop: '1px solid var(--color-neutral-100)',
                flexWrap: 'wrap',
                gap: '0.75rem',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
                {/* Calibrated Confidence Pill (Design Tenet 3) */}
                {exc.calibrated_confidence && (
                  <span
                    style={{
                      background: 'var(--color-neutral-100)',
                      padding: '0.2rem 0.6rem',
                      borderRadius: 'var(--radius-full)',
                      fontSize: '0.72rem',
                      color: 'var(--color-neutral-800)',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.35rem',
                    }}
                  >
                    <Sparkles size={12} color="var(--color-secondary-500)" />
                    <span>Calibrated Confidence: <strong>{Number(exc.calibrated_confidence) * 100}%</strong></span>
                    <span style={{ opacity: 0.5 }}>({Number(exc.raw_confidence) * 100}% Raw)</span>
                  </span>
                )}

                {/* Model Provenance */}
                {exc.investigation_model && (
                  <span style={{ fontSize: '0.7rem', color: 'var(--color-neutral-400)' }}>
                    Investigated by {exc.investigation_model} • Verified by {exc.verification_model}
                  </span>
                )}
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: 'var(--color-primary-500)', fontWeight: 700, fontSize: 'var(--font-size-xs)' }}>
                <span>Inspect Forensic Dossier</span>
                <ArrowRight size={14} />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
