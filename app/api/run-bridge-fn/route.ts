/**
 * POST /api/run-bridge-fn
 *
 * Executes one of the 29 whitemagic.mcp_api_bridge functions server-side.
 * Used by the /mcp-bridge and /zodiac pages for interactive demos.
 *
 * The TS impls in lib/bridge/impl.ts return the same shapes as the
 * Python bridge. When the public MCP server ships (Hetzner-hosted,
 * per site AGENTS.md §2), this route will proxy to the live Python
 * instead of running the TS stubs.
 *
 * Request body:
 *   { function: "zodiac_list_cores", payload: {} }
 *
 * Response body:
 *   { ok: true,  function, result: {...} }   on success
 *   { ok: false, function, error: "..." }     on failure
 *
 * GET is also supported for trivial smoke tests; returns a manifest of
 * available functions and the URL of the machine-readable catalog.
 *
 * Site AGENTS.md §2: low-cost / static endpoints only — no high-traffic
 * proxy work. This route is cache-friendly (each function call is
 * idempotent) and stays well within Vercel Hobby limits.
 */

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { BRIDGE_MODULES } from "@/lib/data/mcp-bridge";
import { dispatchBridgeFunction } from "@/lib/bridge/impl";

const BASE = "https://whitemagic.dev";

export async function GET() {
  return Response.json(
    {
      schema_version: "1.0.0",
      system: { name: "WhiteMagic", version: "22.4.0", url: BASE, license: "MIT" },
      runtime: "nodejs (TS demo impl, see lib/bridge/impl.ts)",
      catalog_url: `${BASE}/api/mcp-bridge.json`,
      functions: BRIDGE_MODULES.map((m) => ({
        name: m.name,
        category: m.category,
        example_payload: m.example_payload,
        example_response: m.example_response,
      })),
      note: "POST { function, payload } to this endpoint to execute. See /mcp-bridge for the human-facing catalog and /zodiac for interactive core activation.",
    },
    {
      headers: {
        "content-type": "application/json; charset=utf-8",
        "cache-control": "no-store",
        "access-control-allow-origin": "*",
      },
    },
  );
}

export async function POST(request: Request) {
  let body: { function?: string; payload?: Record<string, unknown> };
  try {
    body = await request.json();
  } catch {
    return Response.json(
      { ok: false, function: "", error: "invalid JSON body. expected { function, payload }" },
      { status: 400, headers: { "content-type": "application/json" } },
    );
  }

  const name = typeof body?.function === "string" ? body.function : "";
  const payload =
    body?.payload && typeof body.payload === "object" && !Array.isArray(body.payload)
      ? (body.payload as Record<string, unknown>)
      : {};

  if (!name) {
    return Response.json(
      { ok: false, function: "", error: "missing 'function' in request body" },
      { status: 400, headers: { "content-type": "application/json" } },
    );
  }

  const result = dispatchBridgeFunction(name, payload);
  return Response.json(result, {
    status: result.ok ? 200 : 400,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
      "access-control-allow-origin": "*",
    },
  });
}
