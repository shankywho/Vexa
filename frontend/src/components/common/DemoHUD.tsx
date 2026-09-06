import React from 'react';
import { useDemo } from '../../context/DemoContext';
import { Play, Pause, FastForward, Rewind, Radio, CheckCircle, ChevronDown, ChevronUp } from 'lucide-react';

export const DemoHUD: React.FC = () => {
  const {
    demoState,
    traces,
    isHudOpen,
    toggleHud,
    setMode,
    selectTrace,
    play,
    pause,
    setSpeed,
    stepForward,
    stepBackward,
  } = useDemo();

  return (
    <div
      style={{
        position: 'fixed',
        bottom: '1.25rem',
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 90,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
      }}
    >
      {/* Toggle Tab */}
      <button
        onClick={toggleHud}
        style={{
          background: 'var(--color-neutral-950)',
          color: '#ffffff',
          padding: '0.25rem 0.85rem',
          borderRadius: 'var(--radius-full) var(--radius-full) 0 0',
          fontSize: '0.68rem',
          fontWeight: 700,
          display: 'flex',
          alignItems: 'center',
          gap: '0.4rem',
          border: '1px solid rgba(255, 255, 255, 0.15)',
          borderBottom: 'none',
          boxShadow: '0 -4px 12px rgba(0, 0, 0, 0.2)',
        }}
      >
        <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: demoState.mode === 'LIVE' ? 'var(--color-accent-400)' : 'var(--color-secondary-400)' }} />
        <span>DEMO CONTROLLER HUD ({demoState.mode})</span>
        {isHudOpen ? <ChevronDown size={12} /> : <ChevronUp size={12} />}
      </button>

      {/* Main HUD Bar */}
      {isHudOpen && (
        <div
          style={{
            background: 'rgba(26, 26, 26, 0.96)',
            backdropFilter: 'blur(16px)',
            border: '1px solid rgba(255, 255, 255, 0.14)',
            borderRadius: 'var(--radius-lg)',
            boxShadow: '0 20px 40px -10px rgba(0, 0, 0, 0.5)',
            padding: '0.65rem 1.25rem',
            display: 'flex',
            alignItems: 'center',
            gap: '1.25rem',
            color: '#ffffff',
          }}
        >
          {/* Mode Switcher */}
          <div
            style={{
              background: 'rgba(255, 255, 255, 0.08)',
              padding: '0.2rem',
              borderRadius: 'var(--radius-full)',
              display: 'flex',
              alignItems: 'center',
            }}
          >
            <button
              onClick={() => setMode('LIVE')}
              style={{
                padding: '0.3rem 0.65rem',
                borderRadius: 'var(--radius-full)',
                fontSize: '0.7rem',
                fontWeight: 700,
                background: demoState.mode === 'LIVE' ? 'var(--color-accent-500)' : 'transparent',
                color: demoState.mode === 'LIVE' ? '#000000' : 'var(--color-neutral-400)',
                display: 'flex',
                alignItems: 'center',
                gap: '0.3rem',
              }}
            >
              <Radio size={11} />
              LIVE
            </button>
            <button
              onClick={() => setMode('REPLAY')}
              style={{
                padding: '0.3rem 0.65rem',
                borderRadius: 'var(--radius-full)',
                fontSize: '0.7rem',
                fontWeight: 700,
                background: demoState.mode === 'REPLAY' ? 'var(--color-secondary-400)' : 'transparent',
                color: demoState.mode === 'REPLAY' ? '#000000' : 'var(--color-neutral-400)',
                display: 'flex',
                alignItems: 'center',
                gap: '0.3rem',
              }}
            >
              <Play size={11} />
              REPLAY
            </button>
          </div>

          {/* Trace Selector Dropdown */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontSize: '0.7rem', color: 'var(--color-neutral-400)', textTransform: 'uppercase' }}>
              Golden Trace:
            </span>
            <select
              value={demoState.currentTraceId}
              onChange={(e) => selectTrace(e.target.value)}
              style={{
                background: 'rgba(255, 255, 255, 0.1)',
                color: '#ffffff',
                border: '1px solid rgba(255, 255, 255, 0.15)',
                borderRadius: 'var(--radius-sm)',
                padding: '0.3rem 0.65rem',
                fontSize: 'var(--font-size-xs)',
                fontWeight: 600,
                outline: 'none',
                maxWidth: '240px',
              }}
            >
              {traces.map((t) => (
                <option key={t.trace_id} value={t.trace_id} style={{ background: '#1a1a1a', color: '#fff' }}>
                  {t.title}
                </option>
              ))}
            </select>
          </div>

          {/* Playback Controls (Active in REPLAY mode) */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <button
              onClick={stepBackward}
              disabled={demoState.mode !== 'REPLAY'}
              style={{ color: 'var(--color-neutral-300)', padding: '0.25rem' }}
              title="Step Backward"
            >
              <Rewind size={16} />
            </button>

            <button
              onClick={demoState.isPlaying ? pause : play}
              disabled={demoState.mode !== 'REPLAY'}
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '50%',
                background: demoState.isPlaying ? 'var(--color-primary-500)' : 'var(--color-accent-500)',
                color: '#ffffff',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              {demoState.isPlaying ? <Pause size={15} /> : <Play size={15} style={{ marginLeft: '2px' }} />}
            </button>

            <button
              onClick={stepForward}
              disabled={demoState.mode !== 'REPLAY'}
              style={{ color: 'var(--color-neutral-300)', padding: '0.25rem' }}
              title="Step Forward"
            >
              <FastForward size={16} />
            </button>
          </div>

          {/* Speed Multipliers */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
            {[0.5, 1, 2, 5].map((s) => (
              <button
                key={s}
                onClick={() => setSpeed(s)}
                style={{
                  fontSize: '0.65rem',
                  fontWeight: 700,
                  padding: '0.2rem 0.45rem',
                  borderRadius: 'var(--radius-xs)',
                  background: demoState.speed === s ? 'rgba(255, 255, 255, 0.25)' : 'rgba(255, 255, 255, 0.05)',
                  color: demoState.speed === s ? '#ffffff' : 'var(--color-neutral-400)',
                }}
              >
                {s}x
              </button>
            ))}
          </div>

          {/* Step Progress */}
          <div style={{ fontSize: '0.72rem', color: 'var(--color-neutral-400)', fontFamily: 'var(--font-family-mono)' }}>
            Step: <span style={{ color: '#ffffff', fontWeight: 700 }}>{demoState.currentStep}</span>/{demoState.totalSteps}
          </div>
        </div>
      )}
    </div>
  );
};
