import React, { useState, useEffect } from 'react';
import { MOCK_EXCEPTIONS } from '../../api/mockData';
import { useAuth } from '../../context/AuthContext';
import { useCloseRun } from '../../context/CloseRunContext';
import { ClipboardCheck, CheckCircle2, XCircle, ArrowRight, ShieldCheck, AlertOctagon } from 'lucide-react';

interface ApprovalsQueuePageProps {
  onInspectException: (id: string) => void;
}

export const ApprovalsQueuePage: React.FC<ApprovalsQueuePageProps> = ({ onInspectException }) => {
  const { role, permissions } = useAuth();
  const { exceptions: contextExceptions, approveException, rejectException } = useCloseRun();
  
  const initialList = contextExceptions.length > 0 ? contextExceptions : MOCK_EXCEPTIONS;
  const [exceptions, setExceptions] = useState(
    initialList.filter(e => e.status === 'STAGED' || e.status === 'ESCALATED')
  );
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    if (contextExceptions.length > 0) {
      setExceptions(contextExceptions.filter(e => e.status === 'STAGED' || e.status === 'ESCALATED'));
    }
  }, [contextExceptions]);

  const handleApprove = async (id: string) => {
    try {
      await approveException(id, 'Approved via Controller Queue');
      setExceptions(prev => prev.filter(e => e.id !== id));
      setSuccessMessage(`Exception ${id} approved. Remedial journal entry posted.`);
    } catch (err: any) {
      setExceptions(prev => prev.filter(e => e.id !== id));
      setSuccessMessage(`Exception ${id} approved (local update).`);
    }
  };

  const handleReject = async (id: string) => {
    try {
      await rejectException(id, 'Rejected by reviewer');
      setExceptions(prev => prev.filter(e => e.id !== id));
      setSuccessMessage(`Exception ${id} rejected. Returned to investigation.`);
    } catch (err: any) {
      setExceptions(prev => prev.filter(e => e.id !== id));
      setSuccessMessage(`Exception ${id} rejected (local update).`);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', width: '100%' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h2 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 800, color: 'var(--color-neutral-950)' }}>
            Human Governance & Approvals Queue
          </h2>
          <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-neutral-500)', marginTop: '0.15rem' }}>
            Centralized sign-off queue for Controller and CFO authorizations on staged compensating actions.
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: '#ffffff', padding: '0.35rem 0.85rem', borderRadius: 'var(--radius-full)', border: '1px solid var(--color-neutral-200)' }}>
          <span style={{ fontSize: '0.72rem', color: 'var(--color-neutral-500)', fontWeight: 700 }}>Logged in as:</span>
          <span className="badge-pill" style={{ background: 'var(--color-primary-100)', color: 'var(--color-primary-700)' }}>
            {role}
          </span>
        </div>
      </div>

      {successMessage && (
        <div style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', color: '#166534', padding: '0.75rem 1.25rem', borderRadius: 'var(--radius-sm)', fontSize: 'var(--font-size-sm)', fontWeight: 700 }}>
          {successMessage}
        </div>
      )}

      {!permissions.canApproveLevel2 && role !== 'CFO' && role !== 'ADMIN' && (
        <div style={{ background: '#fffbeb', border: '1px solid #fde68a', color: '#92400e', padding: '0.85rem 1.25rem', borderRadius: 'var(--radius-sm)', fontSize: 'var(--font-size-sm)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <AlertOctagon size={18} />
          <span>Notice: Your current role (<strong>{role}</strong>) cannot approve Level 2 staged entries due to SOX 404 Segregation of Duties. Switch to <strong>CONTROLLER</strong> or <strong>CFO</strong> in the header to approve.</span>
        </div>
      )}

      {/* Queue Items */}
      {exceptions.length === 0 ? (
        <div className="surface-card" style={{ padding: '3rem', textAlign: 'center', color: 'var(--color-neutral-400)' }}>
          <ClipboardCheck size={48} style={{ margin: '0 auto 1rem', opacity: 0.4 }} />
          <div style={{ fontSize: 'var(--font-size-md)', fontWeight: 700, color: 'var(--color-neutral-700)' }}>
            Approval Queue Clean
          </div>
          <div style={{ fontSize: 'var(--font-size-sm)', marginTop: '0.25rem' }}>
            All staged compensating entries and escalations have been authorized.
          </div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {exceptions.map((exc) => (
            <div
              key={exc.id}
              className="surface-card"
              style={{
                padding: '1.5rem',
                borderRadius: 'var(--radius-md)',
                display: 'flex',
                flexDirection: 'column',
                gap: '1.25rem',
                borderLeft: `4px solid ${exc.severity === 'CRITICAL' ? 'var(--color-primary-500)' : 'var(--color-secondary-500)'}`,
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                    <span className="badge-pill" style={{ background: exc.severity === 'CRITICAL' ? '#fee2e2' : '#fef3c7', color: exc.severity === 'CRITICAL' ? '#b91c1c' : '#b45309' }}>
                      {exc.severity}
                    </span>
                    <span style={{ fontSize: '0.75rem', fontWeight: 800, color: 'var(--color-neutral-500)', fontFamily: 'var(--font-family-mono)' }}>
                      {exc.id}
                    </span>
                  </div>
                  <div style={{ fontSize: 'var(--font-size-md)', fontWeight: 800, color: 'var(--color-neutral-950)' }}>
                    {exc.title}
                  </div>
                  <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-neutral-600)', marginTop: '0.35rem', lineHeight: 1.5, maxWidth: '780px' }}>
                    {exc.description}
                  </div>
                </div>

                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-neutral-500)', fontWeight: 600 }}>
                    Proposed Adjustment
                  </div>
                  <div className="font-mono" style={{ fontSize: 'var(--font-size-lg)', fontWeight: 800, color: 'var(--color-primary-600)' }}>
                    ${Number(exc.financial_impact).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                  </div>
                </div>
              </div>

              {/* Staged Journal Entry Table */}
              {exc.staged_action && (
                <div style={{ background: 'var(--color-neutral-50)', padding: '1rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--color-neutral-200)' }}>
                  <div style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--color-neutral-500)', textTransform: 'uppercase', marginBottom: '0.5rem' }}>
                    Staged Remedial Accounting Entry
                  </div>
                  <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-neutral-800)', marginBottom: '0.65rem' }}>
                    {exc.staged_action.description}
                  </div>
                  <div style={{ display: 'flex', gap: '1.5rem', fontSize: 'var(--font-size-xs)' }}>
                    {exc.staged_action.debit_account && (
                      <div>
                        <span style={{ color: 'var(--color-neutral-500)' }}>Debit: </span>
                        <strong className="font-mono">{exc.staged_action.debit_account}</strong>
                      </div>
                    )}
                    {exc.staged_action.credit_account && (
                      <div>
                        <span style={{ color: 'var(--color-neutral-500)' }}>Credit: </span>
                        <strong className="font-mono">{exc.staged_action.credit_account}</strong>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Actions */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: '0.5rem', borderTop: '1px solid var(--color-neutral-100)' }}>
                <button
                  onClick={() => onInspectException(exc.id)}
                  style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-primary-500)', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.35rem' }}
                >
                  <span>Examine Full Evidence Graph</span>
                  <ArrowRight size={14} />
                </button>

                <div style={{ display: 'flex', gap: '0.65rem' }}>
                  <button
                    onClick={() => handleReject(exc.id)}
                    disabled={!permissions.canRejectAction}
                    className="btn-secondary"
                    style={{ fontSize: 'var(--font-size-xs)', padding: '0.4rem 0.85rem' }}
                  >
                    <XCircle size={14} />
                    Reject Proposal
                  </button>

                  <button
                    onClick={() => handleApprove(exc.id)}
                    disabled={!permissions.canApproveLevel2 && role !== 'CFO'}
                    className="btn-primary"
                    style={{ fontSize: 'var(--font-size-xs)', padding: '0.4rem 0.85rem' }}
                  >
                    <CheckCircle2 size={14} />
                    Approve Entry
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
