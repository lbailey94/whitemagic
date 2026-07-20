export type FieldArea =
  | "Protocols"
  | "Governance"
  | "Observability"
  | "Commerce"
  | "Regulation";

export interface FieldSignal {
  area: FieldArea;
  title: string;
  external: string;
  whitemagic: string;
  consequence: string;
  source: {
    label: string;
    url: string;
  };
}

export interface FieldConclusion {
  title: string;
  body: string;
}

export interface RoadmapUpdate {
  horizon: string;
  title: string;
  items: string[];
}

export const FIELD_MAP_UPDATED = "May 24, 2026";

export const FIELD_SIGNALS: FieldSignal[] = [
  {
    area: "Protocols",
    title: "MCP is moving from local tool bridge to production substrate.",
    external:
      "The Model Context Protocol now has production-oriented surfaces: Streamable HTTP, authorization guidance, registry metadata, and roadmap work on scalable sessions behind proxies and load balancers.",
    whitemagic:
      "WhiteMagic already treats MCP as a governed runtime surface: stable tool envelopes, an 8-stage dispatch pipeline, memory-aware handlers, and tool-surface compression for large catalogs.",
    consequence:
      "The website should sell MCP engineering as protocol hardening and governance integration, not simply custom tool wiring.",
    source: {
      label: "MCP specification and roadmap",
      url: "https://modelcontextprotocol.io/specification/2025-11-25",
    },
  },
  {
    area: "Protocols",
    title: "A2A makes agent discovery and interop a separate layer from tools.",
    external:
      "Google's Agent2Agent protocol frames agent cards, task exchange, streaming, authentication, and observability as the inter-agent layer above MCP-style tool access.",
    whitemagic:
      "WhiteMagic's distinctive material is not a competing transport. It is the memory, policy, audit, and reputation layer that can sit behind MCP, A2A, or a custom agent runtime.",
    consequence:
      "WhiteMagic should present itself as protocol-compatible governance infrastructure, not as a protocol maximalist.",
    source: {
      label: "Google A2A announcement",
      url: "https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/",
    },
  },
  {
    area: "Governance",
    title: "Mainstream agent SDKs now expose guardrails and tracing as first-class primitives.",
    external:
      "OpenAI's Agents SDK documents tool guardrails, handoffs, approvals, and structured traces around model calls and tool calls.",
    whitemagic:
      "Dharma Rules and Karma Ledger were built as framework-independent runtime controls around tool execution and side effects, rather than as one SDK's policy feature.",
    consequence:
      "The strongest claim is not 'nobody is doing guardrails'; it is 'WhiteMagic turns guardrails into an auditable, framework-agnostic substrate.'",
    source: {
      label: "OpenAI Agents SDK observability",
      url: "https://developers.openai.com/api/docs/guides/agents/integrations-observability",
    },
  },
  {
    area: "Observability",
    title: "Agent telemetry is standardizing around OpenTelemetry conventions.",
    external:
      "OpenTelemetry's GenAI semantic conventions now include agent, workflow, tool, MCP, and model spans, with explicit privacy guidance around capturing prompts and outputs.",
    whitemagic:
      "Karma Ledger, Harmony Vector, PRAT scoring, and dispatch envelopes are already structured enough to export to a standard observability backend.",
    consequence:
      "A high-leverage next step is OTEL-compatible export for Karma and Harmony events, not a proprietary dashboard first.",
    source: {
      label: "OpenTelemetry GenAI semantic conventions",
      url: "https://opentelemetry.io/docs/specs/semconv/gen-ai/",
    },
  },
  {
    area: "Commerce",
    title: "Agent payments are real, but the near-term market is still payments-first.",
    external:
      "x402 and Stripe's machine-payment work show agentic payments becoming developer infrastructure, but the visible commercial motion is settlement, checkout, authorization, and merchant integration.",
    whitemagic:
      "Gratitude Architecture is differentiated when framed as optional, governance-aware contribution infrastructure layered on free tools, not as a direct payments startup.",
    consequence:
      "Keep the agent-economy page, but lead with governance, audit, and voluntary contribution. Do not make transaction volume the 12-month business plan.",
    source: {
      label: "x402 V2 launch",
      url: "https://www.x402.org/writing/x402-v2-launch",
    },
  },
  {
    area: "Regulation",
    title: "Compliance pressure is converging on transparency, oversight, and audit evidence.",
    external:
      "OWASP's GenAI work and the EU AI Act timeline push deployers toward clearer risk taxonomies, transparency duties, human oversight, and evidence that high-impact AI systems are controlled.",
    whitemagic:
      "WhiteMagic's practical fit is an evidence layer: policy verdicts, side-effect audit, approval gates, circuit breakers, and machine-readable runbooks.",
    consequence:
      "The services pages should speak to evidence packaging and operational controls more than abstract AI safety philosophy.",
    source: {
      label: "EU AI Act overview",
      url: "https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai",
    },
  },
];

export const FIELD_CONCLUSIONS: FieldConclusion[] = [
  {
    title: "WhiteMagic is strongest as governance and observability infrastructure.",
    body: "Recent protocols are standardizing transport, discovery, and payments. WhiteMagic's defensible surface is the layer that asks what an agent is allowed to do, records what it actually did, and turns that trace into usable evidence.",
  },
  {
    title: "Memory is substrate, not the product headline.",
    body: "Persistent memory remains important, but major platforms are absorbing basic memory features. WhiteMagic's public positioning should keep 6D memory as a foundation for governance, continuity, and audit rather than sell memory alone.",
  },
  {
    title: "Payments belong behind voluntary contribution and readiness assessment.",
    body: "The agent-commerce stack is maturing, but direct agent-transaction revenue is still speculative. The practical near-term offer is readiness: identity, policy, rate limits, audit, and payment-layer safety before teams expose agents to money movement.",
  },
  {
    title: "The right posture is reference implementation plus research lab.",
    body: "The market is moving too quickly for a solo lab to win every protocol race. WhiteMagic should publish rigorous artifacts, stay compatible with emerging standards, and use consulting to fund the work without forcing a premature SaaS shape.",
  },
];

export const ROADMAP_UPDATES: RoadmapUpdate[] = [
  {
    horizon: "Now–30 days",
    title: "Turn shipped code into citable evidence.",
    items: [
      "Finish the Karma Ledger preprint and benchmark protocol.",
      "Publish agent-native site metadata: /.well-known/agent-economy.json, ai-agent-policy, docs.json, pricing.json.",
      "Package Agent Governance Review and Agent Economy Readiness as concrete services.",
    ],
  },
  {
    horizon: "30–90 days",
    title: "Align with the standards that are winning.",
    items: [
      "Add OpenTelemetry-compatible export for Karma, Harmony, and tool-call audit events.",
      "Make the site and platform easier for MCP and A2A-aware agents to discover.",
      "Run a small reproducible side-effect fidelity benchmark instead of claiming broad validation early.",
    ],
  },
  {
    horizon: "3–12 months",
    title: "Build optionality without pretending the market is mature.",
    items: [
      "Keep x402/XRPL gratitude as optional infrastructure, not the core revenue assumption.",
      "Pursue grants around auditability, metacognition, and agent governance evidence packs.",
      "Extract a focused agent-guardrails package only after the research artifact and benchmark have traction.",
    ],
  },
];
