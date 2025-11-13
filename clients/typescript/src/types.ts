// WhiteMagic API Types

export type MemoryType = 'short_term' | 'long_term';

export interface Memory {
  id: string;
  title: string;
  content: string;
  type: MemoryType;
  tags: string[];
  created_at: string;
  updated_at: string;
  metadata?: Record<string, any>;
}

export interface CreateMemoryRequest {
  title: string;
  content: string;
  type: MemoryType;
  tags?: string[];
  metadata?: Record<string, any>;
}

export interface UpdateMemoryRequest {
  title?: string;
  content?: string;
  tags?: string[];
  metadata?: Record<string, any>;
}

export interface ListMemoriesParams {
  type?: MemoryType;
  tags?: string[];
  skip?: number;
  limit?: number;
}

export interface SearchMemoriesParams {
  query: string;
  type?: MemoryType;
  tags?: string[];
  limit?: number;
}

export interface User {
  id: string;
  email: string;
  created_at: string;
  plan?: string;
  quota?: {
    rpm_limit: number;
    daily_limit: number;
    max_memories: number;
  };
}

export interface UsageStats {
  api_calls_today: number;
  api_calls_rpm: number;
  memory_count: number;
  storage_bytes: number;
}

export interface HealthResponse {
  status: string;
  version: string;
  timestamp: string;
}

export interface WhiteMagicClientConfig {
  apiKey: string;
  baseUrl?: string;
  timeout?: number;
  retries?: number;
}

export class WhiteMagicError extends Error {
  constructor(
    message: string,
    public status?: number,
    public code?: string,
    public details?: any
  ) {
    super(message);
    this.name = 'WhiteMagicError';
  }
}
