/**
 * Monthly budget tracking for the Librarian.
 *
 * Hard cap: $25/month (LOCKED per scoping doc section 2, decision 5 locked).
 * Alert threshold: 80% of cap (sends notice; does not cut off).
 *
 * Tracks real USD spend based on reported LLM usage. Uses the same KV
 * client as rate-limit, so prod hits Upstash and dev hits in-memory.
 */

import { getKV } from "./rate-limit";
import type { BudgetStatus } from "./types";

const HARD_CAP_USD = Number(process.env.LIBRARIAN_MONTHLY_CAP_USD ?? "25");
const ALERT_THRESHOLD = 0.8;

function currentMonth(): string {
  const d = new Date();
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}`;
}

function secondsUntilNextMonth(): number {
  const now = new Date();
  const next = new Date(
    Date.UTC(now.getUTCFullYear(), now.getUTCMonth() + 1, 1, 0, 0, 0),
  );
  return Math.ceil((next.getTime() - now.getTime()) / 1000);
}

export async function getBudget(): Promise<BudgetStatus> {
  const kv = getKV();
  const month = currentMonth();
  const raw = await kv.get(`lib:budget:${month}`);
  const spentUsd = raw ? Number(raw) : 0;
  const percentUsed = (spentUsd / HARD_CAP_USD) * 100;
  return {
    month,
    spentUsd,
    capUsd: HARD_CAP_USD,
    percentUsed,
    exceeded: spentUsd >= HARD_CAP_USD,
    alertThreshold: spentUsd >= HARD_CAP_USD * ALERT_THRESHOLD,
  };
}

export async function recordSpend(costUsd: number): Promise<BudgetStatus> {
  const kv = getKV();
  const month = currentMonth();
  const key = `lib:budget:${month}`;
  const prev = Number((await kv.get(key)) ?? "0");
  const next = prev + costUsd;
  // Store as fixed-precision string; KV treats as opaque.
  await kv.set(key, next.toFixed(6), secondsUntilNextMonth());
  return {
    month,
    spentUsd: next,
    capUsd: HARD_CAP_USD,
    percentUsed: (next / HARD_CAP_USD) * 100,
    exceeded: next >= HARD_CAP_USD,
    alertThreshold: next >= HARD_CAP_USD * ALERT_THRESHOLD,
  };
}
