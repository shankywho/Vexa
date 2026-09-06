import React from 'react';
import { useCloseRun } from '../../context/CloseRunContext';
import { CheckCircle2, Clock, AlertOctagon, ArrowRight, Play, RefreshCw, Layers } from 'lucide-react';
import type { CloseTask, CloseTaskStatus } from '../../types/closeRun';

export const CloseTasksDAGPage: React.FC = () => {
  const { tasks, activeRun } = useCloseRun();

  const getStatusBadge = (status: CloseTaskStatus) => {
    switch (status) {
      case 'COMPLETED':
        return (
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem', background: '#dcfce7', color: '#15803d', padding: '0.2rem 0.55rem', borderRadius: 'var(--radius-full)', fontSize: '0.7rem', fontWeight: 700 }}>
            <CheckCircle2 size={12} />
            COMPLETED
          </span>
        );
      case 'IN_PROGRESS':
        return (
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem', background: '#fef3c7', color: '#b45309', padding: '0.2rem 0.55rem', borderRadius: 'var(--radius-full)', fontSize: '0.7rem', fontWeight: 700 }}>
            <Clock size={12} className="animate-spin" />
            IN PROGRESS
          </span>
        );
      case 'BLOCKED':
        return (
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem', background: '#fee2e2', color: '#b91c1c', padding: '0.2rem 0.55rem', borderRadius: 'var(--radius-full)', fontSize: '0.7rem', fontWeight: 700 }}>
            <AlertOctagon size={12} />
            BLOCKED
          </span>
        );
      default:
        return (
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem', background: 'var(--color-neutral-200)', color: 'var(--color-neutral-600)', padding: '0.2rem 0.55rem', borderRadius: 'var(--radius-full)', fontSize: '0.7rem', fontWeight: 700 }}>
            PENDING
          </span>
        );
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', width: '100%' }}>
      {/* Top Header & Actions */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h2 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 800, color: 'var(--color-neutral-950)' }}>
            10-Task Close Orchestration DAG
          </h2>
          <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-neutral-500)', marginTop: '0.15rem' }}>
            Topological workflow engine executing tasks in deterministic dependency sequence.
          </div>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <button className="btn-secondary" style={{ fontSize: 'var(--font-size-xs)' }}>
            <RefreshCw size={14} />
            Refresh Pipeline
          </button>
          <button className="btn-primary" style={{ fontSize: 'var(--font-size-xs)' }}>
            <Play size={14} />
            Execute Next Task
          </button>
        </div>
      </div>

      {/* DAG Visualization Pipeline Cards */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
        {tasks.map((task, idx) => (
          <div
            key={task.id}
            className="surface-card"
            style={{
              padding: '1.25rem',
              borderRadius: 'var(--radius-md)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              borderLeft: `4px solid ${
                task.status === 'COMPLETED'
                  ? 'var(--color-accent-500)'
                  : task.status === 'BLOCKED'
                  ? 'var(--color-primary-500)'
                  : task.status === 'IN_PROGRESS'
                  ? 'var(--color-secondary-500)'
                  : 'var(--color-neutral-300)'
              }`,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
              <div
                style={{
                  width: '36px',
                  height: '36px',
                  borderRadius: '50%',
                  background: 'var(--color-neutral-100)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontWeight: 800,
                  fontSize: 'var(--font-size-sm)',
                  color: 'var(--color-neutral-800)',
                }}
              >
                {idx + 1}
              </div>

              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                  <span style={{ fontSize: 'var(--font-size-base)', fontWeight: 800, color: 'var(--color-neutral-950)' }}>
                    {task.task_type.replace(/_/g, ' ')}
                  </span>
                  {getStatusBadge(task.status)}
                </div>

                <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-neutral-500)', marginTop: '0.2rem' }}>
                  {task.result_summary || 'Task queued for execution.'}
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem', textAlign: 'right' }}>
              {task.duration_ms && (
                <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-neutral-400)', fontFamily: 'var(--font-family-mono)' }}>
                  Duration: {(task.duration_ms / 1000).toFixed(1)}s
                </div>
              )}

              <button
                className="btn-secondary"
                style={{
                  padding: '0.35rem 0.65rem',
                  fontSize: '0.72rem',
                }}
              >
                Inspect Logs →
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
