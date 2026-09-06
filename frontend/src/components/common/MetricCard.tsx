import React from 'react';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtext?: string;
  subtitle?: string;
  trend?: string;
  trendPositive?: boolean;
  diskColor?: 'primary' | 'secondary' | 'accent' | 'neutral' | 'orange' | 'yellow' | 'green' | 'blue';
  icon: React.ReactNode | React.ComponentType<{ className?: string }>;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  subtext,
  subtitle,
  trend,
  trendPositive = true,
  diskColor = 'primary',
  icon,
}) => {
  const displaySubtext = subtext || subtitle;

  const getDiskStyles = () => {
    switch (diskColor) {
      case 'primary':
      case 'orange':
        return {
          bg: 'var(--color-primary-500)',
          shadow: '0 6px 16px rgba(254, 47, 1, 0.32)',
        };
      case 'secondary':
      case 'yellow':
        return {
          bg: 'var(--color-secondary-500)',
          shadow: '0 6px 16px rgba(255, 200, 0, 0.35)',
        };
      case 'accent':
      case 'green':
        return {
          bg: 'var(--color-accent-500)',
          shadow: '0 6px 16px rgba(72, 200, 132, 0.32)',
        };
      case 'blue':
        return {
          bg: '#3b82f6',
          shadow: '0 6px 16px rgba(59, 130, 246, 0.32)',
        };
      default:
        return {
          bg: '#222225',
          shadow: '0 6px 16px rgba(0, 0, 0, 0.2)',
        };
    }
  };

  const disk = getDiskStyles();

  return (
    <div
      className="surface-card"
      style={{
        width: '100%',
        minWidth: 0,
        height: '100%',
        minHeight: '102px',
        padding: '1.15rem 1.25rem',
        borderRadius: 'var(--radius-lg)',
        display: 'flex',
        alignItems: 'center',
        gap: '1rem',
        boxSizing: 'border-box',
        transition: 'transform 160ms var(--ease-spring-ui), box-shadow 160ms var(--ease-spring-ui)',
      }}
    >
      {/* Circular Colored Icon Disk (Apple Depth & Glow) */}
      <div
        style={{
          width: '46px',
          height: '46px',
          borderRadius: '50%',
          background: disk.bg,
          boxShadow: disk.shadow,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#ffffff',
          flexShrink: 0,
        }}
      >
        {React.isValidElement(icon)
          ? icon
          : typeof icon === 'function'
          ? React.createElement(icon as React.ComponentType<{ className?: string }>, { className: 'w-5 h-5' })
          : icon}
      </div>

      <div
        style={{
          flex: 1,
          minWidth: 0,
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
        }}
      >
        {/* Title Zone (Uniform 16px height across all cards) */}
        <div
          title={title}
          style={{
            fontSize: '0.74rem',
            color: 'var(--color-neutral-400)',
            fontWeight: 600,
            letterSpacing: '0.02em',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            lineHeight: '16px',
            height: '16px',
          }}
        >
          {title}
        </div>

        {/* Value Zone (Unified typography & baseline alignment) */}
        <div
          className="font-mono"
          style={{
            fontFamily: "'Urbanist', var(--font-family-mono)",
            fontSize: '1.45rem',
            fontWeight: 600,
            color: 'var(--color-neutral-950)',
            lineHeight: 1.15,
            letterSpacing: '-0.02em',
            marginTop: '0.2rem',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
          }}
        >
          {value}
        </div>

        {/* Subtitle & Trend Zone (Uniform 16px height across all cards) */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.35rem',
            marginTop: '0.25rem',
            fontSize: '0.72rem',
            height: '16px',
            minHeight: '16px',
            lineHeight: '16px',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
          }}
        >
          {trend && (
            <span
              style={{
                fontWeight: 700,
                color: trendPositive ? 'var(--color-accent-600)' : 'var(--color-primary-600)',
                flexShrink: 0,
              }}
            >
              {trend}
            </span>
          )}
          {displaySubtext && (
            <span
              title={displaySubtext}
              style={{
                color: 'var(--color-neutral-400)',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {displaySubtext}
            </span>
          )}
        </div>
      </div>
    </div>
  );
};
