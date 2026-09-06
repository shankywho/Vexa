import React, { createContext, useContext, useState, useEffect } from 'react';
import type { Company } from '../types/company';
import { apiClient } from '../api/client';
import { MOCK_COMPANY } from '../api/mockData';

interface TenantContextType {
  activeCompany: Company;
  currentTenant: Company;
  companies: Company[];
  tenants: Company[];
  setActiveCompanyId: (id: string) => void;
  setTenantById: (id: string) => void;
  isLoading: boolean;
  refreshCompanies: () => Promise<void>;
}

const TenantContext = createContext<TenantContextType | undefined>(undefined);

export const TenantProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [companies, setCompanies] = useState<Company[]>([MOCK_COMPANY]);
  const [activeCompany, setActiveCompany] = useState<Company>(() => {
    const saved = localStorage.getItem('vexa_active_tenant_data');
    if (saved) {
      try { return JSON.parse(saved); } catch {}
    }
    return MOCK_COMPANY;
  });
  const [isLoading, setIsLoading] = useState(true);

  const refreshCompanies = async () => {
    try {
      setIsLoading(true);
      const list = await apiClient.getCompanies();
      if (list && list.length > 0) {
        setCompanies(list);
        const currentActiveId = localStorage.getItem('vexa_active_tenant') || list[0].id;
        const matched = list.find(c => c.id === currentActiveId) || list[0];
        setActiveCompany(matched);
        localStorage.setItem('vexa_active_tenant', matched.id);
        localStorage.setItem('vexa_active_tenant_data', JSON.stringify(matched));
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    refreshCompanies();
  }, []);

  const setActiveCompanyId = (id: string) => {
    const matched = companies.find(c => c.id === id);
    if (matched) {
      setActiveCompany(matched);
      localStorage.setItem('vexa_active_tenant', matched.id);
      localStorage.setItem('vexa_active_tenant_data', JSON.stringify(matched));
    }
  };

  return (
    <TenantContext.Provider
      value={{
        activeCompany,
        currentTenant: activeCompany,
        companies,
        tenants: companies,
        setActiveCompanyId,
        setTenantById: setActiveCompanyId,
        isLoading,
        refreshCompanies,
      }}
    >
      {children}
    </TenantContext.Provider>
  );
};

export const useTenant = (): TenantContextType => {
  const context = useContext(TenantContext);
  if (!context) {
    throw new Error('useTenant must be used within a TenantProvider');
  }
  return context;
};
