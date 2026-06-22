# WhiteMagic Labs — Information Architecture v1.0.0

**Date:** 2026-05-15
**Status:** Approved — Freeze
**Scope:** Public-facing site under `whitemagic.dev`

---

## 1. URL Scheme

| Path | Purpose | Type |
|------|---------|------|
| `/` | Homepage — platform overview, CTAs | Static page |
| `/about` | Company, team, mission | Static page |
| `/services/` | Service index | Static page |
| `/services/mcp-engineering/` | MCP engineering service detail | Static page |
| `/services/agent-governance/` | Agent governance service detail | Static page |
| `/services/private-ai-deployment/` | Private AI deployment service detail | Static page |
| `/essays/` | Essay domain index (4-domain overview) | Static page |
| `/essays/intelligence/` | Intelligence essays — AI architecture, agent design | Static page |
| `/essays/horizons/` | Horizons essays — emerging tech frontiers | Static page |
| `/essays/worldbuilding/` | Worldbuilding essays — civilizational design, SFW2 | Static page |
| `/essays/philosophy/` | Philosophy essays — ethics, governance, epistemic rigor | Static page |
| `/essays/<domain>/<slug>/` | Individual essay — MDX content | SSG |
| `/writing/` | Technical writing (short-form, cross-domain) | Static page |
| `/research/` | Research and evidence hub | Static page |
| `/librarian/` | Librarian chat interface | Static page |
| `/ladder/` | Capability ladder | Static page |
| `/economy/` | Agent economy overview | Static page |
| `/grants/` | Grant programs and applications | Static page |
| `/pricing/` | Pricing and plans | Static page |
| `/open-source/` | Open-source projects and community | Static page |
| `/timeline/` | Interactive company/product timeline | Static page |
| `/work/` | Work / career opportunities | Static page |
| `/contact/` | Contact form | Static page |
| `/zh/` | Chinese language homepage | Static page |
| `/admin/` | Admin dashboard (authenticated) | Dynamic |

### API Routes

| Path | Purpose |
|------|---------|
| `/api/librarian/chat` | Librarian chat endpoint |
| `/api/librarian/karma` | Karma ledger query |
| `/api/contact` | Contact form submission |
| `/api/well-known/ai-agent-policy` | AI agent policy (A2A protocol) |
| `/api/well-known/agent` | Agent discovery (A2A protocol) |
| `/api/well-known/agent-economy` | Agent economy declaration |

---

## 2. Redirect Map

| Old Path | New Path | Type |
|----------|----------|------|
| N/A | N/A | No legacy redirects needed — clean launch |

*Note: Vaya Vida site was a separate domain. No URL migration required.*

---

## 3. Navigation Structure

### Primary Nav
- **Platform** → `/` (homepage sections: features, services)
- **Essays** → `/essays/` (four-domain index)
- **Research** → `/research/`
- **Librarian** → `/librarian/`
- **Pricing** → `/pricing/`

### Footer
- About, Contact, Open Source, Timeline, Economy, Grants, Writing, Work

---

## 4. Epistemic Tagging

Every essay page renders an epistemic badge from the Vaya Vida confidence ladder:

| Tag | Color | Meaning |
|-----|-------|---------|
| [Proven] | Green | External validation exists |
| [Promising] | Blue | Strong signals, not settled |
| [Contested] | Yellow | Legitimate debate in literature |
| [Speculative] | Red | Theoretically possible, no demo |
| [Mythopoetic] | Purple | Cultural-symbolic frame |

Tags are defined in `apps/site/lib/design-tokens.ts` and rendered by `apps/site/components/essay/EpistemicBadge.tsx`.

---

## 5. Multilingual Support

- English: All routes (canonical)
- Chinese: `/zh/` homepage + i18n infrastructure via `next-intl` (planned — not yet implemented)
- Spanish, Japanese, Korean, French: Planned; translation pipeline TBD

---

## 6. Future Aria Pages

URL scheme reserved for Aria interactive surfaces (Phase 4):

| Path | Purpose |
|------|---------|
| `/ask` | Aria Q&A with epistemic tags and source links |
| `/oracle` | Structured resonance-based responses |
| `/wander` | Serendipitous discovery interface |
| `/signals` | Weekly signal scan feed |
| `/signals/feed.xml` | RSS feed for signal scans |
