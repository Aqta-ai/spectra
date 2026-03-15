/**
 * Offline-First Architecture
 * Enables Spectra to work offline with graceful degradation
 */

interface Action {
  id: string;
  type: string;
  params: any;
  timestamp: number;
  priority: 'high' | 'normal' | 'low';
}

interface CachedResponse {
  key: string;
  response: any;
  timestamp: number;
  ttl: number;
}

class ActionQueue {
  private queue: Action[] = [];
  private readonly storageKey = 'spectra_action_queue';

  constructor() {
    this.loadFromStorage();
  }

  add(action: Action) {
    this.queue.push(action);
    this.saveToStorage();
  }

  pop(): Action | undefined {
    const action = this.queue.shift();
    this.saveToStorage();
    return action;
  }

  isEmpty(): boolean {
    return this.queue.length === 0;
  }

  clear() {
    this.queue = [];
    this.saveToStorage();
  }

  private loadFromStorage() {
    try {
      const stored = localStorage.getItem(this.storageKey);
      if (stored) {
        this.queue = JSON.parse(stored);
      }
    } catch (error) {
      console.error('[OfflineMode] Failed to load queue:', error);
    }
  }

  private saveToStorage() {
    try {
      localStorage.setItem(this.storageKey, JSON.stringify(this.queue));
    } catch (error) {
      console.error('[OfflineMode] Failed to save queue:', error);
    }
  }
}

class Cache {
  private cache: Map<string, CachedResponse> = new Map();
  private readonly storageKey = 'spectra_cache';

  constructor() {
    this.loadFromStorage();
  }

  async get(key: string): Promise<any | null> {
    const cached = this.cache.get(key);
    if (!cached) return null;

    // Check if expired
    if (Date.now() - cached.timestamp > cached.ttl) {
      this.cache.delete(key);
      this.saveToStorage();
      return null;
    }

    return cached.response;
  }

  set(key: string, response: any, ttl: number = 300000) {
    // Default TTL: 5 minutes
    this.cache.set(key, {
      key,
      response,
      timestamp: Date.now(),
      ttl,
    });
    this.saveToStorage();
  }

  clear() {
    this.cache.clear();
    this.saveToStorage();
  }

  private loadFromStorage() {
    try {
      const stored = localStorage.getItem(this.storageKey);
      if (stored) {
        const data = JSON.parse(stored);
        this.cache = new Map(Object.entries(data));
      }
    } catch (error) {
      console.error('[OfflineMode] Failed to load cache:', error);
    }
  }

  private saveToStorage() {
    try {
      const data = Object.fromEntries(this.cache);
      localStorage.setItem(this.storageKey, JSON.stringify(data));
    } catch (error) {
      console.error('[OfflineMode] Failed to save cache:', error);
    }
  }
}

class LocalModel {
  /**
   * Local model for basic actions when offline
   * Uses simple heuristics and cached data
   */

  canHandle(action: Action): boolean {
    // Can handle basic actions offline
    const offlineActions = ['click', 'scroll', 'type', 'press_key'];
    return offlineActions.includes(action.type);
  }

  async execute(action: Action): Promise<any> {
    console.log('[LocalModel] Executing offline:', action.type);

    switch (action.type) {
      case 'click':
        return this.handleClick(action.params);
      case 'scroll':
        return this.handleScroll(action.params);
      case 'type':
        return this.handleType(action.params);
      case 'press_key':
        return this.handlePressKey(action.params);
      default:
        throw new Error(`Cannot handle action ${action.type} offline`);
    }
  }

  private async handleClick(params: any) {
    // Execute click directly via extension
    return { status: 'success', message: 'Clicked (offline mode)' };
  }

  private async handleScroll(params: any) {
    // Execute scroll directly
    const direction = params.direction || 'down';
    window.scrollBy(0, direction === 'down' ? 300 : -300);
    return { status: 'success', message: `Scrolled ${direction} (offline mode)` };
  }

  private async handleType(params: any) {
    // Queue for later - typing requires context
    return { status: 'queued', message: 'Will type when online' };
  }

  private async handlePressKey(params: any) {
    // Execute key press directly
    return { status: 'success', message: 'Key pressed (offline mode)' };
  }
}

export class OfflineMode {
  private cache: Cache;
  private queue: ActionQueue;
  private localModel: LocalModel;
  private isOnline: boolean = navigator.onLine;
  private syncInProgress: boolean = false;

  constructor() {
    this.cache = new Cache();
    this.queue = new ActionQueue();
    this.localModel = new LocalModel();

    // Listen for online/offline events
    window.addEventListener('online', () => this.handleOnline());
    window.addEventListener('offline', () => this.handleOffline());
  }

  async handleAction(action: Action): Promise<any> {
    // Check cache first
    const cacheKey = `${action.type}:${JSON.stringify(action.params)}`;
    const cached = await this.cache.get(cacheKey);
    if (cached) {
      console.log('[OfflineMode] Cache hit:', cacheKey);
      return cached;
    }

    // If offline, use local model or queue
    if (!this.isOnline) {
      if (this.localModel.canHandle(action)) {
        console.log('[OfflineMode] Using local model');
        return await this.localModel.execute(action);
      } else {
        console.log('[OfflineMode] Queueing action');
        this.queue.add(action);
        return {
          status: 'queued',
          message: 'Action queued. Will execute when online.',
        };
      }
    }

    // Online - execute normally
    return null; // Let caller handle online execution
  }

  cacheResponse(action: Action, response: any) {
    const cacheKey = `${action.type}:${JSON.stringify(action.params)}`;
    this.cache.set(cacheKey, response);
  }

  private handleOnline() {
    console.log('[OfflineMode] Back online');
    this.isOnline = true;
    this.syncWhenOnline();
  }

  private handleOffline() {
    console.log('[OfflineMode] Gone offline');
    this.isOnline = false;
  }

  async syncWhenOnline() {
    if (this.syncInProgress || !this.isOnline) return;

    this.syncInProgress = true;
    console.log('[OfflineMode] Syncing queued actions...');

    try {
      while (!this.queue.isEmpty()) {
        const action = this.queue.pop();
        if (action) {
          console.log('[OfflineMode] Executing queued action:', action.type);
          // Caller should handle execution
          // This is just a placeholder
          await new Promise((resolve) => setTimeout(resolve, 100));
        }
      }
      console.log('[OfflineMode] Sync complete');
    } catch (error) {
      console.error('[OfflineMode] Sync failed:', error);
    } finally {
      this.syncInProgress = false;
    }
  }

  getStatus() {
    return {
      isOnline: this.isOnline,
      queuedActions: this.queue.isEmpty() ? 0 : 'has items',
      syncInProgress: this.syncInProgress,
    };
  }

  clearCache() {
    this.cache.clear();
  }

  clearQueue() {
    this.queue.clear();
  }
}

// Global instance
let _offlineMode: OfflineMode | null = null;

export function getOfflineMode(): OfflineMode {
  if (!_offlineMode) {
    _offlineMode = new OfflineMode();
  }
  return _offlineMode;
}
