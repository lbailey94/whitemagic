/**
 * POST /api/contact — plain contact form backend.
 *
 * Pipeline:
 *   1. Per-IP rate limit (5 submissions / IP / day, sliding UTC day)
 *   2. Minimal honeypot (reject when `website` field is non-empty)
 *   3. Validate + store via shared lib/contact.ts
 *
 * Contact submissions land in the same KV namespace as the Librarian's
 * `submit_contact_request` tool, so /admin shows a unified feed.
 */

import type { NextRequest } from "next/server";
import { getKV } from "@/lib/librarian/rate-limit";
import { storeContactRequest } from "@/lib/contact";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const CONTACT_IP_DAILY_LIMIT = 5;

function clientIp(req: NextRequest): string {
  const xff = req.headers.get("x-forwarded-for");
  if (xff) return xff.split(",")[0].trim();
  return req.headers.get("x-real-ip") ?? "unknown";
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

export async function POST(req: NextRequest): Promise<Response> {
  let body: Record<string, unknown>;
  try {
    body = (await req.json()) as Record<string, unknown>;
  } catch {
    return Response.json({ error: "Invalid JSON body." }, { status: 400 });
  }

  // Honeypot — bots fill all fields; humans never see `website`.
  if (typeof body.website === "string" && body.website.trim().length > 0) {
    // Pretend success. Don't tell the bot it lost.
    return Response.json({ ok: true, reference: "wm-accepted" });
  }

  const email = typeof body.email === "string" ? body.email : "";
  const topic = typeof body.topic === "string" ? body.topic : "";
  const summary = typeof body.summary === "string" ? body.summary : "";

  // Per-IP daily rate limit (separate keyspace from Librarian chat).
  const ip = clientIp(req);
  const kv = getKV();
  const rlKey = `contact:ip:${ip}:${todayKey()}`;
  try {
    const count = await kv.incr(rlKey, secondsUntilUtcMidnight());
    if (count > CONTACT_IP_DAILY_LIMIT) {
      return Response.json(
        {
          error:
            "You've submitted several messages today. Try again tomorrow, or email directly.",
        },
        { status: 429 },
      );
    }
  } catch (e) {
    console.error("[contact] rate-limit check failed:", e);
    // Fail open — don't block a legitimate submission on a flaky KV.
  }

  const stored = await storeContactRequest({
    email,
    topic,
    summary,
    source: "form",
  });

  if (!stored.ok || !stored.reference) {
    return Response.json(
      { error: stored.error ?? "Could not accept submission." },
      { status: 400 },
    );
  }

  return Response.json({ ok: true, reference: stored.reference });
}
