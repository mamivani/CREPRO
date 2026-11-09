import { useAuthStore } from '@/store/auth';

export const useAuth = () => {
  const { user, token, loading, isAuthenticated, setUser, setToken, logout } = useAuthStore();

  return {
    user,
    token,
    loading,
    isAuthenticated,
    setUser,
    setToken,
    logout,
  };
};

export const useRequireAuth = (redirectTo: string = '/auth/login') => {
  const { isAuthenticated, loading } = useAuth();

  if (!loading && !isAuthenticated) {
    // Redirect will be handled by middleware or useEffect in component
    return false;
  }

  return true;
};
