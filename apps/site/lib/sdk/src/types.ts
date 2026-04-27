/** WhiteMagic SDK — Core types */

// ---------------------------------------------------------------------------
// Tool result envelope
// ---------------------------------------------------------------------------

export interface ToolResult {
  status: "success" | "error";
  tool: string;
  request_id: string;
  message: string;
  details: Record<string, unknown>;
  error_code?: string;
  retryable: boolean;
  timestamp: string;
}

// ---------------------------------------------------------------------------
// Memory types
// ---------------------------------------------------------------------------

export interface Memory {
  id: string;
  content: string;
  tags: string[];
  created_at: string;
  updated_at: string;
  galaxy?: string;
  holographic_coords?: number[];
  embedding?: number[];
}

export interface MemoryCreateRequest {
  content: string;
  tags?: string[];
  galaxy?: string;
}

export interface MemorySearchRequest {
  query: string;
  limit?: number;
  galaxy?: string;
  method?: "semantic" | "keyword" | "hybrid";
}

export interface MemorySearchResult {
  memories: Memory[];
  total: number;
  elapsed_ms: number;
}

// ---------------------------------------------------------------------------
// Galaxy types
// ---------------------------------------------------------------------------

export interface Galaxy {
  name: string;
  memory_count: number;
  association_count: number;
  created_at: string;
}

// ---------------------------------------------------------------------------
// Governance types
// ---------------------------------------------------------------------------

export interface DharmaEvaluation {
  action: string;
  rule: string;
  verdict: "LOG" | "TAG" | "WARN" | "THROTTLE" | "BLOCK";
  severity: number;
  explanation: string;
}

export interface KarmaEntry {
  action: string;
  evaluation: DharmaEvaluation;
  timestamp: string;
}

// ---------------------------------------------------------------------------
// System status
// ---------------------------------------------------------------------------

export interface SystemStatus {
  version: string;
  uptime_seconds: number;
  memory_count: number;
  association_count: number;
  db_size_bytes: number;
  active_galaxies: string[];
  cycle_phase: string;
  yin_yang_balance: { yin: number; yang: number };
}

// ---------------------------------------------------------------------------
// MCP transport types
// ---------------------------------------------------------------------------

export interface MCPRequest {
  jsonrpc: "2.0";
  id: number | string;
  method: string;
  params?: Record<string, unknown>;
}

export interface MCPResponse {
  jsonrpc: "2.0";
  id: number | string;
  result?: unknown;
  error?: {
    code: number;
    message: string;
    data?: unknown;
  };
}
