import axios, { AxiosInstance, AxiosError } from 'axios';
import * as SecureStore from 'expo-secure-store';
import { AuthToken, User, ApiError } from '@/types';

const API_URL = process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8003';
const IDENTITY_URL = process.env.EXPO_PUBLIC_IDENTITY_URL || 'http://localhost:8001';

class MobileApiClient {
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
    this.client.interceptors.request.use(async (config) => {
      const token = await this.getToken();
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

    this.identityClient.interceptors.request.use(async (config) => {
      const token = await this.getToken();
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

  private async getToken(): Promise<string | null> {
    try {
      return await SecureStore.getItemAsync('access_token');
    } catch {
      return null;
    }
  }

  private async setToken(token: string): Promise<void> {
    try {
      await SecureStore.setItemAsync('access_token', token);
    } catch (error) {
      console.error('Failed to store access token:', error);
    }
  }

  private async setRefreshToken(token: string): Promise<void> {
    try {
      await SecureStore.setItemAsync('refresh_token', token);
    } catch (error) {
      console.error('Failed to store refresh token:', error);
    }
  }

  async refreshToken(): Promise<boolean> {
    try {
      const refreshToken = await SecureStore.getItemAsync('refresh_token');
      if (!refreshToken) {
        return false;
      }

      const response = await this.identityClient.post<AuthToken>(
        '/api/v1/auth/refresh',
        { refresh_token: refreshToken }
      );

      await this.setToken(response.data.access_token);
      await this.setRefreshToken(response.data.refresh_token);
      return true;
    } catch {
      await this.clearTokens();
      return false;
    }
  }

  private async clearTokens(): Promise<void> {
    try {
      await SecureStore.deleteItemAsync('access_token');
      await SecureStore.deleteItemAsync('refresh_token');
    } catch (error) {
      console.error('Failed to clear tokens:', error);
    }
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
    await this.setToken(response.data.access_token);
    await this.setRefreshToken(response.data.refresh_token);
    return response.data;
  }

  async logout(): Promise<void> {
    await this.clearTokens();
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

export const mobileApiClient = new MobileApiClient();
