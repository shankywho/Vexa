import React from 'react';
import { useTenant } from '../../context/TenantContext';
import {
  Building2,
  CheckCircle2,
  ArrowRight,
  Database,
  Calendar,
  DollarSign,
  Plus,
} from 'lucide-react';

interface TenantSelectPageProps {
  onSelectTenant: (tenantId: string) => void;
}

export const TenantSelectPage: React.FC<TenantSelectPageProps> = ({ onSelectTenant }) => {
  const { currentTenant, setTenantById } = useTenant();

  const companies = [
    {
      id: 'abf0fca7-983d-5216-bbde-71a6678ca5e8',
      name: 'NovaScale AI Inc.',
      currency: 'USD',
      fiscalYearEnd: 'December 31',
      erp: 'NetSuite OneWorld (Live Sync)',
      activePeriod: '2026-03',
      status: 'READY_TO_CLOSE',
      reconciledVolume: '$14.8M',
      entitiesCount: 3,
    },
    {
      id: 'apex-fintech-eur',
      name: 'Apex FinTech Global B.V.',
      currency: 'EUR',
      fiscalYearEnd: 'December 31',
      erp: 'SAP S/4HANA Cloud',
      activePeriod: '2026-02',
      status: 'CLOSED',
      reconciledVolume: '€22.4M',
      entitiesCount: 6,
    },
    {
      id: 'strata-logistics-llc',
      name: 'Strata Supply Chain Corp',
      currency: 'USD',
      fiscalYearEnd: 'March 31',
      erp: 'Microsoft Dynamics 365',
      activePeriod: '2026-03',
      status: 'WAITING_FOR_HUMAN',
      reconciledVolume: '$8.2M',
      entitiesCount: 2,
    },
  ];

  const handleSelect = (id: string) => {
    setTenantById(id);
    onSelectTenant(id);
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
            <Building2 size={32} />
          </div>
          <div>
            <h1 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 800, color: 'var(--color-neutral-950)', margin: 0 }}>
              Organization & Legal Entity Directory
            </h1>
            <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-neutral-500)', marginTop: '0.35rem' }}>
              Multi-tenant ledger isolation, ERP connection topology, and consolidation hierarchy.
            </p>
          </div>
        </div>

        <button
          onClick={() => alert('Connect New ERP Entity modal...')}
          className="btn-secondary"
        >
          <Plus size={16} />
          <span>Connect New Entity</span>
        </button>
      </div>

      {/* Companies Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '1.5rem' }}>
        {companies.map(comp => {
          const isCurrent =
            currentTenant?.id === comp.id ||
            (comp.id.startsWith('abf0') && (currentTenant?.id || '').startsWith('abf0'));

          return (
            <div
              key={comp.id}
              onClick={() => handleSelect(comp.id)}
              style={{
                padding: '1.75rem',
                borderRadius: 'var(--radius-xl)',
                background: '#ffffff',
                border: isCurrent ? '2px solid var(--color-primary-500)' : '1px solid var(--color-neutral-200)',
                boxShadow: isCurrent ? '0 12px 28px rgba(254, 47, 1, 0.12)' : 'var(--shadow-sm)',
                cursor: 'pointer',
                transition: 'all var(--transition-normal)',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
              }}
            >
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                  <span className="font-mono" style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-neutral-500)' }}>
                    {comp.currency} • {comp.entitiesCount} Sub-entities
                  </span>
                  {isCurrent && (
                    <span className="badge-green">
                      <CheckCircle2 size={12} />
                      <span>Active Workspace</span>
                    </span>
                  )}
                </div>

                <h3 style={{ fontSize: 'var(--font-size-md)', fontWeight: 800, color: 'var(--color-neutral-950)', margin: '0 0 1rem 0' }}>
                  {comp.name}
                </h3>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem', padding: '1rem 0', borderTop: '1px solid var(--color-neutral-100)', borderBottom: '1px solid var(--color-neutral-100)', marginBottom: '1.25rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--font-size-xs)' }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--color-neutral-500)' }}>
                      <Database size={14} />
                      <span>ERP Connector</span>
                    </span>
                    <strong style={{ color: 'var(--color-neutral-800)' }}>{comp.erp}</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--font-size-xs)' }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--color-neutral-500)' }}>
                      <Calendar size={14} />
                      <span>Fiscal Cycle</span>
                    </span>
                    <strong style={{ color: 'var(--color-neutral-800)' }}>{comp.activePeriod}</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--font-size-xs)' }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--color-neutral-500)' }}>
                      <DollarSign size={14} />
                      <span>Monthly Volume</span>
                    </span>
                    <strong className="font-mono" style={{ color: 'var(--color-neutral-900)' }}>{comp.reconciledVolume}</strong>
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span
                  style={{
                    fontSize: 'var(--font-size-xs)',
                    fontWeight: 800,
                    color: 'var(--color-primary-500)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.35rem',
                  }}
                >
                  <span>{isCurrent ? 'Current Workspace' : 'Switch Workspace'}</span>
                  <ArrowRight size={14} />
                </span>
                <span className={comp.status === 'CLOSED' ? 'badge-green' : comp.status === 'WAITING_FOR_HUMAN' ? 'badge-yellow' : 'badge-blue'}>
                  {comp.status.replace(/_/g, ' ')}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
