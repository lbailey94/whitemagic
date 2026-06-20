/**
 * GET /api/mcp-bridge.json
 *
 * Machine-readable catalog of the 13 whitemagic.core.bridge.* modules
 * (143 functions) exposed by whitemagic.mcp_api_bridge for the public
 * MCP API surface. v22.5.0 expanded the catalog from 30 -> 143
 * functions to match the full Python surface.
 *
 * Spec: docs/strategy_manifestos/AGENT_FIRST_LAB_STRATEGY.md §2.4
 *       (Bridges as a primary public surface)
 *
 * v22.2.2 had 14 unguarded star imports in mcp_api_bridge.py that
 * crashed the entire MCP surface on import. v22.2.3 fixed it. v22.5.0
 * documents the full surface.
 */

export const runtime = "nodejs";
export const revalidate = 3600;

import { BRIDGE_MODULES, BRIDGE_SUMMARY } from "@/lib/data/mcp-bridge";

const BASE = "https://whitemagic.dev";

export async function GET() {
  const body = {
    schema_version: "1.0.0",
    generated_at: new Date().toISOString(),
    system: {
      name: "WhiteMagic",
      version: "22.5.0",
      url: BASE,
      repository: "https://github.com/whitemagic-ai/whitemagic",
      license: "MIT",
    },
    summary: BRIDGE_SUMMARY,
    notes: [
      "These bridge functions are the public facade for the whitemagic.mcp_api_bridge module.",
      "The actual MCP server (planned) will route calls to these functions via the Hetzner VPS.",
      "All examples are illustrative — actual output depends on live core state at call time.",
      "In v22.2.2 the bridge was completely broken (14 unguarded star imports). v22.2.3 fixed it; v22.5.0 documents the full 143-function surface.",
    ],
    functions: BRIDGE_MODULES,
    spec: "whitemagic-mcp-bridge/1.0",
    surface_url: `${BASE}/api/mcp-bridge.json`,
    human_doc: `${BASE}/mcp-bridge`,
  };

  return Response.json(body, {
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "public, max-age=3600, s-maxage=3600",
      "access-control-allow-origin": "*",
    },
  });
}
