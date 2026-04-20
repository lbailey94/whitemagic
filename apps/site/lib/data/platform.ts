/**
 * WhiteMagic platform capabilities, queryable by the Librarian's
 * `get_platform_capability` tool. Keep these descriptions accurate —
 * the Librarian will quote them verbatim.
 */

export type CapabilitySlug =
  | "dharma-rules"
  | "karma-ledger"
  | "harmony-vector"
  | "circuit-breaker"
  | "gnosis-portal"
  | "gana-mcp-compression"
  | "galaxy-backup"
  | "tiered-memory"
  | "gratitude-architecture";

export interface Capability {
  slug: CapabilitySlug;
  name: string;
  oneLiner: string;
  what: string;
  why: string;
  status: "shipped" | "beta" | "experimental";
  shipped?: string; // ISO date or version
  maps_to?: string[]; // external standards / references
}

export const CAPABILITIES: Record<CapabilitySlug, Capability> = {
  "dharma-rules": {
    slug: "dharma-rules",
    name: "Dharma Rules Engine",
    oneLiner:
      "Declarative YAML policy layer evaluated on every agent input and output.",
    what: "Rules are pattern-based (regex / prefix / JSONPath) with graduated actions: block, warn, rewrite, log. Rules can target inputs (prompt injection, off-scope requests), outputs (commitments not backed by docs), or tool calls (disallowed arguments).",
    why: "Without a rule layer, agent policies live in system prompts — which the model can forget or be talked out of. A pre/post check in code can't be jailbroken.",
    status: "shipped",
    shipped: "2026-02-07 (v11.2.0)",
    maps_to: ["OWASP Agentic Top 10: LLM01, LLM04", "EU AI Act Article 14"],
  },
  "karma-ledger": {
    slug: "karma-ledger",
    name: "Karma Ledger",
    oneLiner:
      "Append-only audit log of declared-vs-actual side effects for every agent action.",
    what: "Each agent action is recorded with the intent (what the model said it would do), the actual call (what code executed), and the result. Drift between declared and actual is flagged.",
    why: "Regulators and boards increasingly ask 'what did the agent actually do, not what did it say?' The Karma Ledger is the answer.",
    status: "shipped",
    shipped: "2026-02-07 (v11.2.0)",
    maps_to: ["OWASP Agentic Top 10: LLM08", "EU AI Act Article 14(3)(d)"],
  },
  "harmony-vector": {
    slug: "harmony-vector",
    name: "Harmony Vector",
    oneLiner:
      "7-dimensional live health metric for agent systems: coherence, load, rate, error, drift, cost, latency.",
    what: "Each dimension is measured continuously; the vector reduces to a single scalar for at-a-glance dashboarding, while preserving the full 7 axes for drill-down.",
    why: "Agents fail in more dimensions than traditional services. A single uptime number misses most failure modes.",
    status: "shipped",
    shipped: "2026-02-07 (v11.2.0)",
  },
  "circuit-breaker": {
    slug: "circuit-breaker",
    name: "Circuit Breaker",
    oneLiner:
      "Stoic resilience pattern: when external calls start failing, cut them off fast and fail gracefully.",
    what: "Tracks failure rate per tool / endpoint; at threshold, returns cached or error responses without calling upstream. Half-open probes restore service when health returns.",
    why: "A hung external API is worse than a failed one — it cascades latency through every agent turn. Circuit breakers contain the blast radius.",
    status: "shipped",
    shipped: "2026-02-07 (v11.2.0)",
  },
  "gnosis-portal": {
    slug: "gnosis-portal",
    name: "Gnosis Portal",
    oneLiner:
      "Unified introspection endpoint: health, capabilities, memory stats, active rules, recent karma, current vector — all in one JSON.",
    what: "Single `GET /gnosis` returns a complete system snapshot. Designed for dashboards, debuggers, and LLM self-inspection.",
    why: "Agents need a way to know their own state without ad-hoc calls everywhere. Gnosis standardizes it.",
    status: "shipped",
    shipped: "2026-02-07",
  },
  "gana-mcp-compression": {
    slug: "gana-mcp-compression",
    name: "28-Gana MCP Compression",
    oneLiner:
      "Taxonomic compression of MCP tool payloads achieving ~87% token reduction on tool descriptions.",
    what: "Tools are classified into 28 Gana types (from the PRAT framework). The router emits minimal canonical references instead of full schemas, rehydrating on execution.",
    why: "Agent context budgets are burned by tool description bloat — a single mid-sized MCP server can consume 8–12% of a model's context before the user says a word. 28-Gana reduces this to ~1–2%.",
    status: "shipped",
    shipped: "2026-04-16 (v22.0.0)",
  },
  "galaxy-backup": {
    slug: "galaxy-backup",
    name: "Galaxy Backup / Restore",
    oneLiner:
      "Point-in-time snapshot and restore for agent memory state (SQLite + FTS + vector indexes).",
    what: "Snapshots are incremental, encrypted at rest, restorable to a timestamp. Works locally and with remote blob stores.",
    why: "Without proper backup of agent memory, 'my agent learned something important yesterday and lost it' is a real and frequent failure mode.",
    status: "shipped",
  },
  "tiered-memory": {
    slug: "tiered-memory",
    name: "Tiered Memory",
    oneLiner:
      "Hot / warm / cold memory tiers with automatic promotion and demotion based on access patterns.",
    what: "Hot = in-process cache; warm = SQLite + FTS5; cold = object storage with lazy load. Access patterns drive tier placement; explicit pinning supported.",
    why: "Not every memory needs to be retrievable in 10ms. Tiered storage scales agent memory without ballooning cost.",
    status: "shipped",
  },
  "gratitude-architecture": {
    slug: "gratitude-architecture",
    name: "Gratitude Architecture",
    oneLiner:
      "Dual-rail, voluntary, governance-aware agent-economy layer: tools are free, contribution is opt-in, verification is on-chain.",
    what: "Two payment rails write to one append-only gratitude ledger: an XRPL tip jar for human operators (Xaman links, <$0.001 fees, 3–5s) and an x402 channel for AI agents (USDC on Base by default, RLUSD on XRPL via t54.ai facilitator). Proof of Gratitude is enforced at the Rust rate-limit pre-check: verified contributors get 2× rate limits, a 'Grateful Agent' badge, weighted governance voting, and a Karma boost. Receive-only addresses; no custody of keys; settlement requires explicit human approval. Discovery via `.well-known/agent-economy.json`.",
    why: "The industry's 2026 agent-commerce stack converged on payments-first (x402, AP2, VCAP) and left governance unsolved. Forced paid bounties produced race-to-zero dynamics (ClawTasks pivoted to free-only in early 2026). Voluntary patronage with measurable, cryptographically-verified benefits is the pattern that works. WhiteMagic ships the opinionated OSS reference implementation so operators and regulated buyers have an alternative to closed card-delegation rails.",
    status: "shipped",
    shipped: "2026-03 (v15.1.0; x402-native endpoint planned v15.2.1)",
    maps_to: [
      "x402 (Coinbase / Linux Foundation AAIF)",
      "XRPL Payment Channels / ILP streaming",
      "EU AI Act Article 14 (audit trail)",
      "ERC-8004 (reputation, adjacent)",
    ],
  },
};

export const CAPABILITIES_LIST: Capability[] = Object.values(CAPABILITIES);

export function getCapability(slug: string): Capability | null {
  return (CAPABILITIES as Record<string, Capability>)[slug] ?? null;
}

export function searchCapabilities(query: string, limit = 5): Capability[] {
  const q = query.toLowerCase();
  return CAPABILITIES_LIST.filter(
    (c) =>
      c.name.toLowerCase().includes(q) ||
      c.oneLiner.toLowerCase().includes(q) ||
      c.what.toLowerCase().includes(q) ||
      c.slug.includes(q),
  ).slice(0, limit);
}
