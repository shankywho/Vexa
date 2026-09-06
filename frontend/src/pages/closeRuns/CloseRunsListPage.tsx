import React, { useState } from 'react';
import { useCloseRun } from '../../context/CloseRunContext';
import { useTenant } from '../../context/TenantContext';
import type { CloseRun } from '../../types/closeRun';
import { CreateCloseRunModal } from './CreateCloseRunModal';
import { MetricCard } from '../../components/common/MetricCard';
import {
  Calendar,
  Play,
  CheckCircle2,
  Clock,
  AlertTriangle,
  ArrowRight,
  Filter,
  Search,
  Plus,
  ShieldCheck,
  Zap,
} from 'lucide-react';

interface CloseRunsListPageProps {
  onSelectRun: (runId: string) => void;
}

export const CloseRunsListPage: React.FC<CloseRunsListPageProps> = ({ onSelectRun }) => {
  const { runs, setCurrentRunId } = useCloseRun();
  const { currentTenant } = useTenant();

  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  const filteredRuns = runs.filter(run => {
    const periodStr = run.period || run.period_start || '';
    const matchesSearch = periodStr.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === 'ALL' || run.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const handleSelect = (runId: string) => {
    setCurrentRunId(runId);
    onSelectRun(runId);
  };

  const getStatusBadge = (status: CloseRun['status']) => {
    switch (status) {
      case 'CLOSED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
            <CheckCircle2 className="w-3.5 h-3.5" />
            Closed & Certified
          </span>
        );
      case 'READY_TO_CLOSE':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-500/15 text-blue-400 border border-blue-500/30">
            <CheckCircle2 className="w-3.5 h-3.5" />
            Ready to Close
          </span>
        );
      case 'WAITING_FOR_HUMAN':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/15 text-amber-400 border border-amber-500/30">
            <Clock className="w-3.5 h-3.5" />
            Awaiting Approval
          </span>
        );
      case 'BLOCKED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-500/15 text-rose-400 border border-rose-500/30">
            <AlertTriangle className="w-3.5 h-3.5" />
            Blocked
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-cyan-500/15 text-cyan-400 border border-cyan-500/30">
            <Play className="w-3.5 h-3.5 animate-pulse" />
            Running
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-white tracking-tight">Month-End Close Runs</h1>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-neutral-800 text-neutral-400 border border-neutral-700">
              {currentTenant?.name}
            </span>
          </div>
          <p className="text-sm text-neutral-400 mt-1">
            Enterprise orchestration and audit log for continuous financial close cycles.
          </p>
        </div>

        <button
          onClick={() => setIsCreateModalOpen(true)}
          className="flex items-center gap-2 px-4 py-2.5 bg-primary-500 hover:bg-primary-600 text-white rounded-xl text-sm font-semibold shadow-lg shadow-primary-500/25 transition-all w-fit"
        >
          <Plus className="w-4 h-4" />
          <span>New Close Run</span>
        </button>
      </div>

      {/* Metric Cards Strip (Apple Design: strictly identical dimensions) */}
      <div className="metrics-strip-4">
        <MetricCard
          title="Active Close Cycles"
          value="1 Active"
          subtitle="March 2026 Close (90% done)"
          icon={Calendar}
          diskColor="orange"
        />
        <MetricCard
          title="Average Close Duration"
          value="4.2 hrs"
          subtitle="vs. industry avg of 8.5 days"
          icon={Clock}
          diskColor="blue"
        />
        <MetricCard
          title="Straight-Through Match"
          value="94.8%"
          subtitle="Auto-reconciled under SOX limit"
          icon={Zap}
          diskColor="green"
        />
        <MetricCard
          title="Material Risk Prevented"
          value="$1.42M"
          subtitle="35 synthetic anomalies caught"
          icon={ShieldCheck}
          diskColor="yellow"
        />
      </div>

      {/* Table & Controls Card */}
      <div className="card space-y-4">
        {/* Search & Filter Bar */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="relative w-full sm:w-80">
            <Search className="w-4 h-4 text-neutral-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search by period (e.g. 2026-03)..."
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-neutral-800 border border-neutral-700 rounded-xl text-xs text-white placeholder-neutral-500 focus:outline-none focus:border-primary-500"
            />
          </div>

          <div className="flex items-center gap-2 w-full sm:w-auto">
            <Filter className="w-4 h-4 text-neutral-400" />
            <div className="flex items-center bg-neutral-800 p-1 rounded-xl border border-neutral-700 text-xs">
              {['ALL', 'RUNNING', 'WAITING_FOR_HUMAN', 'CLOSED'].map(status => (
                <button
                  key={status}
                  onClick={() => setStatusFilter(status)}
                  className={`px-3 py-1 rounded-lg font-medium transition-all ${
                    statusFilter === status
                      ? 'bg-primary-500 text-white shadow-sm'
                      : 'text-neutral-400 hover:text-white'
                  }`}
                >
                  {status === 'ALL' ? 'All' : status.replace(/_/g, ' ')}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-neutral-800 text-neutral-400 text-xs uppercase tracking-wider font-semibold">
                <th className="py-3 px-4">Period</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Tasks Progress</th>
                <th className="py-3 px-4">Reconciled Vol.</th>
                <th className="py-3 px-4">Anomalies</th>
                <th className="py-3 px-4">Started At</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-800/60 font-sans">
              {filteredRuns.map(run => {
                const totalTasks = run.totalTasks || 10;
                const completed = run.completedTasks || 0;
                const percent = Math.round((completed / totalTasks) * 100);

                return (
                  <tr
                    key={run.id}
                    onClick={() => handleSelect(run.id)}
                    className="hover:bg-neutral-800/40 cursor-pointer transition-colors group"
                  >
                    <td className="py-3.5 px-4 font-bold text-white flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-primary-500 group-hover:scale-125 transition-transform" />
                      {run.period}
                    </td>
                    <td className="py-3.5 px-4">{getStatusBadge(run.status)}</td>
                    <td className="py-3.5 px-4">
                      <div className="w-36">
                        <div className="flex items-center justify-between text-xs mb-1">
                          <span className="text-neutral-300 font-medium">
                            {completed}/{totalTasks}
                          </span>
                          <span className="text-neutral-400">{percent}%</span>
                        </div>
                        <div className="w-full h-1.5 bg-neutral-800 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-primary-500 rounded-full transition-all duration-500"
                            style={{ width: `${percent}%` }}
                          />
                        </div>
                      </div>
                    </td>
                    <td className="py-3.5 px-4 font-mono text-neutral-200">
                      ${((run.reconciledVolume || 14840120) / 1000000).toFixed(2)}M
                    </td>
                    <td className="py-3.5 px-4">
                      <span className="px-2 py-0.5 rounded text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
                        {run.exceptionsCount || 3} flagged
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-xs text-neutral-400">
                      {new Date(run.startedAt || run.started_at || Date.now()).toLocaleDateString()}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <span className="inline-flex items-center gap-1 text-xs text-primary-400 font-medium group-hover:text-primary-300">
                        <span>Open Command Center</span>
                        <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      <CreateCloseRunModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSuccess={runId => handleSelect(runId)}
      />
    </div>
  );
};
