import React, { useState, useEffect } from 'react';
import { TenantProvider } from './context/TenantContext';
import { AuthProvider } from './context/AuthContext';
import { CloseRunProvider, useCloseRun } from './context/CloseRunContext';
import { DemoProvider } from './context/DemoContext';

// Layout & Common Components
import { Sidebar } from './components/layout/Sidebar';
import { CloseRunShell } from './components/layout/CloseRunShell';
import { CommandPalette } from './components/common/CommandPalette';
import { SlideOverDrawer, type DrawerEntityData } from './components/layout/SlideOverDrawer';
import { DemoHUD } from './components/common/DemoHUD';

// Page Views
import { CloseRunsListPage } from './pages/closeRuns/CloseRunsListPage';
import { CloseRunOverviewPage } from './pages/closeRuns/CloseRunOverviewPage';
import { CloseTasksDAGPage } from './pages/closeRuns/CloseTasksDAGPage';
import { AgentTelemetryPage } from './pages/closeRuns/AgentTelemetryPage';
import { ReconciliationGridPage } from './pages/closeRuns/ReconciliationGridPage';
import { ExceptionsWorkbenchPage } from './pages/closeRuns/ExceptionsWorkbenchPage';
import { ExceptionDossierPage } from './pages/closeRuns/ExceptionDossierPage';
import { ApprovalsQueuePage } from './pages/closeRuns/ApprovalsQueuePage';
import { AuditTrailPage } from './pages/closeRuns/AuditTrailPage';
import { ClosePackagePage } from './pages/closeRuns/ClosePackagePage';
import { CFOBenchDashboardPage } from './pages/benchmarks/CFOBenchDashboardPage';
import { CalibrationStudioPage } from './pages/calibration/CalibrationStudioPage';
import { DemoSafetyNetPage } from './pages/demo/DemoSafetyNetPage';
import { PolicyConfigPage } from './pages/policies/PolicyConfigPage';
import { TenantSelectPage } from './pages/tenants/TenantSelectPage';

const LEGACY_IDS = new Set(['b891a27e-3841-45ea-912b-81f1816db731', 'run-2026-03-apex']);
const DEFAULT_RUN_ID = '341cfa78-09fd-499b-ae0d-399485211be9';

const normalizePath = (rawHash: string, defaultRunId: string): string => {
  const clean = rawHash.replace(/^#+/, '').replace(/\/+$/, '');
  if (!clean || clean === '/') {
    return `/close-runs/${defaultRunId}/overview`;
  }
  const parts = clean.split('/').filter(Boolean);
  if (parts[0] === 'close-runs' && parts[1] && LEGACY_IDS.has(parts[1])) {
    parts[1] = defaultRunId;
    return `/${parts.join('/')}`;
  }
  return clean.startsWith('/') ? clean : `/${clean}`;
};

const ConsoleMain: React.FC = () => {
  const { activeRun, setActiveRunId } = useCloseRun();

  const [currentPath, setCurrentPath] = useState<string>(() =>
    normalizePath(window.location.hash, activeRun?.id || DEFAULT_RUN_ID)
  );
  const [isCmdOpen, setIsCmdOpen] = useState(false);
  const [drawerEntity, setDrawerEntity] = useState<DrawerEntityData | null>(null);

  useEffect(() => {
    const handleHashChange = () => {
      const normalized = normalizePath(window.location.hash, activeRun?.id || DEFAULT_RUN_ID);
      setCurrentPath(normalized);
    };
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, [activeRun?.id]);

  const navigate = (path: string) => {
    const clean = path.startsWith('/') ? path : `/${path}`;
    setCurrentPath(clean);
    window.location.hash = clean;
  };

  // Parse path tokens: e.g. ['', 'close-runs', ':id', ':tab', ':subId']
  const pathParts = currentPath.split('/').filter(Boolean); // ['close-runs', ':id', ':tab']
  const isCloseRunRoute = pathParts[0] === 'close-runs' && pathParts.length >= 2;
  const routeRunId = isCloseRunRoute ? pathParts[1] : '';
  const activeTab = isCloseRunRoute && pathParts.length >= 3 ? pathParts[2] : 'overview';

  // Sync route runId to activeRun in context if URL has a specific run ID
  useEffect(() => {
    if (isCloseRunRoute && routeRunId) {
      if (LEGACY_IDS.has(routeRunId)) {
        navigate(`/close-runs/${activeRun.id || DEFAULT_RUN_ID}/${activeTab}`);
      } else if (routeRunId !== activeRun.id) {
        setActiveRunId(routeRunId);
      }
    }
  }, [isCloseRunRoute, routeRunId, activeRun.id, activeTab, setActiveRunId]);

  // Check if viewing deep exception dossier: /close-runs/:id/exceptions/:exceptionId
  const isExceptionDossier = isCloseRunRoute && pathParts[2] === 'exceptions' && pathParts.length >= 4;
  const exceptionId = isExceptionDossier ? pathParts[3] : '';

  const renderContent = () => {
    // 1. Close Runs List
    if (currentPath === '/close-runs' || currentPath === '/close-runs/') {
      return (
        <CloseRunsListPage
          onSelectRun={(runId) => navigate(`/close-runs/${runId}/overview`)}
        />
      );
    }

    // 2. Exception Dossier Detail
    if (isExceptionDossier && exceptionId) {
      return (
        <ExceptionDossierPage
          exceptionId={exceptionId}
          onBack={() => navigate(`/close-runs/${routeRunId || activeRun.id}/exceptions`)}
        />
      );
    }

    // 3. Close Run Sub-Routes (wrapped in CloseRunShell)
    if (isCloseRunRoute) {
      const currentRunId = routeRunId || activeRun.id;
      let pageElement: React.ReactNode = null;

      switch (activeTab) {
        case 'overview':
          pageElement = (
            <CloseRunOverviewPage
              onNavigateTab={(tab) => navigate(`/close-runs/${currentRunId}/${tab}`)}
            />
          );
          break;
        case 'tasks':
          pageElement = <CloseTasksDAGPage />;
          break;
        case 'telemetry':
          pageElement = <AgentTelemetryPage />;
          break;
        case 'reconciliation':
          pageElement = (
            <ReconciliationGridPage
              onInspectEntity={(entity) => setDrawerEntity(entity)}
            />
          );
          break;
        case 'exceptions':
          pageElement = (
            <ExceptionsWorkbenchPage
              onSelectException={(excId) =>
                navigate(`/close-runs/${currentRunId}/exceptions/${excId}`)
              }
            />
          );
          break;
        case 'approvals':
          pageElement = (
            <ApprovalsQueuePage
              onInspectException={(excId) =>
                navigate(`/close-runs/${currentRunId}/exceptions/${excId}`)
              }
            />
          );
          break;
        case 'audit':
          pageElement = <AuditTrailPage />;
          break;
        case 'package':
          pageElement = <ClosePackagePage />;
          break;
        default:
          pageElement = (
            <CloseRunOverviewPage
              onNavigateTab={(tab) => navigate(`/close-runs/${currentRunId}/${tab}`)}
            />
          );
      }

      return (
        <CloseRunShell
          activeTab={activeTab}
          onSelectTab={(tab) => navigate(`/close-runs/${currentRunId}/${tab}`)}
        >
          {pageElement}
        </CloseRunShell>
      );
    }

    // 4. Benchmarks Studio: /benchmarks or /benchmarks/cfo-bench
    if (currentPath.startsWith('/benchmarks')) {
      return <CFOBenchDashboardPage />;
    }

    // 5. Calibration Studio: /calibration
    if (currentPath.startsWith('/calibration')) {
      return <CalibrationStudioPage />;
    }

    // 6. Demo Center & Safety Net Replay: /demo-center or /demo
    if (currentPath.startsWith('/demo-center') || currentPath.startsWith('/demo')) {
      return <DemoSafetyNetPage />;
    }

    // 7. Governance Policies: /policies
    if (currentPath.startsWith('/policies')) {
      return <PolicyConfigPage />;
    }

    // 8. Tenant Directory: /tenants
    if (currentPath.startsWith('/tenants')) {
      return (
        <TenantSelectPage
          onSelectTenant={() => navigate(`/close-runs/${activeRun.id}/overview`)}
        />
      );
    }

    // Fallback default
    return (
      <CloseRunsListPage
        onSelectRun={(runId) => navigate(`/close-runs/${runId}/overview`)}
      />
    );
  };

  return (
    <div style={{ display: 'flex', width: '100vw', height: '100vh', overflow: 'hidden', background: 'var(--color-neutral-100)' }}>
      {/* 4-Zone Sidebar with all embedded navigation & system controls */}
      <Sidebar
        currentPath={currentPath}
        onNavigate={navigate}
        onOpenCommandPalette={() => setIsCmdOpen(true)}
      />

      {/* Scrollable Center Work Canvas */}
      <main
        style={{
          flex: 1,
          minWidth: 0,
          overflowY: 'auto',
          padding: '1.75rem 2.25rem 6rem 2.25rem',
          height: '100%',
        }}
      >
        <div style={{ maxWidth: '1480px', margin: '0 auto', width: '100%' }}>
          {renderContent()}
        </div>
      </main>

      {/* Universal Slide-Over Record Inspector */}
      <SlideOverDrawer
        isOpen={Boolean(drawerEntity)}
        onClose={() => setDrawerEntity(null)}
        entity={drawerEntity}
      />

      {/* Global ⌘K Command Palette */}
      <CommandPalette
        isOpen={isCmdOpen}
        onClose={() => setIsCmdOpen(false)}
        onNavigate={navigate}
      />

      {/* Bottom Floating Replay HUD */}
      <DemoHUD />
    </div>
  );
};

export default function App() {
  return (
    <TenantProvider>
      <AuthProvider>
        <CloseRunProvider>
          <DemoProvider>
            <ConsoleMain />
          </DemoProvider>
        </CloseRunProvider>
      </AuthProvider>
    </TenantProvider>
  );
}
