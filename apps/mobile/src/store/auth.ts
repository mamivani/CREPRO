import { create } from 'zustand';
import * as SecureStore from 'expo-secure-store';
import { mobileApiClient } from '@/services/api';
import { User, AuthToken } from '@/types';

interface AuthState {
  user: User | null;
  token: string | null;
  loading: boolean;
  isAuthenticated: boolean;
  error: string | null;
  setUser: (user: User | null) => void;
  setToken: (token: string | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  initializeAuth: () => Promise<void>;
  logout: () => Promise<void>;
  handleOAuthCallback: (provider: string, code: string) => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  token: null,
  loading: false,
  isAuthenticated: false,
  error: null,

  setUser: (user: User | null) => {
    set({ user, isAuthenticated: !!user });
  },

  setToken: (token: string | null) => {
    set({ token });
  },

  setLoading: (loading: boolean) => {
    set({ loading });
  },

  setError: (error: string | null) => {
    set({ error });
  },

  initializeAuth: async () => {
    try {
      set({ loading: true });
      const token = await SecureStore.getItemAsync('access_token');
      const userJson = await SecureStore.getItemAsync('user');

      if (token && userJson) {
        const user = JSON.parse(userJson);
        set({
          token,
          user,
          isAuthenticated: true,
          loading: false,
        });
      } else {
        set({ loading: false, isAuthenticated: false });
      }
    } catch (error) {
      console.error('Failed to initialize auth:', error);
      set({ loading: false, isAuthenticated: false });
    }
  },

  logout: async () => {
    try {
      await mobileApiClient.logout();
      await SecureStore.deleteItemAsync('user');
      await SecureStore.deleteItemAsync('access_token');
      await SecureStore.deleteItemAsync('refresh_token');
      set({
        user: null,
        token: null,
        isAuthenticated: false,
        error: null,
      });
    } catch (error) {
      console.error('Logout failed:', error);
      set({ error: 'Logout failed' });
    }
  },

  handleOAuthCallback: async (provider: string, code: string) => {
    try {
      set({ loading: true, error: null });
      const authData = await mobileApiClient.handleOAuthCallback(provider, code);

      // In a real scenario, you'd fetch the user data from the backend
      const user: User = {
        id: '',
        email: '',
        name: '',
        role: 'tenant',
      };

      await SecureStore.setItemAsync('user', JSON.stringify(user));

      set({
        user,
        token: authData.access_token,
        isAuthenticated: true,
        loading: false,
      });
    } catch (error) {
      const errorMessage = mobileApiClient.getErrorMessage(error);
      set({
        error: errorMessage,
        loading: false,
        isAuthenticated: false,
      });
      throw error;
    }
  },
}));
