import React, { createContext, useContext, useState } from 'react';
import type { Role, RolePermissions, UserProfile } from '../types/rbac';
import { ROLE_PERMISSIONS } from '../types/rbac';

interface AuthContextType {
  user: UserProfile;
  role: Role;
  currentRole: Role;
  permissions: RolePermissions;
  setRole: (role: Role) => void;
}

const DEFAULT_USERS: Record<Role, UserProfile> = {
  CFO: {
    id: 'usr-cfo',
    name: 'Alexandra Wright',
    email: 'alexandra.cfo@novascale.ai',
    role: 'CFO',
    avatar_url: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100&auto=format&fit=crop&q=80',
  },
  CONTROLLER: {
    id: 'usr-ctrl',
    name: 'Marcus Sterling',
    email: 'marcus.ctrl@novascale.ai',
    role: 'CONTROLLER',
    avatar_url: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&auto=format&fit=crop&q=80',
  },
  ACCOUNTANT: {
    id: 'usr-acc',
    name: 'Elena Rostova',
    email: 'elena.acc@novascale.ai',
    role: 'ACCOUNTANT',
    avatar_url: 'https://images.unsplash.com/photo-1517841905240-472988babdf9?w=100&auto=format&fit=crop&q=80',
  },
  VIEWER: {
    id: 'usr-view',
    name: 'Audit Observer',
    email: 'observer@external-audit.com',
    role: 'VIEWER',
    avatar_url: 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=100&auto=format&fit=crop&q=80',
  },
  ADMIN: {
    id: 'usr-admin',
    name: 'System Admin',
    email: 'admin@vexa.internal',
    role: 'ADMIN',
    avatar_url: 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=100&auto=format&fit=crop&q=80',
  }
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [role, setRoleState] = useState<Role>(() => {
    return (localStorage.getItem('vexa_active_role') as Role) || 'CFO';
  });

  const setRole = (newRole: Role) => {
    setRoleState(newRole);
    localStorage.setItem('vexa_active_role', newRole);
  };

  const user = DEFAULT_USERS[role];
  const permissions = ROLE_PERMISSIONS[role];

  return (
    <AuthContext.Provider value={{ user, role, currentRole: role, permissions, setRole }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
