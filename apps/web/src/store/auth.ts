import { create } from 'zustand';
import { User } from '@/types';
import { apiClient } from '@/services/api';
import Cookie from 'js-cookie';

interface AuthStore {
  user: User | null;
  token: string | null;
  loading: boolean;
  isAuthenticated: boolean;
  setUser: (user: User | null) => void;
  setToken: (token: string | null) => void;
  setLoading: (loading: boolean) => void;
  logout: () => Promise<void>;
  initializeAuth: () => void;
}

export const useAuthStore = create<AuthStore>((set) => ({
  user: null,
  token: Cookie.get('access_token') || null,
  loading: true,
  isAuthenticated: !!Cookie.get('access_token'),

  setUser: (user) => set({ user }),

  setToken: (token) => set({ token, isAuthenticated: !!token }),

  setLoading: (loading) => set({ loading }),

  logout: async () => {
    await apiClient.logout();
    set({ user: null, token: null, isAuthenticated: false });
  },

  initializeAuth: () => {
    // TODO: Fetch current user from API if token exists
    set({ loading: false });
  },
}));
