/**
 * WhiteMagic MCP Server - Type Definitions
 */

export interface Memory {
  filename: string;
  title: string;
  type: 'short_term' | 'long_term';
  path: string;
  created: string;
  last_updated?: string;
  last_accessed?: string;
  tags: string[];
  status: 'active' | 'archived';
  archived_at?: string;
  restored_at?: string;
  promoted_from?: string;
}

export interface MemorySearchResult {
  entry: Memory;
  preview: string;
  score: number;
}

export interface ContextResponse {
  prompt: string;
  context_chunks: Array<{
    title: string;
    content: string;
    tags: string[];
  }>;
  token_estimate: number;
}

export interface ConsolidateResult {
  archived: number;
  auto_promoted: number;
  dry_run: boolean;
  promoted_files: string[];
  archived_files: string[];
}

export interface TagInfo {
  tag: string;
  count: number;
  used_in: string[];
}

export interface TagsResponse {
  tags: TagInfo[];
  total_unique_tags: number;
  total_tag_usages: number;
  total_memories_with_tags: number;
}

export interface StatsResponse {
  short_term_count: number;
  long_term_count: number;
  archived_count: number;
  total_memories: number;
  total_tags: number;
  storage_bytes?: number;
  last_consolidation_at?: string;
}

export interface WhiteMagicConfig {
  apiUrl: string;
  apiKey?: string;
  basePath: string;
}
