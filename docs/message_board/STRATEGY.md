# WhiteMagic Strategy — Unified

**Created**: 2026-07-04
**Supersedes**: BUSINESS_PLAN_V1.md (archived), REFINED_STRATEGY_V2.md (archived)
**Status**: Active

---

## 1. Core Insight

**The technology gap between WhiteMagic and competitors is enormous. The distribution gap is the entire problem.**

Mem0 raised $24M to build a simpler version of what we already have. They have 90K developers because they invested in distribution. We have zero because we invested in technology. The fix is not more technology — it's telling the story.

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

### Phase 1: AI Discoverability (3 days)
- [x] robots.txt allows all AI crawlers
- [x] llms.txt exists (needs v24 update)
- [x] ai-agent.json manifest created
- [ ] List on MCPize
- [ ] List on MCP Marketplace
- [ ] List on MCPFind
- [ ] Set up Stripe for subscriptions
- [ ] Submit to Cloudflare's isitagentready.com

### Phase 2: Content (1 week)
- [ ] Write "I built a cognitive OS on a $200 laptop" (HN launch post)
- [ ] Write "Why AI needs a subconscious (the Dream Cycle)"
- [ ] Write "Citta: giving AI continuous consciousness via MCP"
- [ ] GitHub README optimization

### Phase 3: Launch
- [ ] Hacker News Show HN post
- [ ] Build in public on Twitter/X
- [ ] Cross-post to Dev.to, Medium

---

## 7. What We Have vs What We Don't

| Asset | Status | Gap |
|-------|--------|-----|
| 49K+ memories, 10 galaxies | Operational | — |
| 614 MCP tools, 28 Ganas | Operational | — |
| STRATA code analysis | Operational | — |
| Citta consciousness | Prototype | Complete P1 tests (done) |
| 4,190+ passing tests | Operational | — |
| Website | Live, needs polish | Finish remaining pages |
| GitHub stars | 0 | Fixable via HN + MCP listings |
| Revenue | $0 | Fixable via MCP listing + Stripe |

---

*This is the single strategy document. All prior strategy docs are archived in `docs/archive/strategy/`.*
