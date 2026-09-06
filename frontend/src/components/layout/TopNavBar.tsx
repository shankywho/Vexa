import React, { useState } from 'react';
import { useTenant } from '../../context/TenantContext';
import { useAuth } from '../../context/AuthContext';
import { useCloseRun } from '../../context/CloseRunContext';
import { useDemo } from '../../context/DemoContext';
import type { Role } from '../../types/rbac';
import {
  Search,
  ChevronDown,
  Building2,
  Play,
  Radio,
  CheckCircle2,
  Sliders,
  UserCheck
} from 'lucide-react';

interface TopNavBarProps {
  onOpenCommandPalette: () => void;
}

export const TopNavBar: React.FC<TopNavBarProps> = ({ onOpenCommandPalette }) => {
  const { activeCompany, companies, setActiveCompanyId } = useTenant();
  const { user, role, setRole } = useAuth();
  const { activeRun } = useCloseRun();
  const { demoState, setMode, toggleHud } = useDemo();

  const [isTenantOpen, setIsTenantOpen] = useState(false);
  const [isRoleOpen, setIsRoleOpen] = useState(false);

  const currentHash = window.location.hash || '';

  const getContextTitle = () => {
    if (currentHash.startsWith('#/benchmarks')) return 'CFO-Bench Studio';
    if (currentHash.startsWith('#/calibration')) return 'Confidence Calibration';
    if (currentHash.startsWith('#/demo-center') || currentHash.startsWith('#/demo')) return 'Safety Net HUD';
    if (currentHash.startsWith('#/policies')) return 'Materiality Policies';
    if (currentHash.startsWith('#/tenants')) return 'Organizations';
    return `${activeRun.period || 'March 2026 Close OS'} • SOX 404`;
  };

  const navigateTo = (path: string) => {
    window.location.hash = path;
  };

  return (
    <header
      style={{
        padding: '0.75rem 1.5rem 0.5rem 1.5rem',
        position: 'sticky',
        top: 0,
        zIndex: 100,
        background: 'transparent',
      }}
    >
      {/* Floating Obsidian Capsule Navbar (Matching User Reference Design & Apple Material Principles) */}
      <div
        style={{
          maxWidth: '1560px',
          margin: '0 auto',
          height: '54px',
          background: 'linear-gradient(180deg, #18181a 0%, #111113 100%)',
          borderRadius: '9999px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 0.5rem 0 1.35rem',
          boxShadow: '0 16px 36px -4px rgba(0, 0, 0, 0.5), 0 2px 8px rgba(0, 0, 0, 0.3)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          borderTop: '1px solid rgba(255, 255, 255, 0.16)', // Apple specular top light highlight
          backdropFilter: 'blur(24px) saturate(180%)',
          gap: '1rem',
        }}
      >
        {/* Left: VEXA Aperture Logo + Organization Selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem', flexShrink: 0 }}>
          {/* Exact Logo from Reference: Geometric 4-Bracket Aperture + VEXA */}
          <div
            onClick={() => navigateTo(`/close-runs/${activeRun.id}/overview`)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.65rem',
              cursor: 'pointer',
              userSelect: 'none',
              transition: 'transform 160ms var(--ease-out), opacity 160ms var(--ease-out)',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.opacity = '0.85')}
            onMouseLeave={(e) => (e.currentTarget.style.opacity = '1')}
          >
            <svg
              width="22"
              height="22"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#ffffff"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              {/* 4 corner brackets */}
              <path d="M7 4H5a2 2 0 0 0-2 2v2" />
              <path d="M17 4h2a2 2 0 0 1 2 2v2" />
              <path d="M7 20H5a2 2 0 0 1-2-2v-2" />
              <path d="M17 20h2a2 2 0 0 0 2-2v-2" />
              {/* center geometric aperture */}
              <circle cx="12" cy="12" r="3.2" strokeWidth="2" />
              <path d="M12 9v6M9 12h6" strokeWidth="1.6" />
            </svg>
            <span
              style={{
                fontWeight: 900,
                fontSize: '0.92rem',
                letterSpacing: '0.18em',
                color: '#ffffff',
                textTransform: 'uppercase',
                fontFamily: 'var(--font-family-sans)',
              }}
            >
              VEXA
            </span>
          </div>

          <div style={{ width: '1px', height: '18px', background: 'rgba(255, 255, 255, 0.12)' }} />

          {/* Compact Tenant Switcher */}
          <div style={{ position: 'relative' }}>
            <button
              onClick={() => setIsTenantOpen(!isTenantOpen)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.45rem',
                background: 'rgba(255, 255, 255, 0.05)',
                padding: '0.35rem 0.75rem',
                borderRadius: '9999px',
                color: '#ffffff',
                fontSize: '0.78rem',
                fontWeight: 600,
                border: '1px solid rgba(255, 255, 255, 0.08)',
                transition: 'background-color 160ms var(--ease-out), border-color 160ms var(--ease-out), transform 160ms var(--ease-out)',
              }}
            >
              <Building2 size={13} color="var(--color-primary-400)" />
              <span style={{ maxWidth: '140px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {activeCompany.name}
              </span>
              <ChevronDown size={12} color="var(--color-neutral-400)" />
            </button>

            {isTenantOpen && (
              <div
                className="popover-dropdown"
                style={{
                  position: 'absolute',
                  top: '100%',
                  left: 0,
                  marginTop: '0.65rem',
                  width: '240px',
                  background: '#1c1c1c',
                  borderRadius: 'var(--radius-md)',
                  boxShadow: 'var(--shadow-xl)',
                  border: '1px solid rgba(255, 255, 255, 0.12)',
                  padding: '0.5rem',
                  zIndex: 200,
                  transformOrigin: 'top left',
                }}
              >
                <div style={{ fontSize: '0.68rem', color: 'var(--color-neutral-400)', padding: '0.25rem 0.5rem', textTransform: 'uppercase', fontWeight: 700 }}>
                  Select Organization
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
                      padding: '0.5rem 0.65rem',
                      borderRadius: 'var(--radius-sm)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      color: c.id === activeCompany.id ? 'var(--color-primary-400)' : '#ffffff',
                      background: c.id === activeCompany.id ? 'rgba(254, 47, 1, 0.12)' : 'transparent',
                      fontSize: 'var(--font-size-xs)',
                      transition: 'background-color 160ms var(--ease-out), color 160ms var(--ease-out)',
                    }}
                  >
                    <span style={{ fontWeight: 600 }}>{c.name}</span>
                    <span style={{ fontSize: '0.7rem', opacity: 0.6 }}>{c.base_currency}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Center: Minimal Context Breadcrumb Capsule (Zero Repetition with Sidebar) */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.55rem',
            background: 'rgba(255, 255, 255, 0.04)',
            padding: '0.35rem 1.15rem',
            borderRadius: '9999px',
            border: '1px solid rgba(255, 255, 255, 0.06)',
            boxShadow: 'inset 0 1px 2px rgba(0, 0, 0, 0.35)',
            fontSize: '0.78rem',
            fontWeight: 600,
            color: 'rgba(255, 255, 255, 0.7)',
            letterSpacing: '0.02em',
          }}
        >
          <span
            style={{
              width: '6px',
              height: '6px',
              borderRadius: '50%',
              background: 'var(--color-primary-400)',
              boxShadow: '0 0 8px var(--color-primary-400)',
            }}
          />
          <span>{getContextTitle()}</span>
        </div>

        {/* Right: Stark White Pill Button (Search / Quick Action) + Persona Switcher */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexShrink: 0 }}>
          {/* Live vs Replay Badge */}
          <button
            onClick={() => setMode(demoState.mode === 'LIVE' ? 'REPLAY' : 'LIVE')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              padding: '0.3rem 0.75rem',
              borderRadius: '9999px',
              background:
                demoState.mode === 'LIVE'
                  ? 'rgba(72, 200, 132, 0.15)'
                  : 'rgba(255, 200, 0, 0.18)',
              color:
                demoState.mode === 'LIVE'
                  ? 'var(--color-accent-400)'
                  : 'var(--color-secondary-400)',
              border: `1px solid ${
                demoState.mode === 'LIVE'
                  ? 'rgba(72, 200, 132, 0.35)'
                  : 'rgba(255, 200, 0, 0.35)'
              }`,
              fontSize: '0.72rem',
              fontWeight: 800,
              letterSpacing: '0.04em',
              transition: 'background-color 160ms var(--ease-out), transform 160ms var(--ease-out), border-color 160ms var(--ease-out)',
            }}
          >
            {demoState.mode === 'LIVE' ? (
              <>
                <Radio size={12} className="animate-pulse-glow" />
                <span>LIVE</span>
              </>
            ) : (
              <>
                <Play size={12} />
                <span>REPLAY</span>
              </>
            )}
          </button>

          <button
            onClick={toggleHud}
            title="Toggle Replay Controls"
            style={{
              color: 'var(--color-neutral-400)',
              padding: '0.35rem',
              borderRadius: '9999px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'color 160ms var(--ease-out), transform 160ms var(--ease-out)',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = '#ffffff')}
            onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--color-neutral-400)')}
          >
            <Sliders size={15} />
          </button>

          {/* Stark White Pill Button (Matching Exact Reference Image) */}
          <button
            onClick={onOpenCommandPalette}
            style={{
              background: '#ffffff',
              color: '#0d0d0f',
              padding: '0.45rem 1.15rem',
              borderRadius: '9999px',
              fontSize: '0.8rem',
              fontWeight: 800,
              display: 'flex',
              alignItems: 'center',
              gap: '0.45rem',
              boxShadow: '0 2px 10px rgba(0, 0, 0, 0.25)',
              transition: 'transform 160ms var(--ease-out), box-shadow 160ms var(--ease-out), background-color 160ms var(--ease-out)',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.transform = 'scale(1.03)')}
            onMouseLeave={(e) => (e.currentTarget.style.transform = 'scale(1)')}
          >
            <Search size={13} strokeWidth={2.6} />
            <span>Search</span>
            <kbd
              style={{
                background: '#ededed',
                color: '#555555',
                padding: '0.1rem 0.35rem',
                borderRadius: '4px',
                fontSize: '0.65rem',
                fontFamily: 'var(--font-family-mono)',
                fontWeight: 700,
              }}
            >
              ⌘K
            </kbd>
          </button>

          {/* Persona Avatar Switcher */}
          <div style={{ position: 'relative' }}>
            <button
              onClick={() => setIsRoleOpen(!isRoleOpen)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.45rem',
                background: 'transparent',
                color: '#ffffff',
                padding: '0.2rem',
                transition: 'transform 160ms var(--ease-out)',
              }}
            >
              <div
                style={{
                  width: '30px',
                  height: '30px',
                  borderRadius: '50%',
                  overflow: 'hidden',
                  border: '2px solid var(--color-primary-400)',
                  boxShadow: '0 0 8px rgba(254, 47, 1, 0.35)',
                }}
              >
                <img
                  src={user.avatar_url}
                  alt={user.name}
                  style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                />
              </div>
              <ChevronDown size={11} color="var(--color-neutral-400)" />
            </button>

            {isRoleOpen && (
              <div
                className="popover-dropdown"
                style={{
                  position: 'absolute',
                  top: '100%',
                  right: 0,
                  marginTop: '0.65rem',
                  width: '230px',
                  background: '#1c1c1c',
                  borderRadius: 'var(--radius-md)',
                  boxShadow: 'var(--shadow-xl)',
                  border: '1px solid rgba(255, 255, 255, 0.12)',
                  padding: '0.5rem',
                  zIndex: 200,
                  transformOrigin: 'top right',
                }}
              >
                <div style={{ fontSize: '0.68rem', color: 'var(--color-neutral-400)', padding: '0.25rem 0.5rem', textTransform: 'uppercase', fontWeight: 700 }}>
                  SOX 404 Persona Switcher
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
                      padding: '0.5rem 0.65rem',
                      borderRadius: 'var(--radius-sm)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      color: r === role ? 'var(--color-primary-400)' : '#ffffff',
                      background: r === role ? 'rgba(254, 47, 1, 0.12)' : 'transparent',
                      fontSize: 'var(--font-size-xs)',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <UserCheck size={14} color={r === role ? 'var(--color-primary-400)' : 'var(--color-neutral-400)'} />
                      <span style={{ fontWeight: 600 }}>{r}</span>
                    </div>
                    {r === role && <CheckCircle2 size={14} color="var(--color-primary-400)" />}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};
