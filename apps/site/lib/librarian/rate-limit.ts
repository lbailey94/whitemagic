/**
 * Rate limiting for the Librarian.
 *
 * Production: backed by Upstash Redis (REST API — works on Vercel Edge).
 * Dev / unconfigured: in-memory Map, resets on every server restart.
 *
 * Two scopes:
 * - Per-IP daily count (coarse) — prevents one bot from hammering us.
 * - Per-session message count (fine) — prevents one conversation from
 *   going runaway.
 *
 * Monthly budget is tracked separately in `./budget`.
 */

import type { RateLimitState } from "./types";

const DAILY_IP_LIMIT = 30; // messages per IP per calendar day
const SESSION_MESSAGE_LIMIT = 40; // messages per session (soft cap)

interface KVClient {
  get(key: string): Promise<string | null>;
  set(key: string, value: string, ttlSec?: number): Promise<void>;
  incr(key: string, ttlSec?: number): Promise<number>;
}

class InMemoryKV implements KVClient {
  private store = new Map<string, { value: string; expiresAt: number }>();

  private sweep() {
    const now = Date.now();
    for (const [k, v] of this.store) {
      if (v.expiresAt > 0 && v.expiresAt < now) this.store.delete(k);
    }
  }

  async get(key: string): Promise<string | null> {
    this.sweep();
    const entry = this.store.get(key);
    return entry ? entry.value : null;
  }

  async set(key: string, value: string, ttlSec?: number): Promise<void> {
    this.store.set(key, {
      value,
      expiresAt: ttlSec ? Date.now() + ttlSec * 1000 : 0,
    });
  }

  async incr(key: string, ttlSec?: number): Promise<number> {
    const current = parseInt((await this.get(key)) ?? "0", 10);
    const next = current + 1;
    await this.set(key, String(next), ttlSec);
    return next;
  }
}

class UpstashKV implements KVClient {
  constructor(
    private url: string,
    private token: string,
  ) {}

  private async call(command: string[]): Promise<unknown> {
    const res = await fetch(this.url, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${this.token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(command),
    });
    if (!res.ok) throw new Error(`Upstash error: ${res.status}`);
    const data = (await res.json()) as { result: unknown };
    return data.result;
  }

  async get(key: string): Promise<string | null> {
    const r = await this.call(["GET", key]);
    return r == null ? null : String(r);
  }

  async set(key: string, value: string, ttlSec?: number): Promise<void> {
    const cmd = ["SET", key, value];
    if (ttlSec) cmd.push("EX", String(ttlSec));
    await this.call(cmd);
  }

  async incr(key: string, ttlSec?: number): Promise<number> {
    const result = (await this.call(["INCR", key])) as number;
    if (ttlSec && result === 1) {
      await this.call(["EXPIRE", key, String(ttlSec)]);
    }
    return result;
  }
}

let _kv: KVClient | null = null;

export function getKV(): KVClient {
  if (_kv) return _kv;
  const url = process.env.UPSTASH_REDIS_REST_URL;
  const token = process.env.UPSTASH_REDIS_REST_TOKEN;
  if (url && token) {
    _kv = new UpstashKV(url, token);
  } else {
    if (process.env.NODE_ENV !== "production") {
      console.warn(
        "[librarian/rate-limit] UPSTASH_* env vars not set; falling back to in-memory KV (dev only).",
      );
    }
    _kv = new InMemoryKV();
  }
  return _kv;
}

function todayKey(): string {
  const d = new Date();
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}-${String(d.getUTCDate()).padStart(2, "0")}`;
}

function secondsUntilUtcMidnight(): number {
  const now = new Date();
  const tomorrow = new Date(
    Date.UTC(
      now.getUTCFullYear(),
      now.getUTCMonth(),
      now.getUTCDate() + 1,
      0,
      0,
      0,
    ),
  );
  return Math.ceil((tomorrow.getTime() - now.getTime()) / 1000);
}

export async function checkRateLimit(
  ip: string,
  sessionId: string | undefined,
): Promise<RateLimitState> {
  const kv = getKV();

  // Per-IP daily
  const ipKey = `lib:ip:${ip}:${todayKey()}`;
  const ipCount = await kv.incr(ipKey, secondsUntilUtcMidnight());
  if (ipCount > DAILY_IP_LIMIT) {
    return {
      allow: false,
      retryAfterSec: secondsUntilUtcMidnight(),
      scope: "ip_daily",
    };
  }

  // Per-session soft cap
  if (sessionId) {
    const sessKey = `lib:sess:${sessionId}`;
    const sessCount = await kv.incr(sessKey, 60 * 60 * 2); // 2h session window
    if (sessCount > SESSION_MESSAGE_LIMIT) {
      return {
        allow: false,
        retryAfterSec: 60 * 60,
        scope: "session_spend",
      };
    }
  }

  return { allow: true };
}

export const RATE_LIMITS_PUBLIC = {
  dailyPerIp: DAILY_IP_LIMIT,
  perSession: SESSION_MESSAGE_LIMIT,
};
