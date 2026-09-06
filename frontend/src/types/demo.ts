export type DemoMode = 'LIVE' | 'REPLAY';

export interface DemoFrame {
  timestamp_offset_ms: number;
  event_type: string;
  data: Record<string, unknown>;
}

export interface DemoTrace {
  id?: string;
  trace_id?: string;
  scenario_id?: string;
  scenario_key?: string;
  title: string;
  description: string;
  duration_ms?: number;
  total_duration_ms?: number;
  frames_count?: number;
  total_steps?: number;
  is_golden?: boolean;
  events?: Record<string, unknown>[];
  frames?: DemoFrame[];
  created_at?: string;
}

export interface DemoState {
  mode: DemoMode;
  currentTraceId?: string;
  isPlaying: boolean;
  speed: number;
  currentStep: number;
  totalSteps: number;
}
