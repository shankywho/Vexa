export type Role = 'VIEWER' | 'ACCOUNTANT' | 'CONTROLLER' | 'CFO' | 'ADMIN';

export interface UserProfile {
  id: string;
  name: string;
  email: string;
  role: Role;
  avatar_url?: string;
}

export interface RolePermissions {
  canStartCloseRun: boolean;
  canInspectEvidence: boolean;
  canStageAction: boolean;
  canApproveLevel2: boolean;
  canRejectAction: boolean;
  canEscalateLevel1: boolean;
  canReverseAction: boolean;
  canGeneratePackage: boolean;
  canSignOffClose: boolean;
  canRunBenchmarks: boolean;
  canToggleDemoMode: boolean;
  canEditPolicies: boolean;
}

export const ROLE_PERMISSIONS: Record<Role, RolePermissions> = {
  VIEWER: {
    canStartCloseRun: false,
    canInspectEvidence: true,
    canStageAction: false,
    canApproveLevel2: false,
    canRejectAction: false,
    canEscalateLevel1: false,
    canReverseAction: false,
    canGeneratePackage: false,
    canSignOffClose: false,
    canRunBenchmarks: false,
    canToggleDemoMode: false,
    canEditPolicies: false,
  },
  ACCOUNTANT: {
    canStartCloseRun: true,
    canInspectEvidence: true,
    canStageAction: true,
    canApproveLevel2: false,
    canRejectAction: false,
    canEscalateLevel1: true,
    canReverseAction: false,
    canGeneratePackage: true,
    canSignOffClose: false,
    canRunBenchmarks: false,
    canToggleDemoMode: false,
    canEditPolicies: false,
  },
  CONTROLLER: {
    canStartCloseRun: true,
    canInspectEvidence: true,
    canStageAction: true,
    canApproveLevel2: true,
    canRejectAction: true,
    canEscalateLevel1: true,
    canReverseAction: false,
    canGeneratePackage: true,
    canSignOffClose: false,
    canRunBenchmarks: false,
    canToggleDemoMode: false,
    canEditPolicies: true,
  },
  CFO: {
    canStartCloseRun: true,
    canInspectEvidence: true,
    canStageAction: true,
    canApproveLevel2: true,
    canRejectAction: true,
    canEscalateLevel1: true,
    canReverseAction: true,
    canGeneratePackage: true,
    canSignOffClose: true,
    canRunBenchmarks: true,
    canToggleDemoMode: true,
    canEditPolicies: true,
  },
  ADMIN: {
    canStartCloseRun: true,
    canInspectEvidence: true,
    canStageAction: true,
    canApproveLevel2: true,
    canRejectAction: true,
    canEscalateLevel1: true,
    canReverseAction: true,
    canGeneratePackage: true,
    canSignOffClose: true,
    canRunBenchmarks: true,
    canToggleDemoMode: true,
    canEditPolicies: true,
  },
};
