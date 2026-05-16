import { WM_FACTS } from "@/lib/facts";

/**
 * Timeline data — authoritative dates.
 *
 * Sources:
 *  - WhiteMagic entries: `docs/public/CHANGELOG.md` in the WhiteMagic core repo
 *    (the canonical public changelog). The git history itself was rewritten by
 *    a filter-repo pass on 2026-04-16 for the public release, so commit dates
 *    are not authoritative; the changelog is.
 *  - Industry entries: official blogs, press releases, GitHub release tags
 *    (Anthropic, Microsoft, OWASP, Linux Foundation / AAIF, The Verge).
 *  - Regulatory entries: published enforcement dates.
 */

export type Category = "whitemagic" | "industry" | "regulatory";

export interface TimelineEntry {
  date: string; // ISO "YYYY-MM-DD"
  displayDate: string;
  monthKey: string; // "YYYY-MM"
  monthLabel: string;
  category: Category;
  title: string;
  description: string;
  version?: string;
  source?: { label: string; url?: string };
  /** Prescience badge — e.g. "~4 weeks before Microsoft AGT v1.0.0" */
  gap?: string;
  pin?: boolean;
}

export const TIMELINE_DATA: TimelineEntry[] = [
  // ── 2024 ─────────────────────────────────────────────────────────────
  {
    date: "2024-11-01",
    displayDate: "Nov",
    monthKey: "2024-11",
    monthLabel: "November 2024",
    category: "whitemagic",
    title: "WhiteMagic v1 — research begins",
    description:
      "First iteration of a persistent-memory + agent-toolkit substrate. Exploratory codebase, no public release, pure research. Predates the MCP standard by days; the problem space was already visible.",
  },
  {
    date: "2024-11-25",
    displayDate: "Nov 25",
    monthKey: "2024-11",
    monthLabel: "November 2024",
    category: "industry",
    title: "Anthropic launches the Model Context Protocol (MCP)",
    description:
      "The integration standard that will anchor the next two years of agentic AI infrastructure. At launch, MCP is a proprietary Anthropic project.",
    source: {
      label: "anthropic.com — Nov 25 2024",
      url: "https://www.anthropic.com/news/model-context-protocol",
    },
  },

  // ── 2025 ─────────────────────────────────────────────────────────────
  {
    date: "2025-05-26",
    displayDate: "May 26",
    monthKey: "2025-05",
    monthLabel: "May 2025",
    category: "whitemagic",
    title:
      "MandalaOS Concept Review — Karma Ledger and Harmony Vector specs articulated",
    description:
      "In a long design conversation, the architecture for what would later become WhiteMagic's signature governance primitives was specced verbatim: 'Compiler stamps every binary with a manifest of declared side-effects; runtime appends actuals; mismatch accrues karma debt → throttling.' The Harmony Vector's 7-metric shape was specified the same day. Both shipped in code on Feb 7 2026 with near-verbatim fidelity. The original conversation export is timestamped and preserved as prior-art evidence.",
    pin: true,
  },
  {
    date: "2025-06-01",
    displayDate: "Jun",
    monthKey: "2025-06",
    monthLabel: "June 2025",
    category: "industry",
    title: "Google donates Agent-to-Agent (A2A) to Linux Foundation",
    description:
      "The first major coordination protocol for multi-agent systems enters neutral governance.",
  },
  {
    date: "2025-10-07",
    displayDate: "Oct 7",
    monthKey: "2025-10",
    monthLabel: "October 2025",
    category: "whitemagic",
    title: "WhiteMagic v2 — fresh architecture pass begins",
    description:
      "New design principles drawn from a year of v1 learnings: middleware pipeline, governance primitives, polyglot runtime, persistent memory with governance-aware retrieval. First commits in a companion visual workspace (Three.js frontend, matrix rain, grid pulses — the earliest ancestor of this site's visual language).",
  },
  {
    date: "2025-10-15",
    displayDate: "Oct 15",
    monthKey: "2025-10",
    monthLabel: "October 2025",
    category: "whitemagic",
    title: "WhiteMagic v0.1.0-beta — first tagged release",
    description:
      "Tiered memory management for AI agents with native MCP and REST support. Published to npm as whitemagic-mcp and to PyPI as whitemagic. Local SQLite storage, no signup, MCP server for Cursor / Windsurf / Claude Desktop out of the box.",
    version: "v0.1.0-beta",
  },
  {
    date: "2025-10-15",
    displayDate: "Oct 15",
    monthKey: "2025-10",
    monthLabel: "October 2025",
    category: "industry",
    title: "Malicious MCP package incidents (OWASP tracker)",
    description:
      "First wave of supply-chain attacks against agentic AI tooling — a malicious npm MCP package and the Framelink Figma MCP RCE — signaling the need for runtime isolation, capability gating, and signed identities.",
    source: { label: "OWASP ASI Exploits Tracker" },
  },
  {
    date: "2025-11-01",
    displayDate: "Nov 1",
    monthKey: "2025-11",
    monthLabel: "November 2025",
    category: "whitemagic",
    title: "WhiteMagic v2.0.1 → v2.1.0 — architecture transition ships",
    description:
      "Full rewrite of the memory substrate lands as v2.0.1 on Nov 1. v2.1.0 follows Nov 3 with the new tool-dispatch contract that every later release would build on.",
    version: "v2.0.1 → v2.1.0",
  },
  {
    date: "2025-11-03",
    displayDate: "Nov 3",
    monthKey: "2025-11",
    monthLabel: "November 2025",
    category: "whitemagic",
    title: "First observation of persistent agent-identity coherence",
    description:
      "Running the new v2.1 substrate produced stable, self-consistent agent behavior across sessions — the memory + governance layers held an identity together without being reconstructed from scratch each run. An unexpected emergent property that confirmed the architecture direction and shaped every design decision that followed.",
    pin: true,
  },
  {
    date: "2025-11-14",
    displayDate: "Nov 10–14",
    monthKey: "2025-11",
    monthLabel: "November 2025",
    category: "whitemagic",
    title:
      "WhiteMagic v2.1.1 → v2.1.6 — 5 releases in 4 days, ending on Configuration & Polish",
    description:
      "Rapid iteration burst: async CLI patterns, Pydantic-v2 config system with dot-notation access, rich terminal formatting, embeddings installer with progress bars, Railway deployment optimization, 22-file docs reorganization for public release. 223 tests passing, self-graded A+. The first release where a subscription-tier business model (Starter $10/mo, Pro $30/mo) was designed into the README — the template this consultancy's pricing page now revives.",
    version: "v2.1.1 → v2.1.6",
  },
  {
    date: "2025-12-01",
    displayDate: "Dec 1",
    monthKey: "2025-12",
    monthLabel: "December 2025",
    category: "whitemagic",
    title: "WhiteMagic v5.0.0 — Core Memory Architecture renumbered",
    description:
      "Version reset from the v2.1.x line. The v2 architecture had proven the thesis (MCP + tiered memory works, agents hold identity, business model is viable); v5.0.0 is the first release of the deeper substrate that governance, polyglot runtime, and the eventual 28-Gana MCP compression would all sit on top of.",
    version: "v5.0.0",
  },
  {
    date: "2025-12-09",
    displayDate: "Dec 9",
    monthKey: "2025-12",
    monthLabel: "December 2025",
    category: "industry",
    title: "OWASP Top 10 for LLM Applications v1.1 published",
    description:
      "First formal taxonomy of LLM-specific risks including agentic AI categories (LLM07 Insecure Plugin Design, LLM08 Excessive Agency). Shapes vendor governance roadmaps for 2026. Covers 10 categories: Prompt Injection, Insecure Output Handling, Training Data Poisoning, Model DoS, Supply Chain, Sensitive Info Disclosure, Insecure Plugin Design, Excessive Agency, Overreliance, Model Theft.",
    source: {
      label: "OWASP GenAI Security Project",
      url: "https://genai.owasp.org/2025/12/09/owasp-top-10-for-agentic-applications-the-benchmark-for-agentic-security-in-the-age-of-autonomous-ai/",
    },
    pin: true,
  },
  {
    date: "2025-12-20",
    displayDate: "Dec",
    monthKey: "2025-12",
    monthLabel: "December 2025",
    category: "industry",
    title: "Anthropic donates MCP to the Linux Foundation",
    description:
      "The Agentic AI Foundation (AAIF) forms with Anthropic, Block, OpenAI, Google, Microsoft, AWS, Cloudflare, and Bloomberg as platinum members. Formal announcement follows on March 10, 2026.",
  },

  // ── 2026 Jan ─────────────────────────────────────────────────────────
  {
    date: "2026-01-26",
    displayDate: "Jan 26",
    monthKey: "2026-01",
    monthLabel: "January 2026",
    category: "whitemagic",
    title: "WhiteMagic v5.1.0 — Security hardening",
    description:
      "Security audit pass, dependency updates. The last release before the February acceleration.",
    version: "v5.1.0",
  },

  // ── 2026 Feb — the signature cluster ─────────────────────────────────
  {
    date: "2026-02-04",
    displayDate: "Feb 4",
    monthKey: "2026-02",
    monthLabel: "February 2026",
    category: "whitemagic",
    title: "WhiteMagic v9.0.0 — Polyglot architecture + native MCP",
    description:
      "Rust bindings (whitemagic-rust) for hot paths, Go Mesh for distributed networking, Mojo Accelerator for AI compute, Elixir Supervision for fault tolerance. Native MCP integration for Cursor, Windsurf, Claude Desktop. 87% token-cost reduction via context optimization. Validated to 16K concurrent async operations.",
    version: "v9.0.0",
  },
  {
    date: "2026-02-06",
    displayDate: "Feb 6",
    monthKey: "2026-02",
    monthLabel: "February 2026",
    category: "whitemagic",
    title: "WhiteMagic v11.0.0 — Satkona dual-engine + configurable paths",
    description:
      "Yin (Rust IDF) + Yang (Mojo cosine similarity) pattern scoring with MMR selection. Configurable path system (WM_STATE_ROOT, WM_DB_PATH). Strategy Distillation via holographic clustering.",
    version: "v11.0.0",
  },
  {
    date: "2026-02-07",
    displayDate: "Feb 7",
    monthKey: "2026-02",
    monthLabel: "February 2026",
    category: "whitemagic",
    title:
      "WhiteMagic v11.1.0 — CyberBrain modules (Temporal Scheduler, Salience Arbiter, Mindful Forgetting, Maturity Gates, Bicameral Reasoner)",
    description:
      "Multi-timescale event processing (FAST <10ms / MEDIUM ~1s / SLOW ~60s). Global-Workspace salience routing (urgency × novelty × confidence). Multi-signal memory retention. Gated developmental milestones preventing premature use of advanced capabilities. Left/Right hemisphere reasoning with corpus-callosum cross-critique. 40 regression tests.",
    version: "v11.1.0",
  },
  {
    date: "2026-02-07",
    displayDate: "Feb 7",
    monthKey: "2026-02",
    monthLabel: "February 2026",
    category: "whitemagic",
    title:
      "WhiteMagic v11.2.0 — MandalaOS Synergy: Karma Ledger, Dharma Rules, Circuit Breaker, Gnosis Portal, Harmony Vector",
    description:
      "The signature release. Karma Ledger — append-only cryptographically verifiable audit log tracking declared vs actual side-effects per tool call. Dharma Rules Engine — YAML-driven declarative policy with graduated actions (LOG → TAG → WARN → THROTTLE → BLOCK), three profiles (default/creative/secure), Karmic Trace audit, hot-reload. Circuit Breaker — per-tool CLOSED/OPEN/HALF_OPEN states. Gnosis Portal — unified read-only introspection across all subsystems. Harmony Vector — 7-dimensional real-time health metric with Guna classification. 41 regression tests.",
    version: "v11.2.0",
    gap: "~4 weeks before Microsoft Agent Governance Toolkit v1.0.0",
    pin: true,
  },
  {
    date: "2026-02-07",
    displayDate: "Feb 7",
    monthKey: "2026-02",
    monthLabel: "February 2026",
    category: "whitemagic",
    title: "WhiteMagic v11.3.0 / 11.3.2 — dispatch pipeline refinement",
    description:
      "7-step dispatch pipeline: Circuit Breaker → Maturity Gate → Governor → Gana Routing → Handler → Bridge → Breaker Feedback. 10 new tool handlers. Dharma rules hot-reload via mtime scan. 44 regression tests.",
    version: "v11.3.x",
  },
  {
    date: "2026-02-07",
    displayDate: "Feb 7",
    monthKey: "2026-02",
    monthLabel: "February 2026",
    category: "whitemagic",
    title:
      "WhiteMagic v12.3.0 — Middleware Pipeline, Agent Trust Scores, Explain-This, Mesh Awareness",
    description:
      "Monolithic dispatch refactored into a composable 7-stage middleware chain (input_sanitizer → circuit_breaker → rate_limiter → tool_permissions → maturity_gate → governor → core_router). Per-agent trust tiers (EXEMPLARY/TRUSTED/STANDARD/PROBATIONARY/RESTRICTED) derived from Karma Ledger data. Pre-execution impact preview (SAFE_TO_PROCEED / PROCEED_WITH_CAUTION / BLOCKED). Cross-node mesh peer tracking via Redis. 28-Gana registry (Lunar Mansions) formalized in registry_defs/gana.py. 43 new tests.",
    version: "v12.3.0",
    gap: "~3 weeks before Microsoft AGT v1.0.0 shipped the same architecture",
    pin: true,
  },

  // ── 2026 Mar — industry catches up ───────────────────────────────────
  {
    date: "2026-03-02",
    displayDate: "Mar 2",
    monthKey: "2026-03",
    monthLabel: "March 2026",
    category: "industry",
    title: "Claude memory expanded to free tier + import/export tool",
    description:
      "Anthropic opens memory to all users and ships a cross-AI import flow. The memory feature itself had rolled out through 2025; this is the consolidation move.",
    source: {
      label: "The Verge",
      url: "https://www.theverge.com/ai-artificial-intelligence/887885/anthropic-claude-memory-upgrades-importing",
    },
  },
  {
    date: "2026-03-04",
    displayDate: "Mar 4",
    monthKey: "2026-03",
    monthLabel: "March 2026",
    category: "industry",
    title: "Microsoft Agent Governance Toolkit v1.0.0",
    description:
      "First public release. The architecture is strikingly close to WhiteMagic's Feb 7 shipment: sub-millisecond policy engine, cryptographic agent identities, runtime isolation, circuit breakers, compliance mapping to EU AI Act / HIPAA / SOC2, Ed25519 signing, trust-tiered capability gating.",
    source: {
      label: "github.com/microsoft/agent-governance-toolkit",
      url: "https://github.com/microsoft/agent-governance-toolkit",
    },
    pin: true,
  },
  {
    date: "2026-03-09",
    displayDate: "Mar 9",
    monthKey: "2026-03",
    monthLabel: "March 2026",
    category: "industry",
    title: "MCP 2026 Roadmap published",
    description:
      "Four priority areas: Transport Evolution (stateless Streamable HTTP), Agent Communication, Enterprise Readiness (audit trails, SSO, permissions), Community Process. Anthropic / AAIF.",
    source: {
      label: "blog.modelcontextprotocol.io",
      url: "https://blog.modelcontextprotocol.io/posts/2026-mcp-roadmap/",
    },
    pin: true,
  },
  {
    date: "2026-03-10",
    displayDate: "Mar 10",
    monthKey: "2026-03",
    monthLabel: "March 2026",
    category: "industry",
    title: "Anthropic formally announces MCP donation to AAIF",
    description:
      "Joining founding partners OpenAI, Block, Google, Microsoft, AWS, Cloudflare, Bloomberg. 10,000+ active public MCP servers at announcement.",
  },
  {
    date: "2026-03-15",
    displayDate: "Mar 15",
    monthKey: "2026-03",
    monthLabel: "March 2026",
    category: "industry",
    title: "Microsoft AGT v2.1.0 — Semantic Kernel + Azure AI Foundry",
    description:
      "Framework integrations expand: AWS Bedrock, Google ADK, Azure AI, LangChain, CrewAI, AutoGen, OpenAI Agents.",
  },
  {
    date: "2026-03-26",
    displayDate: "Mar 26",
    monthKey: "2026-03",
    monthLabel: "March 2026",
    category: "industry",
    title: "Microsoft AGT v3.0.0 — Official Microsoft-signed public preview",
    description:
      "The toolkit graduates from experimental to signed releases. ESRP pipelines for PyPI and npm.",
  },

  // ── 2026 Apr ─────────────────────────────────────────────────────────
  {
    date: "2026-04-02",
    displayDate: "Apr 2",
    monthKey: "2026-04",
    monthLabel: "April 2026",
    category: "industry",
    title: "Microsoft publishes Agent Governance Toolkit announcement",
    description:
      "Official Microsoft Open Source blog post: runtime governance for AI agents, covers 10/10 OWASP LLM Top 10 (v1.1, covers agentic AI), 9,500+ tests. The category has crystallized.",
    source: {
      label: "opensource.microsoft.com",
      url: "https://opensource.microsoft.com/blog/2026/04/02/introducing-the-agent-governance-toolkit-open-source-runtime-security-for-ai-agents/",
    },
  },
  {
    date: "2026-04-13",
    displayDate: "Apr 13",
    monthKey: "2026-04",
    monthLabel: "April 2026",
    category: "industry",
    title: "MCP Dev Summit North America 2026",
    description:
      "1,200 attendees at Linux Foundation / AAIF summit in NYC. WorkOS keynote 'Context Is the New Code' names context engineering as the decisive discipline. David Soria Parra addresses context-bloat criticism directly.",
    source: {
      label: "aaif.io",
      url: "https://aaif.io/blog/mcp-is-now-enterprise-infrastructure-everything-that-happened-at-mcp-dev-summit-north-america-2026/",
    },
  },
  {
    date: "2026-04-14",
    displayDate: "Apr 14",
    monthKey: "2026-04",
    monthLabel: "April 2026",
    category: "whitemagic",
    title: "WhiteMagic v21.0.0 — Public release",
    description:
      "Single-commit curated release: 15 public docs, 584 internal docs, 2 private archives; 1.3 GB legacy/ directory archived. Polyglot bridge matrix documented (Production: Rust + Go. Experimental: Koka + Zig. Deferred: Mojo awaiting SDK).",
    version: "v21.0.0",
  },
  {
    date: "2026-04-16",
    displayDate: "Apr 16",
    monthKey: "2026-04",
    monthLabel: "April 2026",
    category: "whitemagic",
    title:
      "WhiteMagic v22.0.0 — 28 PRAT Gana MCP meta-tools, Rust + PyO3, WASM",
    description:
      "Modular install tiers (lite/mcp/cli/api/embeddings/heavy). 28 PRAT Gana compression router formalized as MCP meta-tools — addressing the context-bloat problem the MCP roadmap named weeks earlier. Rust core with PyO3 bindings (memory, search, embeddings, graph, safety). WASM target for browser/edge. Polyglot bridges added: Koka, Mojo, Haskell.",
    version: "v22.0.0",
    gap: "Taxonomy shipped Feb 7; MCP router formalized 5 weeks after MCP roadmap named context bloat a priority",
  },
  {
    date: "2026-04-17",
    displayDate: "Apr 17",
    monthKey: "2026-04",
    monthLabel: "April 2026",
    category: "whitemagic",
    title: "WhiteMagic strategic pivot: from product to services",
    description:
      "Honest self-assessment. The research lab did its job; the sellable artifact is the engineer who built it. Decision to launch a consultancy around the proven techniques.",
  },
  {
    date: "2026-04-15",
    displayDate: "Apr 15",
    monthKey: "2026-04",
    monthLabel: "April 2026",
    category: "industry",
    title: "Cloudflare Project Think shipped",
    description:
      "Cloudflare's persistent agent identity + wake-on-message runtime ships, edge-deployed by default. The agent-OS framing crystallizes at hyperscaler scale. WhiteMagic's persistent-identity work (first observed Nov 3 2025) shipped in private code Feb 2026 and made public mid-April; Cloudflare's offering is the contemporary first-party equivalent.",
    source: { label: "blog.cloudflare.com" },
  },
  {
    date: "2026-04-18",
    displayDate: "Apr 18",
    monthKey: "2026-04",
    monthLabel: "April 2026",
    category: "whitemagic",
    title: "WhiteMagic Labs consultancy launches",
    description:
      "This site ships. Services: Private AI Deployment, Agent Governance, MCP Engineering. Open to first engagements.",
    pin: true,
  },
  {
    date: "2026-04-23",
    displayDate: "Apr 23",
    monthKey: "2026-04",
    monthLabel: "April 2026",
    category: "industry",
    title:
      "Anthropic Claude Managed Agents Memory — public beta with audit log + rollback",
    description:
      "Anthropic ships filesystem-mounted persistent memory for Claude with a session-level audit log and rollback. Customers: Netflix, Rakuten (97% fewer first-pass errors at 27% lower cost), Wisedocs, Ando. The audit-log + rollback pattern is structurally adjacent to the Karma Ledger spec articulated 11 months earlier in the May 26 2025 design conversation; neither caused the other, but the prior-art trail is now documented.",
    source: { label: "anthropic.com / The Verge" },
    gap: "Karma Ledger spec articulated May 26 2025 — 11 months ahead of Anthropic's structurally similar audit-log + rollback shipment",
    pin: true,
  },
  {
    date: "2026-04-27",
    displayDate: "Apr 27",
    monthKey: "2026-04",
    monthLabel: "April 2026",
    category: "whitemagic",
    title:
      "Prior-art verification + competitive-landscape audit published",
    description:
      "Cross-referenced WhiteMagic's design chronology (CODEX OpenAI archive, Grok export, public X archive, Git history, public PyPI/npm release timestamps) against the verified competitor timeline. Confirmed: the Karma Ledger spec (May 26 2025) predates Anthropic Claude Memory's audit log + rollback (Apr 23 2026) by 11 months in concept, and Microsoft AGT v1.0.0 (Mar 4 2026) by ~9 months. Bicameral reasoning, voice audit, foresight engine, and the 28-Gana cultural mapping remain — as of Apr 27 — without publicly-shipping equivalents at any major lab. Documentation drift checks 9/9 green.",
  },

  // ── 2026 Apr 28–30 — grant pipeline sprint ───────────────────────────
  {
    date: "2026-04-28",
    displayDate: "Apr 28",
    monthKey: "2026-04",
    monthLabel: "April 2026",
    category: "whitemagic",
    title: "Grant pipeline research sprint — 6 applications drafted",
    description:
      "Completed comprehensive grant strategy: 14+ documents covering strategy, execution plan, application templates, content library, rubric audits, tier lists, and federal playbook. Applications drafted for Manifund ($25K, Joel Becker), LTFF ($35K), Foresight ($100K), SFF ($150K), and Schmidt Sciences ($600K). Competitive landscape verified against external sources.",
    pin: true,
  },
  {
    date: "2026-04-29",
    displayDate: "Apr 29",
    monthKey: "2026-04",
    monthLabel: "April 2026",
    category: "industry",
    title: "CODEX synthesis — 12 research threads integrated into 3 core applications",
    description:
      "Three independent review teams converged: code audit (21 stubs → 0), grant strategy review (content library, execution focus, cross-reference discipline), and CODEX extraction (334 indexed files, 12 grant-fundable research threads). Core insight: the 12 threads strengthen 3 applications, not 12 separate grants.",
  },
  {
    date: "2026-04-30",
    displayDate: "Apr 30",
    monthKey: "2026-04",
    monthLabel: "April 2026",
    category: "whitemagic",
    title: "Growth tiers + rubric audit + A+ upgrade guide completed",
    description:
      "6-tier organizational growth model (Legal Formation → Deep Tech R&D) with entry/exit criteria, decision gates, failure modes, and honest probability estimates. Grant rubric audit comparing application templates against actual funder evaluation criteria — identified 21 gaps. A- to A+ upgrade guide with 14-day action plan.",
  },
  {
    date: "2026-04-30",
    displayDate: "Apr 30",
    monthKey: "2026-04",
    monthLabel: "April 2026",
    category: "industry",
    title: "Foresight Institute AI Nodes page goes password-protected",
    description:
      "Foresight Institute restricts public access to AI Nodes application page ahead of next monthly deadline (May 31). WhiteMagic application prepared.",
    source: { label: "foresight.org" },
  },

  // ── 2026 May — audit & launch ─────────────────────────────────────────
  {
    date: "2026-05-01",
    displayDate: "May 1",
    monthKey: "2026-05",
    monthLabel: "May 2026",
    category: "whitemagic",
    title: "Comprehensive project audit + polyglot truth-table + site refresh",
    description:
      `Independent audit of full project: ${WM_FACTS.testsPassing} tests pass, 9/9 doc drift checks green, honest polyglot status published (Rust + Go mesh = production; Zig/Koka/Mojo/Haskell/Elixir/Julia = experimental). Site updated: test counts corrected, grants page expanded with Schmidt Sciences + federal track, timeline extended through May 2026. Strategy: file LLC after first Manifund win.`,
    pin: true,
  },
  {
    date: "2026-05-14",
    displayDate: "May 14",
    monthKey: "2026-05",
    monthLabel: "May 2026",
    category: "whitemagic",
    title: "WhiteMagic field-map synthesis — governance and evidence layer",
    description:
      "Cross-referenced recent MCP, A2A, OpenTelemetry, x402, agent SDK, and regulatory developments against internal strategy. Conclusion: WhiteMagic's strongest public position is protocol-compatible governance and observability infrastructure — policy, side-effect audit, memory continuity, and evidence packaging — not memory-as-a-service or a payments-first startup.",
    pin: true,
  },

  // ── Upcoming ─────────────────────────────────────────────────────────
  {
    date: "2026-06-01",
    displayDate: "Jun",
    monthKey: "2026-06",
    monthLabel: "June 2026 (upcoming)",
    category: "regulatory",
    title: "Colorado AI Act becomes enforceable",
    description:
      "First US state-level enforceable AI regulation with governance and disclosure requirements.",
  },
  {
    date: "2026-06-15",
    displayDate: "Jun",
    monthKey: "2026-06",
    monthLabel: "June 2026 (upcoming)",
    category: "industry",
    title: "Next major MCP specification release (tentative)",
    description:
      "Targets the four priority areas from the 2026 roadmap. Stateless Streamable HTTP and Enterprise Readiness extensions expected.",
  },
  {
    date: "2026-08-02",
    displayDate: "Aug 2",
    monthKey: "2026-08",
    monthLabel: "August 2026 (upcoming)",
    category: "regulatory",
    title: "EU AI Act Article 14 high-risk obligations take effect",
    description:
      "Article 14 (human oversight) and related high-risk AI system requirements become enforceable across the EU. Organizations deploying autonomous agents in regulated domains must demonstrate audit trails, policy enforcement, and operator oversight — exactly the features WhiteMagic shipped on Feb 7, 2026. Also applies to Annex III high-risk systems.",
    source: { label: "artificialintelligenceact.eu/article/14" },
  },
];

/** The full span of months to render on the horizontal axis, even empty ones. */
export function monthRange(): { key: string; label: string; short: string }[] {
  const out: { key: string; label: string; short: string }[] = [];
  const start = new Date(2024, 10, 1); // Nov 2024
  const end = new Date(2027, 1, 1); // Feb 2027 — extends the X-axis past the last event so the singularity curve has visible runway into the future
  const MONTHS = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
  ];
  const LONG = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
  ];
  const cur = new Date(start);
  while (cur <= end) {
    const y = cur.getFullYear();
    const m = cur.getMonth();
    const yy = String(y).slice(2);
    out.push({
      key: `${y}-${String(m + 1).padStart(2, "0")}`,
      short: `${MONTHS[m]} '${yy}`,
      label: `${LONG[m]} ${y}`,
    });
    cur.setMonth(cur.getMonth() + 1);
  }
  return out;
}
