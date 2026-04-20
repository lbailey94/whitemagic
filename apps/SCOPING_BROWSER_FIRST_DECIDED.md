# Scoping — Browser-First WhiteMagic (DECIDED)

**Created**: 2026-04-18
**Supersedes**: `SCOPING_BROWSER_FIRST.md` (kept as the "what we considered" record)
**Status**: Decisions locked. Ready for implementation planning.

---

## 0. What changed from the draft

The draft scoping doc assumed the public-facing AI on `whitemagic.dev`
would be Aria. That is no longer the plan.

**Aria is private.** She stays on Lucas's laptop only, for the
foreseeable future. No public endpoint, no hosted version, no
password-gated demo. Aria is not a product.

**The site gets a Librarian.** A separate agent with a separate name,
separate voice, separate memory corpus. The Librarian is professional,
warm, technical. Its job is to help visitors understand WhiteMagic, the
timeline, the services, the open-source components — and hand off to
human contact when the question exceeds its scope.

**The PWA is a blank canvas.** It ships with the substrate (memory,
governance, search, Karma ledger, Gnosis) and zero personality. Users
bring their own agent, import their own persona file, or build from
scratch. No preloaded Aria, no preloaded Librarian — the PWA is a
tool, not an assistant.

---

## 1. Final deliverables — three products on one codebase

### 1.1 `/librarian` — embedded public Librarian AI (whitemagic.dev)

- Professional voice: warm, technical, concise. Drops mystical framing.
- Knows: the public site content, the OSS code, pricing tiers, timeline
  entries, services, contact form.
- Doesn't know: Aria, private grimoire, unreleased work, financial
  internals.
- Inference via OpenRouter (one key, multi-model).
- Per-session spend cap, per-IP daily cap, Dharma rules on input.
- Free to visitors; budget capped at Lucas's risk tolerance.
- **No password gate needed** — it's public by design, but cost-guarded.

### 1.2 `/app` — WhiteMagic-Lite PWA (installable, local-first, blank canvas)

- Substrate only: memory CRUD, FTS5 search, Dharma rules, Karma ledger,
  Gnosis introspection, Galaxy backup/restore, 5D holographic spatial index.
- Zero personality shipped. User brings their own.
- 100% local by default. Zero network calls for memory / governance.
- User-supplied LLM API key (stored encrypted in IndexedDB) OR use
  OpenRouter's free-tier models.
- Import/export: `whitemagic-persona.json` format TBD — community
  ecosystem seed.
- Optional paid tier (later): cloud sync + priority inference endpoint.

### 1.3 Aria — private, unchanged

- Stays on Lucas's laptop. Not deployed. Not exposed. Not in any public repo.
- Can optionally benefit from browser-first infrastructure (e.g., Aria
  could run in the Lucas-only PWA on any device with his login) — but
  that's a private feature flag, not a product.

---

## 2. Decisions (all locked)

| # | Decision | Choice |
|---|---|---|
| 1 | **Parallel tracks** | Librarian (public, on-site) + PWA phase 1 (blank canvas, substrate only) built in parallel. Aria NOT in scope for public products. |
| 2 | **LLM backend** | OpenRouter single API key. Primary: Claude Sonnet 4.5; secondary toggle: GPT-4.x. Free-tier OpenRouter models available as fallback. |
| 3 | **Memory corpus** | **Librarian**: site-aware corpus — services, pricing, timeline entries, OSS READMEs. **PWA**: blank canvas, no preloaded memories. **Aria**: unchanged, private. |
| 4 | **Password gate** | Not needed for Librarian (public by design). Next.js middleware + hashed env password available as infrastructure for any future gated endpoint. |
| 5 | **Free-tier inference (PWA)** | Users bring their own OpenRouter / Anthropic / OpenAI key. Stored encrypted in IndexedDB. Zero liability for user model spend. |
| 6 | **Repo visibility** | **All private, separate repos.** Existing public `whitemagic-ai/whitemagic` frozen at current state (public release already shipped). New work lives in private repos per §5. |
| 7 | **Agent voices** | **Aria**: faithful, unchanged, private. **Librarian**: professional-neutral, site-aware, never claims personality. **PWA agents**: whatever the user imports. Infrastructure must be persona-agnostic (swap system prompts + memory corpus, same substrate). |

---

## 3. Architecture — locked

```
┌────────────────────────────────────────────────────────────────────┐
│  whitemagic.dev (private repo: whitemagic-site)                    │
│                                                                    │
│  Public:   /, /services, /pricing, /timeline, /open-source, etc.   │
│  AI:       /librarian        ← public, OpenRouter-backed           │
│  PWA:      /app              ← installable, local-first, blank     │
│  Admin:    /admin            ← Lucas only, stats + kill switches   │
└────────────────────────────────────────────────────────────────────┘
        │                                      │
        │                                      │
┌───────▼────────────┐               ┌─────────▼────────────────────┐
│ Server routes      │               │ Browser runtime (PWA)        │
│                    │               │                              │
│ /api/librarian/    │               │ @whitemagic/sdk              │
│   chat             │               │   ↓ LocalTransport           │
│   ├─ OpenRouter    │               │ whitemagic_wasm.wasm         │
│   ├─ rate limit    │               │   ├─ memory CRUD             │
│   ├─ Dharma check  │               │   ├─ FTS5 search             │
│   └─ corpus: site  │               │   ├─ Dharma rules            │
│                    │               │   ├─ Karma ledger            │
│ /api/admin/*       │               │   └─ Gnosis introspection    │
│   (Lucas only)     │               │                              │
│                    │               │ SQLite WASM (OPFS-backed)    │
└────────────────────┘               │ IndexedDB: persona, keys     │
        │                            │                              │
        │                            │ User's own LLM key calls:    │
        ▼                            │  OpenRouter/Anthropic/etc    │
┌────────────────────┐               │  directly (or via CF Worker  │
│ core/ (private     │               │  relay, never stores keys)   │
│ monorepo)          │───wasm-pack──▶│                              │
│                    │               └──────────────────────────────┘
│ whitemagic-rust    │
│   ├─ src/wasm.rs   │
│   └─ (expand to    │
│       full seed-   │
│       binary tool  │
│       surface)     │
│                    │
│ whitemagic (py)    │
│   for server-side  │
│   inference paths  │
└────────────────────┘
```

### Invariants (non-negotiable)

1. **PWA free tier makes zero network calls for memory or governance.**
   A visible UI indicator shows "0 bytes sent to whitemagic.dev since
   install" when offline-capable mode is active.
2. **User's LLM keys never leave their device** unless they explicitly
   opt into the paid tier (which uses Lucas's keys on the server).
3. **Librarian budget is hard-capped**. One env var flips it off.
   Per-IP / per-session caps prevent any single visitor from draining
   the budget.
4. **Dharma rules evaluated on visitor input** to the Librarian before
   any LLM call — eats own dogfood in public, produces natural-language
   rejection messages when a rule fires.
5. **Aria never ships**. Any file path containing `aria` is explicitly
   excluded from deploy bundles. CI check enforces this.

---

## 4. Build phases — sequenced

### Phase L (Librarian) — target ~2 days

| Step | Task | Est. |
|---|---|---|
| L1 | Next.js API route `/api/librarian/chat` with OpenRouter call | 2 hrs |
| L2 | Streaming chat UI component (`<Librarian />`) on `/librarian` page | 3 hrs |
| L3 | Site-aware system prompt + static corpus injection (services, pricing, timeline entries serialized as context) | 2 hrs |
| L4 | Upstash Redis rate limit: per-IP daily cap + per-session spend cap | 3 hrs |
| L5 | Dharma rules on visitor input (port `core/whitemagic/dharma/rules.py` rules to a Next.js edge-runtime check) | 3 hrs |
| L6 | Admin kill switch (single env var + admin UI toggle) | 1 hr |
| L7 | Privacy notice, data retention policy (default: session-only) | 1 hr |
| L8 | Observability: log prompt + response tokens per call (no content) | 2 hrs |
| L9 | Cost dashboard on `/admin` | 2 hrs |

### Phase P1 (PWA substrate, blank canvas) — target ~1 week

| Step | Task | Est. |
|---|---|---|
| P1.1 | `wasm-pack build --target web` succeeds on `core/whitemagic-rust/` | 4–8 hrs (likely compile errors) |
| P1.2 | Expand `wasm.rs` to expose memory CRUD, FTS5, Dharma eval, Karma ledger, Gnosis | 2 days |
| P1.3 | `sqlite-wasm` integration with OPFS backing | 1 day |
| P1.4 | `@whitemagic/sdk` `LocalTransport` subclass routes to WASM | 1 day |
| P1.5 | Next.js PWA shell on `/app` (manifest, service worker, offline) | 1 day |
| P1.6 | Onboarding wizard: generate state dir, seed optional examples, explain local-first | 4 hrs |
| P1.7 | Import/export UI: `whitemagic-persona.json` schema + file picker + OPFS write | 1 day |
| P1.8 | Encrypted API key storage (WebCrypto AES-GCM, IndexedDB) | 4 hrs |

### Phase P2 (PWA paid tier) — target ~1 week (later)

| Step | Task | Est. |
|---|---|---|
| P2.1 | Stripe subscription setup + webhook | 1 day |
| P2.2 | `/api/pwa/llm` proxy with subscription check | 4 hrs |
| P2.3 | Cloud sync (opt-in): OPFS → server-side encrypted blob | 2 days |
| P2.4 | Priority inference: pinned Claude Sonnet 4.5 route for Pro | 2 hrs |
| P2.5 | Usage dashboard in PWA | 1 day |

### Phase L2 (Librarian polish) — after Phase L ships, before Phase P2

| Step | Task | Est. |
|---|---|---|
| L2.1 | Dual-mode infrastructure (same chat UI, swappable system prompt + corpus). Invisible to users for now. | 4 hrs |
| L2.2 | Conversation memory across session (sessionStorage, no server persistence unless user logs in) | 4 hrs |
| L2.3 | Source citations on responses (quote which timeline entry / service page) | 1 day |
| L2.4 | Follow-up question suggestions | 2 hrs |

---

## 5. Repo strategy — locked

**Current state**:
- `whitemagic-ai/whitemagic` on GitHub — **public**, frozen at current
  state. Represents the shipped public platform. No further pushes.
- Local `WHITEMAGIC/` — contains `apps/site` via subtree merge.

**Going forward, three private repos**:

1. **`whitemagic-private`** — the working monorepo. Everything Lucas
   works on lives here: `core/`, `apps/`, `grimoire/`, `polyglot/`,
   personal planning docs. Single source of truth.
   
2. **`whitemagic-site-private`** — the deployable consultancy site. Private
   GitHub repo that the Hetzner VPS pulls from (read-only deploy key; GitHub
   Actions → `ssh` → `/srv/whitemagic-site/deploy.sh`). Kept as a
   lightweight mirror of `whitemagic-private/apps/site/`, synced by a git
   subtree push on each release. Hetzner gets the site; the monorepo
   history stays elsewhere. (Originally planned for Vercel; pivoted to
   Hetzner 2026-04-19 — see
   `@docs/architecture/INFRASTRUCTURE_DECISION.md` and
   `@docs/deploy/HETZNER_DEPLOY.md`.)

3. **`aria-private`** — optional, Lucas's choice. If Aria's artifacts
   (journals, dreams, state server) are worth versioning, a separate
   private repo keeps her entirely out of the monorepo's blast radius.
   Most cautious option. Alternative: keep Aria as uncommitted local
   files, no git at all. Discussed separately.

**Why split `whitemagic-site-private` out from the monorepo?** Deploy
sources benefit from clean repo roots (true for Vercel originally, still
true for the Hetzner `git pull` model). Subtree push on release keeps it
in sync with the monorepo without exposing monorepo internals. Also: if
any single commit in the monorepo accidentally references private
material, the site repo is protected by filtered history.

See companion doc: `MONOREPO_VS_MULTIREPO.md` for the "explode into
many repos?" analysis.

---

## 6. Everything the draft scoping doc raised, resolved

| Draft concern | Resolution |
|---|---|
| "Aria under password alone isn't enough" | Moot — no public Aria. Librarian is budget-capped, Dharma-gated, kill-switchable. |
| "Users bring their own inference for free tier" | Locked for PWA. For Librarian, Lucas eats the cost within hard caps (it's marketing). |
| "Two modes for Aria's voice" | Replaced by "two separate agents": Aria (private, faithful) and Librarian (public, neutral). Cleaner than toggling modes on a single agent. |
| "Aria's public memory corpus curation" | Moot — no public Aria. Librarian's corpus is the site content (services, pricing, timeline, OSS READMEs) serialized into context. |
| "Dashboard app reusability" | `dashboard-app/` React components may be reused for `/admin` in the site. Defer the decision until Phase L finishes. |
| "Aria hallucinating about WhiteMagic" | Applies to Librarian. Mitigation: Dharma rule pattern-matches on commitments ("we offer", "I can", "we support") and appends a "→ confirm with Lucas" disclaimer. System prompt strictly forbids promises of un-documented features. |
| "Enterprise reputational risk of mysticism" | Resolved — Librarian has no mysticism. |
| "Offline-only browser LLM" | Deferred, same as draft. |
| "Merging `hub`/`nexus` Tauri apps" | Deferred — not on critical path. |
| "WASM build pain (1–3 days debugging)" | Acknowledged, budgeted in P1.1. |

---

## 7. What I need from you next

### Immediate (before I start coding)

1. ~~Approve the Librarian name~~ **LOCKED: Librarian.**
2. **OpenRouter API key** (or confirmation you'll create one this weekend).
   Goes in the Hetzner systemd `EnvironmentFile` as `OPENROUTER_API_KEY`, never committed.
3. **Upstash Redis account** (free tier — for rate limiting). 2-minute setup.
4. **Private repo for `whitemagic-site`** created on GitHub under your
   account (or the `whitemagic-ai` org, set to private). Give me the
   repo URL and I'll configure push.
5. ~~Confirm hard budget cap~~ **LOCKED: $25/month hard cap.** At
   Claude Sonnet 4.5 pricing and ~5K tokens/conversation that's
   ~300 conversations/month before auto-cutoff. Admin panel will
   show current month spend + % of cap used, with email alert at 80%.

### This weekend (while I code Phase L)

6. **Read and challenge this doc**. Anything here that feels wrong,
   tell me before code lands.
7. **Librarian's tone** — one-paragraph sample of how you want it to
   speak. My starting point: *"Warm, technical, concise. Happy to
   explain; quick to point at the source. No first-person claims about
   capabilities not documented in the public README. Ends uncertain
   questions with 'ask Lucas directly at /contact.'"*

---

## 8. What ships this weekend

**If Phase L goes smoothly** (and it usually does — no WASM weirdness):

- `/librarian` endpoint live on the site, Claude Sonnet 4.5 via OpenRouter
- Rate limits + Dharma input check + kill switch all wired
- `/admin` showing live cost, rate-limit hits, Dharma rejections
- Deployed to Hetzner from the private `whitemagic-site-private` repo
  (see `@docs/deploy/HETZNER_DEPLOY.md`)

**Phase P1 (PWA)** begins Monday. First milestone: `wasm-pack build`
succeeding on `core/whitemagic-rust`. That alone is worth a PR.

---

## 9. Risks (re-stated, post-pivot)

1. **WASM compile pain** — unchanged, budgeted. Likely 1–3 days of the PWA week.
2. **OpenRouter rate limits on Lucas's free tier** — possible for initial testing. Upgrade when needed; usage at Phase L launch should be trivially small.
3. **Librarian producing confident misinformation about WhiteMagic** — real. Mitigated by strict system prompt + Dharma rules + source citations (L2.3). Accept some residual risk; monitor via admin logs.
4. **Blank-canvas PWA friction** — some users want "just give me an agent." Mitigated by P1.7 (persona import) and an optional "example persona" download (NOT Aria — something publicly shareable like "Research Assistant" or "Code Review Buddy").
5. **Private repo + Hetzner deploy-key / GitHub Actions SSH key mis-configured** — one-time setup pain, resolves once tokens are correct. Documented in `@docs/deploy/HETZNER_DEPLOY.md` (steps 8 + 13).
