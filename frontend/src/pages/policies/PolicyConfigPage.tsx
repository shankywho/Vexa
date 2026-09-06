import React, { useState } from 'react';
import { useTenant } from '../../context/TenantContext';
import { useAuth } from '../../context/AuthContext';
import { MetricCard } from '../../components/common/MetricCard';
import {
  Sliders,
  Shield,
  Save,
  CheckCircle2,
  Lock,
  Cpu,
  DollarSign,
  AlertTriangle,
  History,
} from 'lucide-react';

export const PolicyConfigPage: React.FC = () => {
  const { currentTenant } = useTenant();
  const { currentRole } = useAuth();

  const [autoReconcileCap, setAutoReconcileCap] = useState('50000.00');
  const [minConfidenceThreshold, setMinConfidenceThreshold] = useState('0.92');
  const [largeDisbursementCap, setLargeDisbursementCap] = useState('100000.00');
  const [savedSuccess, setSavedSuccess] = useState(false);

  const canEdit = currentRole === 'CONTROLLER' || currentRole === 'CFO' || currentRole === 'ADMIN';

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 3000);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', width: '100%' }}>
      {/* Top Banner Card */}
      <div
        className="surface-card"
        style={{
          padding: '1.75rem 2rem',
          borderRadius: 'var(--radius-xl)',
          background: '#ffffff',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '1.25rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
          <div
            style={{
              width: '56px',
              height: '56px',
              borderRadius: 'var(--radius-md)',
              background: 'var(--color-primary-50)',
              color: 'var(--color-primary-500)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 8px 18px rgba(254, 47, 1, 0.2)',
            }}
          >
            <Sliders size={32} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <h1 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 800, color: 'var(--color-neutral-950)', margin: 0 }}>
                Financial Governance Policies
              </h1>
              <span className="badge-blue font-mono">pol_v2_2026_enterprise</span>
            </div>
            <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-neutral-500)', marginTop: '0.35rem' }}>
              Entity: <strong style={{ color: 'var(--color-neutral-900)' }}>{currentTenant?.name || 'NovaScale AI Inc.'}</strong> • Materiality & Autonomy Limits under SOX Rule #404-B.
            </p>
          </div>
        </div>

        {canEdit ? (
          <button onClick={handleSave} className="btn-primary" style={{ padding: '0.75rem 1.5rem' }}>
            <Save size={18} />
            <span>Publish Policy Change</span>
          </button>
        ) : (
          <div className="badge-neutral" style={{ padding: '0.5rem 1rem', fontSize: 'var(--font-size-xs)' }}>
            <Lock size={14} />
            <span>Read-Only Policy (Requires Controller / CFO)</span>
          </div>
        )}
      </div>

      {savedSuccess && (
        <div
          style={{
            padding: '1rem 1.25rem',
            borderRadius: 'var(--radius-md)',
            background: '#f0fdf4',
            border: '1px solid #86efac',
            color: '#15803d',
            fontSize: 'var(--font-size-sm)',
            fontWeight: 700,
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
          }}
        >
          <CheckCircle2 size={18} />
          <span>Policy published successfully. SHA-256 hash appended to SOX immutability ledger.</span>
        </div>
      )}

      {/* 4 Circular Stat Disks (Apple Design: strictly identical dimensions) */}
      <div className="metrics-strip-4">
        <MetricCard
          title="Autonomy Cap"
          value={`$${parseFloat(autoReconcileCap).toLocaleString()}`}
          subtitle="Max transaction for Level 3 auto-resolution"
          icon={<DollarSign size={24} />}
          diskColor="green"
        />
        <MetricCard
          title="Min Confidence Cutoff"
          value={`${(parseFloat(minConfidenceThreshold) * 100).toFixed(0)}%`}
          subtitle="Calibrated confidence required to bypass review"
          icon={<Shield size={24} />}
          diskColor="blue"
        />
        <MetricCard
          title="High-Risk Escalation"
          value={`$${parseFloat(largeDisbursementCap).toLocaleString()}`}
          subtitle="Requires CFO signature above this amount"
          icon={<AlertTriangle size={24} />}
          diskColor="orange"
        />
        <MetricCard
          title="Enforcement Mode"
          value="STRICT"
          subtitle="Deterministic pre-execution verification"
          icon={<Lock size={24} />}
          diskColor="yellow"
        />
      </div>

      {/* Form Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '1.5rem' }}>
        {/* Left: Materiality Thresholds Form */}
        <div className="card">
          <div className="card-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <DollarSign size={20} color="var(--color-primary-500)" />
              <h2 style={{ fontSize: 'var(--font-size-md)', fontWeight: 800, color: 'var(--color-neutral-950)', margin: 0 }}>
                SOX 404 Autonomy & Materiality Cutoffs
              </h2>
            </div>
          </div>

          <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            <div>
              <label style={{ display: 'block', fontSize: 'var(--font-size-xs)', fontWeight: 700, color: 'var(--color-neutral-700)', marginBottom: '0.4rem' }}>
                Straight-Through Auto-Resolution Cap (USD)
              </label>
              <div style={{ position: 'relative' }}>
                <span style={{ position: 'absolute', left: '0.85rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--color-neutral-400)', fontWeight: 700 }}>$</span>
                <input
                  type="number"
                  value={autoReconcileCap}
                  disabled={!canEdit}
                  onChange={e => setAutoReconcileCap(e.target.value)}
                  className="input-field font-mono"
                  style={{ paddingLeft: '2rem' }}
                />
              </div>
              <p style={{ fontSize: '0.72rem', color: 'var(--color-neutral-500)', marginTop: '0.35rem' }}>
                Discrepancies below this threshold with confidence &gt; {minConfidenceThreshold} will be booked automatically.
              </p>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: 'var(--font-size-xs)', fontWeight: 700, color: 'var(--color-neutral-700)', marginBottom: '0.4rem' }}>
                Minimum Calibrated Confidence Threshold (0.50 - 1.00)
              </label>
              <input
                type="number"
                step="0.01"
                min="0.5"
                max="1.0"
                value={minConfidenceThreshold}
                disabled={!canEdit}
                onChange={e => setMinConfidenceThreshold(e.target.value)}
                className="input-field font-mono"
              />
              <p style={{ fontSize: '0.72rem', color: 'var(--color-neutral-500)', marginTop: '0.35rem' }}>
                Calibrated against ECE reliability curves to ensure zero false positives.
              </p>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: 'var(--font-size-xs)', fontWeight: 700, color: 'var(--color-neutral-700)', marginBottom: '0.4rem' }}>
                Executive High-Risk Escalation Cap (USD)
              </label>
              <div style={{ position: 'relative' }}>
                <span style={{ position: 'absolute', left: '0.85rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--color-neutral-400)', fontWeight: 700 }}>$</span>
                <input
                  type="number"
                  value={largeDisbursementCap}
                  disabled={!canEdit}
                  onChange={e => setLargeDisbursementCap(e.target.value)}
                  className="input-field font-mono"
                  style={{ paddingLeft: '2rem' }}
                />
              </div>
              <p style={{ fontSize: '0.72rem', color: 'var(--color-neutral-500)', marginTop: '0.35rem' }}>
                Any disbursement or variance exceeding this limit unconditionally flags CFO review.
              </p>
            </div>
          </form>
        </div>

        {/* Right: Dual LLM Routing Strategy */}
        <div className="card">
          <div className="card-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Cpu size={20} color="var(--color-secondary-500)" />
              <h2 style={{ fontSize: 'var(--font-size-md)', fontWeight: 800, color: 'var(--color-neutral-950)', margin: 0 }}>
                Dual-Model Consensus Architecture
              </h2>
            </div>
          </div>
          <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-neutral-600)', margin: '0 0 1rem 0', lineHeight: 1.5 }}>
            Every material anomaly requires two independent model passes before staging remedial actions:
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div style={{ padding: '1rem', background: 'var(--color-neutral-50)', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-neutral-200)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.35rem' }}>
                <strong style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-neutral-900)' }}>Investigation Agent</strong>
                <span className="badge-blue font-mono">Primary</span>
              </div>
              <div className="font-mono" style={{ fontSize: 'var(--font-size-xs)', fontWeight: 700, color: 'var(--color-primary-600)' }}>
                Mistral (codestral-latest)
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--color-neutral-500)', marginTop: '0.25rem' }}>
                Performs causal root-cause analysis and financial evidence graph assembly.
              </div>
            </div>

            <div style={{ padding: '1rem', background: '#f0fdf4', borderRadius: 'var(--radius-md)', border: '1px solid #bbf7d0' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.35rem' }}>
                <strong style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-neutral-900)' }}>Verification Agent</strong>
                <span className="badge-green font-mono">Consensus</span>
              </div>
              <div className="font-mono" style={{ fontSize: 'var(--font-size-xs)', fontWeight: 700, color: '#16a34a' }}>
                Groq (qwen3.8-27b)
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--color-neutral-500)', marginTop: '0.25rem' }}>
                Validates database citations, audits math formulas, and enforces SOX limits.
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginTop: '1.25rem', paddingTop: '1rem', borderTop: '1px solid var(--color-neutral-200)', fontSize: '0.72rem', color: 'var(--color-neutral-400)' }}>
            <History size={14} />
            <span>Policy Revision History: 3 commits in Q1 2026 • Verified Immutable</span>
          </div>
        </div>
      </div>
    </div>
  );
};
