import React, { useState, useEffect, useRef } from 'react';
import { Search, ArrowRight, X, AlertTriangle, ShieldCheck, GitFork, FileText } from 'lucide-react';
import { useCloseRun } from '../../context/CloseRunContext';

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  onNavigate: (path: string) => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({ isOpen, onClose, onNavigate }) => {
  const [query, setQuery] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  const { activeRun } = useCloseRun();

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
    } else {
      setQuery('');
    }
  }, [isOpen]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        isOpen ? onClose() : undefined;
      }
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const quickActions = [
    { label: 'Overview', path: `/close-runs/${activeRun.id}/overview`, icon: <FileText size={16} /> },
    { label: 'Tasks', path: `/close-runs/${activeRun.id}/tasks`, icon: <GitFork size={16} /> },
    { label: 'Exceptions (4 open items)', path: `/close-runs/${activeRun.id}/exceptions`, icon: <AlertTriangle size={16} /> },
    { label: 'Audit Trail', path: `/close-runs/${activeRun.id}/audit`, icon: <ShieldCheck size={16} /> },
    { label: 'Benchmarks (35 Scenarios)', path: '/benchmarks', icon: <FileText size={16} /> },
    { label: 'Calibration (ECE Curve)', path: '/calibration', icon: <FileText size={16} /> },
  ];

  const searchResults = [
    { title: 'Invoice #INV-2026-881 (HyperScale Infra)', subtitle: '$1,450,000.00 • Payment Fragmentation', path: `/close-runs/${activeRun.id}/exceptions/ex-frag-001` },
    { title: 'PO #PO-2026-771 (GPU Server Delivery)', subtitle: '$384,000.00 • 240 units unreceived shortfall', path: `/close-runs/${activeRun.id}/exceptions/ex-po-002` },
    { title: 'SOX Control AP-03 (Payment Structuring Threshold)', subtitle: 'Audit registry verification', path: `/close-runs/${activeRun.id}/audit` },
    { title: 'SOX Control PROC-04 (3-Way Goods Receipt Matching)', subtitle: 'Audit registry verification', path: `/close-runs/${activeRun.id}/audit` },
  ].filter(item => item.title.toLowerCase().includes(query.toLowerCase()) || item.subtitle.toLowerCase().includes(query.toLowerCase()));

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.65)',
        backdropFilter: 'blur(8px)',
        zIndex: 1000,
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'center',
        paddingTop: '10vh',
      }}
      onClick={onClose}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '580px',
          background: '#ffffff',
          borderRadius: 'var(--radius-lg)',
          boxShadow: 'var(--shadow-xl)',
          overflow: 'hidden',
          border: '1px solid var(--color-neutral-200)',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search Input */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.75rem',
            padding: '1rem 1.25rem',
            borderBottom: '1px solid var(--color-neutral-200)',
          }}
        >
          <Search size={20} color="var(--color-neutral-400)" />
          <input
            ref={inputRef}
            type="text"
            placeholder="Search records, SOX controls, or jump to screen..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            style={{
              flex: 1,
              border: 'none',
              outline: 'none',
              fontSize: 'var(--font-size-base)',
              fontFamily: 'var(--font-family-sans)',
            }}
          />
          <button onClick={onClose} style={{ color: 'var(--color-neutral-400)' }}>
            <X size={18} />
          </button>
        </div>

        {/* Results List */}
        <div style={{ maxHeight: '380px', overflowY: 'auto', padding: '0.75rem' }}>
          {query.trim() === '' ? (
            <div>
              <div style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--color-neutral-400)', textTransform: 'uppercase', padding: '0.5rem 0.5rem 0.25rem' }}>
                Navigation Shortcuts
              </div>
              {quickActions.map((action, i) => (
                <button
                  key={i}
                  onClick={() => {
                    onNavigate(action.path);
                    onClose();
                  }}
                  style={{
                    width: '100%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '0.65rem 0.75rem',
                    borderRadius: 'var(--radius-sm)',
                    fontSize: 'var(--font-size-sm)',
                    color: 'var(--color-neutral-800)',
                    transition: 'background var(--transition-fast)',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--color-neutral-100)')}
                  onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                    <span style={{ color: 'var(--color-neutral-500)' }}>{action.icon}</span>
                    <span>{action.label}</span>
                  </div>
                  <ArrowRight size={14} color="var(--color-neutral-400)" />
                </button>
              ))}
            </div>
          ) : (
            <div>
              <div style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--color-neutral-400)', textTransform: 'uppercase', padding: '0.5rem 0.5rem 0.25rem' }}>
                Matching Records & Controls
              </div>
              {searchResults.length === 0 ? (
                <div style={{ padding: '1.5rem', textAlign: 'center', color: 'var(--color-neutral-400)', fontSize: 'var(--font-size-sm)' }}>
                  No matching financial records found for "{query}".
                </div>
              ) : (
                searchResults.map((item, i) => (
                  <button
                    key={i}
                    onClick={() => {
                      onNavigate(item.path);
                      onClose();
                    }}
                    style={{
                      width: '100%',
                      textAlign: 'left',
                      padding: '0.65rem 0.75rem',
                      borderRadius: 'var(--radius-sm)',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '0.15rem',
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--color-neutral-100)')}
                    onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                  >
                    <div style={{ fontSize: 'var(--font-size-sm)', fontWeight: 600, color: 'var(--color-neutral-900)' }}>
                      {item.title}
                    </div>
                    <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-neutral-500)' }}>
                      {item.subtitle}
                    </div>
                  </button>
                ))
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div
          style={{
            background: 'var(--color-neutral-50)',
            padding: '0.5rem 1rem',
            borderTop: '1px solid var(--color-neutral-200)',
            fontSize: '0.7rem',
            color: 'var(--color-neutral-400)',
            display: 'flex',
            justifyContent: 'space-between',
          }}
        >
          <span>Tip: Press ESC to close</span>
          <span>SOX Section 404 Certified Query Engine</span>
        </div>
      </div>
    </div>
  );
};
