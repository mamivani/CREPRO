import axios, { AxiosInstance, AxiosError } from 'axios';
import Cookie from 'js-cookie';
import { AuthToken, User, ApiError } from '@/types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8003';
const IDENTITY_URL = process.env.NEXT_PUBLIC_IDENTITY_URL || 'http://localhost:8001';

class ApiClient {
  private client: AxiosInstance;
  private identityClient: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_URL,
      withCredentials: true,
    });

    this.identityClient = axios.create({
      baseURL: IDENTITY_URL,
      withCredentials: true,
    });

    // Request interceptor - inject auth token
    this.client.interceptors.request.use((config) => {
      const token = this.getToken();
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

    this.identityClient.interceptors.request.use((config) => {
      const token = this.getToken();
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

    // Response interceptor - handle 401 and refresh token
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        if (error.response?.status === 401) {
          await this.refreshToken();
        }
        return Promise.reject(error);
      }
    );
  }

  private getToken(): string | null {
    return Cookie.get('access_token') || null;
  }

  private setToken(token: string): void {
    Cookie.set('access_token', token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'Lax',
      expires: 7,
    });
  }

  private setRefreshToken(token: string): void {
    Cookie.set('refresh_token', token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'Lax',
      expires: 30,
    });
  }

  async refreshToken(): Promise<boolean> {
    try {
      const refreshToken = Cookie.get('refresh_token');
      if (!refreshToken) {
        return false;
      }

      const response = await this.identityClient.post<AuthToken>(
        '/api/v1/auth/refresh',
        { refresh_token: refreshToken }
      );

      this.setToken(response.data.access_token);
      this.setRefreshToken(response.data.refresh_token);
      return true;
    } catch {
      this.clearTokens();
      return false;
    }
  }

  private clearTokens(): void {
    Cookie.remove('access_token');
    Cookie.remove('refresh_token');
  }

  // Auth endpoints
  async loginWithOAuth(provider: string): Promise<string> {
    const response = await this.identityClient.get<{ auth_url: string }>(
      `/api/v1/auth/${provider}`
    );
    return response.data.auth_url;
  }

  async handleOAuthCallback(provider: string, code: string): Promise<AuthToken> {
    const response = await this.identityClient.post<AuthToken>('/api/v1/auth/callback', {
      provider,
      code,
    });
    this.setToken(response.data.access_token);
    this.setRefreshToken(response.data.refresh_token);
    return response.data;
  }

  async logout(): Promise<void> {
    this.clearTokens();
  }

  // Property endpoints
  async getProperties(skip: number = 0, limit: number = 10) {
    return this.client.get('/api/v1/properties', { params: { skip, limit } });
  }

  async getProperty(id: string) {
    return this.client.get(`/api/v1/properties/${id}`);
  }

  async createProperty(data: any) {
    return this.client.post('/api/v1/properties', data);
  }

  async updateProperty(id: string, data: any) {
    return this.client.put(`/api/v1/properties/${id}`, data);
  }

  async deleteProperty(id: string) {
    return this.client.delete(`/api/v1/properties/${id}`);
  }

  async getPropertyAudit(id: string) {
    return this.client.get(`/api/v1/properties/${id}/audit`);
  }

  // Invoice endpoints
  async getInvoices(propertyId?: string) {
    return this.client.get('/api/v1/invoices', {
      params: propertyId ? { property_id: propertyId } : {},
    });
  }

  async createInvoice(data: any) {
    return this.client.post('/api/v1/invoices', data);
  }

  // Payment endpoints
  async createPayment(invoiceId: string, data: any) {
    return this.client.post(`/api/v1/invoices/${invoiceId}/payments`, data);
  }

  getErrorMessage(error: unknown): string {
    if (axios.isAxiosError(error)) {
      const data = error.response?.data as ApiError;
      return data?.message || error.message || 'An error occurred';
    }
    return 'An unexpected error occurred';
  }
}

export const apiClient = new ApiClient();
