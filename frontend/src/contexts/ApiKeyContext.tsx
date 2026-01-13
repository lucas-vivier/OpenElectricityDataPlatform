import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';

export type ApiKeyService = 'renewablesNinja' | 'era5Cds';

interface ApiKeys {
  renewablesNinja?: string;
  era5Cds?: string;
}

interface ApiKeyContextType {
  apiKeys: ApiKeys;
  getApiKey: (service: ApiKeyService) => string | null;
  setApiKey: (service: ApiKeyService, key: string) => void;
  clearApiKey: (service: ApiKeyService) => void;
  hasApiKey: (service: ApiKeyService) => boolean;
}

const STORAGE_KEY = 'openenergydata_api_keys';

const ApiKeyContext = createContext<ApiKeyContextType | null>(null);

function loadKeysFromStorage(): ApiKeys {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      return JSON.parse(stored);
    }
  } catch (e) {
    console.warn('Failed to load API keys from localStorage:', e);
  }
  return {};
}

function saveKeysToStorage(keys: ApiKeys): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(keys));
  } catch (e) {
    console.warn('Failed to save API keys to localStorage:', e);
  }
}

export function ApiKeyProvider({ children }: { children: ReactNode }) {
  const [apiKeys, setApiKeys] = useState<ApiKeys>(() => loadKeysFromStorage());

  useEffect(() => {
    saveKeysToStorage(apiKeys);
  }, [apiKeys]);

  const getApiKey = (service: ApiKeyService): string | null => {
    return apiKeys[service] || null;
  };

  const setApiKey = (service: ApiKeyService, key: string): void => {
    setApiKeys(prev => ({ ...prev, [service]: key }));
  };

  const clearApiKey = (service: ApiKeyService): void => {
    setApiKeys(prev => {
      const next = { ...prev };
      delete next[service];
      return next;
    });
  };

  const hasApiKey = (service: ApiKeyService): boolean => {
    return !!apiKeys[service] && apiKeys[service]!.length > 0;
  };

  return (
    <ApiKeyContext.Provider value={{ apiKeys, getApiKey, setApiKey, clearApiKey, hasApiKey }}>
      {children}
    </ApiKeyContext.Provider>
  );
}

export function useApiKeys(): ApiKeyContextType {
  const context = useContext(ApiKeyContext);
  if (!context) {
    throw new Error('useApiKeys must be used within an ApiKeyProvider');
  }
  return context;
}

export const API_KEY_INFO: Record<ApiKeyService, { name: string; url: string; description: string }> = {
  renewablesNinja: {
    name: 'Renewables.ninja',
    url: 'https://www.renewables.ninja/',
    description: 'Required for solar and wind capacity factor profiles. Register for free to get an API token.',
  },
  era5Cds: {
    name: 'ERA5 / Copernicus CDS',
    url: 'https://cds.climate.copernicus.eu/',
    description: 'Required for ERA5 climate reanalysis data. Register at the Copernicus Climate Data Store.',
  },
};
