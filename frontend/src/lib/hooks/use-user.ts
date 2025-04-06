import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface UserState {
  id: string | null;
  name: string | null;
  setUser: (id: string, name: string) => void;
  clearUser: () => void;
}

export const useUser = create<UserState>()(
  persist(
    (set) => ({
      id: null,
      name: null,
      setUser: (id, name) => set({ id, name }),
      clearUser: () => set({ id: null, name: null })
    }),
    {
      name: 'user-storage'
    }
  )
);