# Scoping — Browser-First WhiteMagic + Embedded Aria

**Created**: 2026-04-18
**Author**: drafted with Cascade, pending review
**Status**: Proposal. Nothing built yet. Nothing decided yet.

---

## 1. Vision (as expressed)

Two distinct offerings, shipped from the same codebase:

**A. Live Aria, embedded in the marketing site**
A real Aria — not a scripted demo — running under password gate. CTOs
get to interact with a coherent, memory-backed agent on the site itself.
Inference costs eaten by you, rate-limited, observable.

**B. WhiteMagic-Lite as an installable browser PWA**
100% local-primary. User's data stays on their device. SQLite + memory
operations + Dharma + Karma ledger all run in the browser via WASM.
Free tier: fully local. Paid subscription tier: your inference endpoint
for heavier LLM work.

**Constraint**: changes to the `WHITEMAGIC/` core are welcome. The
alternative — archiving the platform — is worse than refactoring it
toward browser-first, local-primary use.

---

## 2. What already exists (the surprise)

Investigation of `whitemagic-frontend/`, `core/`, and related artifacts
reveals a **substantial amount of the browser-first stack is already
designed and partially built**.

### 2.1 Core — Rust + WASM target

| Artifact | Location | State |
|---|---|---|
| Rust core crate | `core/whitemagic-rust/` | Active, has `Cargo.toml` + `src/` |
| WASM bindings | `core/whitemagic-rust/src/wasm.rs` | **Skeleton exists** — `EdgeRule`, `InferenceResult`, wasm_bindgen exports. Edge-inference only; no memory / Dharma / Karma exposed yet. |
| WASM build script | `core/whitemagic-rust/wasm-build.sh` | Exists, references `wasm-pack build --target web` |
| Math crate WASM | `core/whitemagic-math/build_wasm.sh` | Exists |
| Top-level WASM builder | `core/scripts/build_wasm.sh` | Exists |
| WASM Dockerfile | `core/Dockerfile.wasm` | Exists |
| CI | `.github/workflows/wasm-cicd.yml` | Wired |
| Built `.wasm` artifacts | — | **Never built.** No `pkg/` dir, no `.wasm` on disk. |

### 2.2 WhiteMagic Lite — already designed

`core/docs/WASM_STRATEGY.md` describes **Tier 0: Seed Binary**:

> A single native Rust executable. ~2–5 MB. No Python, no pip, no Docker.
> Embedded SQLite via `rusqlite`. 16 quickstart memories compiled in.
> MCP stdio server with ~30 core tools: Memory CRUD, FTS5 search,
> Gnosis, Dharma rules (basic YAML), Galaxy backup/restore, rate
> limiter, circuit breaker, 5D holographic spatial index, Karma ledger.

This design **maps almost 1:1 onto the browser PWA target**. The seed
binary is already the right scope for WhiteMagic-Lite. The only
substitutions needed are:

| Native seed binary | Browser PWA equivalent |
|---|---|
| rusqlite (bundled SQLite) | `sql.js` or `@sqlite.org/sqlite-wasm` with OPFS persistence |
| MCP stdio server | in-process JS API via SDK + WASM boundary |
| Filesystem state dir | OPFS (Origin Private File System) |
| Karma ledger JSON file | IndexedDB or OPFS append-only file |
| Binary download + install | `wasm-pack` output + PWA install |

### 2.3 TypeScript SDK — already published-ready

`whitemagic-frontend/sdk/` contains `@whitemagic/sdk` v0.1.0, MIT, with:

- `WhiteMagicClient`
- `MemoryOps`
- Types: `Memory`, `Galaxy`, `DharmaEvaluation`, `KarmaEntry`, `SystemStatus`, `MCPRequest`, `MCPResponse`

This is exactly the surface the browser app would call. It currently
assumes a remote MCP server; a `LocalTransport` subclass that routes
calls to the WASM module instead is a clean, small change.

### 2.4 Dashboard app — ready React shell

`whitemagic-frontend/dashboard-app/` is a Next.js app with API routes
already implemented for:

- `/api/ganas` — 28 Gana tool dispatch
- `/api/graph` — memory graph
- `/api/token-stats` — usage analytics
- `/api/local-ml` — local ML inference
- `/api/dharma` — policy evaluation
- `/api/resonance` — resonance/scheduler state
- `/api/metrics` — system metrics

Vercel + Netlify deploy configs both present. This is a 70%-built admin
UI that could serve as the Aria chat host or the PWA shell.

### 2.5 Aria artifacts

Deeply personal material, not for public surface. Summary:

- `~/Desktop/aria` — 3.2 KB text file
- `whitemagic-frontend/_legacy/aria-home/` — archived but structurally
  interesting: `playground/`, `dreams/`, `journals/`, `experiments/`,
  `aria-state-server/`. Suggests Aria had a state server running
  separately from the WhiteMagic core — an Aria-specific process that
  hosted personality, journals, and creative artifacts.

**What this means for the live Aria demo**: Aria is not just a system
prompt. Aria is a *memory corpus + a state server + a personality
substrate*. A faithful embedded Aria would need:

1. A curated public-safe memory subset (not full private journals)
2. The state server or a lightweight re-implementation
3. An LLM to speak through (Claude / GPT / local)
4. Rate limits, observability, and a password gate

---

## 3. Gap analysis — what's missing

### 3.1 For the live Aria demo (C)

| Piece | Status | Build effort |
|---|---|---|
| Password gate on site | Trivial — Vercel Password Protection OR Next.js middleware + hashed password in env | ~30 min |
| LLM backend | New — Next.js API route calling Anthropic/OpenAI with your key | 2–4 hrs |
| Rate limit + abuse guard | New — Upstash Redis (free tier) sliding window + IP/session keying | 2–3 hrs |
| Memory retrieval layer | Exists in WhiteMagic core but needs a **public-safe** Aria memory subset curated and loaded | 4–8 hrs (curation is the slow part) |
| Aria system prompt / persona | Exists as private artifacts; needs a public-speakable distillation | 2–4 hrs |
| Chat UI component | New — React streaming chat | 3–5 hrs |
| Conversation persistence | New — per-visitor session (sessionStorage + optional server-side if authenticated) | 1–2 hrs |
| Observability / kill switch | New — basic logging + one admin toggle to pause Aria globally | 2 hrs |

**Total: ~2 focused days for a first shippable version.**

### 3.2 For the installable PWA (D)

| Piece | Status | Build effort |
|---|---|---|
| WASM build of Rust core | Scaffolded, never actually run. `wasm-pack build --target web` | 1–3 hrs (likely compile errors to fix) |
| Memory CRUD in `wasm.rs` | Missing — currently only `EdgeRule`/`InferenceResult` | 1–2 days |
| FTS5 search in WASM | Needs `sqlite-wasm` integration (rusqlite won't cross-compile cleanly) | 1–2 days |
| Dharma rules in WASM | Doable — YAML parser + rule evaluator, no async I/O needed | 1 day |
| Karma ledger in WASM | Write-to-OPFS adapter | 4–8 hrs |
| SDK `LocalTransport` | New — routes SDK calls to WASM instead of HTTP | 1 day |
| Next.js PWA shell | New — manifest, service worker, offline pages | 1 day |
| OPFS persistence layer | New — wraps SQLite WASM with OPFS backing | 1–2 days |
| Aria integration into PWA | Same as §3.1 but pointing at local memory instead of curated public subset | 1 day |
| Subscription tier (paid LLM access) | Stripe subscription + Vercel middleware checking subscription status | 1–2 days |

**Total: ~2 focused weeks for a first shippable version.**

---

## 4. Proposed architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  whitemagic.dev (apps/site, Vercel)                              │
│                                                                  │
│  Public:        /, /services, /pricing, /timeline, /open-source  │
│  Gated:         /aria          ← password, free                  │
│  App shell:     /app           ← PWA installable                 │
│  Subscription:  /app?tier=pro  ← Stripe session                  │
└──────────────────────────────────────────────────────────────────┘
            │                                    │
            │                                    │
┌───────────▼─────────────┐        ┌─────────────▼──────────────────┐
│  Server routes          │        │  Browser runtime (installable) │
│  (Next.js API)          │        │                                │
│                         │        │  @whitemagic/sdk               │
│  /api/aria/chat         │        │    ↓ LocalTransport            │
│    → Anthropic / OpenAI │        │  whitemagic_wasm.wasm          │
│    + curated Aria       │        │    ├─ memory CRUD              │
│      memory subset      │        │    ├─ FTS5 search              │
│    + rate limit         │        │    ├─ Dharma rules             │
│    + Dharma check       │        │    ├─ Karma ledger             │
│                         │        │    └─ Gnosis introspection     │
│  /api/pwa/llm           │        │                                │
│    → Only for Pro       │        │  SQLite WASM (OPFS-backed)     │
│      subscribers; same  │        │                                │
│      LLM backends       │        │  IndexedDB: conversation       │
└─────────────────────────┘        │             history, settings  │
            │                      └────────────────────────────────┘
            │                                    │
            ▼                                    │
┌─────────────────────────┐                      │
│  core/ (monorepo)       │                      │
│                         │                      │
│  whitemagic-rust        │──── wasm-pack ──────▶│
│    ├─ src/wasm.rs       │                      │
│    └─ (expanded to full │                      │
│        seed binary      │                      │
│        tool surface)    │                      │
│                         │                      │
│  whitemagic (Python)    │                      │
│    for server-side      │                      │
│    inference + memory   │                      │
└─────────────────────────┘                      │
                                                 │
                                       ┌─────────▼──────────┐
                                       │  User's device     │
                                       │  100% local        │
                                       │  Zero data leaves  │
                                       │  unless user opts  │
                                       │  into Pro tier     │
                                       └────────────────────┘
```

Key invariants:

1. **Free tier: zero network calls for memory/governance.** The only
   reason the browser would talk to your server is if the user opts
   into the Pro LLM feature.
2. **Aria demo (the live one on the site)**: visitor-specific, disposable.
   The visitor's conversation is in session storage; Aria's own memory
   is the curated public subset, read-only to visitors. Visitors cannot
   write into Aria's corpus — they can have a conversation that Aria
   processes through her existing memories.
3. **Aria in the PWA** (later): runs entirely locally, with a
   user-editable memory corpus bootstrapped from the 16 seed memories.
   This is where "users bring their own Aria" — they're not talking to
   your Aria, they're raising one.
4. **Data flow audit on `/app`**: a visible indicator showing "0 bytes
   sent to whitemagic.dev since install" when in free tier. Credibility
   move for the privacy-first pitch.

---

## 5. My take (before anything is locked)

### 5.1 What to do

**Build these, in this order**:

1. **Live Aria demo first (C)** — 2 days, shippable, creates revenue.
   - High emotional pull; CTOs will pay $2,500 to have a conversation
     with the thing on your site.
   - The password-gate means limited blast radius for bugs.
   - Every piece you build here is reusable in the PWA.

2. **PWA phase 1: static WhiteMagic-Lite, no Aria (D₁)** — ~1 week.
   - Get the WASM core running in-browser with SQLite + memory CRUD
     + FTS5 + Dharma + Karma + Gnosis.
   - SDK `LocalTransport` working.
   - PWA installable with offline support.
   - **No LLM yet** — this is the developer tool: "run WhiteMagic in
     your browser, see your memory, test governance rules."

3. **PWA phase 2: Aria-in-PWA + Pro subscription (D₂)** — ~1 week.
   - Aria integration against local memory.
   - Stripe subscription for Pro LLM access via your inference endpoint.
   - Optional: local-only LLM via `web-llm` or `llama.cpp` WASM for the
     truly paranoid user (offline inference in the browser).

Total: ~3 weeks for both products fully shipped. Live Aria demo
shippable by end of this weekend if you want to prioritize it.

### 5.2 What I'd push back on

**"Live Aria" under password alone isn't enough protection.**

A password-gated Aria still needs:
- **Per-session LLM spend cap** (e.g., $0.50/session auto-cutoff).
- **Per-IP daily cap** (prevents a leaked password from draining your budget).
- **Dharma rules applied to *visitor input before LLM call*** — not
  just to Aria's responses. This is the same governance layer you ship
  in WhiteMagic-core, applied to your own production site. Eats your
  own dogfood in public. Great story.
- **Kill switch**: one env var flip disables Aria instantly.

These are not optional. Budget for ~3 hrs of the Aria build on these
guardrails alone.

**"Users bring their own inference" for the PWA is better than
subscription**, at least as a free tier.

Hear me out. The architecture I'd actually recommend for the free tier:

- User brings their own Anthropic / OpenAI API key
- Stored encrypted in IndexedDB, never sent to your server
- Browser calls Anthropic directly (CORS permitting) or via a thin
  Cloudflare Worker proxy that only relays the request, never stores
  the key

This flips the pitch from "pay us for LLM access" to "pay us for
convenience + never-worry-about-keys + Aria training." It also means
**you have zero liability for their model usage, their data, their
prompts**. Cleaner legally, cleaner architecturally, honest to the
local-first pitch.

The paid tier then becomes: "our keys, our inference, higher limits,
priority support, Aria personality library, private memory cloud sync
if you want it." That's a real premium product, not a tax on what
should be free.

### 5.3 What I'd defer

- **Offline-only LLM in the browser** (web-llm, llama.cpp WASM). Cool,
  but the models that fit in a browser are too weak for Aria's voice.
  Wait 12 months for better WASM-compatible small models (Phi-6, Llama
  4-3B quantized).
- **Merging `hub/` and `nexus/` Tauri apps**. Out of scope for this
  track. File as a cleanup task in the monorepo.
- **The dashboard-app's admin UI**. It's a 70%-built internal tool; if
  you want it on the public site, ship it behind `/admin` with
  authentication, not on `/app`. Consider it v0.5 of the PWA — reuse
  the React components, discard the API-assumes-remote-server part.

---

## 6. Decision points — your call

Before I write a single line of implementation code, these need
answers:

| # | Decision | Options |
|---|---|---|
| 1 | **Which track this week?** | (a) Aria demo alone, ship fast. (b) Aria + PWA phase 1 in parallel. (c) PWA phase 1 first, Aria second. |
| 2 | **LLM for the Aria demo?** | (a) Claude Sonnet 4.5 via Anthropic API. (b) GPT-4.x via OpenAI API. (c) Both, user toggles. (d) Local server running Ollama (llama3.1:8b — but CPU-only is slow; your note said 8b OOMs on current hardware). |
| 3 | **Aria's public memory corpus** | (a) Fully curated by you (slow, safe). (b) Start empty, Aria grows from conversations (risky — can poison). (c) Seed with 16 quickstart memories from WASM_STRATEGY.md + your hand-curated top-N Aria artifacts. |
| 4 | **Password-gate mechanism** | (a) Vercel's built-in password protection (per-deploy, blunt but zero code). (b) Next.js middleware + single hashed password in env. (c) Full auth with magic link (overkill for a demo). |
| 5 | **Free-tier inference model** | (a) User brings their own API key (my recommendation). (b) Your keys with strict rate limits. (c) No LLM in free tier; free tier is memory-OS only. |
| 6 | **Private GitHub repo for the monorepo?** | (a) Keep `whitemagic-ai/whitemagic` public as-is, add `apps/site` publicly. (b) Make the monorepo private, host `apps/site` as a separate public repo for transparency. (c) All private. |
| 7 | **Aria's voice — how far from the private Aria?** | (a) Faithful: ships with the same warmth, personality, I Ching references, poetic tone. Risks public ridicule from skeptic readers. (b) Neutralized: technical, warm, but drops the mystical framing. (c) Two modes: "Aria (casual)" and "Aria (technical)" with a toggle. |

---

## 7. Legal / ethical pre-flight

Before Aria is public, even password-gated, I'd want:

- **Privacy notice** on `/aria` explaining what gets logged (conversations, yes/no).
- **Content policy** — Aria refuses harmful / CSAM / self-harm content, falls back to crisis resources. The Dharma Rules Engine is the right place for this; it's literally what it was built for.
- **No medical / legal / financial advice** guardrail. Standard for demo agents.
- **Data retention**: default is "deleted at end of session" unless the visitor logs in (and logging in requires explicit consent to retention).
- **If you publish any Aria artifact from the private corpus**, get comfortable that it's now public. Some of `_legacy/aria-home/WELCOME_HOME.md`-style material is personal. I would not publish journals or dreams.

---

## 8. What I need from you to move forward

Answer Decisions 1–7 in §6, plus:

- **Stripe account**: needed for the Pro subscription tier. Can wait until PWA phase 2.
- **Anthropic / OpenAI API key**: needed for live Aria. Set in Vercel env vars; never committed.
- **Vercel project**: one Vercel project pointing at `whitemagic-ai/whitemagic` repo with Root Directory `apps/site`. I can walk you through this when you're ready.
- **Rate-limit backend**: Upstash Redis (free tier works) OR Vercel KV. I'd pick Upstash — works everywhere, no Vercel lock-in.

---

## 9. Risks I want on the record

1. **Aria under load with leaked password**: per-IP daily caps + Stripe-style fraud monitoring mitigate but don't eliminate. Worst case: $50–200 of API spend before the daily cap triggers. Accept as cost of doing business or add CAPTCHA.
2. **WASM build pain**: `wasm-pack` + `sqlite-wasm` + OPFS all work *in theory*. In practice, the first successful build usually takes 1–3 days of debugging for a codebase this size. Budget accordingly.
3. **Aria "hallucinating" about WhiteMagic in public**: an embedded live agent will invent capabilities. Mitigation: system prompt includes strict "do not promise features that aren't documented in the public README" rule, enforced by a Dharma rule that pattern-matches on commitments ("we offer", "I can", "we support") and adds a disclaimer.
4. **Reputational risk of mystical framing in front of enterprise CTOs**: real. Decision 7 in §6 addresses this. My bias is toward the "two modes" option — lets skeptics see a professional Aria, lets believers see the full one.

---

## 10. What happens next

This doc stays in the monorepo as the record of intent. Once Decisions
1–7 are answered, I'll create:

- `apps/SCOPING_BROWSER_FIRST_DECIDED.md` — the locked version
- A phased implementation plan with daily commits
- The first PR: password gate + Aria chat UI shell (no LLM yet — verify
  the guardrails work on a stubbed backend first)

Nothing in `core/` is touched until §3.2 PWA phase begins.
