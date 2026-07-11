/**
 * GET /api/librarian/karma
 *
 * Returns recent Karma Ledger entries for the /admin dashboard and any
 * public transparency view. Aggregate only — no PII, no conversation
 * content. Session ids are shown as short hashes.
 */

import { recentKarma, karmaStats } from "@/lib/librarian/karma";
import type { NextRequest } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(req: NextRequest): Promise<Response> {
  const { searchParams } = new URL(req.url);
  const limit = Math.min(Number(searchParams.get("limit") ?? "100"), 500);
  const [entries, stats] = await Promise.all([
    recentKarma(limit),
    karmaStats(),
  ]);
  return Response.json(
    { entries, stats },
    { headers: { "Cache-Control": "no-store" } },
  );
}
