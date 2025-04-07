import { createContext, useContext, ReactNode } from 'react';
import { useBackendUser } from '../lib/hooks/useBackendUser';
import type { BackendUser } from '../lib/types/user';

interface UserSyncContextType {
  backendUser: BackendUser | null;
  loading: boolean;
  error: string | null;
  syncState: 'idle' | 'syncing' | 'synced' | 'error';
  syncUser: () => Promise<BackendUser | null>;
}

const UserSyncContext = createContext<UserSyncContextType | undefined>(undefined);

interface UserSyncProviderProps {
  children: ReactNode;
}

export function UserSyncProvider({ children }: UserSyncProviderProps) {
  const { backendUser, loading, error, syncState, syncUser } = useBackendUser();
  
  return (
    <UserSyncContext.Provider value={{ 
      backendUser, 
      loading, 
      error, 
      syncState, 
      syncUser 
    }}>
      {children}
    </UserSyncContext.Provider>
  );
}

// Custom hook to use the user sync context
export function useUserSync() {
  const context = useContext(UserSyncContext);
  if (context === undefined) {
    throw new Error('useUserSync must be used within a UserSyncProvider');
  }
  return context;
}
