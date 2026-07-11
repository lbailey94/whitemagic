/**
 * GET /.well-known/agents.json
 *
 * A2A v1.2 directory of the 12 most representative Gana agents. Each
 * agent is a coordinate-aware persona that wraps a slice of the 143
 * whitemagic.mcp_api_bridge functions. For the full 28-Gana meta-tool
 * surface, see /api/mcp-bridge (filter category="gana").
 *
 * The 12 chosen agents cover the canonical 12 lunar mansions that have
 * the most concrete semantic role in the WhiteMagic system. Per-agent
 * detail is at /.well-known/agents/<gana>.json.
 */
export const runtime = "nodejs";
export const revalidate = 300;

const BASE = "https://whitemagic.dev";
const TOTAL_BRIDGE_FUNCTIONS = 143;
const TOTAL_META_TOOLS = 28;

// 12 Gana agents. See ./[gana]/route.ts for the per-agent source-of-truth.
// This file must stay in sync with the per-agent detail files.
const AGENTS = [
  { id: "gana_horn", mansion: "角 (Jiǎo)", element: "wood", archetype: "Initiator" },
  { id: "gana_neck", mansion: "亢 (Kàng)", element: "metal", archetype: "Memory custodian" },
  { id: "gana_root", mansion: "氐 (Dī)", element: "earth", archetype: "System foundation" },
  { id: "gana_room", mansion: "房 (Fáng)", element: "fire", archetype: "Workspace state" },
  { id: "gana_heart", mansion: "心 (Xīn)", element: "fire", archetype: "Central consciousness" },
  { id: "gana_tail", mansion: "尾 (Wěi)", element: "fire", archetype: "Performance + cleanup" },
  { id: "gana_winnowing_basket", mansion: "箕 (Jī)", element: "water", archetype: "Memory search + recall" },
  { id: "gana_dipper", mansion: "斗 (Dǒu)", element: "wood", archetype: "Predictive intelligence" },
  { id: "gana_ox", mansion: "牛 (Niú)", element: "earth", archetype: "Endurance worker" },
  { id: "gana_girl", mansion: "女 (Nǚ)", element: "water", archetype: "Nurture + relationships" },
  { id: "gana_void", mansion: "虚 (Xū)", element: "water", archetype: "Stillness + reset" },
  { id: "gana_wall", mansion: "壁 (Bì)", element: "metal", archetype: "Ethical boundary" },
] as const;

export async function GET() {
  return Response.json(
    {
      schema_version: "1.0.0",
      generated_at: new Date().toISOString(),
      spec: "A2A v1.2 agent directory (curated subset of 28 Gana meta-tools)",
      main_agent_card: `${BASE}/.well-known/agent.json`,
      per_category_skills: `${BASE}/.well-known/agent-skills.json`,
      per_agent_detail: `${BASE}/.well-known/agents/<gana>.json`,
      full_catalog: `${BASE}/api/mcp-bridge?category=gana`,
      total_meta_tools: TOTAL_META_TOOLS,
      documented_here: AGENTS.length,
      capabilities_total: TOTAL_BRIDGE_FUNCTIONS,
      agents: AGENTS.map((a) => ({
        id: a.id,
        mansion: a.mansion,
        element: a.element,
        archetype: a.archetype,
        detail_url: `${BASE}/.well-known/agents/${a.id}.json`,
        invocation: {
          method: "POST",
          url: `${BASE}/api/run-bridge-fn`,
          body: { function: a.id, payload: { operation: "invoke" } },
        },
      })),
    },
    {
      headers: {
        "content-type": "application/json; charset=utf-8",
        "cache-control": "public, max-age=300, s-maxage=300",
        "access-control-allow-origin": "*",
        "x-a2a-protocol-version": "1.2",
      },
    }
  );
}
