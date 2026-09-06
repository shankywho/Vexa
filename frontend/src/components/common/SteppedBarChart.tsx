import React, { useState } from 'react';

interface BarStepData {
  label: string;
  percentage: string;
  volume: string;
  heightRatio: number; // 0.2 to 1.0
}

interface SteppedBarChartProps {
  data?: BarStepData[];
}

export const SteppedBarChart: React.FC<SteppedBarChartProps> = ({
  data = [
    { label: 'Pass 1', percentage: '28%', volume: '$12.4M Reconciled', heightRatio: 0.55 },
    { label: 'Pass 2', percentage: '42%', volume: '$18.8M Reconciled', heightRatio: 0.88 },
    { label: 'Pass 3', percentage: '26%', volume: '$11.6M Reconciled', heightRatio: 0.52 },
    { label: 'Pass 4', percentage: '20%', volume: '$8.9M Reconciled', heightRatio: 0.40 },
    { label: 'Pass 5', percentage: '34%', volume: '$15.2M Reconciled', heightRatio: 0.70 },
    { label: 'Pass 6', percentage: '18%', volume: '$7.8M Reconciled', heightRatio: 0.36 },
    { label: 'Pass 7', percentage: '48%', volume: '$21.5M Reconciled', heightRatio: 0.95 },
    { label: 'Pass 8', percentage: '30%', volume: '$13.4M Reconciled', heightRatio: 0.62 },
  ],
}) => {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  return (
    <div style={{ width: '100%', position: 'relative' }}>
      {/* Chart Canvas */}
      <div
        style={{
          position: 'relative',
          width: '100%',
          height: '240px',
          display: 'flex',
          alignItems: 'flex-end',
          justifyContent: 'space-between',
          padding: '1.25rem 0.25rem 0.75rem',
          gap: '0.85rem',
          boxSizing: 'border-box',
        }}
      >
        {data.map((bar, idx) => {
          const isHovered = hoveredIndex === idx;
          const barHeight = Math.max(bar.heightRatio * 180, 48);

          return (
            <div
              key={idx}
              onMouseEnter={() => setHoveredIndex(idx)}
              onMouseLeave={() => setHoveredIndex(null)}
              style={{
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                cursor: 'pointer',
                position: 'relative',
                height: '100%',
                justifyContent: 'flex-end',
              }}
            >
              {/* Top Percentage Label */}
              <div
                style={{
                  fontFamily: "'Urbanist', var(--font-family-mono)",
                  fontSize: '0.78rem',
                  fontWeight: isHovered ? 700 : 600,
                  color: isHovered ? 'var(--color-primary-500)' : 'var(--color-neutral-400)',
                  marginBottom: '0.5rem',
                  letterSpacing: '-0.01em',
                  transition: 'color 160ms var(--ease-spring-ui), transform 160ms var(--ease-spring-ui)',
                  transform: isHovered ? 'translateY(-2px)' : 'none',
                }}
              >
                {bar.percentage}
              </div>

              {/* Apple Column Slot / Track with Stepped Tiers */}
              <div
                style={{
                  width: '100%',
                  maxWidth: '56px',
                  height: `${barHeight}px`,
                  position: 'relative',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'flex-end',
                  transition: 'transform 180ms var(--ease-spring-ui)',
                  transform: isHovered ? 'translateY(-4px)' : 'translateY(0)',
                }}
              >
                {/* Ambient Track Slot Backing */}
                <div
                  style={{
                    position: 'absolute',
                    bottom: 0,
                    left: 0,
                    right: 0,
                    height: '100%',
                    background: 'rgba(0, 0, 0, 0.03)',
                    borderRadius: '12px 12px 0 0',
                  }}
                />

                {/* Tier 3: Light translucent top step */}
                <div
                  style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    right: 0,
                    height: '100%',
                    background: 'rgba(254, 47, 1, 0.16)',
                    borderRadius: '12px 12px 0 0',
                  }}
                />

                {/* Tier 2: Medium opacity mid step */}
                <div
                  style={{
                    position: 'absolute',
                    top: '25%',
                    left: 0,
                    right: 0,
                    height: '75%',
                    background: 'rgba(254, 47, 1, 0.42)',
                    borderRadius: '10px 10px 0 0',
                  }}
                />

                {/* Tier 1: Solid vibrant primary base */}
                <div
                  style={{
                    position: 'absolute',
                    top: '50%',
                    left: 0,
                    right: 0,
                    height: '50%',
                    background: 'linear-gradient(180deg, #ff4e26 0%, #fe2f01 100%)',
                    borderRadius: '8px 8px 0 0',
                    boxShadow: isHovered ? '0 8px 20px rgba(254, 47, 1, 0.38)' : 'none',
                    transition: 'box-shadow 180ms var(--ease-spring-ui)',
                  }}
                />
              </div>

              {/* Apple Frosted Glass Tooltip */}
              {isHovered && (
                <div
                  style={{
                    position: 'absolute',
                    bottom: '100%',
                    marginBottom: '1rem',
                    background: 'rgba(29, 29, 31, 0.92)',
                    backdropFilter: 'blur(20px) saturate(180%)',
                    WebkitBackdropFilter: 'blur(20px) saturate(180%)',
                    border: '1px solid rgba(255, 255, 255, 0.14)',
                    color: '#ffffff',
                    padding: '0.5rem 0.85rem',
                    borderRadius: 'var(--radius-sm)',
                    fontSize: '0.74rem',
                    fontWeight: 600,
                    whiteSpace: 'nowrap',
                    boxShadow: '0 12px 28px rgba(0, 0, 0, 0.28)',
                    zIndex: 30,
                    pointerEvents: 'none',
                    animation: 'fadeIn 140ms var(--ease-spring-ui)',
                  }}
                >
                  <div style={{ fontWeight: 700, letterSpacing: '-0.01em' }}>{bar.label}: {bar.volume}</div>
                  <div style={{ color: '#34c759', fontSize: '0.68rem', marginTop: '0.15rem' }}>
                    Automated matching: {bar.percentage}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Baseline X-Axis Rule */}
      <div
        style={{
          width: '100%',
          height: '1px',
          background: 'rgba(0, 0, 0, 0.07)',
          margin: '0 0 0.5rem',
        }}
      />

      {/* X-Axis Labels */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          padding: '0 0.25rem',
          gap: '0.85rem',
        }}
      >
        {data.map((bar, idx) => (
          <div
            key={idx}
            style={{
              flex: 1,
              textAlign: 'center',
              fontSize: '0.68rem',
              fontWeight: 600,
              color: hoveredIndex === idx ? 'var(--color-primary-500)' : 'var(--color-neutral-400)',
              letterSpacing: '0.04em',
              textTransform: 'uppercase',
              transition: 'color 160ms var(--ease-spring-ui)',
            }}
          >
            {bar.label}
          </div>
        ))}
      </div>
    </div>
  );
};
