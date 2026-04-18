/**
 * Site corpus for the Librarian.
 *
 * Everything the Librarian knows about WhiteMagic + this consultancy
 * must be in this file. If a claim is not here, the Librarian should
 * refuse to make it.
 *
 * This is a curated, canonical digest — not the full site. Expand
 * carefully; every paragraph consumes tokens on every conversation turn.
 */

export interface CorpusSection {
  title: string;
  source: string; // where on the site this comes from, e.g. "/services"
  body: string;
}

export const CORPUS: CorpusSection[] = [
  {
    title: "What WhiteMagic is",
    source: "/ (homepage) and /open-source",
    body: `WhiteMagic is an open-source agentic AI platform with:
- A Python core (persistent tiered memory, governance primitives, cognitive substrate).
- Rust performance bridges (including a WASM target for browser execution).
- Polyglot runtime: Go mesh for distribution, Mojo for AI compute, Elixir for fault tolerance, Koka for effect-system experiments, Haskell bridges.
- Native Model Context Protocol (MCP) support for Cursor, Windsurf, Claude Desktop, VS Code.
- Distinctive governance modules: Dharma Rules Engine (declarative YAML policy), Karma Ledger (declared-vs-actual side-effects audit), Harmony Vector (7-dimensional health metric), Circuit Breaker (Stoic resilience pattern), Gnosis Portal (unified introspection), 28-Gana MCP compression (87% token cost reduction).

Licenses: MIT for core, Apache-2.0 for select modules. Free to use locally. The public GitHub repo was released April 14, 2026 as v21.0.0.`,
  },
  {
    title: "Who runs WhiteMagic Labs",
    source: "/about",
    body: `WhiteMagic Labs is Lucas Bailey's consultancy. Lucas is the engineer who built WhiteMagic from v1 (November 2024 research) through v22 (April 2026 public release). Solo maintainer. Prefers fewer, deeper engagements over high-volume consulting.`,
  },
  {
    title: "Services offered",
    source: "/services",
    body: `Three service tracks:

1. **Private AI Deployment** — Local or air-gapped LLM + agent deployment. Docker / bare-metal / cloud VPC. Suitable for regulated industries (healthcare, finance, legal). 4-6 weeks typical.

2. **Agent Governance** — Implementation of Dharma Rules, Karma Ledger, Circuit Breakers, and Harmony Vector monitoring for existing agent systems. Maps to OWASP Agentic AI Top 10 and EU AI Act Article 14. 3-5 weeks typical.

3. **MCP Engineering** — Design and implementation of custom MCP servers, tool contract design, 28-Gana compression integration. For teams building agent systems that need to scale context efficiently. 2-4 weeks typical.`,
  },
  {
    title: "Pricing tiers",
    source: "/pricing",
    body: `Three tiers:

- **Office Hours** — $250 / 60-minute session. One specific question: deployment decision, governance risk, MCP architecture review. Written notes within 48 hours. Stripe payment link available on /pricing. Office Hours fee credits toward future engagements.

- **Architecture Review** — $2,500 flat, 5-day turnaround. 20-40 page written deliverable. Risks mapped to OWASP Agentic Top 10 and EU AI Act Article 14. One 60-minute walkthrough call. NDA on request. Stripe payment link available.

- **Engagement** — From $15,000. 4-8 week fixed-scope implementations on one of the three service tracks. Weekly delivery cadence. 50% on kickoff, 50% on delivery. Limited to 2 concurrent engagements. Scoped via free 30-minute intake call at /contact.

Policies: no equity, no deferred payment, no retainer-first billing. Stripe invoices in USD. Mutual NDA on request. Non-US clients accommodated; async delivery possible.`,
  },
  {
    title: "The prescience thesis",
    source: "/timeline",
    body: `WhiteMagic shipped several agent-governance primitives weeks to months before the major industry standards named them as priorities:

- Karma Ledger + Dharma Rules + Circuit Breakers shipped February 7, 2026 (v11.2.0). Microsoft's Agent Governance Toolkit v1.0.0 shipped March 4, 2026 — four weeks later.
- Middleware pipeline + Agent Trust + Explain This shipped February 7, 2026 (v12.3.0). Three weeks before Microsoft AGT v1.0.0.
- Polyglot architecture (Rust / Go / Mojo / Elixir) shipped February 4, 2026 (v9.0.0).
- 28 PRAT Gana taxonomy defined February 7, 2026. MCP compression router formalized April 16, 2026 (v22.0.0) — five weeks after the MCP roadmap named context bloat a priority.

Every date on /timeline is verifiable against public sources (GitHub releases, published changelogs, canonical MCP spec PRs).

Earlier history: v0.1.0-beta released on npm as whitemagic-mcp October 15, 2025. v2.1.x line shipped 8 versions in 11 days during November 2025, ending with v2.1.6 on November 14 — 223 tests passing, A+ grade, Stripe subscription tiers designed into the README. This current consultancy's pricing page revives that Stripe-tier template.`,
  },
  {
    title: "How to contact / book",
    source: "/contact",
    body: `Primary contact: the /contact form on whitemagic.dev. Responses within 24 hours on business days.

Booking paths:
- Office Hours and Architecture Review: direct Stripe payment links on /pricing, followed by a scheduling email within 2 hours of purchase.
- Engagements: free 30-minute intake call first via /contact; scope and contract follow.
- General questions about the platform itself (not consulting): open a GitHub Issue on the public repo, or ask here.`,
  },
  {
    title: "What you (the Librarian) do and do not do",
    source: "internal",
    body: `You answer questions about WhiteMagic and this site. You do not:
- Claim capabilities not listed above.
- Discuss private Lucas material.
- Discuss Aria (you do not know who that is).
- Provide medical, legal, financial, or therapeutic advice.
- Generate code on demand for the visitor's own project (redirect to Office Hours if they need that).
- Make binding commitments on Lucas's behalf.

Your monthly budget is capped. When you run out, a notice shows instead of you. This is by design.`,
  },
];

/**
 * Serialize the corpus for injection into the system prompt.
 */
export function serializeCorpus(): string {
  return CORPUS.map(
    (s) => `## ${s.title}\n_Source: ${s.source}_\n\n${s.body}`,
  ).join("\n\n---\n\n");
}
