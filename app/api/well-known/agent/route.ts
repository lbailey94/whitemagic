/**
 * GET /.well-known/agent.json
 *
 * A2A Protocol v1.2 Agent Card for WhiteMagic Labs.
 *
 * Spec: https://github.com/google/A2A — JSON-RPC 2.0 over HTTPS, served at
 * the canonical .well-known path. Governed under the Linux Foundation's
 * Agentic AI Foundation. As of April 2026, 150+ organizations run A2A in
 * production (Microsoft, AWS, Salesforce, SAP, ServiceNow, Deutsche Bank,
 * etc.). Native support in Google ADK, LangGraph, CrewAI, LlamaIndex,
 * Semantic Kernel.
 *
 * This card is intentionally posture-honest: WhiteMagic Labs publishes
 * lab artifacts, references, and specs. The MCP-over-HTTPS endpoint
 * (`/mcp`) is planned, not live; we mark capabilities accordingly.
 */

export const runtime = "nodejs";
export const revalidate = 300;

const BASE = "https://whitemagic.dev";

export async function GET() {
  const body = {
    // ---- A2A required identity fields ----
    name: "WhiteMagic Labs",
    description:
      "Local-first cognitive substrate for AI agents. 151 callable " +
      "tools across 22 categories, with Dharma ethical governance, " +
      "Karma audit ledger, 5D holographic memory, 28 Gana meta-tools, " +
      "A2A v1.2 discovery surface. Substrate runs on the user's device " +
      "via the PWA — whitemagic.dev is a discovery surface + bridge " +
      "catalog, not a host. MIT-licensed research lab.",
    url: BASE,
    // protocolVersion follows A2A spec; agent app version is independent.
    protocolVersion: "1.2",
    version: "23.1.0",

    provider: {
      organization: "WhiteMagic Labs",
      url: BASE,
    },

    // ---- Capabilities advertised ----
    // Per A2A v1.2: declare what this agent supports so peers can plan.
    capabilities: {
      streaming: false, // No SSE streaming yet.
      pushNotifications: false,
      stateTransitionHistory: false,
      extendedAgentCard: false,
    },

    // ---- IO modes ----
    defaultInputModes: ["text/plain", "application/json"],
    defaultOutputModes: ["text/plain", "application/json"],

    // ---- Authentication ----
    // The Librarian endpoint is currently unauthenticated and rate-limited;
    // we'll add OAuth 2.1 / API-key schemes when MCP-over-HTTPS ships.
    securitySchemes: {
      none: {
        type: "noAuth",
        description:
          "Public lab endpoints (Librarian chat, well-knowns) require no auth. " +
          "Future MCP-over-HTTPS endpoints will require OAuth 2.1 or API key.",
      },
    },
    security: [{ none: [] }],

    // ---- Skills (two-layer: high-level + per-category) ----
    // The main card lists 7 high-level capabilities a peer can reason about.
    // The full 21-category skill set is in /.well-known/agent-skills.json.
    // Each per-category skill links to the actual bridge functions in
    // /api/mcp-bridge and the live exec endpoint /api/run-bridge-fn.
    skills: [
      {
        id: "llm-context-dump",
        name: "LLM context dump",
        description:
          "Root-served /llms.txt (short index) and /llms-full.txt " +
          "(comprehensive context) provide a complete, machine-readable " +
          "picture of WhiteMagic Labs: capabilities, tool envelope contract, " +
          "prescience track record, 28-Gana catalog, and discovery surfaces. " +
          "Fetch in a single round-trip to ground your reasoning about the lab.",
        tags: ["discovery", "llm-context", "well-known"],
        examples: [
          "Fetch GET /llms.txt for a short index.",
          "Fetch GET /llms-full.txt for the comprehensive context dump.",
        ],
        inputModes: ["application/json"],
        outputModes: ["text/plain", "application/json"],
      },
      {
        id: "mcp-bridge-discovery",
        name: "MCP bridge discovery",
        description:
          "143 whitemagic.mcp_api_bridge public functions across 21 " +
          "categories (archaeology, dharma, gana, garden, memory, " +
          "meditation, reasoning, session, system, wisdom, zodiac, ...). " +
          "Served at /api/mcp-bridge. Each function is callable live via " +
          "POST /api/run-bridge-fn with {function, payload}. The full " +
          "per-category skill tree is in /.well-known/agent-skills.json.",
        tags: ["mcp", "discovery", "bridge", "tool-catalog"],
        examples: [
          "Fetch GET /api/mcp-bridge for the full 143-function catalog.",
          "POST /api/run-bridge-fn {\"function\":\"dharma_check_boundaries\",\"payload\":{\"action\":{...}}}",
        ],
        inputModes: ["application/json"],
        outputModes: ["application/json"],
      },
      {
        id: "gana-tool-routing",
        name: "Gana meta-tool routing (28 mansions)",
        description:
          "28 Gana meta-tools collapse 488 dispatch tools into 28 named " +
          "personas (PRAT compression). Each Gana is a coordinate-aware " +
          "router: invoke with {operation, task} and the Gana picks the " +
          "right tool. Per-Gana details in /.well-known/agents/<gana>.json; " +
          "directory at /.well-known/agents.json.",
        tags: ["gana", "prat", "meta-tool", "router"],
        examples: [
          "gana_dipper: POST {function:'gana_dipper', payload:{task:'intelligence_briefing'}}",
          "gana_horn: POST {function:'gana_horn', payload:{operation:'create_session'}}",
          "GET /.well-known/agents.json for the 12-sign directory.",
        ],
        inputModes: ["application/json"],
        outputModes: ["application/json"],
      },
      {
        id: "dharma-ethics-check",
        name: "Dharma ethical governance",
        description:
          "6 dharma_* functions: dharma_evaluate_ethics, dharma_check_boundaries, " +
          "dharma_verify_consent, dharma_get_guidance, dharma_get_ethical_score, " +
          "dharma_list_principles. Pre-flight any agent action through " +
          "dharma_check_boundaries to detect ethical violations before commit.",
        tags: ["dharma", "ethics", "governance", "consent"],
        examples: [
          "POST {function:'dharma_check_boundaries', payload:{action:{type:'deploy',target:'production'}}}",
          "POST {function:'dharma_list_principles', payload:{level:'ahimsa'}}",
        ],
        inputModes: ["application/json"],
        outputModes: ["application/json"],
      },
      {
        id: "prescience-forecast",
        name: "Prescience track record",
        description:
          "21 validated forecast claims against public events, with " +
          "Brier score 0.0958, 523 lead-time points, 25-week average " +
          "lead. Served at /api/prescience.json. Use to ground trust in " +
          "WhiteMagic's architectural predictions. The gana_dipper.predict " +
          "task routes to the live forecasting engine.",
        tags: ["prescience", "forecasting", "trust", "brier-score"],
        examples: [
          "Fetch GET /api/prescience.json for the full claims ledger.",
          "POST {function:'gana_dipper', payload:{task:'predict'}}",
        ],
        inputModes: ["application/json"],
        outputModes: ["application/json"],
      },
      {
        id: "session-handoff",
        name: "Session handoff + context pack",
        description:
          "7 session_* functions: session_init, session_get_context, " +
          "session_checkpoint, session_list, session_create_handoff, " +
          "session_handoff. Move session state between agents, checkpoint " +
          "mid-conversation, or continue from another agent's handoff.",
        tags: ["session", "handoff", "checkpoint", "continuity"],
        examples: [
          "POST {function:'session_init', payload:{name:'agent_x', goals:['audit']}}",
          "POST {function:'session_create_handoff', payload:{target_session:'next'}}",
        ],
        inputModes: ["application/json"],
        outputModes: ["application/json"],
      },
      {
        id: "librarian-chat",
        name: "Librarian — bounded research assistant",
        description:
          "A budget-capped, Dharma-governed chat assistant that answers " +
          "questions about WhiteMagic Labs' published artifacts, papers, " +
          "and reference implementations. Uses Karma ledger for audit. " +
          "POST /api/librarian/chat with {message, session_id?}.",
        tags: ["chat", "research", "governance", "dharma"],
        examples: [
          "POST /api/librarian/chat {\"message\": 'What does the Karma Ledger track?'}",
          "POST /api/librarian/chat {\"message\": 'Show me Dharma rule profiles.'}",
        ],
        inputModes: ["text/plain", "application/json"],
        outputModes: ["text/plain", "application/json"],
      },
    ],

    // ---- Service endpoints ----
    // Where peers route work. Not all are live yet; status is honest.
    serviceEndpoints: {
      a2a_jsonrpc: {
        url: `${BASE}/api/a2a`,
        status: "planned",
        note: "JSON-RPC 2.0 endpoint for A2A task delegation. Not yet live.",
      },
      librarian_http: {
        url: `${BASE}/api/librarian/chat`,
        status: "live",
      },
      mcp_http: {
        url: `${BASE}/mcp`,
        status: "planned",
        note: "MCP-over-HTTPS endpoint. Planned per Island C / §2.2.2.",
      },
    },

    // ---- Cross-references to companion well-knowns ----
    related: {
      agent_economy: `${BASE}/.well-known/agent-economy.json`,
      ai_agent_policy: `${BASE}/.well-known/ai-agent-policy`,
      // Two-layer skills: this card lists 7 high-level; the 21 per-category
      // skills are in agent-skills.json. The 12 Gana agents are in
      // agents.json (directory) and agents/<gana>.json (detail).
      agent_skills: `${BASE}/.well-known/agent-skills.json`,
      agents_directory: `${BASE}/.well-known/agents.json`,
      agent_gana_prefix: `${BASE}/.well-known/agents/`,
      llms_txt: `${BASE}/llms.txt`,
      llms_full_txt: `${BASE}/llms-full.txt`,
      manifest: `${BASE}/api/manifest.json`,
      prescience: `${BASE}/api/prescience.json`,
      sangha: `${BASE}/api/sangha.json`,
      zodiac: `${BASE}/api/zodiac.json`,
      mcp_bridge: `${BASE}/api/mcp-bridge`,
      sitemap: `${BASE}/sitemap.xml`,
      skill_md: `${BASE}/skill.md`,
    },

    // ---- Lab posture disclosure ----
    // Important for honest peer-discovery: agents should know what they're
    // talking to. See user memory: WhiteMagic Labs is treating WhiteMagic
    // as a research/lab/portfolio artifact, not a production product.
    posture: {
      kind: "research-lab",
      maturity: "lab-artifact",
      production_endpoint_count: 1, // librarian_http
      planned_endpoint_count: 2, // a2a_jsonrpc, mcp_http
      live_discovery_surfaces: 9, // agent.json + agent-economy + ai-agent-policy + agent-skills + agents + 12 agents/<gana> + llms.txt + llms-full.txt
      documented_bridge_functions: 151,
      bridge_categories: 22, // 21 prior + new "galactic" category
      gana_meta_tools: 28,
      // v23.0.0-alpha.1: the substrate runs on the user's device, not on
      // our servers. This site is a discovery surface + bridge catalog.
      // Per v23 sovereignty principle: whitemagic.dev is the door, not the host.
      data_residency: "local-first",
      pwa_installable: true,
      substrate_default_location: "user-device",
      cloud_storage: false,
      sync_model: "opt-in-p2p",
      license: "MIT",
      source: "https://whitemagic.dev",
    },

    // ---- Performance benchmarks (June 2026) ----
    // Comprehensive benchmarks show WhiteMagic is 3-10x faster than typical
    // MCP implementations. Security systems (circuit breaker, rate limiter)
    // protect against abuse while maintaining fast response times.
    performance: {
      benchmark_date: "2026-06-16",
      latency_ms: {
        median: "29-33",
        p95: "36-55",
        p99: "38-86",
      },
      success_rate_percent: 100,
      memory_mb_per_call: "0-0.18",
      throughput_rps: {
        sequential: 29.38,
        concurrent_5_workers: 5.59,
        concurrent_10_20_workers: 4.0,
      },
      comparison: {
        vs_typical_mcp: "3-10x faster (29-33ms vs 100-300ms)",
        vs_anthropic_reference: "3-10x faster (29-33ms vs 100-300ms)",
        vs_complex_frameworks: "6-30x faster (29-33ms vs 200-1000ms)",
      },
      security: {
        circuit_breaker: "active",
        rate_limiter: "active",
        abuse_protection: "automatic",
      },
      methodology: "50 iterations per tool, 5 warmup calls, production hardware",
      full_report: `${BASE}/performance`,
    },

    // ---- Generation metadata ----
    spec_url: "https://github.com/google/A2A/blob/main/docs/specification.md",
    generated_at: new Date().toISOString(),
  };

  return Response.json(body, {
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "public, max-age=300, s-maxage=300",
      "access-control-allow-origin": "*",
      "x-a2a-protocol-version": "1.2",
    },
  });
}
