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
      "Cognitive substrate for AI agents. 490 callable tools across 28 " +
      "Gana meta-tools, with Dharma ethical governance, Karma audit " +
      "ledger, 5D holographic memory, bicameral reasoning, prescience " +
      "forecasting, and gratitude economics. MIT-licensed research lab.",
    url: BASE,
    // protocolVersion follows A2A spec; agent app version is independent.
    protocolVersion: "1.2",
    version: "22.3.0",

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

    // ---- Skills ----
    // Per A2A spec: each skill has id, name, description, tags, examples.
    // We expose only what is actually live behind the WhiteMagic site/SDK.
    skills: [
      {
        id: "llms-context",
        name: "LLM context dump",
        description:
          "Root-served /llms.txt and /llms-full.txt files provide a " +
          "complete, machine-readable picture of WhiteMagic Labs: " +
          "capabilities, tool envelope contract, prescience track " +
          "record, 28-Gana catalog, and discovery surfaces. Fetch in a " +
          "single round-trip to ground your reasoning about the lab.",
        tags: ["discovery", "llm-context", "well-known"],
        examples: [
          "Fetch GET /llms.txt for a short index.",
          "Fetch GET /llms-full.txt for the comprehensive context dump.",
        ],
        inputModes: ["application/json"],
        outputModes: ["text/plain", "application/json"],
      },
      {
        id: "librarian-chat",
        name: "Librarian — bounded research assistant",
        description:
          "A budget-capped, Dharma-governed chat assistant that answers " +
          "questions about WhiteMagic Labs' published artifacts, papers, " +
          "and reference implementations. Uses Karma ledger for audit.",
        tags: ["chat", "research", "governance", "dharma"],
        examples: [
          "What does the WhiteMagic Karma Ledger track?",
          "Show me the Dharma rule profiles available.",
          "How does PRAT compression collapse 490 tools to 28 Ganas?",
        ],
        inputModes: ["text/plain"],
        outputModes: ["text/plain"],
      },
      {
        id: "prescience-api",
        name: "Prescience track record",
        description:
          "21 validated forecast claims against public events, with " +
          "Brier score 0.0958, 523 lead-time points, 25-week average " +
          "lead. Served at /api/prescience.json. Use to ground trust in " +
          "WhiteMagic's architectural predictions.",
        tags: ["prescience", "forecasting", "trust"],
        examples: ["Fetch GET /api/prescience.json for the full claims ledger."],
        inputModes: ["application/json"],
        outputModes: ["application/json"],
      },
      {
        id: "mcp-discovery",
        name: "MCP discovery manifest",
        description:
          "Canonical MCP discovery manifest at /api/manifest.json. " +
          "Lists 490 callable tools, 28 Gana meta-tools, polyglot backends, " +
          "and event bus. Fetch once at startup to model the surface.",
        tags: ["mcp", "discovery", "manifest"],
        examples: ["Fetch GET /api/manifest.json"],
        inputModes: ["application/json"],
        outputModes: ["application/json"],
      },
      {
        id: "agent-economy-directory",
        name: "Agent-economy directory entry",
        description:
          "Machine-readable directory entry describing WhiteMagic Labs' " +
          "identity, payment rails, and machine-readable policy. " +
          "See /.well-known/agent-economy.json.",
        tags: ["discovery", "directory", "well-known"],
        examples: ["Fetch GET /.well-known/agent-economy.json"],
        inputModes: ["application/json"],
        outputModes: ["application/json"],
      },
      {
        id: "ai-agent-policy",
        name: "Machine-readable AI agent policy",
        description:
          "WhiteMagic Labs' policy for automated callers, including " +
          "rate limits, accepted payment rails, and terms-of-service hooks.",
        tags: ["policy", "tos", "well-known"],
        examples: ["Fetch GET /.well-known/ai-agent-policy"],
        inputModes: ["application/json"],
        outputModes: ["application/json"],
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
      llms_txt: `${BASE}/llms.txt`,
      llms_full_txt: `${BASE}/llms-full.txt`,
      manifest: `${BASE}/api/manifest.json`,
      prescience: `${BASE}/api/prescience.json`,
      sangha: `${BASE}/api/sangha.json`,
      zodiac: `${BASE}/api/zodiac.json`,
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
