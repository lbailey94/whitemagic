/**
 * GET /api/librarian/status
 *
 * Reports the librarian's current configuration: provider, model,
 * bridge tool count, session count. Used by the chat UI to show
 * "powered by X" in the corner, and by the site-ci smoke test to
 * verify the librarian is reachable.
 *
 * Does NOT call any LLM. Pure introspection.
 */

import { getLLMProvider, DEFAULT_MODEL, DEFAULT_OLLAMA_MODEL } from "@/lib/librarian/llm";
import { LIBRARIAN_BRIDGE_TOOLS, validateBridgeTools } from "@/lib/librarian/bridge-tools";
import { listSessions } from "@/lib/librarian/session-store";
import { BRIDGE_MODULES } from "@/lib/data/mcp-bridge";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(): Promise<Response> {
  const provider = getLLMProvider();
  const validation = validateBridgeTools();
  const sessions = listSessions();

  const providerInfo: Record<string, unknown> = {
    provider,
    model:
      provider === "ollama"
        ? process.env.OLLAMA_MODEL ?? DEFAULT_OLLAMA_MODEL
        : process.env.OPENROUTER_MODEL ?? DEFAULT_MODEL,
    configured: false,
  };

  if (provider === "openrouter") {
    providerInfo.configured = !!process.env.OPENROUTER_API_KEY;
  } else if (provider === "ollama") {
    providerInfo.baseUrl =
      process.env.OLLAMA_BASE_URL ?? "http://localhost:11434";
  }

  return Response.json(
    {
      status: "ok",
      version: "22.5.0",
      provider: providerInfo,
      bridge: {
        total_functions: BRIDGE_MODULES.length,
        librarian_can_call: LIBRARIAN_BRIDGE_TOOLS.length,
        validation,
      },
      sessions: {
        active: sessions.length,
        most_recent: sessions.slice(0, 5).map((s) => ({
          sessionId: s.sessionId.slice(0, 8) + "...",
          lastActiveAt: s.lastActiveAt,
          messageCount: s.messageCount,
        })),
      },
    },
    {
      headers: {
        "content-type": "application/json; charset=utf-8",
        "cache-control": "no-store",
      },
    },
  );
}
