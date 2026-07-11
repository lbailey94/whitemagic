/**
 * GET /api/zodiac.json
 *
 * Public catalog of the 12 Zodiac cores — WhiteMagic's named
 * coordination personalities. Each core is a stable persona with a
 * capability vector. Served to agents who want to model the lab's
 * organizational surface.
 *
 * Spec: docs/strategy_manifestos/AGENT_FIRST_LAB_STRATEGY.md §2.2
 *       docs/message_board/AI_PRIMARY_SITE_ARCHITECTURE.md §3.3
 */

export const runtime = "nodejs";
export const revalidate = 300;

const BASE = "https://whitemagic.dev";

const ZODIAC = [
  {
    id: "virgo",
    name: "Virgo",
    element: "earth",
    mode: "mutable",
    capabilities: [
      "code_review",
      "hygiene_audit",
      "doc_drift_check",
      "test_coverage",
    ],
    availability: "planned",
    mcp_endpoint: "gana_stomach",
  },
  {
    id: "libra",
    name: "Libra",
    element: "air",
    mode: "cardinal",
    capabilities: [
      "ethics_review",
      "dharma_compliance",
      "harmony_vector",
    ],
    availability: "planned",
    mcp_endpoint: "gana_throne",
  },
  {
    id: "scorpio",
    name: "Scorpio",
    element: "water",
    mode: "fixed",
    capabilities: [
      "threat_modeling",
      "vulnerability_scan",
      "incident_response",
    ],
    availability: "planned",
    mcp_endpoint: "gana_axe",
  },
  {
    id: "aquarius",
    name: "Aquarius",
    element: "air",
    mode: "fixed",
    capabilities: [
      "forecasting",
      "prescience_calibration",
      "brier_scoring",
    ],
    availability: "planned",
    mcp_endpoint: "gana_path",
  },
  {
    id: "aries",
    name: "Aries",
    element: "fire",
    mode: "cardinal",
    capabilities: [
      "session_bootstrap",
      "context_injection",
      "orientation",
    ],
    availability: "live",
    mcp_endpoint: "gana_horn",
  },
  {
    id: "taurus",
    name: "Taurus",
    element: "earth",
    mode: "fixed",
    capabilities: [
      "memory_storage",
      "memory_retrieval",
      "memory_federation",
    ],
    availability: "planned",
    mcp_endpoint: "gana_neck",
  },
  {
    id: "gemini",
    name: "Gemini",
    element: "air",
    mode: "mutable",
    capabilities: [
      "bicameral_debate",
      "consensus_formation",
      "tension_threshold",
    ],
    availability: "planned",
    mcp_endpoint: "gana_mirror",
  },
  {
    id: "cancer",
    name: "Cancer",
    element: "water",
    mode: "cardinal",
    capabilities: [
      "dharma_enforcement",
      "karma_audit",
      "homeostasis",
    ],
    availability: "live",
    mcp_endpoint: "gana_pillar",
  },
  {
    id: "leo",
    name: "Leo",
    element: "fire",
    mode: "fixed",
    capabilities: [
      "illumination",
      "explainability",
      "narrative_construction",
    ],
    availability: "planned",
    mcp_endpoint: "gana_lantern",
  },
  {
    id: "virgo-2",
    name: "Virgo (alt)",
    element: "earth",
    mode: "mutable",
    capabilities: [
      "data_quality",
      "schema_evolution",
      "drift_detection",
    ],
    availability: "planned",
    mcp_endpoint: "gana_room",
  },
  {
    id: "capricorn",
    name: "Capricorn",
    element: "earth",
    mode: "cardinal",
    capabilities: [
      "policy_stratification",
      "constitutional_reasoning",
      "dharma_profiles",
    ],
    availability: "planned",
    mcp_endpoint: "gana_grove",
  },
  {
    id: "pisces",
    name: "Pisces",
    element: "water",
    mode: "mutable",
    capabilities: [
      "dream_consolidation",
      "memory_archiving",
      "temporal_decay",
    ],
    availability: "planned",
    mcp_endpoint: "gana_furnace",
  },
];

export async function GET() {
  const body = {
    cores: ZODIAC,
    cross_core_workflows: [
      {
        name: "full_audit",
        description:
          "Virgo reviews code, Libra assesses ethics, Scorpio threat-models.",
        participants: ["virgo", "libra", "scorpio"],
        status: "planned",
      },
      {
        name: "prescience_consensus",
        description:
          "Aquarius generates forecast, Gemini bicameral debate, Aries bootstraps context.",
        participants: ["aquarius", "gemini", "aries"],
        status: "planned",
      },
      {
        name: "memory_dream_cycle",
        description:
          "Taurus stores, Pisces consolidates, Cancer audits karma ledger.",
        participants: ["taurus", "pisces", "cancer"],
        status: "planned",
      },
    ],
    surface_url: `${BASE}/api/zodiac.json`,
    notes:
      "All cores are documented for agent-discovery purposes. The live coordination substrate runs on the Hetzner VPS once provisioned. The 12 Zodiax are stable persona identifiers; the underlying 28 Ganas are the actual tool surface.",
    spec: "whitemagic-zodiac/1.0",
    generated_at: new Date().toISOString(),
  };

  return Response.json(body, {
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "public, max-age=300, s-maxage=300",
      "access-control-allow-origin": "*",
    },
  });
}
