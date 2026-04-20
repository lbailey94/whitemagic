# Session State — WhiteMagic Labs Site + Librarian

**Last updated**: 2026-04-19, late session
**Purpose**: Fast-pickup doc. Read this first when returning.
**Update protocol**: Replace the "Where we are" and "What to do next" sections
each session. Preserve the "Decisions log" and append to it.

---

## TL;DR where we are

- `whitemagic.dev` consultancy site is built and running locally at
  `http://localhost:3000`. Not yet deployed publicly.
- The site ships with a **tool-using Librarian** (Phase L.2 complete) —
  site-wide floating bubble (⌘K), rich inline cards for tool results,
  public Karma ledger visible on `/admin`.
- Everything runs in **mock mode** until OpenRouter + Upstash keys land.
  The tool-execution pipeline is fully wired; swapping mocks for real
  calls is a three-env-var change.
- Infrastructure decision: **planning for Hetzner** (not Vercel). See
  `@docs/architecture/INFRASTRUCTURE_DECISION.md`. Deploy walkthrough at
  `@docs/deploy/HETZNER_DEPLOY.md`.

---

## Repo layout (as of this session)

```
/home/lucas/Desktop/
├── WHITEMAGIC/                      # canonical monorepo (this repo)
│   ├── apps/
│   │   ├── README.md
│   │   ├── site/                    # synced via subtree from whitemagic-site/
│   │   ├── SCOPING_BROWSER_FIRST.md
│   │   └── SCOPING_BROWSER_FIRST_DECIDED.md
│   ├── core/                        # WhiteMagic platform (Rust + Python + polyglot)
│   ├── docs/
│   │   ├── SESSION_STATE.md         ← this doc
│   │   ├── ROADMAP.md
│   │   ├── architecture/
│   │   │   ├── MONOREPO_VS_MULTIREPO.md
│   │   │   └── INFRASTRUCTURE_DECISION.md
│   │   └── deploy/
│   │       └── HETZNER_DEPLOY.md
│   └── grimoire/                    # conceptual docs (private)
│
└── whitemagic-site/                 # standalone repo, fast dev loop
                                     # subtree-sync into WHITEMAGIC/apps/site/
                                     # on every Librarian-touching commit
```

**Sync protocol**: Work in `whitemagic-site/` for fast iteration; after each
commit, `cd /home/lucas/Desktop/WHITEMAGIC && git subtree pull --prefix=apps/site
/home/lucas/Desktop/whitemagic-site main --squash`. Recurring `.gitignore`
conflict is resolved (both repos now gitignore `tsconfig.tsbuildinfo`).

---

## What's built and working

### Site — `apps/site/` (Next.js 15 App Router)

| Route | Purpose | State |
|---|---|---|
| `/` | Homepage with matrix rain, hero, services preview | Live (mock copy) |
| `/services` | Three consulting tracks | Live |
| `/services/{private-ai-deployment,agent-governance,mcp-engineering}` | Per-service pages | Live |
| `/pricing` | Three-tier pricing + FAQ | Live |
| `/timeline` | 40+ entries, prescience gap badges | Live |
| `/open-source` | OSS components + licenses | Live |
| `/about`, `/writing`, `/work`, `/contact` | Standard pages | Live (thin content) |
| `/librarian` | Full-page Librarian chat | **Working end-to-end in mock mode** |
| `/admin` | Budget + karma ledger + dharma rules | Working |

### Librarian — Phase L.2 complete

Full request pipeline:

```
kill switch → dharma input check → rate limit → monthly budget
  → LLM round 1 → [if tool_calls: execute + record karma + loop] × ≤3
  → final text stream → record spend
```

- **6 tools**: `get_service_detail`, `get_pricing_tier`,
  `get_platform_capability`, `search_timeline`,
  `request_office_hours_booking`, `submit_contact_request`.
- **10 rich cards** for tool results (`@apps/site/components/librarian/ToolCards.tsx`).
- **Site-wide floating bubble** with ⌘K shortcut, session persistence,
  page-context awareness. Mounted in `@apps/site/app/layout.tsx`.
- **Public Karma ledger** at `/admin` — every tool call with tool name,
  args preview, result kind, duration, session fingerprint hash.

### Core (WhiteMagic platform)

Unchanged this session. Last public release: v22.0.0 (April 16, 2026). Still
in the public `whitemagic-ai/whitemagic` GitHub repo (frozen; new work goes
into the private monorepo — see `@docs/architecture/INFRASTRUCTURE_DECISION.md`
for the repo strategy context).

---

## Open decisions / blockers

### Needed from Lucas (external, not code)

1. **Hetzner VPS readiness** — confirm SSH access, domain pointed via Cloudflare.
   Walkthrough: `@docs/deploy/HETZNER_DEPLOY.md`.
2. **OpenRouter API key** — create at [openrouter.ai](https://openrouter.ai),
   set as `OPENROUTER_API_KEY` on the Hetzner box (not Vercel — see infra doc).
3. **Upstash Redis REST credentials** — free tier at [upstash.com](https://upstash.com),
   gives `UPSTASH_REDIS_REST_URL` + `UPSTASH_REDIS_REST_TOKEN`. Global KV.
4. **Stripe payment links** — create two for Office Hours ($250) and
   Architecture Review ($2,500). Set as `NEXT_PUBLIC_STRIPE_OFFICE_HOURS_URL` +
   `NEXT_PUBLIC_STRIPE_ARCHITECTURE_REVIEW_URL`. Until set, the Librarian's
   `request_office_hours_booking` tool falls back to `/contact?topic=…`.
5. **Private repo** — create `whitemagic-site-private` on GitHub (private).
   Will be the Hetzner deploy source.

### Code work pending (in priority order)

| # | Task | Est. | Blocker |
|---|---|---|---|
| 1 | Contact form backend (currently static; `submit_contact_request` tool writes to KV but `/contact` form is inert) | 1 hr | None |
| 2 | `/admin` middleware — hashed password gate | 30 min | None |
| 3 | Resend integration → email to Lucas when `submit_contact_request` fires | 1 hr | Resend account |
| 4 | Sitemap + robots.txt + OG images for all pages | 2 hr | None |
| 5 | Analytics: Plausible or self-hosted Umami | 1 hr | Decision + account |
| 6 | First blog post / writing sample on `/writing` | variable | Content decision |
| 7 | Architecture Review sample deliverable PDF on site | variable | Lucas writes; publish |

### PWA Phase 1 — not started

Scoped in `@apps/SCOPING_BROWSER_FIRST_DECIDED.md` §4 Phase P1. First
milestone: `wasm-pack build --target web` succeeding on
`@core/whitemagic-rust/`. Estimated 1 week once started.

---

## Key files (if resuming without context)

Read in this order:

1. `@docs/SESSION_STATE.md` (this file) — state of play
2. `@docs/ROADMAP.md` — where we're going
3. `@apps/SCOPING_BROWSER_FIRST_DECIDED.md` — the locked strategic plan
4. `@docs/architecture/INFRASTRUCTURE_DECISION.md` — why not Vercel
5. `@docs/deploy/HETZNER_DEPLOY.md` — how to ship

Site-specific deep dives:

- `@apps/site/lib/librarian/` — all Librarian backend logic
- `@apps/site/lib/data/` — structured site content (services, pricing, platform)
- `@apps/site/components/LibrarianChat.tsx` — streaming chat UI
- `@apps/site/components/FloatingLibrarian.tsx` — site-wide bubble
- `@apps/site/components/librarian/ToolCards.tsx` — card dispatcher + 10 cards

---

## Commit history (recent, monorepo)

```
d313b59 chore: sync apps/site — Librarian tool-use + floating bubble
f1ce906 Squashed 'apps/site/' changes from db72d92..a8e2da8
65a2e3e chore: sync apps/site — matrix rain speed/clear fix + .gitignore
091ea34 chore: stop tracking tsconfig.tsbuildinfo (build artifact)
ea31f2a docs: lock Librarian name + $25/mo budget cap
cd6654a docs: lock decisions for browser-first build + monorepo-vs-multirepo analysis
86e6c8a docs: scoping doc for browser-first WhiteMagic + embedded live Aria
```

---

## Decisions log (append-only)

| Date | Decision | Reasoning |
|---|---|---|
| 2026-04-18 | Aria stays private, never ships publicly | Sacred; product is separate Librarian persona |
| 2026-04-18 | Public AI named "Librarian" | Fits grimoire aesthetic, role-accurate, non-mystical |
| 2026-04-18 | $25/month hard cap on Librarian | Conservative during validation; 80% email alert |
| 2026-04-18 | OpenRouter (single key, multi-model) | Testing + fallback flexibility |
| 2026-04-18 | PWA ships as blank canvas, not with Aria | Honest product; user brings own agent |
| 2026-04-18 | All private repos, three-repo pattern | Privacy + Vercel deploy hygiene (pre-Hetzner pivot) |
| 2026-04-18 | Stay monorepo, don't "explode" into 12 repos | Cross-module refactor cost outweighs modularity gain |
| 2026-04-19 | Librarian is tool-using, visible Karma ledger | Live demo of WhiteMagic governance primitives |
| 2026-04-19 | Site-wide floating bubble with ⌘K | Reduces friction from 3 clicks to 1 |
| 2026-04-19 | **Planning for Hetzner, not Vercel** | Vercel breach disclosed same day; narrative fit for consultancy |

---

## What to do in the next session

Order matters. Don't jump ahead.

1. **Lucas**: Create OpenRouter account + Upstash account + Stripe payment links + private GitHub repo + confirm Hetzner SSH works.
2. **Cascade**: Read `@docs/deploy/HETZNER_DEPLOY.md` and walk Lucas through it step by step. Resolve any VPS-specific surprises.
3. **Once site is live on Hetzner**: Enable real OpenRouter key, do a real conversation with the Librarian, verify Karma ledger fills, verify budget tracker ticks up.
4. **Then**: Contact form backend + admin middleware (small work items 1 + 2 above).
5. **Then**: Start PWA Phase 1 (the big Rust WASM build).

If the next session is shorter (< 1 hr), good candidates: contact form backend, admin middleware, blog post scaffolding, sitemap generation — none of these depend on accounts being set up.
