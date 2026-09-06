import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import type { CloseRun, CloseTask } from '../types/closeRun';
import type { Exception } from '../types/exception';
import { apiClient } from '../api/client';
import { MOCK_CLOSE_RUN, MOCK_CLOSE_TASKS, MOCK_EXCEPTIONS } from '../api/mockData';
import { CloseRunEventStream } from '../api/sse';

export interface StagedApprovalItem {
  id: string;
  exceptionId: string;
  title: string;
  amount: string;
  status: 'PENDING' | 'APPROVED' | 'REJECTED';
}

interface CloseRunContextType {
  activeRun: CloseRun;
  currentRun: CloseRun;
  runs: CloseRun[];
  tasks: CloseTask[];
  activeTasks: CloseTask[];
  exceptions: Exception[];
  stagedApprovals: StagedApprovalItem[];
  isLoading: boolean;
  setActiveRunId: (id: string) => Promise<void>;
  setCurrentRunId: (id: string) => Promise<void>;
  createCloseRun: (period_start: string, period_end?: string) => Promise<CloseRun>;
  refreshRun: () => Promise<void>;
  startRun: () => Promise<void>;
  approveException: (id: string, notes?: string) => Promise<void>;
  rejectException: (id: string, notes?: string) => Promise<void>;
  escalateException: (id: string, reason: string) => Promise<void>;
  reverseException: (id: string, reason: string) => Promise<void>;
}

const CloseRunContext = createContext<CloseRunContextType | undefined>(undefined);

const HISTORICAL_RUNS: CloseRun[] = [
  MOCK_CLOSE_RUN,
  {
    id: 'run-2026-02-apex',
    companyId: MOCK_CLOSE_RUN.company_id,
    period: '2026-02',
    status: 'CLOSED',
    started_at: '2026-03-01T08:00:00Z',
    completed_at: '2026-03-01T12:24:00Z',
    version: 4,
    total_tasks: 10,
    tasks_completed: 10,
    reconciledVolume: 13950200,
    blocking_exceptions_count: 0,
  },
  {
    id: 'run-2026-01-apex',
    companyId: MOCK_CLOSE_RUN.company_id,
    period: '2026-01',
    status: 'CLOSED',
    started_at: '2026-02-01T08:00:00Z',
    completed_at: '2026-02-01T14:10:00Z',
    version: 8,
    total_tasks: 10,
    tasks_completed: 10,
    reconciledVolume: 12840000,
    blocking_exceptions_count: 1,
  },
];

export const CloseRunProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [runs, setRuns] = useState<CloseRun[]>(HISTORICAL_RUNS);
  const [activeRun, setActiveRun] = useState<CloseRun>(MOCK_CLOSE_RUN);
  const [tasks, setTasks] = useState<CloseTask[]>(MOCK_CLOSE_TASKS);
  const [exceptions, setExceptions] = useState<Exception[]>(MOCK_EXCEPTIONS);
  const [isLoading, setIsLoading] = useState(false);

  // Derive staged approvals from exceptions
  const stagedApprovals: StagedApprovalItem[] = exceptions
    .filter((e) => e.status === 'STAGED' || e.status === 'INVESTIGATING' || e.status === 'OPEN')
    .map((e) => ({
      id: `app-${e.id.slice(0, 8)}`,
      exceptionId: e.id,
      title: e.title || e.root_cause || `${e.type.replace(/_/g, ' ')} Review`,
      amount: e.financial_impact.startsWith('$') ? e.financial_impact : `$${parseFloat(e.financial_impact).toLocaleString()}`,
      status: 'PENDING',
    }));

  // Initial load of close runs from backend
  const loadRunsList = useCallback(async () => {
    try {
      const backendRuns = await apiClient.getCloseRuns();
      if (backendRuns && backendRuns.length > 0) {
        setRuns(backendRuns);
        setActiveRun((prev) => {
          const match = backendRuns.find((b) => b.id === prev.id);
          return match || backendRuns[0];
        });
      }
    } catch (err) {
      console.warn('Could not fetch close runs from backend, keeping local runs', err);
    }
  }, []);

  useEffect(() => {
    loadRunsList();
  }, [loadRunsList]);

  // Load a single run along with its tasks and exceptions
  const loadRun = useCallback(async (id: string) => {
    if (!id) return;
    try {
      setIsLoading(true);
      const [runData, taskData, exceptionData] = await Promise.all([
        apiClient.getCloseRun(id),
        apiClient.getCloseTasks(id),
        apiClient.getCloseExceptions(id),
      ]);

      if (runData) {
        setActiveRun(runData);
      }

      if (taskData && taskData.length > 0) {
        setTasks(taskData);
      }

      if (exceptionData && exceptionData.length > 0) {
        setExceptions(exceptionData);
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadRun(activeRun.id);
  }, [activeRun.id, loadRun]);

  // Connect SSE for active run state updates
  useEffect(() => {
    const stream = new CloseRunEventStream(activeRun.id);
    const unsubscribe = stream.subscribe((event, data) => {
      if (event === 'close_run_state_change' && data.status) {
        setActiveRun((prev) => ({ ...prev, status: data.status, version: (prev.version || 1) + 1 }));
      }
      if (event === 'close_task_state_change' && data.task_type && data.status) {
        setTasks((prev) =>
          prev.map((t) => (t.task_type === data.task_type ? { ...t, status: data.status } : t))
        );
      }
      if (event === 'actions_executed') {
        // Refresh exceptions when actions execute
        apiClient.getCloseExceptions(activeRun.id).then((fresh) => {
          if (fresh && fresh.length > 0) setExceptions(fresh);
        });
      }
    });

    stream.connect();
    return () => {
      unsubscribe();
      stream.disconnect();
    };
  }, [activeRun.id]);

  const setActiveRunId = async (id: string) => {
    await loadRun(id);
  };

  const refreshRun = async () => {
    await loadRun(activeRun.id);
  };

  const startRun = async () => {
    const updated = await apiClient.startCloseRun(activeRun.id);
    if (updated) {
      setActiveRun(updated);
      await loadRun(activeRun.id);
    }
  };

  const createCloseRun = async (period_start: string, period_end?: string): Promise<CloseRun> => {
    let start = period_start;
    let end = period_end;
    if (!end && start.length === 7 && start.includes('-')) {
      const [year, month] = start.split('-');
      start = `${year}-${month}-01`;
      const lastDay = new Date(parseInt(year), parseInt(month), 0).getDate();
      end = `${year}-${month}-${lastDay}`;
    }
    const newRun = await apiClient.createCloseRun(start, end || start);
    setRuns((prev) => [newRun, ...prev]);
    setActiveRun(newRun);
    return newRun;
  };

  const approveException = async (id: string, notes?: string) => {
    await apiClient.approveException(id, notes);
    await refreshRun();
  };

  const rejectException = async (id: string, notes?: string) => {
    await apiClient.rejectException(id, notes);
    await refreshRun();
  };

  const escalateException = async (id: string, reason: string) => {
    await apiClient.escalateException(id, reason);
    await refreshRun();
  };

  const reverseException = async (id: string, reason: string) => {
    await apiClient.reverseException(id, reason);
    await refreshRun();
  };

  return (
    <CloseRunContext.Provider
      value={{
        activeRun,
        currentRun: activeRun,
        runs,
        tasks,
        activeTasks: tasks,
        exceptions,
        stagedApprovals,
        isLoading,
        setActiveRunId,
        setCurrentRunId: setActiveRunId,
        createCloseRun,
        refreshRun,
        startRun,
        approveException,
        rejectException,
        escalateException,
        reverseException,
      }}
    >
      {children}
    </CloseRunContext.Provider>
  );
};

export const useCloseRun = (): CloseRunContextType => {
  const context = useContext(CloseRunContext);
  if (!context) {
    throw new Error('useCloseRun must be used within a CloseRunProvider');
  }
  return context;
};
