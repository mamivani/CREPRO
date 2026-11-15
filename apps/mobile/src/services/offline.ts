import { create } from 'zustand';
import * as SQLite from 'expo-sqlite';
import { Property, Invoice } from '@/types';

interface CacheEntry<T> {
  data: T;
  timestamp: number;
  ttl: number; // milliseconds
}

interface CacheStore {
  // Properties
  properties: CacheEntry<Property[]> | null;
  cacheProperties: (properties: Property[], ttl?: number) => void;
  getProperties: () => Property[] | null;
  isPropertiesCached: () => boolean;

  // Invoices
  invoices: CacheEntry<Invoice[]> | null;
  cacheInvoices: (invoices: Invoice[], ttl?: number) => void;
  getInvoices: () => Invoice[] | null;
  isInvoicesCached: () => boolean;

  // General
  clear: () => void;
}

export const useCacheStore = create<CacheStore>((set, get) => ({
  properties: null,
  invoices: null,

  cacheProperties: (properties: Property[], ttl = 5 * 60 * 1000) => {
    set({
      properties: {
        data: properties,
        timestamp: Date.now(),
        ttl,
      },
    });
  },

  getProperties: () => {
    const cache = get().properties;
    if (!cache) return null;

    const now = Date.now();
    if (now - cache.timestamp > cache.ttl) {
      set({ properties: null });
      return null;
    }

    return cache.data;
  },

  isPropertiesCached: () => {
    const cache = get().properties;
    if (!cache) return false;

    const now = Date.now();
    return now - cache.timestamp <= cache.ttl;
  },

  cacheInvoices: (invoices: Invoice[], ttl = 5 * 60 * 1000) => {
    set({
      invoices: {
        data: invoices,
        timestamp: Date.now(),
        ttl,
      },
    });
  },

  getInvoices: () => {
    const cache = get().invoices;
    if (!cache) return null;

    const now = Date.now();
    if (now - cache.timestamp > cache.ttl) {
      set({ invoices: null });
      return null;
    }

    return cache.data;
  },

  isInvoicesCached: () => {
    const cache = get().invoices;
    if (!cache) return false;

    const now = Date.now();
    return now - cache.timestamp <= cache.ttl;
  },

  clear: () => {
    set({ properties: null, invoices: null });
  },
}));

// SQLite Database for offline sync
const DB_NAME = 'crepro_offline.db';

export class OfflineDatabase {
  private static instance: SQLite.SQLiteDatabase | null = null;

  static async getInstance(): Promise<SQLite.SQLiteDatabase> {
    if (this.instance) {
      return this.instance;
    }

    const db = await SQLite.openDatabaseAsync(DB_NAME);
    await this.initializeTables(db);
    this.instance = db;
    return db;
  }

  static async initializeTables(db: SQLite.SQLiteDatabase) {
    // Sync queue table
    await db.execAsync(`
      CREATE TABLE IF NOT EXISTS sync_queue (
        id TEXT PRIMARY KEY,
        endpoint TEXT NOT NULL,
        method TEXT NOT NULL,
        payload TEXT NOT NULL,
        timestamp INTEGER NOT NULL,
        retries INTEGER DEFAULT 0,
        max_retries INTEGER DEFAULT 3,
        status TEXT DEFAULT 'pending'
      );
    `);

    // Offline properties cache
    await db.execAsync(`
      CREATE TABLE IF NOT EXISTS properties_cache (
        id TEXT PRIMARY KEY,
        data TEXT NOT NULL,
        timestamp INTEGER NOT NULL
      );
    `);

    // Offline invoices cache
    await db.execAsync(`
      CREATE TABLE IF NOT EXISTS invoices_cache (
        id TEXT PRIMARY KEY,
        data TEXT NOT NULL,
        timestamp INTEGER NOT NULL
      );
    `);
  }

  static async addToSyncQueue(
    endpoint: string,
    method: string,
    payload: any
  ): Promise<void> {
    const db = await this.getInstance();
    const id = `${Date.now()}-${Math.random()}`;

    await db.runAsync(
      `INSERT INTO sync_queue (id, endpoint, method, payload, timestamp)
       VALUES (?, ?, ?, ?, ?)`,
      [id, endpoint, method, JSON.stringify(payload), Date.now()]
    );
  }

  static async getSyncQueue(): Promise<any[]> {
    const db = await this.getInstance();
    const result = await db.getAllAsync(
      `SELECT * FROM sync_queue WHERE status = 'pending' ORDER BY timestamp ASC`
    );
    return result;
  }

  static async removeSyncQueueItem(id: string): Promise<void> {
    const db = await this.getInstance();
    await db.runAsync(`DELETE FROM sync_queue WHERE id = ?`, [id]);
  }

  static async updateSyncQueueStatus(id: string, status: string): Promise<void> {
    const db = await this.getInstance();
    await db.runAsync(`UPDATE sync_queue SET status = ? WHERE id = ?`, [status, id]);
  }

  static async incrementRetries(id: string): Promise<void> {
    const db = await this.getInstance();
    await db.runAsync(
      `UPDATE sync_queue SET retries = retries + 1 WHERE id = ?`,
      [id]
    );
  }

  static async cacheProperties(properties: Property[]): Promise<void> {
    const db = await this.getInstance();
    await db.runAsync(`DELETE FROM properties_cache`);

    for (const prop of properties) {
      await db.runAsync(
        `INSERT INTO properties_cache (id, data, timestamp) VALUES (?, ?, ?)`,
        [prop.id, JSON.stringify(prop), Date.now()]
      );
    }
  }

  static async getCachedProperties(): Promise<Property[]> {
    const db = await this.getInstance();
    const result = await db.getAllAsync(
      `SELECT data FROM properties_cache ORDER BY timestamp DESC`
    );
    return result.map((row: any) => JSON.parse(row.data));
  }

  static async cacheInvoices(invoices: Invoice[]): Promise<void> {
    const db = await this.getInstance();
    await db.runAsync(`DELETE FROM invoices_cache`);

    for (const invoice of invoices) {
      await db.runAsync(
        `INSERT INTO invoices_cache (id, data, timestamp) VALUES (?, ?, ?)`,
        [invoice.id, JSON.stringify(invoice), Date.now()]
      );
    }
  }

  static async getCachedInvoices(): Promise<Invoice[]> {
    const db = await this.getInstance();
    const result = await db.getAllAsync(
      `SELECT data FROM invoices_cache ORDER BY timestamp DESC`
    );
    return result.map((row: any) => JSON.parse(row.data));
  }
}
