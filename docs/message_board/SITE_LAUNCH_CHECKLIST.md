# Site Launch Checklist — whitemagic.dev Day 1

**Status**: Active working doc for the Day 1 site-polish-and-ship sprint.
**Last updated**: 2026-04-20
**Related**:
- `docs/SESSION_STATE.md` — current state of play
- `docs/ROADMAP.md` — 12-month direction
- `docs/strategy_manifestos/ON_PREMISE_EDGE_AI_SCENARIOS.md` — the 7 target scenarios
- `docs/strategy_manifestos/AGENT_FIRST_LAB_STRATEGY.md` — lab thesis
- `docs/deploy/HETZNER_DEPLOY.md` — ship procedure

---

## 0. Scope of this doc

Everything that should be true about `whitemagic.dev` **before** we
cut DNS and announce. Structured as:

- §1 — Global changes (cross-page, brand, nav, footer, credibility).
- §2 — Page-by-page updates.
- §3 — Pricing and services SKUs (the source-of-truth table).
- §4 — Librarian updates (corpus, tools, system prompt).
- §5 — SEO / agent-native surfaces.
- §6 — Pre-launch verification checklist.
- §7 — Deferred (not for Day 1).

Work through §1 → §6 in order. §7 is explicitly **out of scope** for
the launch sprint and should be resisted.

---

## 1. Global changes

### 1.1 Credibility pass — fix the inflated claims

Current homepage (`@apps/site/app/page.tsx:64-70`) claims:

> "WhiteMagic is a 170,000-line open-source cognitive OS for AI
> agents — 374 MCP tools, 11 languages, persistent holographic
> memory, an 8-stage governance pipeline, and **1,318 passing tests**."

The "1,318 passing tests" figure is stale. Current honest number
from `STRATEGIC_PIVOT_ANALYSIS.md §2` is roughly **766 passing / 189
failing** on unit tests. An engineer who clones the repo catches this
in 90 seconds. Options:

- **Option A (recommended)**: remove the test count entirely.
  Replace with a qualitative claim ("extensively tested across
  memory, governance, and tool-execution layers") or with a
  different concrete number that is currently true (number of
  tools, number of languages, LOC).
- **Option B**: fix the platform so the number is true again.
  Out of scope for Day 1.
- **Option C**: replace with "v22.0.0 public release · pinned
  research snapshot" and link to a status page. Honest and turns
  a liability into a lab-posture signal.

**Decision**: Option C. Aligns with the lab thesis and the 10-day
plan's README fix.

Other claims to audit on the homepage:
- "374 MCP tools" — verify against current registry. If not exactly
  true, use "~350 MCP tools" or omit.
- "11 languages" — count the actually-shipping polyglot tracks.
  Be honest.
- "persistent holographic memory" — metaphorical; either explain or
  soften to "persistent structured memory."

### 1.2 Navigation — align with service ranking

Current nav: Services / Pricing / Timeline / Open Source / Writing /
Work / About / Contact.

Updated nav (reflects positioning from `AGENT_FIRST_LAB_STRATEGY`
and pricing SKU rework):

- **Services** (dropdown or /services page)
- **Pricing**
- **Work** (case studies — currently thin, see §2.8)
- **Writing** (essays — currently empty, see §2.7)
- **Economy** (keep — recently-shipped differentiator)
- **Lab** (NEW — surfaces `/timeline`, `/open-source`, GitHub orgs)
- **About**
- **Contact**

"Lab" as a parent for research-flavored pages frames the whole
operation correctly. Timeline and Open Source stop being orphan
tabs and become sub-pages under a recognized identity.

### 1.3 Footer — expand with agent-native surfaces

Current footer: basic. Add:

- Link to `/.well-known/agent-economy.json`
- Link to `/.well-known/ai-agent-policy`
- "Agent-addressable via MCP at `mcp://whitemagic.dev`" (once live)
- DID string: `did:web:whitemagic.dev` (once bound)
- RSS feed for `/writing`
- Canonical repo links

Small, tasteful, signals to the right readers.

### 1.4 Brand consistency audit

- Verify every page uses the same spelling: **WhiteMagic Labs**
  for the org, **whitemagic.dev** for the site, **WhiteMagic**
  (no space) for the platform/codebase.
- "Librarian" as the agent name, consistently. Never "AI assistant."
- "Consultancy," "lab," or "firm" — pick one. Recommendation:
  **lab** as the identity, **consulting** as an activity. Not the
  other way around. Use "consultancy" sparingly.

### 1.5 Accessibility and finish

- Every link has discernible text (no bare URL-as-link).
- Every image has alt text.
- Keyboard navigation works on the floating Librarian bubble.
- Contrast checked on lavender-on-paper palette (WCAG AA target).
- Forms have proper labels and error states.
- Mobile layout audited at 375px and 768px breakpoints.

---

## 2. Page-by-page

### 2.1 `/` (homepage)

- **Hero**: single-sentence positioning. Current "Ready for AI that
  lives inside your walls?" is on the right track — tighten to one
  line at the top. Suggested:
  > "On-premise AI that your auditors can read and your engineers
  > can run."
- **Three services grid**: reorder per §3.2 of this doc. MCP
  Engineering first (highest close rate), Agent Governance second
  (narrative spine), Private AI Deployment third (highest-ticket).
- **"Proof" section** (`page.tsx:53-91`): rewrite per §1.1. Stop
  claiming 1,318 tests. Refocus on what's actually provable:
  "public Karma ledger at /admin", "live tool-using Librarian on
  every page", "open-source platform at github.com/whitemagic-ai".
- **"Scarcity" block** (NEW, see §1 part 2.7 of the prior convo):
  "Currently booking: [X] in [month]. [Y] in [next month]."
  Live, updated manually as calendar fills.
- **Final CTA**: keep. "Book a discovery call" → `/contact`.

### 2.2 `/services` and service sub-pages

- **`/services`** (overview): replace three-card layout with ranked
  four-card layout per §3 of this doc. Add the three new SKUs
  (Advisory Pack, AI Act Readiness, Governance Readiness) as
  secondary rows below.
- **`/services/mcp-engineering`**: lead service. Expand to include
  a "what you get" deliverables list and a sample timeline.
- **`/services/agent-governance`**: reposition as the *framing*
  umbrella for all engagements. Include Karma Ledger screenshot
  from `/admin`. Link to `ON_PREMISE_EDGE_AI_SCENARIOS.md` themes
  (but not the internal doc itself) — e.g. a "For regulated
  industries" sub-section.
- **`/services/private-ai-deployment`**: rename and refocus. Current
  name is generic. Consider: "On-Premise & Air-Gapped AI" or
  "Sovereign AI Deployment." Expand to call out the 7 buyer
  scenarios at high level (hospitals, defense, law firms, finance,
  EU industrial, research, public sector).

### 2.3 `/pricing`

Replace entire pricing structure with §3 of this doc. Specifically:

- Remove $700 / $7,000 tiers as currently structured.
- Add the 7-SKU table.
- Add FAQ entries for: scoping engagement model, discounted first
  client, retainer structure, international invoicing.
- Add scarcity block matching homepage.
- Add explicit note: "Engagements outside the US and EU negotiated
  individually" — honest and opens the door without committing.

### 2.4 `/economy`

Keep as-is. Recently shipped, well-built, differentiator.
Minor: add a link to `AGENT_FIRST_ECONOMICS.md` for the deeper read.

### 2.5 `/timeline`

Keep. Moves under new `Lab` nav section.

### 2.6 `/open-source`

Keep. Moves under `Lab` nav. Ensure repo links all work. Add a
"status" column — which repos are active vs pinned.

### 2.7 `/writing`

**Currently empty. This is a credibility leak.** Either:

- **Option A (recommended)**: ship with one post on Day 5 of the
  10-day plan — "What we shipped in four weeks: a tool-using
  Librarian with a public audit ledger." Link from homepage.
- **Option B**: remove from nav until first post exists. Cleaner
  than empty shelf.

For Day 1: Option B (remove from nav). Day 5: reinstate with real
content.

### 2.8 `/work`

**Currently thin.** Same treatment:

- For Day 1: remove from nav.
- For Day 4 of the 10-day plan: reinstate with the sample
  Architecture Review deliverable.

### 2.9 `/about`

Audit for accuracy. Ensure no claims that depend on the inflated
platform metrics from §1.1. Add a short paragraph on WhiteMagic
Labs' posture (lab + consulting, artifacts-first, MIT license,
Hetzner-hosted) — the infrastructure story itself is a trust signal.

### 2.10 `/contact`

- Verify form uses the Day 3 qualification questions:
  1. What's the use case and what's the regulatory or data-
     sensitivity constraint?
  2. What's your timeline?
  3. Budget range you're working with?
- Add Cal.com link for Office Hours bookings directly.
- Keep honeypot + rate limit as currently built.

### 2.11 `/admin`

Keep. Verify Basic Auth works in production with real
`ADMIN_PASSWORD_HASH`.

### 2.12 `/librarian`

Full-page Librarian chat. Verify streaming works end-to-end with
real `OPENROUTER_API_KEY` before launch.

### 2.13 `/zh`

Decision point: the `/zh` route exists (`@apps/site/app/zh/`).
Three options:

- **A**: Ship as-is if content is already translated properly.
- **B**: Remove the route until professional translation is done.
  Half-translated sites damage credibility with Chinese readers
  more than no translation does.
- **C**: Ship with only the homepage translated; every other link
  goes to English with a note.

**Decision for Day 1**: inspect the page. If it's clearly
machine-translated or incomplete, go with B. Re-add properly in
Stage 1 of the roadmap.

### 2.14 `/ladder`

Unclear what this route is currently. Audit and either integrate
or remove before launch.

---

## 3. Pricing and services — source of truth

### 3.1 The 7 SKUs

| # | SKU | Duration | Price | Entry point? |
|---|---|---|---|---|
| 1 | **Office Hours** — 60 min call | 1 hr | **$750** | ✓ lowest friction |
| 2 | **Advisory Pack** — 5× 60 min over 1 month | ~5 hr | **$4,500** | mid-funnel |
| 3 | **Scoping Engagement** | 2–3 wk | **$8,000–$18,000** | ✓ qualified-lead entry |
| 4 | **Architecture Review** | 2–3 wk | **$12,000–$18,000** | deliverable-focused |
| 5 | **Governance Readiness Assessment** | 6 wk | **$25,000–$40,000** | compliance-flavored |
| 6 | **Full Engagement** (MCP / Governance / Deploy) | 8–16 wk | **$60,000–$250,000** | main line |
| 7 | **Retainer** (post-engagement) | monthly | **$4,500–$8,000/mo** | recurring |

Special named engagements:
- **EU AI Act Readiness** (variant of #5): €25,000–€40,000
- **Custom MCP Server Engineering** (variant of #6): $30,000–$45,000
- **Air-Gapped Deployment** (variant of #6): $60,000–$250,000

### 3.2 Service ranking for site display

Order on homepage and `/services`:

1. **MCP Engineering** — "Production-grade MCP servers for teams
   building serious agent infrastructure." Highest close rate.
   Bread-and-butter. $30–45K.
2. **Agent Governance** — "Runtime guardrails, policy enforcement,
   audit trails. Satisfies OWASP Agentic Top 10 and emerging AI Act
   requirements." Narrative spine. $25–40K assessment, $80K+ full.
3. **On-Premise / Air-Gapped AI** — "AI that never leaves your
   network, for hospitals, banks, law firms, defense, regulated
   industry." Largest-ticket. $80K–$250K.
4. **Office Hours & Advisory** — "Strategic input without the full
   engagement commitment." Sampler / mid-funnel. $750 / $4,500.

### 3.3 Pricing page structure

```
Engagement →
  1. Office Hours ($750)
  2. Advisory Pack ($4,500)
  3. Scoping Engagement ($8K–$18K) ← paid gateway to everything below
  4. Architecture Review ($12K–$18K)
  5. Governance Readiness Assessment ($25K–$40K)
  6. Full Engagement ($60K–$250K)
  7. Retainer ($4.5K–$8K/mo)

All fixed-fee. All with clear deliverables. All scoped in writing.
```

### 3.4 Pricing copy principles

- **Fixed-fee**, not hourly, for everything except Office Hours.
  Signals seniority and confidence.
- **Clear deliverables** listed for each tier. Buyer should know
  exactly what they're getting.
- **Scoping credits toward engagement**. Removes "pay twice"
  objection.
- **Honest "who this is for"** block on each tier. Disqualifies
  wrong buyers proactively.

---

## 4. Librarian updates

### 4.1 Corpus

- Add the 7 on-premise scenarios (high-level) to the Librarian
  corpus so it can answer "do you work with hospitals?" etc.
- Update pricing tool (`get_pricing_tier`) to reflect §3.1 SKUs.
- Update platform capability tool to include any new framing.

### 4.2 System prompt

- Reflect new positioning: **MCP engineering** is the lead service,
  not one-of-three.
- Add honest "who we're not for" guidance — if someone asks about
  consumer AI apps, growth hacking, ad targeting, suggest they're
  probably looking for a different kind of consultancy.
- Keep the scarcity frame: "We accept 2 concurrent engagements; ask
  about current availability."

### 4.3 Tools audit

Current 6 tools (`@apps/site/lib/librarian/tools.ts`):
- `get_service_detail` — update to reflect new ranking.
- `get_pricing_tier` — replace with new SKU table.
- `get_platform_capability` — keep, expand to 9 capabilities if
  gratitude-architecture counts as #8 and we add "on-premise
  deployment" as #9.
- `search_timeline` — keep.
- `request_office_hours_booking` — wire to Cal.com link in production.
- `submit_contact_request` — keep.

### 4.4 Verification

On launch day: one real conversation through the Librarian that
touches at least two tools. Verify:
- OpenRouter round-trip works.
- Tool call records land on `/admin`.
- Karma ledger entry is Merkle-chain valid.
- Upstash rate limit triggers correctly.
- Budget cap decrements.

---

## 5. SEO / agent-native surfaces

### 5.1 Structured data (already shipped)

- Verify JSON-LD is present on every production page.
- Verify Organization and WebSite emit from root layout.
- Verify per-page schema (Service, FAQPage, Person) are correct.

### 5.2 OG images (already shipped)

- Verify all 7 OG routes render correctly in production.
- Add OG images for any pages added in §2 that don't have them.

### 5.3 Well-known endpoints

- `/.well-known/agent-economy.json` — verify v0.1 is current.
- `/.well-known/ai-agent-policy` — verify matches spec at
  `docs/spec/`.
- Both should update to reflect the new pricing SKUs and any
  new services.

### 5.4 Sitemap and robots

- Verify `sitemap.ts` includes all new pages and excludes drafts.
- Verify `robots.ts` allows indexing on production domain.

### 5.5 Canonical URLs

Every page should declare a canonical URL matching its production
path (not the Vercel-preview or subdomain pattern).

---

## 6. Pre-launch verification checklist

Run these in order on launch day. No step skipped.

- [ ] `next build` clean, zero warnings
- [ ] `next lint` clean
- [ ] TypeScript: `tsc --noEmit` clean
- [ ] All env vars present in `/srv/whitemagic-site/.env.production.local`:
  - [ ] `OPENROUTER_API_KEY`
  - [ ] `UPSTASH_REDIS_REST_URL` + `UPSTASH_REDIS_REST_TOKEN`
  - [ ] `RESEND_API_KEY` + `CONTACT_NOTIFY_EMAIL`
  - [ ] `ADMIN_PASSWORD_HASH`
  - [ ] `NEXT_PUBLIC_STRIPE_OFFICE_HOURS_URL`
  - [ ] `NEXT_PUBLIC_STRIPE_ARCHITECTURE_REVIEW_URL`
- [ ] Systemd unit running, auto-restart enabled
- [ ] Caddy TLS working, cert auto-renews
- [ ] DNS resolves correctly, Cloudflare proxy on
- [ ] Homepage loads in <1s (Lighthouse mobile)
- [ ] Floating Librarian bubble opens on ⌘K
- [ ] One real Librarian conversation completes with ≥2 tool calls
- [ ] Karma ledger shows real entry on `/admin`
- [ ] Basic Auth on `/admin` works (wrong password denied,
      right password allows, constant-time compare)
- [ ] Contact form submits → Resend email arrives in inbox
- [ ] Contact form rate limit triggers after N submissions
- [ ] Stripe payment links work (test purchase to own card, refund)
- [ ] Cal.com booking link works
- [ ] `/.well-known/agent-economy.json` returns valid JSON
- [ ] `/.well-known/ai-agent-policy` returns valid JSON
- [ ] `sitemap.xml` lists all public pages
- [ ] `robots.txt` allows indexing
- [ ] OG image preview correct for `/`, `/pricing`, `/services/*`
- [ ] JSON-LD validates (use Google Rich Results test)
- [ ] No broken internal links (`broken-link-checker` run)
- [ ] No broken external links
- [ ] Mobile layout at 375px renders correctly on homepage, `/pricing`,
      `/services`, `/contact`
- [ ] 404 page exists and is on-brand
- [ ] No `console.log` in production build
- [ ] No `TODO` comments visible in rendered HTML
- [ ] Analytics (Plausible or Umami) firing correctly — optional,
      not strictly launch-blocking

---

## 7. Explicitly deferred (NOT Day 1)

Do not let any of these creep into the launch sprint.

- New `/writing` posts beyond the single Day 5 launch post.
- `/work` case studies beyond the single Day 4 sample deliverable.
- MCP-over-HTTPS endpoint (`mcp://whitemagic.dev`).
- DID-bound signed JSON artifacts (`docs.json`, `pricing.json`
  signatures).
- Observatory scaffold.
- NixOS showpiece `lab.whitemagic.dev`.
- Reference implementation repos.
- Platform repo (`whitemagic-ai/whitemagic`) test suite repair.
- MandalaOS spec publication.
- Any new polyglot tracks.
- Analytics dashboard beyond the default Plausible / Umami install.
- A/B testing infrastructure.
- Internationalization beyond current `/zh` decision.
- Blog / CMS migration — Markdown-in-repo is fine.

**Rule**: if it's not on §1–6, it waits until after launch. Every
deferred item can be added post-launch without the site going down.
The site does not need to be complete to launch; it needs to be
honest, coherent, and pointed at a buyer.

---

## 8. Day 1 execution order

Suggested sequencing within the Day 1 block:

1. **Morning — site polish** (in this order):
   1. §1.1 credibility pass (homepage claims)
   2. §3 pricing rewrite (page.tsx for `/pricing`)
   3. §2.1 homepage reordering
   4. §2.2 service pages update
   5. §1.2 nav cleanup + §2.7/§2.8 remove empty tabs
   6. §4 Librarian corpus + system prompt + tools update
2. **Midday — verification locally**:
   1. Full §6 verification run on `localhost:3000`
   2. Fix anything that breaks
3. **Afternoon — ship**:
   1. Hetzner bootstrap per `docs/deploy/HETZNER_DEPLOY.md`
   2. DNS cutover
   3. Env vars in place
   4. HTTP first, then TLS
   5. Full §6 verification run on `https://whitemagic.dev`
4. **Evening — first real conversation**:
   1. Open `/librarian`
   2. Ask a qualifying question
   3. Verify tool call → Karma ledger → admin visibility
   4. Update `SESSION_STATE.md` with launch notes

Estimated effort: 6–9 focused hours. If it runs long, sleep and
finish Day 1 the next morning — **do not cut verification steps**.

---

## 9. Rollback

If anything breaks post-launch:

- Caddy reverse-proxy to maintenance page: one-line edit to Caddyfile.
- Revert last deploy: `systemctl restart whitemagic-site` after
  `git checkout <previous-sha>` in `/srv/whitemagic-site`.
- Kill switch for Librarian: set `LIBRARIAN_DISABLED=true` in env,
  restart. (Implement this env var if not already present.)
- DNS rollback: Cloudflare → grey cloud + original A record.

Have all four rollback paths tested before needing them.
