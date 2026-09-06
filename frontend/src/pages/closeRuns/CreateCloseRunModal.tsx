import React, { useState } from 'react';
import { X, Calendar, Sparkles, Shield, ArrowRight } from 'lucide-react';
import { useCloseRun } from '../../context/CloseRunContext';
import { useTenant } from '../../context/TenantContext';

interface CreateCloseRunModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (runId: string) => void;
}

export const CreateCloseRunModal: React.FC<CreateCloseRunModalProps> = ({ isOpen, onClose, onSuccess }) => {
  const { currentTenant } = useTenant();
  const { createCloseRun } = useCloseRun();

  const [period, setPeriod] = useState('2026-04');
  const [subledgers, setSubledgers] = useState({
    ap: true,
    ar: true,
    bank: true,
    accruals: true,
    inventory: true,
    tax: false,
  });
  const [targetDurationHours, setTargetDurationHours] = useState('4');
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      const newRun = await createCloseRun(period);
      setIsSubmitting(false);
      onSuccess(newRun.id);
      onClose();
    } catch (err) {
      setIsSubmitting(false);
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-in fade-in">
      <div className="bg-neutral-900 border border-neutral-800 rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-800">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-primary-500/10 text-primary-500 flex items-center justify-center">
              <Calendar className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white">Initialize New Month-End Close</h2>
              <p className="text-xs text-neutral-400">Entity: {currentTenant?.name}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-neutral-400 hover:text-white p-1 rounded-lg hover:bg-neutral-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-xs font-semibold text-neutral-300 mb-1.5">
              Accounting Period (YYYY-MM)
            </label>
            <input
              type="month"
              value={period}
              onChange={e => setPeriod(e.target.value)}
              className="w-full px-3.5 py-2.5 bg-neutral-800 border border-neutral-700 rounded-xl text-white text-sm focus:outline-none focus:border-primary-500 font-medium"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-neutral-300 mb-2">
              Subledgers to Ingest & Reconcile
            </label>
            <div className="grid grid-cols-2 gap-2 text-xs">
              {[
                { key: 'ap', label: 'Accounts Payable (AP & POs)' },
                { key: 'ar', label: 'Accounts Receivable (Invoices)' },
                { key: 'bank', label: 'Cash & Bank Feeds (Plaid/Fed)' },
                { key: 'accruals', label: 'Accruals & Prepaids' },
                { key: 'inventory', label: 'Inventory & COGS' },
                { key: 'tax', label: 'Sales Tax & VAT Postings' },
              ].map(sub => (
                <label
                  key={sub.key}
                  className="flex items-center gap-2.5 p-2.5 bg-neutral-800/60 rounded-xl border border-neutral-700/50 hover:border-neutral-600 cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={subledgers[sub.key as keyof typeof subledgers]}
                    onChange={e =>
                      setSubledgers(prev => ({ ...prev, [sub.key]: e.target.checked }))
                    }
                    className="accent-primary-500 rounded"
                  />
                  <span className="text-neutral-200">{sub.label}</span>
                </label>
              ))}
            </div>
          </div>

          <div className="p-3 rounded-xl bg-neutral-800/40 border border-neutral-700/40 space-y-2">
            <div className="flex items-center gap-2 text-xs text-neutral-300 font-medium">
              <Sparkles className="w-4 h-4 text-secondary-500" />
              <span>Multi-Agent Close Orchestration Policy</span>
            </div>
            <p className="text-[11px] text-neutral-400">
              Spawns 10 autonomous agents in DAG sequence. Transactions &lt; $50,000 with confidence &gt; 92% will be auto-reconciled under SOX Rule #404-B.
            </p>
          </div>

          <div className="flex items-center justify-end gap-3 pt-3 border-t border-neutral-800">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm text-neutral-400 hover:text-white rounded-xl hover:bg-neutral-800 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex items-center gap-2 px-5 py-2.5 bg-primary-500 hover:bg-primary-600 text-white text-sm font-semibold rounded-xl shadow-lg shadow-primary-500/25 transition-all"
            >
              {isSubmitting ? (
                'Initializing DAG...'
              ) : (
                <>
                  <span>Launch Close Run</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
