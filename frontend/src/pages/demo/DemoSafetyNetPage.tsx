import React from 'react';
import { useDemo } from '../../context/DemoContext';
import { MetricCard } from '../../components/common/MetricCard';
import {
  Play,
  Pause,
  SkipForward,
  RotateCcw,
  ShieldAlert,
  Radio,
  Sparkles,
  Layers,
  Clock,
  CheckCircle2,
  Cpu,
} from 'lucide-react';

export const DemoSafetyNetPage: React.FC = () => {
  const {
    isReplayMode,
    toggleReplayMode,
    activeTrace,
    traces,
    selectTrace,
    isPlaying,
    togglePlayback,
    stepForward,
    resetPlayback,
    speed,
    setSpeed,
    currentFrameIndex,
  } = useDemo();

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
              background: 'var(--color-secondary-50)',
              color: 'var(--color-secondary-600)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 8px 18px rgba(255, 200, 0, 0.25)',
            }}
          >
            <ShieldAlert size={32} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <h1 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 800, color: 'var(--color-neutral-950)', margin: 0 }}>
                Demo Safety Net & Replay Studio
              </h1>
              <span className={isReplayMode ? 'badge-yellow' : 'badge-green'}>
                {isReplayMode ? 'REPLAY SAFETY NET' : 'LIVE BACKEND ACTIVE'}
              </span>
            </div>
            <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-neutral-500)', marginTop: '0.35rem' }}>
              Guaranteed zero-risk deterministic trace replay for high-stakes executive demonstrations.
            </p>
          </div>
        </div>

        {/* Live vs Replay Switcher */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            background: 'var(--color-neutral-100)',
            padding: '0.3rem',
            borderRadius: 'var(--radius-full)',
            border: '1px solid var(--color-neutral-200)',
          }}
        >
          <button
            onClick={() => isReplayMode && toggleReplayMode()}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              padding: '0.5rem 1rem',
              borderRadius: 'var(--radius-full)',
              fontSize: 'var(--font-size-xs)',
              fontWeight: 800,
              background: !isReplayMode ? '#16a34a' : 'transparent',
              color: !isReplayMode ? '#ffffff' : 'var(--color-neutral-600)',
              boxShadow: !isReplayMode ? '0 4px 12px rgba(22, 163, 74, 0.3)' : 'none',
              transition: 'all var(--transition-fast)',
            }}
          >
            <Radio size={14} className={!isReplayMode ? 'animate-pulse' : ''} />
            <span>LIVE BACKEND</span>
          </button>
          <button
            onClick={() => !isReplayMode && toggleReplayMode()}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              padding: '0.5rem 1rem',
              borderRadius: 'var(--radius-full)',
              fontSize: 'var(--font-size-xs)',
              fontWeight: 800,
              background: isReplayMode ? 'var(--color-secondary-500)' : 'transparent',
              color: isReplayMode ? '#000000' : 'var(--color-neutral-600)',
              boxShadow: isReplayMode ? '0 4px 12px rgba(255, 200, 0, 0.4)' : 'none',
              transition: 'all var(--transition-fast)',
            }}
          >
            <Sparkles size={14} />
            <span>REPLAY SAFETY NET</span>
          </button>
        </div>
      </div>

      {/* 4 Circular Stat Disks (Apple Design: strictly identical dimensions) */}
      <div className="metrics-strip-4">
        <MetricCard
          title="Current Mode"
          value={isReplayMode ? 'Replay Mode' : 'Live Mode'}
          subtitle={isReplayMode ? 'Zero network/LLM failure risk' : 'Direct backend API & SSE streaming'}
          icon={<Cpu size={24} />}
          diskColor={isReplayMode ? 'yellow' : 'green'}
        />
        <MetricCard
          title="Active Trace"
          value={activeTrace?.scenario_id || 'None'}
          subtitle={(activeTrace?.title || '').slice(0, 28) + '...'}
          icon={<Layers size={24} />}
          diskColor="blue"
        />
        <MetricCard
          title="Frame Progress"
          value={`${currentFrameIndex} / ${activeTrace?.frames_count || 42}`}
          subtitle="Simulated SSE telemetry frames"
          icon={<Clock size={24} />}
          diskColor="orange"
        />
        <MetricCard
          title="Playback Speed"
          value={`${speed}x`}
          subtitle="Real-time timeline multiplier"
          icon={<Play size={24} />}
          diskColor="green"
        />
      </div>

      {/* Trace Selector Cards */}
      <div className="card">
        <div className="card-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Layers size={20} color="var(--color-primary-500)" />
            <h2 style={{ fontSize: 'var(--font-size-md)', fontWeight: 800, color: 'var(--color-neutral-950)', margin: 0 }}>
              Select Golden Scenario Trace
            </h2>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.25rem' }}>
          {traces.map((trace, index) => {
            const isSelected = activeTrace?.trace_id === trace.trace_id;
            return (
              <div
                key={trace.trace_id || index}
                onClick={() => trace.trace_id && selectTrace(trace.trace_id)}
                style={{
                  padding: '1.25rem',
                  borderRadius: 'var(--radius-lg)',
                  border: isSelected ? '2px solid var(--color-primary-500)' : '1px solid var(--color-neutral-200)',
                  background: isSelected ? 'var(--color-primary-50)' : '#ffffff',
                  cursor: 'pointer',
                  transition: 'all var(--transition-fast)',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  gap: '1rem',
                  boxShadow: isSelected ? '0 8px 24px rgba(254, 47, 1, 0.12)' : 'var(--shadow-sm)',
                }}
              >
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                    <span className="badge-blue font-mono">{trace.scenario_id || trace.scenario_key}</span>
                    {isSelected && (
                      <span className="badge-green">
                        <CheckCircle2 size={12} />
                        <span>Active Trace</span>
                      </span>
                    )}
                  </div>
                  <h3 style={{ fontSize: 'var(--font-size-sm)', fontWeight: 800, color: 'var(--color-neutral-950)', margin: '0 0 0.5rem 0' }}>
                    {trace.title || trace.scenario_key || 'Telemetry Trace'}
                  </h3>
                  <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-neutral-600)', margin: 0, lineHeight: 1.5 }}>
                    {trace.description || `Autonomous execution trace for ${trace.scenario_key}`}
                  </p>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--color-neutral-500)', paddingTop: '0.75rem', borderTop: '1px solid var(--color-neutral-200)' }}>
                  <span>{trace.frames_count ?? trace.total_steps ?? 0} Telemetry Frames</span>
                  <span>{(((trace.duration_ms ?? trace.total_duration_ms) || 0) / 1000).toFixed(0)}s Duration</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Playback Control Bar */}
      <div
        className="card"
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '1rem',
          padding: '1.25rem 1.5rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <button
            onClick={togglePlayback}
            className="btn-primary"
            style={{
              padding: '0.65rem 1.25rem',
              background: isPlaying ? 'var(--color-secondary-500)' : 'var(--color-primary-500)',
              color: isPlaying ? '#000000' : '#ffffff',
            }}
          >
            {isPlaying ? <Pause size={18} fill="currentColor" /> : <Play size={18} fill="currentColor" />}
            <span>{isPlaying ? 'Pause Simulation' : 'Play Simulation'}</span>
          </button>

          <button onClick={stepForward} className="btn-secondary" title="Step One Frame Forward">
            <SkipForward size={16} />
            <span>Step Forward</span>
          </button>

          <button onClick={resetPlayback} className="btn-secondary" title="Reset Trace to Beginning">
            <RotateCcw size={16} />
            <span>Reset</span>
          </button>
        </div>

        {/* Speed Multiplier */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', background: 'var(--color-neutral-100)', padding: '0.25rem', borderRadius: 'var(--radius-full)' }}>
          {[0.5, 1, 2, 5].map(s => (
            <button
              key={s}
              onClick={() => setSpeed(s)}
              style={{
                padding: '0.3rem 0.75rem',
                borderRadius: 'var(--radius-full)',
                fontSize: 'var(--font-size-xs)',
                fontWeight: 700,
                background: speed === s ? 'var(--color-neutral-900)' : 'transparent',
                color: speed === s ? '#ffffff' : 'var(--color-neutral-600)',
                transition: 'all var(--transition-fast)',
              }}
            >
              {s}x
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};
