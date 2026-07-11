/**
 * GET /api/librarian/session?id=<sessionId>
 *
 * Returns the stored session: message history, total cost, total tokens.
 * Used by the chat UI on page load to resume a previous conversation.
 *
 * Returns 200 with the session, or 404 if not found.
 *
 * The session store is in-memory (see lib/librarian/session-store.ts) so
 * sessions are lost on Vercel serverless cold start. This endpoint
 * honestly reports the current state.
 */

import type { NextRequest } from "next/server";
import { getSession } from "@/lib/librarian/session-store";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(req: NextRequest): Promise<Response> {
  const sessionId = req.nextUrl.searchParams.get("id");
  if (!sessionId) {
    return new Response("Missing id query param", { status: 400 });
  }
  const session = getSession(sessionId);
  if (!session) {
    return Response.json(
      {
        status: "not_found",
        message:
          "Session not found. The in-memory session store loses data on Vercel serverless cold starts. Start a new conversation or check the chat history below.",
        sessionId,
      },
      { status: 404 },
    );
  }
  return Response.json({
    status: "ok",
    sessionId: session.sessionId,
    createdAt: session.createdAt,
    lastActiveAt: session.lastActiveAt,
    messages: session.messages,
    history: session.history,
    totals: {
      costUsd: session.totalCostUsd,
      inputTokens: session.totalInputTokens,
      outputTokens: session.totalOutputTokens,
    },
  });
}
