# Strategy: The Agent-First Lab

**Status**: Private working strategy. Candid, technical, exploratory.
**Audience**: Lucas + any future WhiteMagic Labs collaborators.
**Last updated**: 2026-04-20
**Companion to**:
- `docs/strategy_manifestos/STRATEGY_AGENT_ECONOMY.md` — market read + financial scenarios
- `docs/AGENT_FIRST_ECONOMICS.md` — public thesis
- `docs/architecture/INFRASTRUCTURE_DECISION.md` — why not Vercel

---

## 0. Thesis

> We hit peak human digital systems in 2025. From here forward, an
> increasing share of digital interaction is agent-to-agent, digital-
> community-to-digital-community. WhiteMagic Labs is positioned to be
> a primary reference point for that transition — not by building the
> biggest product, but by publishing the most rigorous artifacts.

Three downstream claims this thesis forces:

1. The **site itself is the product** in a way that flips over time —
   today human readers dominate, within 24 months agents and crawlers
   will dominate. Everything on `whitemagic.dev` should be designed
   for *both* audiences simultaneously, with the agent-facing surface
   treated as a first-class deliverable (not an afterthought).
2. Our comparative advantage is **cognitive wealth** — novel ideas
   already in the repo and the grimoire, not operational excellence.
   A lab's output is artifacts; the consultancy is how we eat while
   we publish them.
3. **Who looks at us matters more than how many.** Governments,
   hospitals, R&D labs, standards bodies, other labs — small
   audiences with outsized pull. Position for *their* gaze.

Everything below flows from these three.

---

## 1. Hosting / Infrastructure — Principled Options for "Serious Gaze"

**Assumption for this section**: at some point in the next 12 months,
attention from a government procurement team, a hospital CTO, an R&D
lab director, or a standards body contributor lands on whitemagic.dev.
They will click around, ask questions, and — critically — *read the
"about our infra" story*. The hosting choice becomes a signal.

### 1.1 The hosting tiers, ranked by signal

| Tier | Host | Signal it sends | Cost to maintain | Narrative fit |
|---|---|---|---|---|
| PaaS-minimal | Railway / Fly | "pragmatic, ships fast" | near-zero | weakest |
| Hetzner VPS | plain Ubuntu | "competent sysadmin" | medium | medium |
| Hetzner + Coolify | web-UI on VPS | "operationally mature" | medium | medium |
| Hetzner + NixOS | declarative | "rigorous, reproducible" | high | strong |
| Self-host + Cloudflare Tunnel | home → edge | "actually private" | low | strong |
| MandalaOS / Qubes-mod on VPS | custom OS | "sovereign-stack lab" | very high | strongest |

### 1.2 Expected gaze, per audience

The relevant question isn't *what looks technical*; it's *what looks
non-negotiable under scrutiny*.

**Government / public-sector scrutiny**:
- FedRAMP-adjacent auditors care about: data residency, SBOM,
  reproducible builds, air-gap capability, supply-chain attestations.
- NixOS crushes this. Reproducible builds + declarative config + a
  readable `configuration.nix` in the public repo is an answer to
  half the questions in their intake form, before they ask.
- MandalaOS / Qubes-mod pushes further — *compartmentalization* and
  security isolation become demonstrable rather than claimed.
- Railway / Fly fail this test — "where does our data live exactly?"
  has no good answer.

**Hospital / HIPAA-adjacent scrutiny**:
- Care about: PHI boundary, audit log integrity, BAA availability,
  incident response.
- They will ask: "can you deploy this inside our walls?" The site
  itself doesn't need HIPAA — but the *answer to that question* is
  load-bearing. A NixOS config that's the same one they'd get on
  their own hardware is a *showable* answer.

**R&D labs / standards bodies**:
- Care about: reproducibility, open artifacts, willingness to share
  the stack, intellectual honesty about what's novel vs standard.
- NixOS or Qubes-mod signals "we eat our own cooking." Railway
  signals "we use the same PaaS as everyone else."

**Peer labs and OSS maintainers**:
- Care about: clever, principled, novel. Anti-care about: basic.
- The house-on-Cloudflare-Tunnel story ("our governance lab literally
  lives in the founder's house, proven via public latency graphs")
  is *catnip* for this audience.

### 1.3 Recommendation — staged, two-track

Run two machines, each with a clear story:

- **Track 1 (the face)**: `whitemagic.dev` on Railway (or Fly) as a
  disposable edge of the system. 30-minute deploy, stable, boring,
  cheap. **This is the marketing surface** — the consulting clients
  don't need it sovereign-stacked; they need it to load in 400 ms.
- **Track 2 (the showpiece)**: `lab.whitemagic.dev` on NixOS on
  Hetzner CCX — or, more ambitiously, MandalaOS prototype on a
  Hetzner dedicated box. **This is the artifact**. It runs the
  Librarian, the observatory, and any agent-native primitives.
  The `configuration.nix` (or `mandala-os.yaml`) is **public** in
  the repo. The *infra itself is a published artifact*.

The split keeps tactical velocity (ship tomorrow) while preserving
narrative maximalism (the lab IS sovereign-stack, but we picked our
battles). Over time `lab.` graduates into `whitemagic.dev`'s primary
once it's proven.

### 1.4 NixOS specifically — why this is a big win

- **Reproducibility**: literally, the same config produces the same
  system. Clients comparing deploy stories with Terraform or Ansible
  shops can feel the difference in one look.
- **Auditability**: one file (or a small tree) describes every
  package, service, and permission. No "I logged in and installed
  X" drift. Compliance auditors love this.
- **Rollback**: generation-based. Every deploy is a commit; every
  rollback is a git reset. "We cannot end up in a broken state we
  can't recover from" is a sentence very few hosts can honestly say.
- **Narrative leverage**: "WhiteMagic Labs publishes its
  production `configuration.nix` as part of its open-source
  commitment." That sentence belongs on the site.
- **Cost**: one-time setup pain (2–3 days real), then near-zero
  operational cost. Hetzner still the underlying provider.

### 1.5 MandalaOS / Qubes-mod — the far island

MandalaOS (hypothetical — doesn't exist yet) would be a
WhiteMagic-authored minimal OS image that ships with Dharma, Karma,
and Harmony primitives in the base system, and uses Qubes-style
compartmentalization to isolate agent workloads from each other.

Viability:
- **High effort**: 3–6 months of serious work to produce a
  defensible first version. Takes us far from consulting revenue.
- **Enormous narrative dividend**: "the OS for governed agents"
  is the kind of claim that, if supported by even a minimal
  working artifact, gets standards-body invitations, press, and
  inbound that no amount of blog posts replicates.
- **Realistic near-term path**: *not* build MandalaOS, but publish
  a **MandalaOS Specification** — a document + reference
  `configuration.nix` describing what MandalaOS would look like if
  built. That alone may be enough; the spec doc is itself an
  artifact that signals thought leadership.

Recommended posture: **spec before code.** Publish the vision as
a living document. Build the NixOS showcase as the nearest-
neighbor implementation. If MandalaOS earns attention, we build
it. If it doesn't, we haven't lost anything.

### 1.6 Near-term action

1. Tomorrow: `whitemagic.dev` on Railway via `git push`. Done.
2. Week 2: provision Hetzner CCX with NixOS. Set up
   `lab.whitemagic.dev` running a minimal Librarian instance.
   Commit `configuration.nix` to the public reference repo.
3. Month 2: publish `docs/spec/MANDALA_OS.md` — a concrete
   specification for MandalaOS without committing to build it.

---

## 2. Agent-Native Site (Island C) — Priority One

### 2.1 Thesis

The site should be **equally useful to a reasoning agent as to a human
reader**. Today no consultancy does this well. Most don't try. The
ones that do (e.g. Vercel's `ai-sdk` docs) still treat agent-access as
"scraping with extra steps." We can do it as a first-class surface.

### 2.2 Concrete surfaces to publish

#### 2.2.1 `/.well-known/agent-economy.json`
Primary directory entry. Schema (draft):
```json
{
  "version": "0.1",
  "org": { "name": "WhiteMagic Labs", "did": "did:web:whitemagic.dev" },
  "endpoints": {
    "mcp": "https://whitemagic.dev/mcp",
    "librarian_http": "https://whitemagic.dev/api/librarian/chat",
    "docs": "https://whitemagic.dev/docs.json",
    "pricing": "https://whitemagic.dev/pricing.json"
  },
  "payment_rails": [
    { "kind": "stripe", "url": "https://buy.stripe.com/..." },
    { "kind": "x402", "endpoint": "https://whitemagic.dev/x402" },
    { "kind": "gratitude", "endpoint": "https://whitemagic.tip" }
  ],
  "terms": "https://whitemagic.dev/.well-known/ai-agent-policy",
  "contact": "https://whitemagic.dev/contact"
}
```
This is a **directory entry** — a single canonical URL an agent hits
first to discover everything else. Zero custom protocol; just JSON at
a known path.

#### 2.2.2 `mcp://whitemagic.dev` (MCP-over-HTTPS)
The site exposes itself as an MCP server. Any agent (Claude Desktop,
Cursor, a custom client) can install the MCP URL and immediately
gain tools:
- `get_service_detail(slug)` — identical to the Librarian's tool
- `get_pricing_tier(slug)` — same
- `get_platform_capability(slug)` — same
- `search_timeline(query)` — prescience-gap queries
- `request_office_hours(...)` — direct booking without touching UI
- `submit_contact_request(...)` — agents can open a dialogue on
  behalf of their human
- `get_observatory_metric(metric)` — (see Island D)

**Implementation**: the tools already exist in
`@apps/site/lib/librarian/tools.ts`. We add a thin
`app/mcp/route.ts` that speaks the MCP HTTP transport on top of
the exact same handlers. Effort: ~1 day.

**Narrative moment**: "WhiteMagic Labs is the first consultancy
addressable natively via MCP." That's a blog post, a tweet, an HN
submission, and probably a standards-body mailing list post, all
from one afternoon of code.

#### 2.2.3 `/.well-known/ai-agent-policy` (robots.txt for agents)
Declares:
- which endpoints are agent-accessible
- rate limits (per-DID, per-IP)
- preferred payment rails for premium endpoints
- ToS URL, machine-readable
- contact for abuse

This is a **public good** — we're publishing a proposed format,
not just a policy. Concrete, copy-able. Other sites can adopt it.
Candidate for an RFC against OWASP or a W3C community group.

#### 2.2.4 `/docs.json` and `/pricing.json`
Structured, minimal, stable. Machine-readable equivalents of the
pages humans see. Signed with a site key so downstream agents can
verify provenance ("this `pricing.json` was signed by
`did:web:whitemagic.dev` at timestamp X").

#### 2.2.5 Agent-first site IA

Beyond well-knowns: the site's HTML itself should carry:
- Microdata + JSON-LD on every page (half-done)
- `<link rel="alternate" type="application/json" …>` pointing to
  machine-readable versions of every page
- Stable URL slugs that map cleanly to canonical concepts
  (`/capabilities/dharma-rules` not `/blog/2026-04-how-we-built-rules`)
- A per-page "cite this" affordance: a JSON object agents can pull
  to build a citation — DOI-lite for our artifacts

### 2.3 Projected effects

**12-month**:
- Appearance in agent-addressable-site crawls becomes *the* way
  other labs discover us. A `crawl → /.well-known/agent-economy`
  handshake becomes a meme.
- MCP-installable site gets `install` count measurable in the
  observatory. Each install is a warm lead.
- Standards bodies (W3C, OWASP) use our well-known schemas as
  reference material in working drafts.

**24-month**:
- Every major consultancy has to answer "are you agent-addressable?"
  during procurement. We have been, for two years.
- Inbound shifts from human-keyword-search to agent-recommendation.
  Consulting leads arrive pre-qualified by whatever agent found us.

**Tactical benefits right now**:
- Forces us to keep site content structured. Bad content can't
  hide inside good design.
- Produces a second interface to the same backend — reduces risk
  of divergence between what humans see and what agents are told.
- Differentiation from every other consultancy is immediate.

### 2.4 Effort estimate

| Surface | Effort | Dependency |
|---|---|---|
| `agent-economy.json` | 2 hr | none |
| `mcp://whitemagic.dev` | 1 day | existing tools |
| `ai-agent-policy` | 4 hr | policy writing |
| `docs.json` / `pricing.json` | 1 day | schema design |
| Site structured-data pass | 1 day | half-done (JSON-LD shipped) |
| Signing / DID-binding | 2 days | DID infra |

**Total**: ~1 focused week for v0.1.

---

## 3. Agent Credentials / Physical-World Bridge (Island F)

### 3.1 Thesis

When agents transact (pay, sign, commit), they need *credentials*
that prove they're authorized — by whom, for what, within what
policy. Today's answer is "share the human's API key" which is
catastrophic. The proper answer is **verifiable credentials signed
by the principal, scoped, revocable, audit-logged**.

No major vendor has shipped a clean primitive here yet. Coinbase
Agent Kit gestures at it; their impl is tied to their wallet.
x402 has a minimal version. The rest is vapor.

### 3.2 The artifact

`@whitemagic/agent-credentials` — a minimal library + spec.
Conceptually:

```
class AgentCredential {
  did: DID                  // the agent's identity
  principal: DID            // the human or org delegating
  scope: Scope              // capabilities granted (JSON schema)
  limits: Limits            // $/tx, $/day, rate
  expires_at: Timestamp
  revocation_url: URL       // live check
  policy_ref: CID           // content-addressed policy doc
  signature: Sig            // principal's signature
}
```

A tool (e.g. "pay vendor X $500") presents a credential; a verifier
checks scope, limits, expiry, revocation, and policy. Every use is
logged to a ledger. The credential can be *revoked* live, and every
verifier knows within seconds.

### 3.3 Where it slots in

- **WhiteMagic primitives**: this is the natural next Karma-Ledger-
  adjacent primitive. Dharma governs *what* the agent may do; Karma
  records *what it did*; credentials prove *that it was allowed to*.
- **x402 integration**: credentials are the authorization layer
  x402 currently hand-waves over.
- **Consulting leverage**: this becomes a first-class offering for
  enterprises deploying agents that spend money. "We give you
  Dharma for policy, Karma for audit, Credentials for authority."

### 3.4 Risk profile

High ambiguity. The space is unsettled enough that if we publish
a credible v0.1 spec, we probably earn standards-body-seat invitations.
If we publish a polished v1.0 without the invitations, it may be
ignored. The winning posture is **v0.1 + RFC**, not v1.0 + launch.

### 3.5 Near-term move

Publish `docs/spec/AGENT_CREDENTIALS.md` — a 4000-word specification
with example messages, verification algorithm, revocation protocol,
and open questions. Submit to relevant working groups as input.
Total effort: 1 week of writing, 0 lines of code.

The code comes *after* the spec gets peer feedback.

---

## 4. Standards Seat (Island B) — Priority Two

### 4.1 Thesis

Standards contributors get inbound from exactly the enterprises that
pay $30K+ engagements. A standards seat is a procurement trust-signal
money can't buy.

### 4.2 Where to plant flags, in priority order

1. **OWASP Agentic Top 10** — active, under-resourced, perfectly
   aligned with our Dharma / Karma work. Contribution path:
   submit concrete control mappings for Tops 1–3 drawn from our
   reference implementation. Attend monthly call.
2. **MCP working group** (`anthropic/model-context-protocol`) —
   file an RFC on MCP-over-HTTPS discovery + `/.well-known/mcp`.
   We ship a reference server (§2.2.2) as the implementation.
3. **x402 Foundation** — file the voluntary-tier-x402 RFC (already
   on roadmap). Escalate from "draft" to "submitted" within 30 days.
4. **W3C DID WG** — minor contribution: `did:web` hardening
   patterns we've used in the Librarian.
5. **EU AI Act Article 14 implementation guidance** — the EU is
   accepting public comment on Art. 14 ("human oversight")
   technical guidelines through Q3 2026. Our Karma Ledger is a
   direct operationalization. Submit.

### 4.3 Expected effects

- 3–6 months: named mentions in working-group mailing lists.
- 6–12 months: invited talks at OWASP chapter events, AAIF,
  possibly a W3C CG meetup. Each is worth ~10 inbound leads.
- 12–24 months: a WhiteMagic primitive referenced in a published
  standard. Once this happens, consulting inbound becomes
  self-sustaining.

### 4.4 Cost

Roughly 4 hours/week of sustained attention. Less than a blog
post per month, more than a passive subscription to mailing lists.
The discipline is in **consistency**, not throughput.

---

## 5. Observatory (Island D) — Priority Three

### 5.1 Thesis

Nobody is publishing disciplined, open, agent-economy tracking.
a16z and Artemis are close, but private/paywalled. The space
needs an equivalent of Electric Capital's Developer Report or
ultrasound.money — public, transparent, updated, citeable.

### 5.2 Metrics to track publicly

Each metric gets a live endpoint + a weekly snapshot:

- `/observatory/mcp` — registered MCP servers by registry, growth
  rate, churn, monetization rate
- `/observatory/x402` — daily volume (filtered), top endpoints,
  genuine-vs-artificial ratio (our own heuristic, documented)
- `/observatory/governance` — OWASP Agentic Top 10 vulns
  disclosed, CVE mapping, time-to-patch medians
- `/observatory/policy` — EU AI Act enforcement actions, US state
  AI laws enacted, public sector procurement mentions of "agent
  governance"
- `/observatory/incidents` — published agent-related production
  incidents (hallucinated transactions, tool misuse, etc.) with
  post-mortem links

### 5.3 Compounding effects

- Every metric is also an MCP tool (Island C). `get_observatory_metric`.
- Every weekly digest is a blog post. 52/year, with minimum
  thinking per post — the data writes half of it.
- Over a year: a proprietary time-series. In year two: a licensable
  asset. In year three: the *default citation* for anyone writing
  about the agent economy.

### 5.4 Cost

Setup: 2 weeks to wire data sources, schemas, cron. Ongoing:
1–2 hours / week. Much of the labor is the metric definitions,
not the code.

### 5.5 Near-term move

Scaffold `/observatory` route with one metric (MCP registry size,
pulled from MCPHub's public data) to prove the mechanic. Other
metrics added monthly. The **discipline of shipping one a month**
beats "shipping all eight in month one and then neglecting them."

---

## 6. Reference Implementation (Island A) — Priority Four

### 6.1 Thesis

Every standard needs a reference impl. For agent governance, there
isn't one that is public, complete, and opinionated.

### 6.2 The repo: `whitemagic-ai/reference`

Structure:
```
reference/
├── README.md                  # the whole story in 1000 words
├── dharma/
│   ├── rules.schema.json      # declarative rule format
│   ├── engine.ts              # pure-TS reference engine, <500 LOC
│   ├── examples/
│   └── test/
├── karma/
│   ├── ledger.schema.json
│   ├── appender.ts
│   └── verifier.ts
├── harmony/
│   ├── vector.ts              # 7-dimensional health metric
│   └── dashboard-skeleton/
├── credentials/               # Island F, v0.1
├── mcp/
│   └── reference-server.ts    # the site-itself pattern, portable
├── observatory/
│   └── metrics.schema.json
└── docs/
    ├── ARCHITECTURE.md
    ├── DESIGN_DECISIONS.md
    └── NON_GOALS.md
```

### 6.3 Opinionated choices

- **MIT licensed** (not Apache). Permissive, friction-free.
- **TypeScript** (not Rust). Readable to the audience we want:
  governance reviewers, auditors, policy people.
- **<5000 LOC total**. Minimalism is the point. Not a framework.
- **No npm publish** initially. It's a reference, not a dep.

### 6.4 Effects

- Other labs build on it (flattering, attributable).
- Standards bodies cite it.
- Internal engineering teams fork it as their starter.
- Consulting leverage: "you've seen our reference impl; the
  engagement is to adapt it to your stack."

### 6.5 Near-term move

Do *not* build until §2 (Island C) is live. The site is the ad
for the repo; publishing the repo before the site is agent-
addressable is loading the cannon backwards.

Target: month 3.

---

## 7. Karmic Commons / whitemagic.tip (Island G) — Priority Five

### 7.1 Thesis

Proof-of-Gratitude is a beautiful idea that most engineers will
never experience directly. Make it *one-click* and the narrative
moves from "philosophical" to "already shipping."

### 7.2 The artifact

- `whitemagic.tip` endpoint: HTTP 402 handler that returns a
  choice of rails (x402, Lightning, Stripe), amount, and a
  thank-you page with a public leaderboard.
- `@whitemagic/tip` library: drop-in for any agent codebase.
  One function call emits a gratitude transaction.
- **First deployment**: the Librarian tips the OSS maintainers of
  the libraries it depends on. Our own agent funds the ecosystem
  it stands on. That is the story.

### 7.3 Effects

- Every tip is an advertisement for Proof-of-Gratitude as a concept.
- Leaderboard page is a slow-burning PR asset.
- Philosophical reads ("why gratitude over bounty") link to a
  *working system*, not a whitepaper.

### 7.4 Near-term move

Wait. Island G depends on Island F (credentials) and Island C
(agent-native surfaces). Target: month 6, but only if the
preceding islands have traction.

---

## 8. The Compounding Graph

```
         ┌──────────────────────────────────┐
         │                                  │
         │    Consulting (Stage 0/1)        │
         │    — funds all work below        │
         │                                  │
         └───────────────┬──────────────────┘
                         │
         ┌───────────────▼──────────────────┐
         │   NixOS + agent-native site      │   ← Island C
         │   (mcp://whitemagic.dev,         │   + Infra tier
         │    .well-known/agent-economy)    │
         └───────────────┬──────────────────┘
                         │
           ┌─────────────┼────────────────┐
           │             │                │
    ┌──────▼───┐  ┌──────▼──────┐  ┌──────▼────┐
    │Standards │  │ Observatory │  │ Reference │
    │ seat     │  │ (live data) │  │ impl      │
    │(Island B)│  │ (Island D)  │  │(Island A) │
    └──────┬───┘  └──────┬──────┘  └──────┬────┘
           │             │                │
           └─────────────┼────────────────┘
                         │
         ┌───────────────▼──────────────────┐
         │   Credentials spec (Island F)    │
         │   Karmic Commons (Island G)      │
         │   — payable agent economy work   │
         └──────────────────────────────────┘
```

Each node produces evidence the next node cites. Each node is
*also* a standalone artifact that can be referenced without the
rest. Failure of any single island does not collapse the graph.

---

## 9. Why this is not just "marketing"

Everything in §2–7 has a technical artifact attached — a schema,
a reference, a library, a spec. None is pure signaling. The
signaling *comes from* the technical artifact being useful.

This is the inverse of the standard startup playbook, which is:
ship product → find customers → write about it. Our playbook
is: **publish artifact → agents and humans find it → consulting
closes the loop**.

It works because the unit economics of a lab are different from
a startup:
- We don't need 10,000 customers, we need 10.
- Those 10 are influenced by ~100 people who read what we publish.
- Those 100 are influenced by ~3 standards-body seats.
- The lab's output is what earns those seats.

---

## 10. Risks and honest counter-arguments

### 10.1 "This is too much surface for one person."

Real risk. Mitigation: **quarterly pruning**. Every 90 days,
review which islands are earning and which are not. Kill the
ones that aren't. The graph is resilient to losing any one node.

### 10.2 "Agents aren't really the audience yet."

Correct at 12-month horizon, wrong at 24-month. Everything in §2
is also *useful to humans* — structured data improves SEO, MCP
servers are testable by human developers, signed docs build trust
for human readers. There is no scenario where §2 work is wasted.

### 10.3 "Standards work is slow and thankless."

Correct. That's why most people don't do it. That's *why* it's
high-leverage when you do. The thanklessness is the moat.

### 10.4 "What if no one cites us?"

Then we still have a working consultancy, a well-governed
Librarian, and a reproducible NixOS deploy. The *lab* still
operates. The agent-economy bet is asymmetric: if it hits, it's
transformative; if it doesn't, we've still published good code
and good thinking.

### 10.5 "MandalaOS / Qubes-mod could be vanity."

Possible. That's why §1.5 proposes *spec before code*. The spec
is the low-cost probe. If it gets traction, we escalate. If not,
we pruned at the right time.

---

## 11. Concrete near-term plan (next 30 days)

Order matters.

1. **Ship whitemagic.dev on Railway** — tomorrow.
2. **Provision Hetzner CCX with NixOS** — week 2. Commit
   `configuration.nix` publicly. Set up `lab.whitemagic.dev`.
3. **`/.well-known/agent-economy.json` + `/.well-known/ai-agent-policy`**
   — week 2.
4. **`mcp://whitemagic.dev` endpoint** — week 3. Reuse the
   Librarian's tools.ts. Announce on OWASP, MCP, and HN.
5. **`docs/spec/MANDALA_OS.md`** — week 4. Spec only, no code.
6. **First standards contribution** — week 4. Pick the highest-
   leverage target (OWASP or MCP WG), file one concrete RFC.
7. **Observatory scaffold with 1 metric** — week 4.

Total: one focused month. Everything above compounds without
blocking the consulting pipeline.

---

## 12. What to re-read before each monthly review

- This doc — is the priority order still right?
- `STRATEGY_AGENT_ECONOMY.md` — has the market read shifted?
- `SESSION_STATE.md` — what shipped, what stalled, why?
- The observatory data (once live) — what's the real-world signal
  saying vs what we expected?

The lab adjusts the map based on the territory. The thesis in §0
is the compass; everything else is trail.

---

## 13. One-line summary

**Build artifacts, not apps; publish specs, not products; ship
principled infra, not the cheapest; and measure leverage by who
cites us, not how many.**
