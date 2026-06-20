/**
 * In-memory session store for the Librarian.
 *
 * Persists conversation messages per session_id cookie. The store lives in
 * the Node.js process; on Vercel serverless cold start, sessions reset.
 * For persistent sessions, swap with Vercel KV, Supabase, or a SQLite file.
 *
 * Constraints (per site AGENTS.md §2):
 *   - No filesystem writes outside WM_STATE_ROOT.
 *   - In-memory is fine for demo; document the limitation.
 */

import type { ChatMessage } from "./types";

export interface StoredSession {
  sessionId: string;
  messages: ChatMessage[];
  createdAt: number;
  lastActiveAt: number;
  totalCostUsd: number;
  totalInputTokens: number;
  totalOutputTokens: number;
  // Bounded ring of (inputTokens, outputTokens, costUsd) per message
  // so we can show a session-scoped cost summary.
  history: Array<{
    ts: number;
    inputTokens: number;
    outputTokens: number;
    costUsd: number;
    toolNames: string[];
  }>;
}

// In-process map keyed by sessionId.
const sessions = new Map<string, StoredSession>();

// Bound the total number of sessions to avoid memory leaks in long-lived
// processes. Older sessions are evicted when the cap is reached.
const MAX_SESSIONS = 1000;

// Bound the message count per session to keep payloads small.
const MAX_MESSAGES_PER_SESSION = 200;

export function getOrCreateSession(sessionId: string): StoredSession {
  const now = Date.now();
  const existing = sessions.get(sessionId);
  if (existing) {
    existing.lastActiveAt = now;
    return existing;
  }
  // Evict oldest if at cap.
  if (sessions.size >= MAX_SESSIONS) {
    let oldestKey: string | null = null;
    let oldestTime = Infinity;
    for (const [k, v] of sessions) {
      if (v.lastActiveAt < oldestTime) {
        oldestTime = v.lastActiveAt;
        oldestKey = k;
      }
    }
    if (oldestKey) sessions.delete(oldestKey);
  }
  const fresh: StoredSession = {
    sessionId,
    messages: [],
    createdAt: now,
    lastActiveAt: now,
    totalCostUsd: 0,
    totalInputTokens: 0,
    totalOutputTokens: 0,
    history: [],
  };
  sessions.set(sessionId, fresh);
  return fresh;
}

export function appendMessages(
  sessionId: string,
  newMessages: ChatMessage[],
): StoredSession {
  const session = getOrCreateSession(sessionId);
  session.messages.push(...newMessages);
  // Bound message count.
  if (session.messages.length > MAX_MESSAGES_PER_SESSION) {
    session.messages = session.messages.slice(-MAX_MESSAGES_PER_SESSION);
  }
  return session;
}

export function recordUsage(
  sessionId: string,
  usage: {
    inputTokens: number;
    outputTokens: number;
    costUsd: number;
    toolNames: string[];
  },
): void {
  const session = getOrCreateSession(sessionId);
  session.totalInputTokens += usage.inputTokens;
  session.totalOutputTokens += usage.outputTokens;
  session.totalCostUsd += usage.costUsd;
  session.history.push({ ts: Date.now(), ...usage });
  // Bound history to last 100 entries.
  if (session.history.length > 100) {
    session.history = session.history.slice(-100);
  }
}

export function getSession(sessionId: string): StoredSession | null {
  return sessions.get(sessionId) ?? null;
}

export function listSessions(): Array<{
  sessionId: string;
  createdAt: number;
  lastActiveAt: number;
  messageCount: number;
  totalCostUsd: number;
}> {
  return Array.from(sessions.values())
    .map((s) => ({
      sessionId: s.sessionId,
      createdAt: s.createdAt,
      lastActiveAt: s.lastActiveAt,
      messageCount: s.messages.length,
      totalCostUsd: s.totalCostUsd,
    }))
    .sort((a, b) => b.lastActiveAt - a.lastActiveAt);
}

export function clearSession(sessionId: string): void {
  sessions.delete(sessionId);
}

/**
 * Cookie helpers. The session_id is set by the client (the chat component
 * generates a UUID on first load and stores in localStorage). The cookie
 * is set by the server via the Set-Cookie response header.
 */
export const SESSION_COOKIE = "wm_librarian_sid";
export const SESSION_COOKIE_MAX_AGE = 60 * 60 * 24 * 30; // 30 days
