import React, { useState } from 'react';
import type { DrawerEntityData } from '../../components/layout/SlideOverDrawer';
import { Search, Filter, ArrowUpRight, Scale, CheckCircle2, AlertTriangle } from 'lucide-react';

interface ReconciliationGridPageProps {
  onInspectEntity: (entity: DrawerEntityData) => void;
}

export const ReconciliationGridPage: React.FC<ReconciliationGridPageProps> = ({ onInspectEntity }) => {
  const [selectedDomain, setSelectedDomain] = useState<'BANK' | 'AP' | 'AR' | 'PO' | 'GR'>('AP');
  const [searchQuery, setSearchQuery] = useState('');

  const domains = [
    { id: 'BANK', label: 'Bank Feeds (6 Accounts)' },
    { id: 'AP', label: 'Accounts Payable (Invoices & Vouchers)' },
    { id: 'AR', label: 'Accounts Receivable (Aging & Billing)' },
    { id: 'PO', label: 'Purchase Orders (Commitments)' },
    { id: 'GR', label: 'Goods Receipts (3-Way Delivery)' },
  ];

  const transactions = [
    {
      id: 'INV-2026-881',
      date: '2026-03-24',
      vendor: 'HyperScale Infra Corp',
      description: 'Distributed Cluster Server Ingestion',
      subledger_amount: '1450000.00',
      bank_amount: '1450000.00',
      variance: '0.00',
      currency: 'USD',
      status: 'VARIANCE (STRUCTURAL)',
      statusColor: 'var(--color-primary-500)',
      details: {
        vendor_id: 'VEND-8849',
        gstin: 'US-884920',
        payment_terms: 'NET_30',
        notes: 'Flagged for payment fragmentation (14 sub-100k disbursements)',
      },
    },
    {
      id: 'INV-2026-902',
      date: '2026-03-26',
      vendor: 'Silicon Core Foundry',
      description: '1,000x GPU Accelerator Boards',
      subledger_amount: '1600000.00',
      bank_amount: '1216000.00',
      variance: '384000.00',
      currency: 'USD',
      status: 'VARIANCE (STAGED)',
      statusColor: 'var(--color-secondary-600)',
      details: {
        po_id: 'PO-2026-771',
        gr_id: 'GR-2026-104',
        billed_qty: 1000,
        received_qty: 760,
        shortfall: 240,
      },
    },
    {
      id: 'INV-2026-742',
      date: '2026-03-15',
      vendor: 'Cloudflare Enterprise',
      description: 'Edge CDN & DDoS Security Suite',
      subledger_amount: '48200.42',
      bank_amount: '48200.00',
      variance: '0.42',
      currency: 'USD',
      status: 'AUTO_RESOLVED',
      statusColor: 'var(--color-accent-600)',
      details: {
        fx_rate_applied: '1.0842 EUR/USD',
        auto_booked_account: '8020-FX-Gain-Loss',
      },
    },
    {
      id: 'INV-2026-619',
      date: '2026-03-10',
      vendor: 'Datadog Observability',
      description: 'APM Infrastructure Monitoring Plan',
      subledger_amount: '18500.00',
      bank_amount: '18500.00',
      variance: '0.00',
      currency: 'USD',
      status: 'MATCHED',
      statusColor: 'var(--color-accent-600)',
      details: {
        voucher_id: 'PV-90124',
        clearing_account: '2010-Accounts-Payable',
      },
    },
  ].filter(
    (t) =>
      t.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.vendor.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.description.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', width: '100%' }}>
      {/* Top Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h2 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 800, color: 'var(--color-neutral-950)' }}>
            Multi-Domain Reconciliation Workbench
          </h2>
          <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-neutral-500)', marginTop: '0.15rem' }}>
            Deterministic 10-pass matching grid tying source documents, subledgers, and external bank records.
          </div>
        </div>

        {/* Search */}
        <div style={{ position: 'relative', width: '280px' }}>
          <Search size={16} color="var(--color-neutral-400)" style={{ position: 'absolute', left: '0.85rem', top: '50%', transform: 'translateY(-50%)' }} />
          <input
            type="text"
            placeholder="Filter transactions..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              width: '100%',
              padding: '0.45rem 0.75rem 0.45rem 2.4rem',
              borderRadius: 'var(--radius-full)',
              border: '1px solid var(--color-neutral-200)',
              fontSize: 'var(--font-size-sm)',
              outline: 'none',
            }}
          />
        </div>
      </div>

      {/* Domain Sub-Tabs */}
      <div style={{ display: 'flex', gap: '0.5rem', borderBottom: '1px solid var(--color-neutral-200)', paddingBottom: '0.5rem', overflowX: 'auto' }}>
        {domains.map((dom) => (
          <button
            key={dom.id}
            onClick={() => setSelectedDomain(dom.id as any)}
            style={{
              padding: '0.45rem 0.95rem',
              borderRadius: 'var(--radius-sm)',
              fontSize: 'var(--font-size-sm)',
              fontWeight: selectedDomain === dom.id ? 700 : 500,
              background: selectedDomain === dom.id ? 'var(--color-neutral-950)' : 'transparent',
              color: selectedDomain === dom.id ? '#ffffff' : 'var(--color-neutral-600)',
            }}
          >
            {dom.label}
          </button>
        ))}
      </div>

      {/* Data Table */}
      <div
        className="surface-card"
        style={{
          borderRadius: 'var(--radius-md)',
          overflow: 'hidden',
          border: '1px solid var(--color-neutral-200)',
        }}
      >
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: 'var(--font-size-sm)' }}>
          <thead>
            <tr style={{ background: 'var(--color-neutral-50)', borderBottom: '1px solid var(--color-neutral-200)' }}>
              <th style={{ padding: '0.85rem 1rem', fontWeight: 700, color: 'var(--color-neutral-500)', fontSize: '0.72rem', textTransform: 'uppercase' }}>Document Ref</th>
              <th style={{ padding: '0.85rem 1rem', fontWeight: 700, color: 'var(--color-neutral-500)', fontSize: '0.72rem', textTransform: 'uppercase' }}>Date</th>
              <th style={{ padding: '0.85rem 1rem', fontWeight: 700, color: 'var(--color-neutral-500)', fontSize: '0.72rem', textTransform: 'uppercase' }}>Counterparty / Vendor</th>
              <th style={{ padding: '0.85rem 1rem', fontWeight: 700, color: 'var(--color-neutral-500)', fontSize: '0.72rem', textTransform: 'uppercase' }}>Subledger Total</th>
              <th style={{ padding: '0.85rem 1rem', fontWeight: 700, color: 'var(--color-neutral-500)', fontSize: '0.72rem', textTransform: 'uppercase' }}>Bank Settlement</th>
              <th style={{ padding: '0.85rem 1rem', fontWeight: 700, color: 'var(--color-neutral-500)', fontSize: '0.72rem', textTransform: 'uppercase' }}>Variance</th>
              <th style={{ padding: '0.85rem 1rem', fontWeight: 700, color: 'var(--color-neutral-500)', fontSize: '0.72rem', textTransform: 'uppercase' }}>Match Status</th>
              <th style={{ padding: '0.85rem 1rem', textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {transactions.map((tx) => (
              <tr
                key={tx.id}
                style={{
                  borderBottom: '1px solid var(--color-neutral-100)',
                  transition: 'background var(--transition-fast)',
                }}
                onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--color-neutral-50)')}
                onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
              >
                <td style={{ padding: '1rem', fontWeight: 700, color: 'var(--color-neutral-900)' }}>
                  {tx.id}
                </td>
                <td style={{ padding: '1rem', color: 'var(--color-neutral-500)', fontSize: 'var(--font-size-xs)' }}>
                  {tx.date}
                </td>
                <td style={{ padding: '1rem' }}>
                  <div style={{ fontWeight: 600, color: 'var(--color-neutral-900)' }}>{tx.vendor}</div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--color-neutral-400)' }}>{tx.description}</div>
                </td>
                <td className="font-mono" style={{ padding: '1rem', fontWeight: 700, color: 'var(--color-neutral-900)' }}>
                  ${Number(tx.subledger_amount).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                </td>
                <td className="font-mono" style={{ padding: '1rem', color: 'var(--color-neutral-700)' }}>
                  ${Number(tx.bank_amount).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                </td>
                <td
                  className="font-mono"
                  style={{
                    padding: '1rem',
                    fontWeight: 700,
                    color: tx.variance === '0.00' ? 'var(--color-accent-600)' : 'var(--color-primary-600)',
                  }}
                >
                  {tx.variance === '0.00' ? '$0.00' : `($${Number(tx.variance).toLocaleString('en-US', { minimumFractionDigits: 2 })})`}
                </td>
                <td style={{ padding: '1rem' }}>
                  <span
                    style={{
                      fontSize: '0.68rem',
                      fontWeight: 800,
                      padding: '0.2rem 0.55rem',
                      borderRadius: 'var(--radius-full)',
                      background: 'rgba(0, 0, 0, 0.05)',
                      color: tx.statusColor,
                    }}
                  >
                    {tx.status}
                  </span>
                </td>
                <td style={{ padding: '1rem', textAlign: 'right' }}>
                  <button
                    onClick={() =>
                      onInspectEntity({
                        id: tx.id,
                        type: 'Invoice / Disbursement',
                        title: tx.vendor,
                        amount: tx.subledger_amount,
                        currency: tx.currency,
                        metadata: tx.details,
                      })
                    }
                    className="btn-secondary"
                    style={{ padding: '0.35rem 0.65rem', fontSize: '0.72rem' }}
                  >
                    Inspect <ArrowUpRight size={12} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
