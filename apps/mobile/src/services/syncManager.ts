import { create } from 'zustand';
import NetInfo from '@react-native-community/netinfo';
import { OfflineDatabase } from './offline';
import { mobileApiClient } from './api';

interface SyncItem {
  id: string;
  endpoint: string;
  method: string;
  payload: any;
  timestamp: number;
  retries: number;
  max_retries: number;
  status: 'pending' | 'syncing' | 'completed' | 'failed';
}

interface OfflineSyncStore {
  isOnline: boolean;
  syncQueue: SyncItem[];
  syncing: boolean;
  setOnline: (online: boolean) => void;
  addToQueue: (endpoint: string, method: string, payload: any) => Promise<void>;
  getSyncQueue: () => Promise<SyncItem[]>;
  syncWithBackend: () => Promise<void>;
  clearQueue: () => Promise<void>;
}

export const useOfflineSyncStore = create<OfflineSyncStore>((set, get) => ({
  isOnline: true,
  syncQueue: [],
  syncing: false,

  setOnline: (online: boolean) => {
    set({ isOnline: online });
    if (online) {
      get().syncWithBackend();
    }
  },

  addToQueue: async (endpoint: string, method: string, payload: any) => {
    await OfflineDatabase.addToSyncQueue(endpoint, method, payload);
    const queue = await get().getSyncQueue();
    set({ syncQueue: queue });
  },

  getSyncQueue: async () => {
    const items = await OfflineDatabase.getSyncQueue();
    set({ syncQueue: items as SyncItem[] });
    return items as SyncItem[];
  },

  syncWithBackend: async () => {
    const { isOnline, syncing } = get();

    if (!isOnline || syncing) return;

    set({ syncing: true });

    try {
      const queue = await get().getSyncQueue();

      for (const item of queue) {
        try {
          // Update status to syncing
          await OfflineDatabase.updateSyncQueueStatus(item.id, 'syncing');

          // Make the API call
          let response;
          switch (item.method.toUpperCase()) {
            case 'GET':
              response = await mobileApiClient.getProperties();
              break;
            case 'POST':
              if (item.endpoint.includes('properties')) {
                response = await mobileApiClient.createProperty(item.payload);
              } else if (item.endpoint.includes('invoices')) {
                response = await mobileApiClient.createInvoice(item.payload);
              }
              break;
            case 'PUT':
              response = await mobileApiClient.updateProperty(
                item.payload.id,
                item.payload
              );
              break;
            case 'DELETE':
              response = await mobileApiClient.deleteProperty(item.payload.id);
              break;
          }

          // Mark as completed
          await OfflineDatabase.updateSyncQueueStatus(item.id, 'completed');
          await OfflineDatabase.removeSyncQueueItem(item.id);
        } catch (error) {
          await OfflineDatabase.incrementRetries(item.id);

          if (item.retries >= item.max_retries) {
            await OfflineDatabase.updateSyncQueueStatus(item.id, 'failed');
          }

          console.error(`Sync failed for ${item.id}:`, error);
        }
      }

      // Refresh queue after sync
      await get().getSyncQueue();
    } finally {
      set({ syncing: false });
    }
  },

  clearQueue: async () => {
    // Note: In production, only clear after successful sync
    set({ syncQueue: [] });
  },
}));

// Monitor network connectivity
export function setupNetworkMonitoring() {
  const unsubscribe = NetInfo.addEventListener((state) => {
    const isOnline = state.isConnected && state.isInternetReachable;
    useOfflineSyncStore.getState().setOnline(isOnline ?? false);
  });

  return unsubscribe;
}

// Offline-aware API wrapper
export class OfflineAwareApi {
  static async get(endpoint: string) {
    const { isOnline } = useOfflineSyncStore.getState();

    if (!isOnline) {
      // Return cached data
      if (endpoint.includes('properties')) {
        return OfflineDatabase.getCachedProperties();
      } else if (endpoint.includes('invoices')) {
        return OfflineDatabase.getCachedInvoices();
      }
    }

    // Make live request and cache
    try {
      const response = await mobileApiClient.getProperties();
      if (endpoint.includes('properties')) {
        await OfflineDatabase.cacheProperties(response.data);
      }
      return response.data;
    } catch (error) {
      // Fall back to cache on error
      if (endpoint.includes('properties')) {
        return OfflineDatabase.getCachedProperties();
      }
      throw error;
    }
  }

  static async post(endpoint: string, data: any) {
    const { isOnline } = useOfflineSyncStore.getState();

    if (!isOnline) {
      // Queue for later sync
      await useOfflineSyncStore.getState().addToQueue(endpoint, 'POST', data);
      return { queued: true };
    }

    // Make live request
    return await mobileApiClient.createProperty(data);
  }

  static async put(endpoint: string, id: string, data: any) {
    const { isOnline } = useOfflineSyncStore.getState();

    if (!isOnline) {
      // Queue for later sync
      await useOfflineSyncStore
        .getState()
        .addToQueue(endpoint, 'PUT', { ...data, id });
      return { queued: true };
    }

    // Make live request
    return await mobileApiClient.updateProperty(id, data);
  }

  static async delete(endpoint: string, id: string) {
    const { isOnline } = useOfflineSyncStore.getState();

    if (!isOnline) {
      // Queue for later sync
      await useOfflineSyncStore
        .getState()
        .addToQueue(endpoint, 'DELETE', { id });
      return { queued: true };
    }

    // Make live request
    return await mobileApiClient.deleteProperty(id);
  }
}
