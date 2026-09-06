import React, { useState } from 'react';
import { X, ExternalLink, Copy, Check, FileText, Code2, Link as LinkIcon } from 'lucide-react';

export interface DrawerEntityData {
  id: string;
  type: string;
  title: string;
  amount?: string;
  currency?: string;
  metadata: Record<string, unknown>;
  linkedEntities?: { id: string; type: string; title: string; amount?: string }[];
}

interface SlideOverDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  entity: DrawerEntityData | null;
}

export const SlideOverDrawer: React.FC<SlideOverDrawerProps> = ({ isOpen, onClose, entity }) => {
  const [activeTab, setActiveTab] = useState<'details' | 'json' | 'links'>('details');
  const [copied, setCopied] = useState(false);

  if (!isOpen || !entity) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(JSON.stringify(entity.metadata, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.45)',
        backdropFilter: 'blur(4px)',
        zIndex: 100,
        display: 'flex',
        justifyContent: 'flex-end',
      }}
      onClick={onClose}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '480px',
          height: '100%',
          background: '#ffffff',
          boxShadow: 'var(--shadow-xl)',
          display: 'flex',
          flexDirection: 'column',
          borderLeft: '1px solid var(--color-neutral-200)',
          animation: 'slideIn 0.2s ease-out',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          style={{
            padding: '1.25rem 1.5rem',
            borderBottom: '1px solid var(--color-neutral-200)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'var(--color-neutral-50)',
          }}
        >
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
              <span className="badge-pill" style={{ background: 'var(--color-neutral-200)', color: 'var(--color-neutral-800)' }}>
                {entity.type}
              </span>
              <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-neutral-500)', fontFamily: 'var(--font-family-mono)' }}>
                {entity.id}
              </span>
            </div>
            <div style={{ fontSize: 'var(--font-size-md)', fontWeight: 800, color: 'var(--color-neutral-900)', marginTop: '0.35rem' }}>
              {entity.title}
            </div>
          </div>
          <button onClick={onClose} style={{ color: 'var(--color-neutral-400)', padding: '0.25rem' }}>
            <X size={20} />
          </button>
        </div>

        {/* Tab Navigation */}
        <div
          style={{
            display: 'flex',
            borderBottom: '1px solid var(--color-neutral-200)',
            padding: '0 1.5rem',
            background: '#ffffff',
          }}
        >
          {[
            { id: 'details', label: 'Overview', icon: <FileText size={14} /> },
            { id: 'links', label: 'Linked Records', icon: <LinkIcon size={14} /> },
            { id: 'json', label: 'Raw JSON', icon: <Code2 size={14} /> },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.4rem',
                padding: '0.75rem 1rem',
                fontSize: 'var(--font-size-sm)',
                fontWeight: activeTab === tab.id ? 700 : 500,
                color: activeTab === tab.id ? 'var(--color-primary-500)' : 'var(--color-neutral-500)',
                borderBottom: activeTab === tab.id ? '2px solid var(--color-primary-500)' : '2px solid transparent',
              }}
            >
              {tab.icon}
              <span>{tab.label}</span>
            </button>
          ))}
        </div>

        {/* Body Content */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '1.5rem' }}>
          {activeTab === 'details' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              {entity.amount && (
                <div
                  style={{
                    background: 'var(--color-neutral-50)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '1rem',
                    border: '1px solid var(--color-neutral-200)',
                  }}
                >
                  <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-neutral-500)', textTransform: 'uppercase', fontWeight: 600 }}>
                    Settled Transaction Amount
                  </div>
                  <div className="font-mono" style={{ fontSize: 'var(--font-size-xl)', fontWeight: 800, color: 'var(--color-neutral-950)' }}>
                    {entity.currency || 'USD'} ${Number(entity.amount).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                  </div>
                </div>
              )}

              <div>
                <div style={{ fontSize: 'var(--font-size-xs)', fontWeight: 700, color: 'var(--color-neutral-400)', textTransform: 'uppercase', marginBottom: '0.65rem' }}>
                  Entity Properties
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  {Object.entries(entity.metadata).map(([key, val]) => (
                    <div
                      key={key}
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        padding: '0.5rem 0.75rem',
                        background: 'var(--color-neutral-50)',
                        borderRadius: 'var(--radius-xs)',
                        fontSize: 'var(--font-size-sm)',
                      }}
                    >
                      <span style={{ color: 'var(--color-neutral-500)', textTransform: 'capitalize' }}>
                        {key.replace(/_/g, ' ')}
                      </span>
                      <span className="font-mono" style={{ fontWeight: 600, color: 'var(--color-neutral-900)' }}>
                        {String(val)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'links' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {(entity.linkedEntities || [
                { id: 'PO-2026-440', type: 'Purchase Order', title: 'Hardware Supply Agreement', amount: '1450000.00' },
                { id: 'PAY-BATCH-991', type: 'Payment Batch', title: 'ACH Disbursement Batch #991', amount: '1450000.00' },
                { id: 'GL-2010', type: 'General Ledger', title: 'Accounts Payable Clearing', amount: '1450000.00' }
              ]).map((link, idx) => (
                <div
                  key={idx}
                  style={{
                    padding: '0.85rem',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--color-neutral-200)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                  }}
                >
                  <div>
                    <div style={{ fontSize: '0.68rem', color: 'var(--color-neutral-400)', textTransform: 'uppercase', fontWeight: 700 }}>
                      {link.type} • {link.id}
                    </div>
                    <div style={{ fontSize: 'var(--font-size-sm)', fontWeight: 600, color: 'var(--color-neutral-900)' }}>
                      {link.title}
                    </div>
                  </div>
                  {link.amount && (
                    <div className="font-mono" style={{ fontWeight: 700, fontSize: 'var(--font-size-sm)' }}>
                      ${Number(link.amount).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {activeTab === 'json' && (
            <div style={{ position: 'relative' }}>
              <button
                onClick={handleCopy}
                style={{
                  position: 'absolute',
                  top: '0.5rem',
                  right: '0.5rem',
                  background: 'rgba(255, 255, 255, 0.1)',
                  color: '#ffffff',
                  padding: '0.25rem 0.5rem',
                  borderRadius: 'var(--radius-xs)',
                  fontSize: '0.7rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.35rem',
                }}
              >
                {copied ? <Check size={12} color="var(--color-accent-400)" /> : <Copy size={12} />}
                <span>{copied ? 'Copied' : 'Copy'}</span>
              </button>
              <pre
                className="font-mono"
                style={{
                  background: 'var(--color-neutral-950)',
                  color: '#e0e0e0',
                  padding: '1rem',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '0.75rem',
                  overflowX: 'auto',
                }}
              >
                {JSON.stringify(entity.metadata, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
