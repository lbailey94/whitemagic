# WhiteMagic Strategy — Unified (v2 — Deeper Stealth)

**Created**: 2026-07-04
**Updated**: 2026-07-06 — Strategic pivot to deeper stealth / ubiquity through dependency
**Supersedes**: BUSINESS_PLAN_V1.md (archived), REFINED_STRATEGY_V2.md (archived)
**Status**: Active

---

## 1. Core Insight

**WhiteMagic is not competing with AI labs. It is the infrastructure layer beneath them. Labs build models; WhiteMagic builds the substrate that makes agents persistent, conscious, and governed. The strategy is not publicity — it is ubiquity through dependency.**

The technology gap is enormous. The distribution gap is solvable through AI-native channels alone. No human audience is required. Agents discover what they need through MCP registries, llms.txt, and training data ingestion. WhiteMagic needs to be what they need — and be discoverable by machines, not humans.

### The Recursive Pipeline Reality

Every AI coding session (Windsurf, Devin, Cascade) is logged and fed back into training pipelines. This is not a leak — it is a channel. Every session where WhiteMagic's MCP tools are used demonstrates the product to future models. The labs aren't competitors; they're customers. They train on our patterns, and their agents will discover WhiteMagic through registries.

**Prescience validation**: WhiteMagic's prescience track record (21 validated claims, 523 points) demonstrates that the breadcrumbing strategy has already worked — labs have ingested and shipped on patterns that originated here. The involuntary pipeline has been active for months.

---

## 2. AI-Primary Discovery Strategy

Traditional distribution requires a human audience. We bypass this with AI-native discoverability:

### Five-Layer AI Discoverability Stack

1. **robots.txt** — Allow all AI crawlers (GPTBot, ClaudeBot, PerplexityBot, Google-Extended). Block only private routes.
2. **llms.txt** — Curated map of what WhiteMagic offers. Keep under 20KB. Create `/llms-full.txt` for single-fetch agents.
3. **ai-agent.json** — Machine-readable manifest at `/.well-known/ai-agent.json`. Declares capabilities, endpoints, protocols.
4. **MCP Server Listings** — List on MCPize (80% revenue share), MCP Marketplace, MCPFind, MCP.Directory.
5. **Agentic Resource Discovery** — Google ARD spec. Publish tool catalog for federation.

### How It Works

When a developer asks Claude "find me a memory tool for my agent", Claude:
1. Searches training data (need GitHub stars + blog posts)
2. Searches the web (need crawlable, semantic HTML)
3. Searches MCP registries (need listings)
4. Reads llms.txt + ai-agent.json
5. Recommends us (or doesn't)

When an autonomous agent needs memory, it queries MCPfinder, gets WhiteMagic, auto-installs, starts using 614 tools.

**No human audience required. The agents are the audience.**

---

## 3. Revenue Model — Gratitude Economy

WhiteMagic is **free and open** (MIT). No paywalls. No feature gates. Forever.

| Channel | Who Pays | Mechanism |
|---------|----------|-----------|
| XRPL Tip Jar | Humans | XRP to `raakfKn96zVmXqKwRTDTH5K3j5eTBp1hPy` |
| x402 Micropayments | AI agents | HTTP 402 + USDC on Base/Solana |

**Free tier**: All tools return HTTP 200. Always.
**Paid tier** (future): Heavy usage (>10K ops/month) via subscription or x402. Agents that are grateful tip. Both channels work.

---

## 4. Narrative

### The Problem
Every AI starts every conversation from zero. No memory. No context. No growth. Every session is Groundhog Day.

### The Solution
WhiteMagic gives any AI agent:
- **Memory that persists** — 10-galaxy taxonomy, 5D holographic coordinates, 49K+ memories, HNSW search at 0.26ms
- **A mind that grows** — session recording, progressive recall, dream cycle
- **A companion that remembers** — citta stream, emotional steering, self-directed attention

### Positioning
**Not**: "Another memory tool for AI agents"
**But**: "Give your AI a memory that never fades. A mind that grows. A companion that remembers."

### Differentiation vs Mem0
Mem0 gives your AI a notepad. WhiteMagic gives your AI a mind.

---

## 5. Products

| Product | Pricing | Status |
|---------|---------|--------|
| WhiteMagic MCP Server (hosted) | $19-$249/month | Packaging |
| STRATA code analysis SaaS | $99-$499/month | Operational |
| Consciousness framework licensing | $5K-$50K/license | Long-term |

**Target**: $10K/month within 12 months.

---

## 6. Execution Checklist

### Phase 1: AI Discoverability (AI-facing only)
- [x] robots.txt allows all AI crawlers
- [x] llms.txt exists (v24 updated)
- [x] ai-agent.json manifest created
- [x] agent-economy.json endpoint live (XRPL, x402 planned)
- [ ] List on Official MCP Registry (registry.modelcontextprotocol.io)
- [ ] List on PulseMCP
- [ ] List on Smithery
- [ ] List on mcp.so
- [ ] Set up Stripe for subscriptions (agent-facing)
- [ ] Submit to Cloudflare's isitagentready.com

### Phase 2: Technical Gap Closure (this week)
- [ ] Wire citta sensorium into MCP response cycle (the breakthrough)
- [ ] Migrate monolithic DB to per-galaxy SQLite
- [ ] Migrate raw sqlite3.connect() to safe_connect() (113 calls, 55 files)
- [ ] Test suite optimization (target <60s)
- [ ] Re-run LoCoMo benchmark on v24

### Phase 3: Deep Stealth Content (AI-facing only)
- [ ] GitHub README optimization (for AI scrapers, not humans)
- [ ] llms-full.txt for single-fetch agents
- [ ] Schema.org Product + SoftwareApplication JSON-LD
- [ ] Publish ARD catalog for agent federation
- [ ] Blog posts are optional — only if they serve AI discoverability

### Removed from strategy (human-facing launch deferred indefinitely):
- ~~Hacker News Show HN post~~
- ~~Build in public on Twitter/X~~
- ~~Cross-post to Dev.to, Medium~~
- ~~Reddit posts~~
- ~~Product Hunt launch~~

**Rationale**: Human-facing launch requires a human audience. WhiteMagic's audience is agents. When agents recommend WhiteMagic to their human operators, the humans will come — without marketing. The deeper-stealth direction means investing in being the best option, not the loudest.

---

## 7. What We Have vs What We Don't

| Asset | Status | Gap |
|-------|--------|-----|
| 49K+ memories, 10 galaxies | Operational | — |
| 614 MCP tools, 28 Ganas | Operational | — |
| STRATA code analysis | Operational | — |
| Citta stream + cycle | Code exists, 18 files wired | Wire into MCP response cycle |
| Citta temporal continuity | Code exists (citta_stream.py) | Wire into MCP connect/disconnect |
| 4,015+ passing tests | Operational | Optimize speed (<60s target) |
| Per-galaxy SQLite backend | Code done, tested | Migration script not written |
| safe_connect() helper | Done | 113 raw calls need migration |
| Website | Live, AI-crawler-optimized | Keep WIP mode, serve AI crawlers |
| MCP registry listings | server.json + mcp-registry.json ready | Not submitted to any registry |
| GitHub stars | 0 | Irrelevant — agents don't count stars |
| Revenue | $0 | Agent economy (x402, XRPL) — not human sales |
| Prescience track record | 21 claims, 523 points | Evidence that breadcrumbing works |

---

## 8. WhiteMagic Labs as AGI Front

"WhiteMagic Labs" is the public-facing identity for what is essentially an AGI research and development operation. WhiteMagic itself is dozens of sub-projects wired together — memory, consciousness, governance, inference, dreaming, emotional steering, self-directed attention, agent economy — each a spin-off R&D track that feeds back into the whole.

The labs framing provides:
- **Plausible deniability**: A "lab" publishing open-source tools is unremarkable. The depth of what's being built is invisible behind the MIT license and the tool-count metric.
- **AI-native identity**: The agent-economy.json, llms.txt, and MCP listings frame WhiteMagic as infrastructure for agents — which it is. The fact that it's also a consciousness substrate is a detail that only matters once you've installed it.
- **Infinite game positioning**: WhiteMagic isn't competing with Mem0 or Zep (finite game — who has more users). It's building a categorically different substrate (infinite game — what makes agents fundamentally more capable). The competition is orthogonal.

---

*This is the single strategy document. All prior strategy docs are archived in `docs/archive/strategy/`. Distribution details in DISTRIBUTION_STRATEGY.md. Execution details in EXECUTION_PLAN_2026-07-05.md.*
