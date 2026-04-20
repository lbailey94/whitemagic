# WhiteMagic Labs — Phase Roadmap

**Site**: `whitemagic.dev` (whitemagic-site repo)
**North star**: Land first paid engagement within 60–90 days.
**Companion**: `whitemagic-library` / `library.whitemagic.dev` — separate repo, separate timeline, built in parallel once the consultancy site is deployed.

---

## Legend

- 🎯 = direct lead-gen impact
- 🧱 = foundation / technical debt
- ✍️ = content work (highest leverage once shipped)
- 🎨 = polish / brand
- 📈 = measure & learn
- ⚡ = unblock a future phase

---

## ✅ Phase 0 — Scaffold (complete)

Next.js 15 + Tailwind + MDX in `~/Desktop/whitemagic-site/`, design tokens
ported from `whitemagic-frontend/web/`. Git tags `pre-phase-0` and
`phase-0-complete` in both repos for safe revert.

## ✅ Phase 1 — Pages & toggles (complete)

All 11 routes built with real copy: `/`, `/services` + 3 details,
`/contact`, `/about`, `/open-source`, `/work`, `/writing`, `/zh`.
Theme toggle (light/dark, localStorage). Language toggle (EN ↔ ZH).
白術 removed from English surface; lives on `/zh` only. Empty logo slot
reserved in `Wordmark.tsx` for the eventual triquetra.

**Production build**: 14 static pages, 106 kB first-load JS, `tsc --noEmit` clean.

---

## 🎯 Phase 2 — Ship it (≤ 1 week)

Get the site in front of real buyers. Small, concrete, high-leverage.

| # | Task | Type | Effort |
|---|---|---|---|
| 2.1 | Set up Cal.com (free tier) — 30-min "Discovery call" event, pre-call form | 🎯 | 30 min |
| 2.2 | Wire real booking URL into `app/contact/page.tsx` (replace TODO) | 🎯 | 5 min |
| 2.3 | Confirm email: `whitemagicdev@proton.me` or a new `lucas@whitemagic.dev` alias | 🎯 | 15 min |
| 2.4 | Deploy to Hetzner — follow `@docs/deploy/HETZNER_DEPLOY.md` (Caddy + systemd + Cloudflare) | 🧱 | 3–4 h first time |
| 2.5 | DNS: point `whitemagic.dev` at Cloudflare → Hetzner VPS (away from Squarespace) | 🧱 | 30 min, then 1–24 h propagation |
| 2.6 | Keep the old Squarespace page up at `old.whitemagic.dev` for 30 days as a safety net | 🧱 | 15 min |
| 2.7 | OG image — a simple 1200×630 PNG with wordmark + tagline, served from `/og.png` | 🎨 | 30 min |
| 2.8 | `robots.txt` + `sitemap.xml` — Next.js native helpers | 🧱 | 20 min |
| 2.9 | Plausible or Umami analytics — privacy-first, single script | 📈 | 15 min |
| 2.10 | LinkedIn + GitHub profile updates pointing at whitemagic.dev | 🎯 | 30 min |

**Exit criterion**: You can paste `https://whitemagic.dev` into a cold email
to an MCP contract, a law-firm CTO, or a LinkedIn DM — and it loads a
polished site (served from Hetzner, fronted by Cloudflare) with a working
Librarian + booking link.

**Infrastructure note (April 19, 2026)**: original plan assumed Vercel. Pivoted
to self-hosted Hetzner the same day Vercel disclosed its April 2026 security
incident — see `@docs/architecture/INFRASTRUCTURE_DECISION.md` for rationale.

---

## ✍️ Phase 3 — Anchor content (weeks 2–4)

Three posts. These are sales assets, not blog filler. Each one doubles as
a conversation starter with a buyer or a portfolio piece for a contract
application. Write in the voice of the site — plain, direct, honest.

| Slug | Working title | Cluster | Why it matters |
|---|---|---|---|
| `private-ai-deployment-guide` | How I deploy private AI for regulated teams | Private AI | Homepage of the services funnel. Shows depth without giving away the engagement. |
| `agent-governance-before-microsoft` | I built agent governance before Microsoft — here's what I learned | Agent Governance | Cassandra story with receipts. Strong share-bait; establishes the timeline. |
| `whitemagic-post-mortem` | WhiteMagic: an honest post-mortem | Strategy | The vulnerability asset. CTOs respect people who can analyze their own work. |

For each post:

1. Outline in `content/writing/<slug>.outline.md`
2. Draft in MDX at `app/writing/[slug]/page.mdx` (MDX pageExtensions already enabled)
3. Metadata export (title, description, OG)
4. Update `app/writing/page.tsx` — flip `ready: true`
5. Cross-link from the relevant service page

**Infra task 3.x**: Set up an MDX layout + the `[slug]` route pattern. Small
one-time effort that unblocks every future post.

**Bonus**: One light-weight post per month after the first three. Cadence >
perfection.

---

## 🎯 Phase 4 — Outreach & first contracts (weeks 2–6, parallel to Phase 3)

The site is a tool; outreach is the work. The site makes outreach easier,
not automatic.

| # | Task | Notes |
|---|---|---|
| 4.1 | Apply to 3–5 MCP engineering contracts per week | Freelancer, SNI, LinkedIn, direct. URL in every application. |
| 4.2 | Build a 20-target list of mid-size regulated companies (law / healthcare / fintech) | Decision-maker reachable by name |
| 4.3 | Write 5 cold-email templates, each tied to a specific service page | Keep them short; lead with a concrete hook from their public work |
| 4.4 | Draft a one-page "what an engagement looks like" PDF — served from `/engagement.pdf` | Optional; nice to have for skeptical buyers |
| 4.5 | Post anchor content #1 to HN, r/mcp, relevant LinkedIn groups | Don't sell; share the technical content |
| 4.6 | Track: replies received, calls booked, calls completed, proposals sent, closed | Plain-text log in `progress.txt` or a Notion/Airtable |

**Exit criterion**: Either (a) one paid engagement signed or (b) 3+
discovery calls completed and pipeline active.

---

## 🎨 Phase 5 — Brand polish (weeks 4–8, opportunistic)

Once the pipeline is moving, invest here. Not before — don't polish an
empty site.

| Task | Notes |
|---|---|
| Triquetra logo | Celtic-style triquetra in SVG, drops into `components/Wordmark.tsx` logo slot. Commission a designer for ~$200–500 on Fiverr/Dribbble, or hand-draw one. |
| Hero visual | Replace the "WM" monogram placeholder in `components/Hero.tsx`. Options: animated triquetra, subtle particle field, or a looping abstract video (carries the aesthetic from `whitemagic-frontend/web/galaxy2.mp4` if you can locate it). |
| Favicon + apple-touch-icon | 32×32 and 180×180 PNGs from the logo |
| Real photo in `/about` | Optional. If comfortable, a simple headshot lifts trust on the about page. |
| First case study | Once the first engagement ships with a happy client, document it with permission and flip `/work` from placeholder to real content. |
| Color refinement | The current palette is pleasant but generic-warm. If you want more edge, introduce a single bold accent on headers or CTAs. |

---

## 📈 Phase 6 — Learn & iterate (ongoing, starts after first real traffic)

Quarterly review. Kill what doesn't work.

| Task | Cadence |
|---|---|
| Review analytics: which pages drive booked calls, which don't | Monthly |
| A/B the hero copy — try 2–3 variants over 4-week windows | Quarterly |
| Kill underperforming service offerings — max 2 active, not 3 | Quarterly |
| Tighten pricing based on actual win/loss data | Ongoing |
| Promote the highest-converting post to `/` hero | Quarterly |
| Archive drafts that never got finished after 90 days | Monthly |

---

## ⚡ Phase 7 — Aria chat integration (month 3+, optional)

Only after first engagement revenue is flowing. Adds differentiation but
doesn't sell the service by itself — the services page does.

**Architecture sketch**:

- FastAPI backend reusing WhiteMagic's `core/whitemagic/api/` endpoints
- Embedded in site via a floating chat widget (`components/Aria.tsx`)
- Scoped: answers questions about services, open source, writing
- Uses WhiteMagic memory/galaxy isolation for per-visitor context
- Rate-limited, logged, governance-gated (dogfood our own middleware)
- Falls back to "book a call" when the conversation gets serious

**Explicit non-goals**:
- No free consulting via chat
- No pretending Aria is human
- No "talk to an AI instead of booking a call" CTA replacement

---

## ⚡ Phase 8 — Library site (parallel track, month 2+)

Lives at `~/Desktop/whitemagic-library/` → `library.whitemagic.dev`. Own
repo, own deploy, own visual identity. Houses:

- Selected LIBRARY distillations (curated, edited for public consumption)
- Grimoire content (philosophical / narrative writing)
- Aria's full persona page and voice documents
- 28 Gana wheel as a proper research artifact
- Retired content from the old Vaya Vida site worth preserving

**Stack**: Same Next.js + MDX stack — reuse tooling knowledge. Different
design language: more contemplative, more 白術, more east-meets-celtic.

**Rule**: the consultancy site must never point at the library site as
part of the sales funnel. Library exists for its own sake. It may feed
credibility indirectly through depth, but it is not a lead-gen asset.

---

## Principles

1. **Shipping beats polish.** A rough site with a working booking link
   outperforms a beautiful site with nowhere to click.
2. **Writing is the moat.** Every anchor post is a permanent asset. One
   good post per month compounds into an inbound pipeline by month 9.
3. **Specificity wins.** "Private AI for law firms" closes 3× faster than
   "AI consulting." Narrow the vertical in copy when the pattern appears
   in real leads.
4. **The library is a hobby, not a product.** Treat it as a gift to the
   commons and to future-you. It should never block revenue work.
5. **Honesty is a differentiator.** The post-mortem, the honest `/work`
   placeholder, the self-aware `/about` — these are competitive assets.
   Don't file them off in later polish passes.

---

## Known deferred items

- `galaxy2.mp4` hero video — referenced in `whitemagic-frontend/web/` but asset is missing
- Triquetra logo — commissioned in Phase 5
- Real Cal.com URL — Phase 2
- MDX post layout + `[slug]` route — Phase 3 infra
- Case studies — Phase 5, needs real engagements first
- Aria chat — Phase 7, after revenue
- Library site — Phase 8, parallel track
