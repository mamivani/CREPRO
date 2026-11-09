import { mobileApiClient } from '@/services/api';
import * as SecureStore from 'expo-secure-store';
import axios from 'axios';

jest.mock('expo-secure-store');
jest.mock('axios');

describe('Mobile API Client', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('injects authorization token in requests', async () => {
    (SecureStore.getItemAsync as jest.Mock).mockResolvedValueOnce('test-token');

    // Test token injection
  });

  it('refreshes token on 401 response', async () => {
    (SecureStore.getItemAsync as jest.Mock)
      .mockResolvedValueOnce('expired-token')
      .mockResolvedValueOnce('refresh-token');

    // Test auto-refresh
  });

  it('clears tokens on logout', async () => {
    await mobileApiClient.logout();
    expect(SecureStore.deleteItemAsync).toHaveBeenCalledWith('access_token');
    expect(SecureStore.deleteItemAsync).toHaveBeenCalledWith('refresh_token');
  });

  it('parses API errors into user-friendly messages', () => {
    const error = {
      response: {
        data: { message: 'Invalid credentials' },
      },
    };

    const message = mobileApiClient.getErrorMessage(error);
    expect(message).toBe('Invalid credentials');
  });

  it('fetches properties with pagination', async () => {
    // Test property list fetching
  });

  it('creates new property', async () => {
    // Test property creation
  });

  it('fetches invoices', async () => {
    // Test invoice fetching
  });

  it('records payment', async () => {
    // Test payment creation
  });
});
