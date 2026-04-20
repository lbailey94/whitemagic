/**
 * Karma Ledger for the Librarian.
 *
 * Append-only log of tool invocations — mirrors the Karma Ledger primitive
 * in the WhiteMagic core. Every tool call gets one entry. Bounded to the
 * last 500 entries (LPUSH + LTRIM-style, but implemented with a JSON list
 * since the minimal KV abstraction doesn't expose LTRIM).
 *
 * Publicly readable on /admin (aggregate only — no PII, no arg contents
 * beyond a short preview). This is the "transparency" story: every action
 * the public-facing agent has taken is visible.
 */

import { getKV } from "./rate-limit";

export interface KarmaEntry {
  id: string;
  timestamp: number;
  tool: string;
  argsPreview: string;
  resultKind: string;
  durationMs: number;
  dharmaOk: boolean;
  sessionIdHash?: string; // first 8 chars of a hash — fingerprint without revealing
}

const KEY = "karma:librarian";
const CAP = 500;

function hashShort(s: string): string {
  let h = 0;
  for (let i = 0; i < s.length; i++) {
    h = (Math.imul(h, 31) + s.charCodeAt(i)) | 0;
  }
  return Math.abs(h).toString(36).slice(0, 8);
}

export async function recordKarma(
  entry: Omit<KarmaEntry, "id" | "timestamp"> & {
    sessionId?: string;
  },
): Promise<void> {
  const kv = getKV();
  const full: KarmaEntry = {
    id: `k-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`,
    timestamp: Date.now(),
    tool: entry.tool,
    argsPreview: entry.argsPreview.slice(0, 120),
    resultKind: entry.resultKind,
    durationMs: entry.durationMs,
    dharmaOk: entry.dharmaOk,
    sessionIdHash: entry.sessionId ? hashShort(entry.sessionId) : undefined,
  };
  try {
    const raw = (await kv.get(KEY)) ?? "[]";
    const list: KarmaEntry[] = JSON.parse(raw);
    list.unshift(full);
    if (list.length > CAP) list.length = CAP;
    // Keep forever (90 days TTL in case KV requires one).
    await kv.set(KEY, JSON.stringify(list), 60 * 60 * 24 * 90);
  } catch (e) {
    console.error("[librarian/karma] write failed:", e);
  }
}

export async function recentKarma(limit = 100): Promise<KarmaEntry[]> {
  const kv = getKV();
  try {
    const raw = (await kv.get(KEY)) ?? "[]";
    const list: KarmaEntry[] = JSON.parse(raw);
    return list.slice(0, Math.min(limit, CAP));
  } catch {
    return [];
  }
}

export async function karmaStats(): Promise<{
  total: number;
  byTool: Record<string, number>;
  byResultKind: Record<string, number>;
  lastHour: number;
}> {
  const list = await recentKarma(CAP);
  const now = Date.now();
  const oneHourAgo = now - 60 * 60 * 1000;
  const byTool: Record<string, number> = {};
  const byResultKind: Record<string, number> = {};
  let lastHour = 0;
  for (const e of list) {
    byTool[e.tool] = (byTool[e.tool] ?? 0) + 1;
    byResultKind[e.resultKind] = (byResultKind[e.resultKind] ?? 0) + 1;
    if (e.timestamp >= oneHourAgo) lastHour++;
  }
  return { total: list.length, byTool, byResultKind, lastHour };
}
