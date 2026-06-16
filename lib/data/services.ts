/**
 * Structured service data, read by both the Librarian's
 * `get_service_detail` tool and (eventually) the service pages
 * themselves. Single source of truth.
 */

export type ServiceSlug =
  | "private-ai-deployment"
  | "agent-governance"
  | "mcp-engineering";

export interface Service {
  slug: ServiceSlug;
  name: string;
  shortName: string;
  oneLiner: string;
  whoThisIsFor: string[];
  whatYouGet: string[];
  typicalDuration: string;
  engagementType: string;
  path: string;
  relatedCapabilities: string[];
}

export const SERVICES: Record<ServiceSlug, Service> = {
  "private-ai-deployment": {
    slug: "private-ai-deployment",
    name: "Private AI Deployment",
    shortName: "Private AI",
    oneLiner:
      "Local or air-gapped LLM + agent deployment for regulated industries.",
    whoThisIsFor: [
      "Healthcare, finance, legal, government teams with compliance constraints",
      "Teams that need an LLM working against sensitive data without leaving their perimeter",
      "Engineers who already tried hosted providers and hit policy walls",
    ],
    whatYouGet: [
      "Working deployment: Docker / bare-metal / cloud VPC",
      "Model selection + quantization appropriate to hardware budget",
      "Agent layer with persistent memory (WhiteMagic or equivalent)",
      "Runbooks, monitoring, and handoff documentation",
    ],
    typicalDuration: "4–6 weeks",
    engagementType: "Research collaboration",
    path: "/services/private-ai-deployment",
    relatedCapabilities: ["harmony-vector", "circuit-breaker", "galaxy-backup"],
  },
  "agent-governance": {
    slug: "agent-governance",
    name: "Agent Governance",
    shortName: "Governance",
    oneLiner:
      "Framework-agnostic policy, side-effect audit, and observability for existing agent systems.",
    whoThisIsFor: [
      "Teams with agents already in production that need audit + policy layers",
      "Organizations mapping to OWASP LLM Top 10 (v1.1, covers agentic AI) or EU AI Act Article 14",
      "Leaders who've been asked 'can we prove what the agent did?' and didn't have an answer",
    ],
    whatYouGet: [
      "Dharma Rules Engine integrated against your existing agent framework",
      "Karma Ledger recording declared vs actual side effects",
      "Circuit breakers on all external tool calls",
      "Harmony Vector dashboard: 7-dimensional live health metric",
      "OpenTelemetry-compatible trace plan for agent and tool events",
      "Mapping document: each control → OWASP / EU AI Act reference",
    ],
    typicalDuration: "3–5 weeks",
    engagementType: "Research collaboration",
    path: "/services/agent-governance",
    relatedCapabilities: [
      "dharma-rules",
      "karma-ledger",
      "harmony-vector",
      "circuit-breaker",
    ],
  },
  "mcp-engineering": {
    slug: "mcp-engineering",
    name: "MCP Governance & Scale",
    shortName: "MCP",
    oneLiner:
      "Production MCP servers, tool contract design, observability, and governance integration.",
    whoThisIsFor: [
      "Teams building agent systems that need to scale context efficiently",
      "Engineers whose agents already burn too many tokens on tool descriptions",
      "Anyone exposing business logic to Claude Desktop, Cursor, Windsurf, or VS Code Agent",
    ],
    whatYouGet: [
      "Custom MCP server(s) for your domain, stdio or Streamable HTTP transport",
      "Tool contract design: input/output schemas that minimize bloat",
      "28-Gana compression integration where it fits (87% token reduction on tool payloads)",
      "Auth, idempotency, structured errors, and audit middleware",
      "Client wiring examples for Claude Desktop / Cursor / Windsurf",
    ],
    typicalDuration: "2–4 weeks",
    engagementType: "Research collaboration",
    path: "/services/mcp-engineering",
    relatedCapabilities: ["gana-mcp-compression", "gnosis-portal"],
  },
};

export const SERVICES_LIST: Service[] = Object.values(SERVICES);

export function getService(slug: string): Service | null {
  return (SERVICES as Record<string, Service>)[slug] ?? null;
}
