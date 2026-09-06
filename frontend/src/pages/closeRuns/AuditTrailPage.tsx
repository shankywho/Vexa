import React, { useState, useEffect } from 'react';
import { MOCK_AUDIT_EVENTS } from '../../api/mockData';
import type { AuditEvent } from '../../types/audit';
import { useAuth } from '../../context/AuthContext';
import { useCloseRun } from '../../context/CloseRunContext';
import { apiClient } from '../../api/client';
import { ShieldCheck, RotateCcw, Filter, AlertOctagon, CheckCircle2, History } from 'lucide-react';

export const AuditTrailPage: React.FC = () => {
  const { role, permissions } = useAuth();
  const { activeRun } = useCloseRun();
  const [events, setEvents] = useState<AuditEvent[]>(MOCK_AUDIT_EVENTS);
  const [filterType, setFilterType] = useState<string>('ALL');
  const [reversalModalEvent, setReversalModalEvent] = useState<AuditEvent | null>(null);
  const [reversalReason, setReversalReason] = useState('');
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  useEffect(() => {
    const fetchAudit = async () => {
      try {
        if (activeRun?.id) {
          const runAudit = await apiClient.getCloseRunAudit(activeRun.id);
          if (runAudit && runAudit.length > 0) {
            setEvents(runAudit);
            return;
          }
        }
        const globalAudit = await apiClient.getAuditEvents();
        if (globalAudit && globalAudit.length > 0) {
          setEvents(globalAudit);
        }
      } catch (err) {
        console.warn('Using local audit events fallback:', err);
      }
    };
    fetchAudit();
  }, [activeRun?.id]);

  const filtered = events.filter((ev) => {
    if (filterType !== 'ALL' && ev.event_type !== filterType) return false;
    return true;
  });

  const handleExecuteReversal = async () => {
    if (!reversalModalEvent || !reversalReason.trim()) return;

    try {
      await apiClient.reverseException(reversalModalEvent.exception_id || 'ex-po-002', reversalReason);
      const updatedEvents = activeRun?.id
        ? await apiClient.getCloseRunAudit(activeRun.id)
        : await apiClient.getAuditEvents();
      if (updatedEvents && updatedEvents.length > 0) {
        setEvents(updatedEvents);
      }
      setStatusMessage(`Reversal executed for Action ${reversalModalEvent.id}. Reversal audit entry created.`);
    } catch {
      setStatusMessage(`Reversal simulated for Action ${reversalModalEvent.id}.`);
    }
    setReversalModalEvent(null);
    setReversalReason('');
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', width: '100%' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h2 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 800, color: 'var(--color-neutral-950)' }}>
            SOX 404 Immutable Audit Trail & Post-Close Reversals
          </h2>
          <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-neutral-500)', marginTop: '0.15rem' }}>
            Cryptographically sealed, append-only ledger tracking all agent steps, policy versions, and human approvals.
          </div>
        </div>

        {/* Filter */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', background: '#ffffff', border: '1px solid var(--color-neutral-200)', borderRadius: 'var(--radius-full)', padding: '0.3rem 0.75rem' }}>
          <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-neutral-400)', fontWeight: 700 }}>Event:</span>
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            style={{ border: 'none', background: 'transparent', outline: 'none', fontSize: 'var(--font-size-xs)', fontWeight: 700 }}
          >
            <option value="ALL">All Event Types</option>
            <option value="CLOSE_RUN_STATE_CHANGE">State Changes</option>
            <option value="EXCEPTION_DETECTED">Exceptions</option>
            <option value="ACTION_STAGED">Actions Staged</option>
            <option value="APPROVAL">Approvals</option>
            <option value="REVERSAL">Reversals</option>
          </select>
        </div>
      </div>

      {statusMessage && (
        <div style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', color: '#166534', padding: '0.75rem 1.25rem', borderRadius: 'var(--radius-sm)', fontSize: 'var(--font-size-sm)', fontWeight: 700 }}>
          {statusMessage}
        </div>
      )}

      {/* Audit Log Table */}
      <div className="surface-card" style={{ borderRadius: 'var(--radius-md)', overflow: 'hidden', border: '1px solid var(--color-neutral-200)' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: 'var(--font-size-sm)' }}>
          <thead>
            <tr style={{ background: 'var(--color-neutral-50)', borderBottom: '1px solid var(--color-neutral-200)' }}>
              <th style={{ padding: '0.85rem 1rem', fontSize: '0.72rem', color: 'var(--color-neutral-500)', textTransform: 'uppercase' }}>Timestamp</th>
              <th style={{ padding: '0.85rem 1rem', fontSize: '0.72rem', color: 'var(--color-neutral-500)', textTransform: 'uppercase' }}>Event Type</th>
              <th style={{ padding: '0.85rem 1rem', fontSize: '0.72rem', color: 'var(--color-neutral-500)', textTransform: 'uppercase' }}>Actor</th>
              <th style={{ padding: '0.85rem 1rem', fontSize: '0.72rem', color: 'var(--color-neutral-500)', textTransform: 'uppercase' }}>Control Code</th>
              <th style={{ padding: '0.85rem 1rem', fontSize: '0.72rem', color: 'var(--color-neutral-500)', textTransform: 'uppercase' }}>Reason / Justification</th>
              <th style={{ padding: '0.85rem 1rem', fontSize: '0.72rem', color: 'var(--color-neutral-500)', textTransform: 'uppercase' }}>Versions</th>
              <th style={{ padding: '0.85rem 1rem', textAlign: 'right', fontSize: '0.72rem', color: 'var(--color-neutral-500)', textTransform: 'uppercase' }}>Reversal Path</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((ev) => (
              <tr
                key={ev.id}
                style={{
                  borderBottom: '1px solid var(--color-neutral-100)',
                  background: ev.is_reversal ? '#fff1f2' : 'transparent',
                }}
              >
                <td className="font-mono" style={{ padding: '1rem', fontSize: '0.75rem', color: 'var(--color-neutral-500)' }}>
                  {new Date(ev.timestamp).toLocaleTimeString()}
                </td>
                <td style={{ padding: '1rem' }}>
                  <span
                    style={{
                      fontSize: '0.68rem',
                      fontWeight: 800,
                      padding: '0.2rem 0.55rem',
                      borderRadius: 'var(--radius-full)',
                      background: ev.is_reversal ? '#fee2e2' : 'var(--color-neutral-100)',
                      color: ev.is_reversal ? '#b91c1c' : 'var(--color-neutral-800)',
                    }}
                  >
                    {ev.event_type}
                  </span>
                </td>
                <td style={{ padding: '1rem' }}>
                  <div style={{ fontWeight: 600, color: 'var(--color-neutral-900)' }}>{ev.actor}</div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--color-neutral-400)' }}>{ev.actor_type}</div>
                </td>
                <td className="font-mono" style={{ padding: '1rem', fontWeight: 700, color: 'var(--color-primary-600)' }}>
                  {ev.control_id || 'GEN-01'}
                </td>
                <td style={{ padding: '1rem', color: 'var(--color-neutral-700)', maxWidth: '340px' }}>
                  {ev.reason}
                </td>
                <td className="font-mono" style={{ padding: '1rem', fontSize: '0.7rem', color: 'var(--color-neutral-400)' }}>
                  {ev.prompt_version_id || 'default'}<br />
                  {ev.policy_version_id || 'pol_v2'}
                </td>
                <td style={{ padding: '1rem', textAlign: 'right' }}>
                  {ev.reversible && permissions.canReverseAction && (
                    <button
                      onClick={() => setReversalModalEvent(ev)}
                      className="btn-secondary"
                      style={{ fontSize: '0.72rem', padding: '0.35rem 0.65rem' }}
                    >
                      <RotateCcw size={12} />
                      Reverse Action
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Reversal Confirmation Modal */}
      {reversalModalEvent && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.5)',
            backdropFilter: 'blur(4px)',
            zIndex: 1000,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <div
            style={{
              width: '100%',
              maxWidth: '480px',
              background: '#ffffff',
              borderRadius: 'var(--radius-lg)',
              padding: '1.75rem',
              boxShadow: 'var(--shadow-xl)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--color-primary-600)', marginBottom: '0.5rem' }}>
              <RotateCcw size={20} />
              <h3 style={{ fontSize: 'var(--font-size-md)', fontWeight: 800 }}>
                SOX 404 Action Reversal
              </h3>
            </div>

            <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-neutral-600)', marginBottom: '1.25rem' }}>
              You are executing a post-close reversal for <strong>{reversalModalEvent.id}</strong>. 
              This will create a compensating counter-entry and reopen the affected exception.
            </div>

            <div style={{ marginBottom: '1.25rem' }}>
              <label style={{ display: 'block', fontSize: 'var(--font-size-xs)', fontWeight: 700, marginBottom: '0.35rem' }}>
                Mandatory Auditor Justification Reason:
              </label>
              <textarea
                value={reversalReason}
                onChange={(e) => setReversalReason(e.target.value)}
                placeholder="e.g. Counterparty credit memo confirmed after period close..."
                style={{
                  width: '100%',
                  height: '80px',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--color-neutral-300)',
                  padding: '0.65rem',
                  fontSize: 'var(--font-size-sm)',
                  fontFamily: 'var(--font-family-sans)',
                  outline: 'none',
                }}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
              <button onClick={() => setReversalModalEvent(null)} className="btn-secondary">
                Cancel
              </button>
              <button onClick={handleExecuteReversal} disabled={!reversalReason.trim()} className="btn-primary">
                Confirm & Seal Reversal
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
