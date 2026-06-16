# AGENTS.md — whitemagic.dev

**Version**: 1.0.0
**Last Updated**: 2026-06-16
**Audience**: AI agents (LLM-based, agentic, or human collaborators) contributing to or extending the WhiteMagic Labs public site.

---

## 1. What this site is

This is the **public marketing + agent-discovery surface** for WhiteMagic Labs. It runs on **Next.js 14 (App Router)** and is deployed to **Vercel Hobby**.

Two distinct audiences:

1. **Human visitors** — designers, founders, technical leads, researchers. Marketing pages, prescience track record, research, library, fund/grants.
2. **AI agents and crawlers** — LLM-powered tools, MCP clients, A2A peers. The site is heavily optimized for machine-readable discovery.

The site is **not** the WhiteMagic core runtime. The core lives at `~/Desktop/WHITEMAGIC/core/` and is the Python package. The site mirrors the core's public surface (counts, capabilities, prescience claims) and exposes discovery endpoints.

---

## 2. Hard constraints (read before editing)

These are non-negotiable. Violating any of them risks the site being terminated or the work needing to be redone.

### Vercel Hobby plan rules

- **No commercial activity.** No dollar prices, no Stripe price displays, no "buy now" or "subscribe" CTAs. Frame services as "research collaboration" or "discovery call" only.
- **No high-traffic endpoints.** The site must not become a hot egress path. Static or low-cost API endpoints only.
- **Self-host anything expensive.** The MCP server, x402 payment rails, Discord bot, and high-traffic API endpoints should run on Hetzner CCX23, not Vercel.

The `lib/facts.ts` module is the single source of truth for the canonical numbers. Update it last, after every core change. Use `WM_FACTS.callableTools` etc. — never hardcode numbers in page components.

### Site architecture rules

- **One source of truth for facts**: `lib/facts.ts` → re-exported as `WM_FACTS` and `WM_FACT_TEXT`.
- **One source of truth for the tool manifest**: `app/api/manifest/route.ts` (dynamic) AND `public/api/manifest.json` (static). Both must agree. Regenerate the static one with `python core/scripts/generate_manifest_json.py` from the core repo, then copy it over.
- **No emoji** unless explicitly approved.
- **No new dependencies** without an `AGENTS.md` note explaining the cost (Vercel Hobby has bundle size limits).

---

## 3. Discovery surfaces (always live, machine-readable)

The site publishes these endpoints for AI agents. They are the highest-leverage surfaces and should remain stable, versioned, and well-documented.

| Endpoint | Purpose | Format | Cache |
|---|---|---|---|
| `/.well-known/agent.json` | A2A Protocol v1.2 Agent Card | JSON | 5 min |
| `/.well-known/agent-economy.json` | Directory entry, payment rails, services | JSON | 5 min |
| `/.well-known/ai-agent-policy` | Machine-readable ToS for agents | text/plain | static |
| `/api/manifest.json` | Canonical tool manifest (490 tools, 28 Ganas) | JSON | 5 min (static) |
| `/api/prescience.json` | 21 validated forecast claims | JSON | static |
| `/api/sangha.json` | Collective memory + pattern federation snapshot | JSON | daily |
| `/api/zodiac.json` | 12 cores + cross-core workflows catalog | JSON | weekly |
| `/llms.txt` | Short LLM context (markdown index) | text | weekly |
| `/llms-full.txt` | Comprehensive LLM context (the canonical everything file) | text | weekly |
| `/sitemap.xml` | XML sitemap (all human + agent pages) | XML | runtime |
| `/robots.txt` | Crawler policy | text | static |

Any new public agent surface **must** be added to `app/sitemap.ts` and ideally to `/llms-full.txt` so agents can find it.

---

## 4. The facts module

`lib/facts.ts` is the canonical numbers store. Single source of truth.

```ts
export const WM_FACTS = {
  version: "22.2.0",
  verifiedDate: "June 16, 2026",
  linesShort: "178K",
  linesLong: "178,000",
  callableTools: "490",
  dispatchTools: "462",
  ganaTools: "28",
  testsPassing: "2478",
  testsSkipped: "0",
  testsFailing: "0",
  languages: "8",
} as const;

export const WM_FACT_TEXT = {
  toolSurface: `${WM_FACTS.callableTools} callable tools (${WM_FACTS.dispatchTools} dispatch + ${WM_FACTS.ganaTools} PRAT Gana meta-tools)`,
  testSuite: `${WM_FACTS.testsPassing} passing tests, ${WM_FACTS.testsSkipped} skipped, ${WM_FACTS.testsFailing} failures`,
  shortPassingSuite: `${WM_FACTS.testsPassing} passing tests with zero failures`,
  mcpSurface: `${WM_FACTS.callableTools} callable tools across ${WM_FACTS.ganaTools} Gana meta-tools`,
} as const;
```

**Update protocol**: when the core adds or removes a tool, the doc-drift check in `core/scripts/check_doc_drift.py` will report mismatches. Update `lib/facts.ts` in the same commit as the corresponding core change, and update `AI_PRIMARY.md`, `AGENTS.md` (the core one), and `SYSTEM_MAP.md` to match. Run `python core/scripts/check_doc_drift.py` from the core repo root to verify.

---

## 5. Service and product data

`lib/data/services.ts` defines the three consulting service tracks (Private AI, Agent Governance, MCP Engineering). These are exposed via:
- `app/services/page.tsx` (index)
- `app/services/<slug>/page.tsx` (one per service)
- `app/api/well-known/agent-economy/route.ts` (machine-readable)
- `components/librarian/ToolCards.tsx` (librarian chat cards)
- `lib/jsonld.ts` → `serviceLd()` (JSON-LD service nodes)

The `engagementType` field replaces the old `startingPrice` field. Values are currently `"Research collaboration"`. The data is also used by the librarian's `get_pricing_tier` tool, which can answer pricing questions in chat if `PRICING_TIERS` is configured (see `lib/data/pricing.ts`).

**Never add a `priceHint` or dollar amount to a public surface.** That's a Vercel Hobby ToS violation.

---

## 6. The custom 404 page

`app/not-found.tsx` is the canonical 404 page. It links to `/llms.txt` and the A2A Agent Card, so an agent that lands on a missing page can recover into discovery. Update it whenever a new high-value agent surface ships.

---

## 7. The home page Proof section

`app/page.tsx` (the home page) is the canonical "first impression" page. Its `proof` section uses `WM_FACT_TEXT.toolSurface` and `WM_FACT_TEXT.shortPassingSuite` to surface the numbers — never hardcode them in the JSX.

The home page service cards use `<ServiceCard>` from `components/ServiceCard.tsx`. The component falls back to `"Research collaboration"` when no `priceHint` is provided — **do not** add a `priceHint` back.

---

## 8. The MCP server, the librarian, and the site

- **MCP server** (`/mcp`): planned, not yet live. When it ships, the site will proxy `https://whitemagic.dev/mcp` to the Hetzner-hosted MCP server (via Cloudflare Tunnel or similar).
- **Librarian chat** (`/api/librarian/chat`): live, runs on Vercel Hobby. Budget-capped, Dharma-governed. It can answer questions about WhiteMagic Labs. Its tools live in `lib/librarian/tools.ts` and persona in `lib/librarian/persona.ts`.
- **Aria**: the assistant on the home page, runs in-browser. Code in `components/aria/`.

The site is **not** the source of truth for the core system. Always cross-check counts, capabilities, and prescience claims against `core/` before updating the site.

---

## 9. Build, test, and deploy

```bash
# Install
cd ~/Desktop/WHITEMAGIC-aux/site/whitemagic-site
npm install

# Type check
npx tsc --noEmit

# Local dev
npm run dev

# Production build
npm run build

# Deploy (auto-deploys to Vercel on push to main)
git push origin main
```

Vercel auto-deploys from `main`. The build takes ~2-3 min. Vercel Hobby has a 100 GB/month egress budget — check the dashboard if you make a change that could spike traffic.

---

## 10. Common pitfalls

1. **Updating the home page proof section with hardcoded numbers** — use `WM_FACT_TEXT.toolSurface` instead.
2. **Adding a `priceHint` to a service card** — Vercel Hobby ToS violation.
3. **Updating `lib/facts.ts` without updating the core repo docs** — the doc-drift check will fail.
4. **Adding a new service page without adding to `lib/data/services.ts`** — the librarian will not know about it.
5. **Forgetting to add a new endpoint to `app/sitemap.ts`** — agents won't find it.

---

## 11. Contact and ownership

- **Repository**: `github.com/lbailey94/whitemagic-site-private` (private)
- **Owner**: Lucas Bailey, WhiteMagic Labs
- **Contact**: whitemagicdev@proton.me
- **Core repo**: `~/Desktop/WHITEMAGIC/` (private; canonical for counts, capabilities, claims)
- **License**: MIT (the site source is MIT, the WhiteMagic core is also MIT)

---

*This document is a living artifact. Update it when conventions change.*
