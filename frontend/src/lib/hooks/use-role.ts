import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { UserRole } from '@/lib/types';

interface RoleState {
  role: UserRole | null;
  previousRole: UserRole | null;
  isLoading: boolean;
  setRole: (role: UserRole) => void;
  switchRole: () => void;
}

export const useRole = create<RoleState>()(
  persist(
    (set) => ({
      role: null,
      previousRole: null,
      isLoading: false,
      setRole: (role) =>
        set((state) => ({
          role,
          previousRole: state.role,
        })),
      switchRole: () =>
        set((state) => ({
          role: state.previousRole,
          previousRole: state.role,
        })),
    }),
    {
      name: 'user-role',
    }
  )
);