'use client';

import { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { apiClient } from '@/services/api';
import { useAuthStore } from '@/store/auth';

export default function CallbackPage() {
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const setToken = useAuthStore((state) => state.setToken);
  const setUser = useAuthStore((state) => state.setUser);

  useEffect(() => {
    const handleCallback = async () => {
      try {
        const provider = searchParams.get('provider');
        const code = searchParams.get('code');

        if (!provider || !code) {
          throw new Error('Invalid callback parameters');
        }

        const authToken = await apiClient.handleOAuthCallback(provider, code);
        setToken(authToken.access_token);

        // TODO: Fetch user details from API
        setLoading(false);

        // Redirect to dashboard
        window.location.href = '/dashboard';
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Authentication failed');
        setLoading(false);
      }
    };

    handleCallback();
  }, [searchParams, setToken, setUser]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold mb-4">Authenticating...</h1>
          <p className="text-muted-foreground">Please wait while we complete your login.</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-destructive mb-4">Authentication Failed</h1>
          <p className="text-muted-foreground mb-6">{error}</p>
          <a href="/auth/login" className="text-primary hover:underline">
            Return to login
          </a>
        </div>
      </div>
    );
  }

  return null;
}
