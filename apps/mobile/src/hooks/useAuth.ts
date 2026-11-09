import { useEffect } from 'react';
import { useAuthStore } from '@/store/auth';

export const useAuth = () => {
  const store = useAuthStore();

  useEffect(() => {
    store.initializeAuth();
  }, []);

  return {
    user: store.user,
    token: store.token,
    loading: store.loading,
    isAuthenticated: store.isAuthenticated,
    error: store.error,
    logout: store.logout,
    handleOAuthCallback: store.handleOAuthCallback,
    setError: store.setError,
  };
};
