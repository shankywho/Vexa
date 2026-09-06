import React, { createContext, useContext, useState, useEffect } from 'react';
import type { DemoMode, DemoTrace, DemoState } from '../types/demo';
import { apiClient } from '../api/client';
import { MOCK_DEMO_TRACES } from '../api/mockData';

interface DemoContextType {
  demoState: DemoState;
  traces: DemoTrace[];
  activeTrace: DemoTrace | undefined;
  isReplayMode: boolean;
  isPlaying: boolean;
  speed: number;
  currentFrameIndex: number;
  isHudOpen: boolean;
  toggleHud: () => void;
  setMode: (mode: DemoMode) => Promise<void>;
  toggleReplayMode: () => Promise<void>;
  selectTrace: (traceId: string) => void;
  play: () => void;
  pause: () => void;
  togglePlayback: () => void;
  resetPlayback: () => void;
  setSpeed: (speed: number) => void;
  stepForward: () => void;
  stepBackward: () => void;
}

const DemoContext = createContext<DemoContextType | undefined>(undefined);

export const DemoProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [demoState, setDemoState] = useState<DemoState>({
    mode: 'LIVE',
    currentTraceId: MOCK_DEMO_TRACES[0].trace_id,
    isPlaying: false,
    speed: 1.0,
    currentStep: 14,
    totalSteps: 42,
  });
  const [traces, setTraces] = useState<DemoTrace[]>(MOCK_DEMO_TRACES);
  const [isHudOpen, setIsHudOpen] = useState(true);

  useEffect(() => {
    apiClient.getDemoTraces().then(list => {
      if (list && list.length > 0) setTraces(list);
    });
    apiClient.getDemoMode().then(res => {
      if (res && res.mode) setDemoState(prev => ({ ...prev, mode: res.mode }));
    });
  }, []);

  const toggleHud = () => setIsHudOpen(prev => !prev);

  const setMode = async (mode: DemoMode) => {
    await apiClient.setDemoMode(mode);
    setDemoState(prev => ({ ...prev, mode, isPlaying: mode === 'REPLAY' }));
  };

  const toggleReplayMode = async () => {
    const nextMode: DemoMode = demoState.mode === 'LIVE' ? 'REPLAY' : 'LIVE';
    await setMode(nextMode);
  };

  const selectTrace = (traceId: string) => {
    const matched = traces.find(t => t.trace_id === traceId);
    setDemoState(prev => ({
      ...prev,
      currentTraceId: traceId,
      currentStep: 1,
      totalSteps: matched?.frames_count || 30,
      isPlaying: true,
    }));
  };

  const play = () => setDemoState(prev => ({ ...prev, isPlaying: true }));
  const pause = () => setDemoState(prev => ({ ...prev, isPlaying: false }));
  const togglePlayback = () => setDemoState(prev => ({ ...prev, isPlaying: !prev.isPlaying }));
  const resetPlayback = () => setDemoState(prev => ({ ...prev, currentStep: 1, isPlaying: false }));
  const setSpeed = (speed: number) => setDemoState(prev => ({ ...prev, speed }));

  const stepForward = () => {
    setDemoState(prev => ({
      ...prev,
      currentStep: Math.min(prev.currentStep + 1, prev.totalSteps),
    }));
  };

  const stepBackward = () => {
    setDemoState(prev => ({
      ...prev,
      currentStep: Math.max(prev.currentStep - 1, 1),
    }));
  };

  // Replay simulation ticker
  useEffect(() => {
    if (!demoState.isPlaying || demoState.mode !== 'REPLAY') return;

    const interval = setInterval(() => {
      setDemoState(prev => {
        if (prev.currentStep >= prev.totalSteps) {
          return { ...prev, isPlaying: false };
        }
        return { ...prev, currentStep: prev.currentStep + 1 };
      });
    }, 1500 / demoState.speed);

    return () => clearInterval(interval);
  }, [demoState.isPlaying, demoState.mode, demoState.speed]);

  const activeTrace = traces.find(t => t.trace_id === demoState.currentTraceId) || traces[0];

  return (
    <DemoContext.Provider
      value={{
        demoState,
        traces,
        activeTrace,
        isReplayMode: demoState.mode === 'REPLAY',
        isPlaying: demoState.isPlaying,
        speed: demoState.speed,
        currentFrameIndex: demoState.currentStep,
        isHudOpen,
        toggleHud,
        setMode,
        toggleReplayMode,
        selectTrace,
        play,
        pause,
        togglePlayback,
        resetPlayback,
        setSpeed,
        stepForward,
        stepBackward,
      }}
    >
      {children}
    </DemoContext.Provider>
  );
};

export const useDemo = (): DemoContextType => {
  const context = useContext(DemoContext);
  if (!context) {
    throw new Error('useDemo must be used within a DemoProvider');
  }
  return context;
};
