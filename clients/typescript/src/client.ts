import type {
  Memory,
  CreateMemoryRequest,
  UpdateMemoryRequest,
  ListMemoriesParams,
  SearchMemoriesParams,
  User,
  UsageStats,
  HealthResponse,
  WhiteMagicClientConfig,
} from './types.js';
import { WhiteMagicError } from './types.js';

export class WhiteMagicClient {
  private apiKey: string;
  private baseUrl: string;
  private timeout: number;
  private retries: number;

  constructor(config: WhiteMagicClientConfig) {
    this.apiKey = config.apiKey;
    this.baseUrl = config.baseUrl || 'https://api.whitemagic.dev';
    this.timeout = config.timeout || 30000;
    this.retries = config.retries !== undefined ? config.retries : 3;
  }

  private async request<T>(
    method: string,
    path: string,
    body?: any,
    params?: Record<string, any>
  ): Promise<T> {
    const url = new URL(path, this.baseUrl);

    // Add query parameters
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          if (Array.isArray(value)) {
            value.forEach(v => url.searchParams.append(key, String(v)));
          } else {
            url.searchParams.set(key, String(value));
          }
        }
      });
    }

    const headers: Record<string, string> = {
      'X-API-Key': this.apiKey,
      'Content-Type': 'application/json',
    };

    const options: RequestInit = {
      method,
      headers,
      signal: AbortSignal.timeout(this.timeout),
    };

    if (body) {
      options.body = JSON.stringify(body);
    }

    let lastError: Error | null = null;

    for (let attempt = 0; attempt <= this.retries; attempt++) {
      try {
        const response = await fetch(url.toString(), options);

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new WhiteMagicError(
            errorData.message || `HTTP ${response.status}: ${response.statusText}`,
            response.status,
            errorData.code,
            errorData.details
          );
        }

        // Handle 204 No Content
        if (response.status === 204) {
          return null as T;
        }

        return await response.json();
      } catch (error) {
        lastError = error as Error;

        // Don't retry on client errors (4xx)
        if (error instanceof WhiteMagicError && error.status && error.status < 500) {
          throw error;
        }

        // Don't retry on last attempt
        if (attempt === this.retries) {
          break;
        }

        // Exponential backoff
        await new Promise(resolve => setTimeout(resolve, Math.pow(2, attempt) * 1000));
      }
    }

    throw lastError || new WhiteMagicError('Request failed after retries');
  }

  // Memory operations
  memories = {
    create: async (data: CreateMemoryRequest): Promise<Memory> => {
      return this.request<Memory>('POST', '/api/v1/memories', data);
    },

    list: async (params: ListMemoriesParams = {}): Promise<Memory[]> => {
      return this.request<Memory[]>('GET', '/api/v1/memories', undefined, params);
    },

    get: async (id: string): Promise<Memory> => {
      return this.request<Memory>('GET', `/api/v1/memories/${id}`);
    },

    update: async (id: string, data: UpdateMemoryRequest): Promise<Memory> => {
      return this.request<Memory>('PUT', `/api/v1/memories/${id}`, data);
    },

    delete: async (id: string): Promise<void> => {
      return this.request<void>('DELETE', `/api/v1/memories/${id}`);
    },

    restore: async (id: string): Promise<Memory> => {
      return this.request<Memory>('POST', `/api/v1/memories/${id}/restore`);
    },

    search: async (params: SearchMemoriesParams): Promise<Memory[]> => {
      return this.request<Memory[]>('GET', '/api/v1/search', undefined, params);
    },

    addRelationship: async (
      id: string,
      targetId: string,
      type: string,
      description?: string
    ): Promise<any> => {
      return this.request('POST', `/api/v1/memories/${id}/relationships`, {
        target_filename: targetId,
        type,
        description,
      });
    },

    getRelationships: async (id: string): Promise<any[]> => {
      return this.request<any[]>('GET', `/api/v1/memories/${id}/relationships`);
    },
  };

  // User operations
  users = {
    me: async (): Promise<User> => {
      return this.request<User>('GET', '/api/v1/users/me');
    },

    usage: async (): Promise<UsageStats> => {
      return this.request<UsageStats>('GET', '/api/v1/users/me/usage');
    },
  };

  // System operations
  health = async (): Promise<HealthResponse> => {
    return this.request<HealthResponse>('GET', '/health');
  };
}
