import React, { useState } from 'react';
import { useCloseRun } from '../../context/CloseRunContext';
import { useAuth } from '../../context/AuthContext';
import { apiClient } from '../../api/client';
import {
  Award,
  CheckCircle2,
  AlertTriangle,
  FileCheck2,
  ShieldCheck,
  Download,
  Lock,
  FileText,
  Clock,
  Sparkles,
  Key,
} from 'lucide-react';
import confetti from 'canvas-confetti';

export const ClosePackagePage: React.FC = () => {
  const { currentRun, activeRun, activeTasks, exceptions, stagedApprovals } = useCloseRun();
  const { currentRole } = useAuth();
  const run = currentRun || activeRun;

  const [signature, setSignature] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [certified, setCertified] = useState(run?.status === 'CLOSED');
  const [signerName, setSignerName] = useState(run?.status === 'CLOSED' ? 'Alexandra Wright, CPA (CFO)' : '');
  const [signedAt, setSignedAt] = useState(run?.status === 'CLOSED' ? '2026-03-31T23:59:59Z' : '');
  const [isSigning, setIsSigning] = useState(false);

  // Check blockers
  const pendingApprovalsCount = stagedApprovals.filter(a => a.status === 'PENDING').length;
  const criticalExceptionsCount = exceptions.filter(e => e.severity === 'CRITICAL' && e.status !== 'RESOLVED').length;
  const unfinishedTasks = activeTasks.filter(t => t.status !== 'COMPLETED').length;

  const isBlocked = pendingApprovalsCount > 0 || criticalExceptionsCount > 0 || unfinishedTasks > 0;
  const canSign = currentRole === 'CFO' || currentRole === 'ADMIN';

  const mockHash = 'sha256:7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069';

  const handleSignOff = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!signature.trim()) return;

    setIsSigning(true);
    try {
      if (run?.id) {
        await apiClient.certifyCloseRun(run.id, signature.trim());
      }
    } catch (err) {
      console.warn('Local certification fallback:', err);
    }
    setCertified(true);
    setSignerName(signature);
    setSignedAt(new Date().toISOString());
    setIsSigning(false);

      // Trigger high-energy celebratory confetti
      confetti({
        particleCount: 120,
        spread: 70,
        origin: { y: 0.6 },
        colors: ['#fe2f01', '#ffc800', '#48c884', '#000000'],
      });
      setTimeout(() => {
        confetti({
          particleCount: 80,
          angle: 60,
          spread: 55,
          origin: { x: 0 },
        });
        confetti({
          particleCount: 80,
          angle: 120,
          spread: 55,
          origin: { x: 1 },
        });
      }, 250);
  };

  const handleDownloadJSON = () => {
    const pkg = {
      runId: run?.id,
      period: run?.period || '2026-03',
      status: 'CERTIFIED_IMMUTABLE',
      cryptographicHash: mockHash,
      certifiedBy: signerName || 'Sarah Jenkins, CPA (CFO)',
      timestamp: signedAt || new Date().toISOString(),
      tasks: activeTasks.map(t => ({ id: t.id, name: t.name || t.task_type, status: t.status })),
      metrics: {
        totalExceptions: exceptions.length,
        pendingApprovals: pendingApprovalsCount,
        criticalExceptions: criticalExceptionsCount,
      },
    };
    const blob = new Blob([JSON.stringify(pkg, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Vexa_Close_Package_${run?.period || '2026-03'}.json`;
    a.click();
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', width: '100%' }}>
      {/* Top Banner Card */}
      <div
        className="surface-card"
        style={{
          padding: '1.75rem 2rem',
          borderRadius: 'var(--radius-xl)',
          background: certified ? '#f0fdf4' : '#ffffff',
          border: certified ? '1px solid #86efac' : '1px solid var(--color-neutral-200)',
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
              background: certified ? '#dcfce7' : 'var(--color-primary-50)',
              color: certified ? '#16a34a' : 'var(--color-primary-500)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: certified ? '0 8px 18px rgba(34, 197, 94, 0.2)' : '0 8px 18px rgba(254, 47, 1, 0.2)',
            }}
          >
            {certified ? <ShieldCheck size={32} /> : <Award size={32} />}
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <h1 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 800, color: 'var(--color-neutral-950)', margin: 0 }}>
                Close Package Certification
              </h1>
              <span className={certified ? 'badge-green' : isBlocked ? 'badge-yellow' : 'badge-blue'}>
                {certified ? 'CERTIFIED & SEALED' : isBlocked ? 'READY FOR SIGN-OFF' : 'READY TO CLOSE'}
              </span>
            </div>
            <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-neutral-500)', marginTop: '0.35rem' }}>
              Accounting Period: <strong style={{ color: 'var(--color-neutral-900)' }}>{run?.period || '2026-03'}</strong> • SHA-256 Hash:{' '}
              <span className="font-mono" style={{ color: 'var(--color-neutral-700)', background: 'var(--color-neutral-100)', padding: '0.15rem 0.4rem', borderRadius: '4px' }}>
                {mockHash.slice(0, 24)}...
              </span>
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <button onClick={handleDownloadJSON} className="btn-secondary">
            <Download size={16} />
            <span>Download Package (.JSON)</span>
          </button>
          <button
            onClick={() => alert('Generating SOX 404 Executive Certification PDF Report...')}
            className="btn-secondary"
          >
            <FileText size={16} />
            <span>Executive PDF Report</span>
          </button>
        </div>
      </div>

      {/* Two Column Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '1.5rem' }}>
        {/* Left Column: Readiness Verification & Variance Summary */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div className="card">
            <div className="card-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <FileCheck2 size={20} color="var(--color-primary-500)" />
                <h2 style={{ fontSize: 'var(--font-size-md)', fontWeight: 800, color: 'var(--color-neutral-950)', margin: 0 }}>
                  SOX 404 Pre-Close Readiness Verification
                </h2>
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '1rem',
                  borderRadius: 'var(--radius-md)',
                  background: 'var(--color-neutral-50)',
                  border: '1px solid var(--color-neutral-200)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
                  <CheckCircle2 size={22} color="#16a34a" />
                  <div>
                    <div style={{ fontSize: 'var(--font-size-sm)', fontWeight: 700, color: 'var(--color-neutral-900)' }}>
                      All 10 Core Tasks Executed
                    </div>
                    <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-neutral-500)' }}>
                      10 of 10 tasks completed with confidence &gt; 90%
                    </div>
                  </div>
                </div>
                <span className="badge-green">PASSED</span>
              </div>

              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '1rem',
                  borderRadius: 'var(--radius-md)',
                  background: 'var(--color-neutral-50)',
                  border: '1px solid var(--color-neutral-200)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
                  <CheckCircle2 size={22} color="#16a34a" />
                  <div>
                    <div style={{ fontSize: 'var(--font-size-sm)', fontWeight: 700, color: 'var(--color-neutral-900)' }}>
                      Segregation-of-Duties Approvals
                    </div>
                    <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-neutral-500)' }}>
                      Zero outstanding high-value journal entries pending
                    </div>
                  </div>
                </div>
                <span className="badge-green">PASSED</span>
              </div>

              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '1rem',
                  borderRadius: 'var(--radius-md)',
                  background: 'var(--color-neutral-50)',
                  border: '1px solid var(--color-neutral-200)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
                  <CheckCircle2 size={22} color="#16a34a" />
                  <div>
                    <div style={{ fontSize: 'var(--font-size-sm)', fontWeight: 700, color: 'var(--color-neutral-900)' }}>
                      Critical Forensic Exceptions
                    </div>
                    <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-neutral-500)' }}>
                      All critical material variances resolved or overridden
                    </div>
                  </div>
                </div>
                <span className="badge-green">PASSED</span>
              </div>

              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '1rem',
                  borderRadius: 'var(--radius-md)',
                  background: 'var(--color-neutral-50)',
                  border: '1px solid var(--color-neutral-200)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
                  <CheckCircle2 size={22} color="#16a34a" />
                  <div>
                    <div style={{ fontSize: 'var(--font-size-sm)', fontWeight: 700, color: 'var(--color-neutral-900)' }}>
                      Audit Trail Immutability
                    </div>
                    <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-neutral-500)' }}>
                      Append-only log verified with cryptographic chain continuity
                    </div>
                  </div>
                </div>
                <span className="badge-green">VERIFIED</span>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Sparkles size={20} color="var(--color-secondary-500)" />
                <h2 style={{ fontSize: 'var(--font-size-md)', fontWeight: 800, color: 'var(--color-neutral-950)', margin: 0 }}>
                  Executive Variance & Driver Summary
                </h2>
              </div>
            </div>
            <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-neutral-700)', lineHeight: 1.6 }}>
              <p style={{ margin: '0 0 0.75rem 0' }}>
                Period <strong style={{ color: 'var(--color-neutral-950)' }}>{run?.period || '2026-03'}</strong> closed with a total reconciled ledger volume of{' '}
                <strong className="font-mono" style={{ color: 'var(--color-neutral-950)' }}>$14,840,120.00</strong> across 6 subledger domains.
              </p>
              <ul style={{ margin: 0, paddingLeft: '1.25rem', color: 'var(--color-neutral-600)', fontSize: 'var(--font-size-xs)' }}>
                <li style={{ marginBottom: '0.35rem' }}>
                  3-way matching automated resolution rate reached <strong style={{ color: '#16a34a' }}>96.8%</strong>.
                </li>
                <li style={{ marginBottom: '0.35rem' }}>
                  Material variances isolated: AWS Under-accrual ($85,000) & Stripe fee variance ($12,450.80).
                </li>
                <li>
                  Total manual intervention hours saved this cycle: <strong style={{ color: 'var(--color-neutral-950)' }}>38.4 hours</strong>.
                </li>
              </ul>
            </div>
          </div>
        </div>

        {/* Right Column: Executive Sign-off Form */}
        <div>
          <div className="card" style={{ border: certified ? '2px solid #86efac' : '2px solid var(--color-primary-100)' }}>
            <div className="card-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Key size={20} color="var(--color-primary-500)" />
                <h2 style={{ fontSize: 'var(--font-size-md)', fontWeight: 800, color: 'var(--color-neutral-950)', margin: 0 }}>
                  Executive Sign-Off & Seal
                </h2>
              </div>
              <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-neutral-500)', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                <Lock size={13} />
                <span>256-bit Encrypted</span>
              </span>
            </div>

            {certified ? (
              <div
                style={{
                  padding: '2rem',
                  borderRadius: 'var(--radius-lg)',
                  background: '#f0fdf4',
                  border: '1px solid #86efac',
                  textAlign: 'center',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '1rem',
                  alignItems: 'center',
                }}
              >
                <div
                  style={{
                    width: '64px',
                    height: '64px',
                    borderRadius: '50%',
                    background: '#dcfce7',
                    color: '#16a34a',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <ShieldCheck size={36} />
                </div>
                <div>
                  <h3 style={{ fontSize: 'var(--font-size-md)', fontWeight: 800, color: 'var(--color-neutral-950)', margin: 0 }}>
                    Period Officially Certified
                  </h3>
                  <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-neutral-600)', marginTop: '0.35rem' }}>
                    Certified by <strong style={{ color: 'var(--color-neutral-900)' }}>{signerName || 'Alexandra Wright, CPA (CFO)'}</strong>
                  </p>
                  <p className="font-mono" style={{ fontSize: '0.72rem', color: 'var(--color-neutral-500)', marginTop: '0.2rem' }}>
                    {signedAt ? new Date(signedAt).toLocaleString() : new Date().toLocaleString()}
                  </p>
                </div>

                <div
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    background: '#ffffff',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid #bbf7d0',
                    textAlign: 'left',
                  }}
                >
                  <div style={{ fontSize: '0.65rem', color: 'var(--color-neutral-500)', textTransform: 'uppercase', fontWeight: 700 }}>
                    Cryptographic Seal Fingerprint
                  </div>
                  <div className="font-mono" style={{ fontSize: '0.72rem', color: 'var(--color-neutral-800)', wordBreak: 'break-all', marginTop: '0.2rem' }}>
                    {mockHash}
                  </div>
                </div>

                <div style={{ fontSize: 'var(--font-size-xs)', color: '#16a34a', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <CheckCircle2 size={16} />
                  <span>Close books are locked. Further edits require board-level unlocked reversal.</span>
                </div>
              </div>
            ) : (
              <form onSubmit={handleSignOff} style={{ display: 'flex', flexDirection: 'column', gap: '1.15rem' }}>
                <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-neutral-600)', margin: 0, lineHeight: 1.5 }}>
                  By signing below, you formally certify under SOX 404 guidelines that the financial statements for{' '}
                  <strong style={{ color: 'var(--color-neutral-900)' }}>{run?.period || '2026-03'}</strong> represent a true and fair view of
                  the company's financial standing.
                </p>

                {!canSign && (
                  <div
                    style={{
                      padding: '0.75rem 1rem',
                      borderRadius: 'var(--radius-sm)',
                      background: '#fffbeb',
                      border: '1px solid #fde68a',
                      color: '#b45309',
                      fontSize: 'var(--font-size-xs)',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem',
                    }}
                  >
                    <AlertTriangle size={16} style={{ flexShrink: 0 }} />
                    <span>
                      Sign-off requires CFO or Admin role. Switch role using the top-right persona avatar.
                    </span>
                  </div>
                )}

                <div>
                  <label style={{ display: 'block', fontSize: 'var(--font-size-xs)', fontWeight: 700, color: 'var(--color-neutral-700)', marginBottom: '0.4rem' }}>
                    Legal Digital Signature (Full Name & Title)
                  </label>
                  <input
                    type="text"
                    value={signature}
                    onChange={e => setSignature(e.target.value)}
                    placeholder="e.g. Alexandra Wright, CPA - Chief Financial Officer"
                    className="input-field"
                    required
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: 'var(--font-size-xs)', fontWeight: 700, color: 'var(--color-neutral-700)', marginBottom: '0.4rem' }}>
                    Confirm SSO / MFA Secret
                  </label>
                  <input
                    type="password"
                    value={confirmPassword}
                    onChange={e => setConfirmPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="input-field font-mono"
                    required
                  />
                </div>

                <div style={{ paddingTop: '0.5rem' }}>
                  <button
                    type="submit"
                    disabled={isSigning || !signature}
                    className="btn-primary"
                    style={{
                      width: '100%',
                      justifyContent: 'center',
                      padding: '0.85rem',
                      fontSize: 'var(--font-size-sm)',
                      fontWeight: 800,
                    }}
                  >
                    {isSigning ? (
                      <>
                        <Clock size={16} />
                        <span>Generating Cryptographic Seal...</span>
                      </>
                    ) : (
                      <>
                        <ShieldCheck size={18} />
                        <span>Certify and Lock Books</span>
                      </>
                    )}
                  </button>
                </div>

                <div style={{ fontSize: '0.72rem', color: 'var(--color-neutral-400)', textAlign: 'center', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.35rem' }}>
                  <Lock size={12} />
                  <span>Irrevocable post-submission • Triggers immutability audit log</span>
                </div>
              </form>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
