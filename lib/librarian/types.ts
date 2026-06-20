/**
 * Shared types for the Librarian — the public-facing AI on whitemagic.dev.
 *
 * The Librarian is a persona-bounded agent whose knowledge scope is limited
 * to the public site + the public OSS README. It does NOT know about Aria,
 * private grimoire material, or unreleased work.
 */

export type Role = "user" | "assistant" | "system";

export interface ChatMessage {
  role: Role;
  content: string;
}

export interface ChatRequest {
  messages: ChatMessage[];
  /** Optional session id for rate limiting; generated client-side. */
  sessionId?: string;
  /** Optional page context so the Librarian knows where the visitor is. */
  pageContext?: { path: string; title?: string };
}

export interface StreamChunk {
  /** Incremental text delta from the LLM. */
  delta?: string;
  /** Emitted when a tool call is issued by the LLM (before execution). */
  tool_call?: {
    id: string;
    name: string;
    argsPreview: string;
  };
  /** Emitted when a tool call completes, with the structured result. */
  tool_result?: {
    callId: string;
    name: string;
    // Structured result — see lib/librarian/tools.ts ToolResult.
    // Typed as unknown here to avoid circular import; the client narrows.
    result: unknown;
  };
  /** Emitted when the stream ends, with usage stats. */
  done?: {
    inputTokens: number;
    outputTokens: number;
    costUsd: number;
    model: string;
    provider?: "stub" | "openrouter" | "ollama";
  };
  /** Emitted if the backend refuses (Dharma, rate limit, budget, kill switch). */
  refusal?: {
    reason:
      | "dharma"
      | "rate_limit_ip"
      | "rate_limit_session"
      | "monthly_budget"
      | "kill_switch"
      | "internal_error";
    message: string;
  };
}

export interface DharmaCheck {
  allow: boolean;
  rule?: string;
  message?: string;
}

export interface RateLimitState {
  /** true if the caller is permitted to proceed. */
  allow: boolean;
  /** seconds until the next call would be allowed, if blocked. */
  retryAfterSec?: number;
  /** scope that blocked (useful for user messaging). */
  scope?: "ip_daily" | "session_spend" | "monthly_budget";
}

export interface BudgetStatus {
  /** Month in ISO YYYY-MM format. */
  month: string;
  spentUsd: number;
  capUsd: number;
  /** Percentage of cap used, 0–100+. */
  percentUsed: number;
  /** true if over the cap (Librarian should refuse). */
  exceeded: boolean;
  /** true if over the 80% alert threshold but still serving. */
  alertThreshold: boolean;
}
