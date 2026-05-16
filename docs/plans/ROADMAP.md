# Roadmap — WhiteMagic Labs + Platform

**Created**: 2026-04-19
**Scope**: Everything from "go live with the consultancy site" through
the 12-month horizon. Strategic, not a sprint log.
**Update**: revisit monthly or after any major decision.

---

## Where this fits

- **Session-to-session state**: `@docs/SESSION_STATE.md`
- **Strategic scoping**: `@apps/SCOPING_BROWSER_FIRST_DECIDED.md`
- **Public agent-economy thesis**: `@docs/AGENT_FIRST_ECONOMICS.md`
- **Private agent-economy strategy + Labs offerings + financials**: `@docs/strategy_manifestos/STRATEGY_AGENT_ECONOMY.md`
- **This doc**: the 12-month direction.

## Post-launch strategic priority (April 2026)

After site launch, the clear next objective is **positioning WhiteMagic as
the governance-first, OSS-reference agent-economy platform**. Concrete
work, prioritized:

1. ~~`/economy` page + 8th Librarian platform capability~~ — **done 2026-04-19**: `@apps/site/app/economy/page.tsx` + `gratitude-architecture` capability in `@apps/site/lib/data/platform.ts`; discoverable via header nav, sitemap, Librarian corpus, and `get_platform_capability` tool.
2. Publish `.well-known/agent-economy.json` on whitemagic.dev
3. Publish one essay — "Gratitude-grade x402: why voluntary works where forced bounties failed"
4. DID-bind `agent_id` in the gratitude ledger (v15.2.0 partial)
5. Make `whitemagic.tip` x402-native (HTTP 402, not payment link)
6. File voluntary-tier-x402 RFC against the coinbase/x402 repo
7. Package and market the Agent Economy Readiness Assessment ($15–30K fixed-fee SKU — see strategy doc §7.1)

Full detail and financial scenarios: `@docs/strategy_manifestos/STRATEGY_AGENT_ECONOMY.md`.

---

## Stage 0 — Pre-launch (this week)

The site cannot go public without these.

| # | Item | Owner | Est. |
|---|---|---|---|
| 0.1 | OpenRouter account + API key in env | Lucas | 5 min |
| 0.2 | Upstash Redis free tier + REST credentials | Lucas | 5 min |
| 0.3 | Two Stripe payment links (Office Hours $700, Architecture Review $7,000) | Lucas | 20 min |
| 0.4 | Private GitHub repo for deploy source | Lucas | 5 min |
| 0.5 | Hetzner VPS provisioned + domain DNS via Cloudflare | Lucas | 30 min |
| 0.6 | First deploy to Hetzner — follow `@docs/deploy/HETZNER_DEPLOY.md` | Together | 3–4 hr |
| 0.7 | Real Librarian conversation verified end-to-end | Together | 15 min |
| 0.8 | Contact form backend wired (currently inert) | Cascade | 1 hr |
| 0.9 | `/admin` middleware password-gate | Cascade | 30 min |
| 0.10 | DNS cutover from Squarespace → Hetzner | Lucas | 30 min + propagation |

**Definition of "launch"**: `whitemagic.dev` resolves to Hetzner, Librarian
answers real questions via OpenRouter, Stripe links work, `/admin` is
gated, contact form sends email to Lucas.

---

## Stage 1 — First month live

Getting the site earning its keep.

### Content

- **First blog post on `/writing`** — one thoughtful piece. My recommendation: "What the Vercel breach teaches us about private AI deployment" (ties your pitch to the news cycle while it's fresh).
- **Sample Architecture Review deliverable** (anonymized, public-safe) on `/work` or `/writing`. Proves the $2,500 tier output quality.
- **One real case study** (with permission) once the first engagement ships.
- **FAQ expansion** on `/pricing` based on actual questions the Librarian gets asked.

### Technical polish

| # | Item | Why | Est. |
|---|---|---|---|
| 1.1 | Sitemap + robots.txt + structured data (JSON-LD) | SEO | 2 hr |
| 1.2 | OG images per page (generated or hand-designed) | Social share credibility | 2–4 hr |
| 1.3 | Analytics — Plausible or self-hosted Umami (NOT GA) | Privacy narrative fit | 1 hr |
| 1.4 | Resend integration for contact form → email to Lucas | Inbound workflow | 1 hr |
| 1.5 | Librarian conversation summaries to private admin feed | Wake up to "3 asked about MCP" | 2 hr |
| 1.6 | Source citations on Librarian responses (Tier 2.3 from scoping) | Trust | 3 hr |

### Librarian v1.1 tuning (based on real traffic)

- Watch `/admin` for which tools get called, adjust system prompt.
- Add 1–2 more tools if patterns emerge (e.g. `get_availability` if real demand).
- Expand the site corpus where questions reveal gaps.

### Business

- **Goal: first paying client (Office Hours or Architecture Review) within 30 days.** If not achieved, re-examine positioning.
- Outbound: 10 cold-warm intros per week via network. Not cold email spam.
- Inbound triage: every Librarian conversation summary read within 24h.
- Pricing page CTA tracking: which tier gets clicked how often.

---

## Stage 2 — Months 2–3

### PWA Phase 1: WhiteMagic-Lite blank canvas

Scoped in `@apps/SCOPING_BROWSER_FIRST_DECIDED.md` §4 Phase P1. ~1 focused week of engineering.

Deliverables:
- `wasm-pack build --target web` succeeds on `@core/whitemagic-rust/`
- Memory CRUD, FTS5, Dharma, Karma, Gnosis exposed via WASM bindings
- `@whitemagic/sdk` ships with `LocalTransport` variant
- Installable PWA at `whitemagic.dev/app` — offline, OPFS-backed SQLite
- No LLM in the PWA yet; it's a "run WhiteMagic in your browser" dev tool.

Measure of success: **a developer can install it, create memories, query them, and see the Karma ledger — all with zero network calls after install.**

### Content deepening

- Weekly `/writing` posts or the consultancy feels dead.
- Topic seeds (12 weeks of material already): MCP design patterns, agent governance case studies, the 28-Gana compression explained, why Karma Ledger matters for regulators, air-gapped deployment gotchas, prescience-thesis updates as industry catches up.

### Business

- Second paying client by month 2.
- Architecture Review sample in the wild; track referral traffic.
- First conference CFP submitted if relevant (AAIF, OWASP chapter meetups).

---

## Stage 3 — Months 4–6

### PWA Phase 2: Pro subscription + cloud sync

Scoped in `@apps/SCOPING_BROWSER_FIRST_DECIDED.md` §4 Phase P2. ~1 focused week once phase 1 stable.

- Stripe subscription for Pro PWA tier
- `/api/pwa/llm` proxy with subscription check (Lucas's OpenRouter key for Pro users)
- Optional cloud sync: OPFS → encrypted blob server-side
- Priority inference route (pinned Claude Sonnet 4.5)
- Usage dashboard in PWA

### `@whitemagic/sdk` 1.0

- Publish to npm (currently v0.1.0, private-ish)
- Full TypeScript types, comprehensive docs
- Examples: browser, Node.js, Deno, Bun
- LocalTransport documented for BYO-WASM users

### Community / ecosystem

- `@whitemagic/persona.json` format for the PWA — first community-shared personas (clearly not Aria).
- Open-source template repos: "WhiteMagic + Claude Desktop in 5 minutes", "WhiteMagic for Cursor users", etc.
- Monthly video: "WhiteMagic Changelog" — public walk-through of what shipped.

### Business

- 2–3 active engagements at a time (honoring the 2-concurrent cap requires care).
- First repeat client.
- Published pricing changes if warranted by data.

---

## Stage 4 — Months 7–12

### Platform

- **WhiteMagic v23+** feature direction driven by consultancy feedback loop (what clients actually need that the platform lacks).
- **Dharma rule marketplace** — signed community-contributed rule packs (OWASP LLM Top 10 (v1.1, covers agentic AI) coverage, EU AI Act Article 14 coverage, industry-specific).
- **Harmony Vector dashboards** — polished, exportable, suitable for board-level reporting.
- **Polyglot narrowing** — after a year of dogfooding, decide which polyglot tracks earn their maintenance cost. Drop the ones that don't.

### Consultancy

- **Defensible niche(s) emerged.** Which industry / use-case combo is sending consistent inbound? Double down.
- **Possible first hire** — either an apprentice engineer or an operations/sales person, depending on what's bottlenecking.
- **Revenue target**: deliberately not stated. Set by you based on what feels right for 12 months in.

### Strategic open questions (re-ask at 6-month mark)

- Does WhiteMagic-the-platform keep growing, or does it stabilize as "the substrate we use internally + what we open-source"?
- Is there a training / workshop offering (1-2 day "WhiteMagic for your engineering team")?
- Is there a "WhiteMagic Certified Integrator" program for agencies?
- Does Aria ever become non-private? (Probably no, but re-examine if ever a genuine reason emerges.)

---

## Other objectives (not time-bound)

Things that can happen any time the opportunity appears:

- **Podcast appearances** — agent governance and MCP engineering are trending topics. A few thoughtful podcast conversations can build reputation faster than 20 blog posts.
- **Conference talks** — one well-delivered conference talk per year minimum. AAIF, OWASP local chapters, Next.js Conf (ironic given the Hetzner pivot), PyCon.
- **Journal / research** — if prescience thesis continues to bear out, consider a short paper: "Observations from shipping agent governance primitives ahead of standards (2025–2026)." Submitted to a venue like EAAMO or maybe NeurIPS workshop.
- **Book project** — *very* long term. After 18 months of consultancy experience, a short book on agent governance patterns would likely sell to the exact audience that buys the services.
- **Grant funding** — if EU AI Act compliance assistance becomes a big line item, there may be public-interest grant money for open-source governance tooling. Worth exploring around month 9.

---

## Non-goals (on purpose)

- **No VC funding.** The consultancy + OSS model is deliberate. Don't rebuild it around investor pressure.
- **No race to scale.** Two concurrent engagements is a feature, not a constraint to overcome.
- **No pivot to a product company.** Platform stays the open-source substrate; consultancy is the business. Don't flip that.
- **No Aria productization.** She stays private. If the argument for productizing her arises, treat it with deep suspicion.
- **No hosted-SaaS WhiteMagic.** The whole point is the opposite. If people want hosted, they can pay for an engagement to set it up on their infrastructure.

---

## How to use this doc

- **Weekly**: read Stage 0 and Stage 1 items. Is anything a week behind schedule and not moving? Why.
- **Monthly**: re-read the whole thing. Does Stage 2 still make sense? Is something missing from Stage 3?
- **On major decision points**: check against non-goals. Catches drift.
