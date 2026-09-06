import React, { useState, useRef, useEffect } from 'react';
import { useCloseRun } from '../../context/CloseRunContext';
import { useTenant } from '../../context/TenantContext';
import { useAuth } from '../../context/AuthContext';
import { useDemo } from '../../context/DemoContext';
import type { Role } from '../../types/rbac';
import {
  LayoutDashboard,
  GitFork,
  Radio,
  Scale,
  AlertTriangle,
  ClipboardCheck,
  ShieldCheck,
  FileCheck2,
  Cpu,
  LineChart,
  PlaySquare,
  SlidersHorizontal,
  Building2,
  ChevronDown,
  Search,
  Sliders,
  UserCheck,
  CheckCircle2,
  Play,
} from 'lucide-react';

interface SidebarProps {
  currentPath: string;
  onNavigate: (path: string) => void;
  onOpenCommandPalette?: () => void;
}

interface NavItem {
  id: string;
  label: string;
  path: string;
  icon: React.ReactNode;
  badge?: string | number;
  badgeVariant?: 'neutral' | 'accent' | 'warning' | 'critical' | 'brand';
}

const getInitials = (name?: string): string => {
  if (!name) return 'VX';
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
};

export const Sidebar: React.FC<SidebarProps> = ({ currentPath, onNavigate, onOpenCommandPalette }) => {
  const { activeRun } = useCloseRun();
  const { activeCompany, companies, setActiveCompanyId } = useTenant();
  const { user, role, setRole } = useAuth();
  const { demoState, setMode, toggleHud } = useDemo();

  const [isTenantOpen, setIsTenantOpen] = useState(false);
  const [isRoleOpen, setIsRoleOpen] = useState(false);

  const tenantRef = useRef<HTMLDivElement>(null);
  const roleRef = useRef<HTMLDivElement>(null);

  // Close popovers on click outside or escape key
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (tenantRef.current && !tenantRef.current.contains(event.target as Node)) {
        setIsTenantOpen(false);
      }
      if (roleRef.current && !roleRef.current.contains(event.target as Node)) {
        setIsRoleOpen(false);
      }
    };
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setIsTenantOpen(false);
        setIsRoleOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, []);

  const operationsNav: NavItem[] = [
    {
      id: 'overview',
      label: 'Overview',
      path: `/close-runs/${activeRun.id}/overview`,
      icon: <LayoutDashboard size={15} strokeWidth={2} />,
    },
    {
      id: 'tasks',
      label: 'Tasks',
      path: `/close-runs/${activeRun.id}/tasks`,
      icon: <GitFork size={15} strokeWidth={2} />,
      badge: `${activeRun.tasks_completed || 8}/10`,
      badgeVariant: 'accent',
    },
    {
      id: 'telemetry',
      label: 'Live Activity',
      path: `/close-runs/${activeRun.id}/telemetry`,
      icon: <Radio size={15} strokeWidth={2} />,
    },
    {
      id: 'reconciliation',
      label: 'Reconciliation',
      path: `/close-runs/${activeRun.id}/reconciliation`,
      icon: <Scale size={15} strokeWidth={2} />,
    },
    {
      id: 'exceptions',
      label: 'Exceptions',
      path: `/close-runs/${activeRun.id}/exceptions`,
      icon: <AlertTriangle size={15} strokeWidth={2} />,
      badge: 4,
      badgeVariant: 'critical',
    },
  ];

  const governanceNav: NavItem[] = [
    {
      id: 'approvals',
      label: 'Approvals',
      path: `/close-runs/${activeRun.id}/approvals`,
      icon: <ClipboardCheck size={15} strokeWidth={2} />,
      badge: 2,
      badgeVariant: 'warning',
    },
    {
      id: 'audit',
      label: 'Audit Trail',
      path: `/close-runs/${activeRun.id}/audit`,
      icon: <ShieldCheck size={15} strokeWidth={2} />,
    },
    {
      id: 'package',
      label: 'Close Package',
      path: `/close-runs/${activeRun.id}/package`,
      icon: <FileCheck2 size={15} strokeWidth={2} />,
    },
  ];

  const qualityNav: NavItem[] = [
    {
      id: 'benchmarks',
      label: 'Benchmarks',
      path: '/benchmarks',
      icon: <Cpu size={15} strokeWidth={2} />,
      badge: '35/35',
      badgeVariant: 'accent',
    },
    {
      id: 'calibration',
      label: 'Calibration',
      path: '/calibration',
      icon: <LineChart size={15} strokeWidth={2} />,
    },
  ];

  const systemNav: NavItem[] = [
    {
      id: 'demo-center',
      label: 'Demo Replay',
      path: '/demo-center',
      icon: <PlaySquare size={15} strokeWidth={2} />,
    },
    {
      id: 'policies',
      label: 'Policies',
      path: '/policies',
      icon: <SlidersHorizontal size={15} strokeWidth={2} />,
    },
    {
      id: 'tenants',
      label: 'Organizations',
      path: '/tenants',
      icon: <Building2 size={15} strokeWidth={2} />,
    },
  ];

  const renderBadge = (badge: string | number, variant: NavItem['badgeVariant'] = 'neutral', isActive: boolean) => {
    let bg = 'rgba(0, 0, 0, 0.05)';
    let color = 'rgba(60, 60, 67, 0.75)';

    if (isActive) {
      bg = 'rgba(0, 0, 0, 0.07)';
      color = 'rgba(0, 0, 0, 0.85)';
    } else if (variant === 'critical') {
      bg = 'rgba(255, 59, 48, 0.12)';
      color = '#d70015';
    } else if (variant === 'warning') {
      bg = 'rgba(255, 149, 0, 0.12)';
      color = '#b25000';
    } else if (variant === 'accent') {
      bg = 'rgba(52, 199, 89, 0.13)';
      color = '#1b8a3e';
    } else if (variant === 'brand') {
      bg = 'rgba(254, 47, 1, 0.1)';
      color = '#d72800';
    }

    return (
      <span
        style={{
          fontSize: '0.68rem',
          fontWeight: 600,
          padding: '0.1rem 0.45rem',
          borderRadius: '9999px',
          background: bg,
          color: color,
          fontVariantNumeric: 'tabular-nums',
          letterSpacing: '0.01em',
          lineHeight: 1.2,
          transition: 'background 140ms ease, color 140ms ease',
        }}
      >
        {badge}
      </span>
    );
  };

  const renderSection = (title: string, items: NavItem[]) => (
    <div style={{ marginBottom: '1.1rem' }}>
      <div
        style={{
          fontSize: '0.68rem',
          fontWeight: 600,
          color: 'rgba(60, 60, 67, 0.52)',
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
          padding: '0 0.55rem 0.3rem',
          userSelect: 'none',
          fontFamily: '-apple-system, BlinkMacSystemFont, var(--font-family-sans)',
        }}
      >
        {title}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
        {items.map((item) => {
          const isActive = currentPath === item.path || (item.id === 'overview' && currentPath === '/');
          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.path)}
              style={{
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '0.4rem 0.55rem',
                borderRadius: '7px',
                // macOS HIG subtle selection: refined neutral frosted tint with brand icon
                background: isActive ? 'rgba(0, 0, 0, 0.065)' : 'transparent',
                color: isActive ? '#000000' : 'rgba(0, 0, 0, 0.76)',
                fontWeight: isActive ? 600 : 500,
                fontSize: '0.8125rem',
                letterSpacing: '-0.01em',
                boxShadow: isActive
                  ? 'inset 0 0.5px 0.5px rgba(255, 255, 255, 0.8), 0 1px 2px rgba(0, 0, 0, 0.02)'
                  : 'none',
                border: 'none',
                cursor: 'pointer',
                textAlign: 'left',
                position: 'relative',
                transition: 'background 120ms cubic-bezier(0.16, 1, 0.3, 1), transform 80ms ease, color 120ms ease',
                userSelect: 'none',
              }}
              onMouseDown={(e) => (e.currentTarget.style.transform = 'scale(0.98)')}
              onMouseUp={(e) => (e.currentTarget.style.transform = 'scale(1)')}
              onMouseEnter={(e) => {
                if (!isActive) {
                  e.currentTarget.style.background = 'rgba(0, 0, 0, 0.04)';
                  e.currentTarget.style.color = '#000000';
                }
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'scale(1)';
                if (!isActive) {
                  e.currentTarget.style.background = 'transparent';
                  e.currentTarget.style.color = 'rgba(0, 0, 0, 0.76)';
                }
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                {/* Active Indicator Accent Pill */}
                {isActive && (
                  <span
                    style={{
                      position: 'absolute',
                      left: '2px',
                      width: '3px',
                      height: '14px',
                      borderRadius: '9999px',
                      background: 'var(--color-primary-500)',
                    }}
                  />
                )}
                <span
                  style={{
                    color: isActive ? 'var(--color-primary-600)' : 'rgba(60, 60, 67, 0.65)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    transition: 'color 120ms ease',
                    marginLeft: isActive ? '4px' : '0',
                  }}
                >
                  {item.icon}
                </span>
                <span>{item.label}</span>
              </div>
              {item.badge !== undefined && renderBadge(item.badge, item.badgeVariant, isActive)}
            </button>
          );
        })}
      </div>
    </div>
  );

  return (
    <aside
      style={{
        width: '260px',
        background: 'rgba(247, 247, 249, 0.84)',
        backdropFilter: 'blur(40px) saturate(190%)',
        WebkitBackdropFilter: 'blur(40px) saturate(190%)',
        borderRight: '1px solid rgba(0, 0, 0, 0.08)',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        flexShrink: 0,
        height: '100vh',
        overflow: 'hidden',
        position: 'relative',
        zIndex: 50,
      }}
    >
      {/* 1. Apple-Grade Workspace Brand Bar & Spotlight Capsule */}
      <div style={{ padding: '1rem 0.85rem 0.75rem 0.85rem' }}>
        {/* Brand Bar: Official Vexa Insignia + Live/Replay Mode Capsule */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.85rem' }}>
          {/* VEXA Logo + Title */}
          <div
            onClick={() => onNavigate(`/close-runs/${activeRun.id}/overview`)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.6rem',
              cursor: 'pointer',
              userSelect: 'none',
              transition: 'opacity 120ms ease, transform 120ms ease',
            }}
            onMouseDown={(e) => (e.currentTarget.style.transform = 'scale(0.97)')}
            onMouseUp={(e) => (e.currentTarget.style.transform = 'scale(1)')}
            onMouseEnter={(e) => (e.currentTarget.style.opacity = '0.82')}
            onMouseLeave={(e) => {
              e.currentTarget.style.opacity = '1';
              e.currentTarget.style.transform = 'scale(1)';
            }}
          >
            {/* Official Vexa Black Insignia */}
            <div
              style={{
                width: '28px',
                height: '28px',
                borderRadius: '7px',
                background: '#ffffff',
                border: '1px solid rgba(0, 0, 0, 0.08)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: '0 1px 3px rgba(0, 0, 0, 0.06), inset 0 1px 0 rgba(255, 255, 255, 0.9)',
                flexShrink: 0,
              }}
            >
              <img
                src="/vexa_black_logo.png"
                alt="VEXA"
                style={{
                  width: '20px',
                  height: '20px',
                  objectFit: 'contain',
                }}
              />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span
                style={{
                  fontWeight: 800,
                  fontSize: '0.9rem',
                  letterSpacing: '0.06em',
                  color: 'rgba(0, 0, 0, 0.94)',
                  lineHeight: 1.1,
                  fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", var(--font-family-sans)',
                }}
              >
                VEXA
              </span>
              <span
                style={{
                  fontSize: '0.62rem',
                  color: 'rgba(60, 60, 67, 0.52)',
                  fontWeight: 600,
                  letterSpacing: '0.04em',
                  marginTop: '1px',
                }}
              >
                CLOSE OS
              </span>
            </div>
          </div>

          {/* Mode Segment & Floating HUD Toggle */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <button
              onClick={() => setMode(demoState.mode === 'LIVE' ? 'REPLAY' : 'LIVE')}
              title={`Currently in ${demoState.mode} mode. Click to toggle.`}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.3rem',
                padding: '0.22rem 0.5rem',
                borderRadius: '9999px',
                background: demoState.mode === 'LIVE' ? 'rgba(52, 199, 89, 0.12)' : 'rgba(255, 149, 0, 0.14)',
                color: demoState.mode === 'LIVE' ? '#1b8a3e' : '#b25000',
                border: `1px solid ${demoState.mode === 'LIVE' ? 'rgba(52, 199, 89, 0.22)' : 'rgba(255, 149, 0, 0.25)'}`,
                fontSize: '0.68rem',
                fontWeight: 700,
                letterSpacing: '0.02em',
                cursor: 'pointer',
                transition: 'transform 80ms ease, background 140ms ease',
              }}
              onMouseDown={(e) => (e.currentTarget.style.transform = 'scale(0.95)')}
              onMouseUp={(e) => (e.currentTarget.style.transform = 'scale(1)')}
            >
              {demoState.mode === 'LIVE' ? (
                <>
                  <span
                    style={{
                      width: '6px',
                      height: '6px',
                      borderRadius: '50%',
                      background: '#34c759',
                      boxShadow: '0 0 6px rgba(52, 199, 89, 0.8)',
                    }}
                  />
                  <span>LIVE</span>
                </>
              ) : (
                <>
                  <Play size={10} fill="#b25000" />
                  <span>REPLAY</span>
                </>
              )}
            </button>

            <button
              onClick={toggleHud}
              title="Toggle HUD Telemetry"
              style={{
                width: '26px',
                height: '26px',
                borderRadius: '7px',
                border: '1px solid rgba(0, 0, 0, 0.08)',
                background: '#ffffff',
                color: 'rgba(60, 60, 67, 0.7)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: 'pointer',
                transition: 'transform 80ms ease, background 120ms ease, color 120ms ease',
                boxShadow: '0 1px 2px rgba(0, 0, 0, 0.04)',
              }}
              onMouseDown={(e) => (e.currentTarget.style.transform = 'scale(0.92)')}
              onMouseUp={(e) => (e.currentTarget.style.transform = 'scale(1)')}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'rgba(0, 0, 0, 0.04)';
                e.currentTarget.style.color = '#000000';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = '#ffffff';
                e.currentTarget.style.color = 'rgba(60, 60, 67, 0.7)';
              }}
            >
              <Sliders size={12} />
            </button>
          </div>
        </div>

        {/* 2. Apple Spotlight Search Trigger Bar */}
        <button
          onClick={onOpenCommandPalette}
          style={{
            width: '100%',
            background: 'rgba(0, 0, 0, 0.035)',
            border: '1px solid rgba(0, 0, 0, 0.06)',
            borderRadius: '8px',
            padding: '0.42rem 0.65rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            cursor: 'pointer',
            fontSize: '0.78rem',
            color: 'rgba(60, 60, 67, 0.6)',
            boxShadow: 'inset 0 1px 2px rgba(0, 0, 0, 0.02)',
            marginBottom: '0.5rem',
            transition: 'background 120ms ease, border-color 120ms ease, transform 80ms ease',
          }}
          onMouseDown={(e) => (e.currentTarget.style.transform = 'scale(0.985)')}
          onMouseUp={(e) => (e.currentTarget.style.transform = 'scale(1)')}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = 'rgba(0, 0, 0, 0.055)';
            e.currentTarget.style.borderColor = 'rgba(0, 0, 0, 0.12)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'rgba(0, 0, 0, 0.035)';
            e.currentTarget.style.borderColor = 'rgba(0, 0, 0, 0.06)';
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
            <Search size={13} color="rgba(60, 60, 67, 0.55)" />
            <span>Search or command...</span>
          </div>
          <kbd
            style={{
              background: '#ffffff',
              border: '1px solid rgba(0, 0, 0, 0.08)',
              color: 'rgba(60, 60, 67, 0.75)',
              padding: '0.08rem 0.35rem',
              borderRadius: '4px',
              fontSize: '0.64rem',
              fontFamily: '-apple-system, BlinkMacSystemFont, var(--font-family-mono)',
              fontWeight: 600,
              boxShadow: '0 1px 1px rgba(0, 0, 0, 0.04)',
            }}
          >
            ⌘K
          </kbd>
        </button>

        {/* 3. Apple Organization Menu Trigger */}
        <div ref={tenantRef} style={{ position: 'relative' }}>
          <button
            onClick={() => setIsTenantOpen(!isTenantOpen)}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              background: 'rgba(0, 0, 0, 0.035)',
              border: '1px solid rgba(0, 0, 0, 0.06)',
              padding: '0.4rem 0.65rem',
              borderRadius: '8px',
              cursor: 'pointer',
              transition: 'background 120ms ease, border-color 120ms ease, transform 80ms ease',
            }}
            onMouseDown={(e) => (e.currentTarget.style.transform = 'scale(0.985)')}
            onMouseUp={(e) => (e.currentTarget.style.transform = 'scale(1)')}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'rgba(0, 0, 0, 0.055)';
              e.currentTarget.style.borderColor = 'rgba(0, 0, 0, 0.12)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'rgba(0, 0, 0, 0.035)';
              e.currentTarget.style.borderColor = 'rgba(0, 0, 0, 0.06)';
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', minWidth: 0 }}>
              <div
                style={{
                  width: '20px',
                  height: '20px',
                  borderRadius: '5px',
                  background: 'rgba(254, 47, 1, 0.1)',
                  color: 'var(--color-primary-600)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                }}
              >
                <Building2 size={12} />
              </div>
              <span
                style={{
                  fontSize: '0.78rem',
                  fontWeight: 600,
                  color: 'rgba(0, 0, 0, 0.88)',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  letterSpacing: '-0.01em',
                }}
              >
                {activeCompany.name}
              </span>
            </div>
            <ChevronDown size={13} color="rgba(60, 60, 67, 0.5)" />
          </button>

          {/* Apple Popover Menu */}
          {isTenantOpen && (
            <div
              style={{
                position: 'absolute',
                top: 'calc(100% + 5px)',
                left: 0,
                right: 0,
                background: 'rgba(255, 255, 255, 0.95)',
                backdropFilter: 'blur(24px) saturate(200%)',
                WebkitBackdropFilter: 'blur(24px) saturate(200%)',
                borderRadius: '10px',
                boxShadow: '0 12px 30px rgba(0, 0, 0, 0.12), 0 2px 8px rgba(0, 0, 0, 0.05)',
                border: '1px solid rgba(0, 0, 0, 0.08)',
                padding: '0.35rem',
                zIndex: 100,
              }}
            >
              <div
                style={{
                  fontSize: '0.64rem',
                  color: 'rgba(60, 60, 67, 0.55)',
                  padding: '0.25rem 0.5rem',
                  textTransform: 'uppercase',
                  fontWeight: 700,
                  letterSpacing: '0.04em',
                }}
              >
                Organizations
              </div>
              {companies.map((c) => (
                <button
                  key={c.id}
                  onClick={() => {
                    setActiveCompanyId(c.id);
                    setIsTenantOpen(false);
                  }}
                  style={{
                    width: '100%',
                    textAlign: 'left',
                    padding: '0.45rem 0.55rem',
                    borderRadius: '6px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    color: c.id === activeCompany.id ? 'var(--color-primary-600)' : 'rgba(0, 0, 0, 0.85)',
                    background: c.id === activeCompany.id ? 'rgba(254, 47, 1, 0.08)' : 'transparent',
                    fontSize: '0.76rem',
                    border: 'none',
                    cursor: 'pointer',
                    fontWeight: c.id === activeCompany.id ? 600 : 500,
                    transition: 'background 100ms ease',
                  }}
                  onMouseEnter={(e) => {
                    if (c.id !== activeCompany.id) e.currentTarget.style.background = 'rgba(0, 0, 0, 0.04)';
                  }}
                  onMouseLeave={(e) => {
                    if (c.id !== activeCompany.id) e.currentTarget.style.background = 'transparent';
                  }}
                >
                  <span style={{ fontWeight: 600 }}>{c.name}</span>
                  <span style={{ fontSize: '0.68rem', opacity: 0.6, fontFamily: 'var(--font-family-mono)' }}>
                    {c.base_currency}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* 2. Scrollable Navigation List (Apple Translucent Scroll) */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '0.5rem 0.75rem',
        }}
      >
        {renderSection('Operations', operationsNav)}
        {renderSection('Governance', governanceNav)}
        {renderSection('Evaluation', qualityNav)}
        {renderSection('System', systemNav)}
      </div>

      {/* 3. Apple-Grade User Card & Living SOX 404 Seal */}
      <div
        style={{
          padding: '0.65rem 0.75rem',
          borderTop: '1px solid rgba(0, 0, 0, 0.06)',
          background: 'rgba(255, 255, 255, 0.45)',
          display: 'flex',
          flexDirection: 'column',
          gap: '0.4rem',
        }}
      >
        {/* Persona Switcher Button */}
        <div ref={roleRef} style={{ position: 'relative' }}>
          <button
            onClick={() => setIsRoleOpen(!isRoleOpen)}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              background: 'rgba(0, 0, 0, 0.03)',
              border: '1px solid rgba(0, 0, 0, 0.06)',
              borderRadius: '9px',
              padding: '0.4rem 0.6rem',
              cursor: 'pointer',
              transition: 'background 120ms ease, border-color 120ms ease, transform 80ms ease',
            }}
            onMouseDown={(e) => (e.currentTarget.style.transform = 'scale(0.985)')}
            onMouseUp={(e) => (e.currentTarget.style.transform = 'scale(1)')}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'rgba(0, 0, 0, 0.055)';
              e.currentTarget.style.borderColor = 'rgba(0, 0, 0, 0.12)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'rgba(0, 0, 0, 0.03)';
              e.currentTarget.style.borderColor = 'rgba(0, 0, 0, 0.06)';
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.55rem' }}>
              {/* Apple Initials Avatar */}
              <div
                style={{
                  width: '28px',
                  height: '28px',
                  borderRadius: '50%',
                  background: 'linear-gradient(180deg, #3a3a3c 0%, #1c1c1e 100%)',
                  color: '#ffffff',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontWeight: 600,
                  fontSize: '0.72rem',
                  letterSpacing: '0.02em',
                  boxShadow: '0 1px 3px rgba(0, 0, 0, 0.18), inset 0 1px 0 rgba(255, 255, 255, 0.22)',
                  flexShrink: 0,
                  userSelect: 'none',
                  fontFamily: '-apple-system, BlinkMacSystemFont, var(--font-family-sans)',
                }}
              >
                {getInitials(user.name)}
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', textAlign: 'left' }}>
                <span
                  style={{
                    fontSize: '0.76rem',
                    fontWeight: 600,
                    color: 'rgba(0, 0, 0, 0.88)',
                    lineHeight: 1.15,
                    letterSpacing: '-0.01em',
                  }}
                >
                  {user.name}
                </span>
                <span
                  style={{
                    fontSize: '0.64rem',
                    color: 'var(--color-primary-600)',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    letterSpacing: '0.02em',
                  }}
                >
                  {role}
                </span>
              </div>
            </div>
            <ChevronDown size={13} color="rgba(60, 60, 67, 0.5)" />
          </button>

          {/* Persona Menu Popover */}
          {isRoleOpen && (
            <div
              style={{
                position: 'absolute',
                bottom: 'calc(100% + 5px)',
                left: 0,
                right: 0,
                background: 'rgba(255, 255, 255, 0.95)',
                backdropFilter: 'blur(24px) saturate(200%)',
                WebkitBackdropFilter: 'blur(24px) saturate(200%)',
                borderRadius: '10px',
                boxShadow: '0 12px 30px rgba(0, 0, 0, 0.12), 0 2px 8px rgba(0, 0, 0, 0.05)',
                border: '1px solid rgba(0, 0, 0, 0.08)',
                padding: '0.35rem',
                zIndex: 100,
              }}
            >
              <div
                style={{
                  fontSize: '0.64rem',
                  color: 'rgba(60, 60, 67, 0.55)',
                  padding: '0.25rem 0.5rem',
                  textTransform: 'uppercase',
                  fontWeight: 700,
                  letterSpacing: '0.04em',
                }}
              >
                SOX 404 Persona
              </div>
              {(['CFO', 'CONTROLLER', 'ACCOUNTANT', 'VIEWER', 'ADMIN'] as Role[]).map((r) => (
                <button
                  key={r}
                  onClick={() => {
                    setRole(r);
                    setIsRoleOpen(false);
                  }}
                  style={{
                    width: '100%',
                    textAlign: 'left',
                    padding: '0.45rem 0.55rem',
                    borderRadius: '6px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    color: r === role ? 'var(--color-primary-600)' : 'rgba(0, 0, 0, 0.85)',
                    background: r === role ? 'rgba(254, 47, 1, 0.08)' : 'transparent',
                    fontSize: '0.76rem',
                    border: 'none',
                    cursor: 'pointer',
                    fontWeight: r === role ? 600 : 500,
                    transition: 'background 100ms ease',
                  }}
                  onMouseEnter={(e) => {
                    if (r !== role) e.currentTarget.style.background = 'rgba(0, 0, 0, 0.04)';
                  }}
                  onMouseLeave={(e) => {
                    if (r !== role) e.currentTarget.style.background = 'transparent';
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
                    <UserCheck size={13} color={r === role ? 'var(--color-primary-600)' : 'rgba(60, 60, 67, 0.5)'} />
                    <span>{r}</span>
                  </div>
                  {r === role && <CheckCircle2 size={13} color="var(--color-primary-600)" />}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Apple Status Seal: SOX 404 Living Ledger Guarantee */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0.35rem 0.55rem',
            background: 'rgba(52, 199, 89, 0.06)',
            border: '1px solid rgba(52, 199, 89, 0.14)',
            borderRadius: '7px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <ShieldCheck size={13} color="#1b8a3e" />
            <span style={{ fontSize: '0.68rem', fontWeight: 600, color: '#1b8a3e' }}>
              SOX 404 Ledger
            </span>
          </div>
          <div
            className="animate-pulse-glow"
            style={{
              width: '6px',
              height: '6px',
              borderRadius: '50%',
              background: '#34c759',
              boxShadow: '0 0 6px rgba(52, 199, 89, 0.8)',
            }}
          />
        </div>
      </div>
    </aside>
  );
};

