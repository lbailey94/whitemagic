# Roadmap Consolidation — All Sources Merged

**Date**: 2026-06-03
**Current Version**: v22.2.0 (core)
**Repo Root VERSION**: 15.8.0 (⚠️ stale — see F-01)
**Test Baseline**: 2,243 passed, 67 skipped, 0 failed
**Sources Audited**: 8 roadmap/strategy documents + 2 session handoffs

---

## Executive Summary

WhiteMagic has **at least 8 active roadmap documents** spanning code quality, platform evolution, consultancy operations, site deployment, and cognitive architecture. Many contain contradictory timelines, stale metrics, and duplicated objectives. This document consolidates all of them into a single truth source.

**Key decisions from this consolidation**:
1. `STRATEGIC_ROADMAP_V23.md` (May 26) is the **single canonical platform roadmap** going forward
2. `PHASE_ROADMAP.md` (site) remains the **canonical site/consultancy roadmap**
3. `SCOPING_BROWSER_FIRST_DECIDED.md` remains the **canonical architecture contract**
4. All other roadmaps are archived with redirect headers
5. The April `CODE_QUALITY_REVIEW` findings are folded into V23 as **Quality Gates**, not a separate track
6. Six findings from the April audit are still unfixed and block production readiness

---

## 1. Source Registry

| Document | Date | Scope | Status After Consolidation |
|----------|------|-------|---------------------------|
| `docs/CODE_QUALITY_REVIEW_2026-04-15.md` | Apr 15 | 26 code-quality findings + 6-phase fix plan | **Archived** → findings merged into V23 Quality Gates |
| `core/docs/STRATEGIC_ROADMAP.md` | Apr 2026 | v22→v23 platform leaps, cognitive OS pivot, enterprise fork | **Archived** → cognitive OS items merged into V23; enterprise fork deferred |
| `docs/plans/ROADMAP.md` | Apr 19 | 12-month consultancy + platform horizon | **Archived** → site items merged into PHASE_ROADMAP; platform items into V23 |
| `docs/message_board/STRATEGIC_ROADMAP_V23.md` | May 26 | 8-week sprint to v23.0.0 | **Canonical** → updated with merged items + quality gates |
| `apps/site/PHASE_ROADMAP.md` | Apr 19 | Site build + content + outreach phases | **Canonical** → site track only |
| `apps/SCOPING_BROWSER_FIRST_DECIDED.md` | Apr 18 | Browser-first architecture (Librarian + PWA) | **Canonical** → architecture contract |
| `docs/archive/V22_2_ROADMAP.md` | Apr 25 | v22.2 immediate/short/medium phases | **Archived** → all items complete |
| `docs/message_board/SESSION_SUMMARY.md` | Apr 25 / May 21 | Session handoff with full history | **Reference** → historical context |

---

## 2. What's Actually Done (Verified)

### From v22.2 Roadmap (Apr 25)
- ✅ Gana meta-tool dispatch fixed
- ✅ Salience arbiter rebuilt
- ✅ Browser automation suite recovered (2,496 lines)
- ✅ `simd_unified.py` recovered from archive
- ✅ 7 missing handler modules created
- ✅ Stub Zero — all 41 stubs eliminated across 4 sprints
- ✅ 3 critical archive recoveries (`lifecycle.py` +383, `solver_engine.py` +110, `db_manager.py` +196)
- ✅ MCP hardening (input sanitizer, LRU cache, structured error codes)
- ✅ Memory stress tests (500 concurrent stores, 2000-memory aggressive test)
- ✅ Doc drift detection CI gate (`check_doc_drift.py`)
- ✅ `db_manager.py` connection pool with WAL, SQLCipher, backoff
- ✅ Foresight engine (Layer 7) with 4 tools wired
- ✅ Polyglot revival: Haskell (`whitemagic-hs/`) + Julia (`whitemagic-jl/`) scaffolds
- ✅ MCP startup latency: ~2,800ms → ~400ms via `_LazyMCPTypes`
- ✅ Stub audit CI gate (`check_stubs.py`)
- ✅ Engine registry garden bug fixed (18 mismatches)

### From Site Roadmap (Apr 19–20)
- ✅ Next.js 15 scaffold (Phase 0)
- ✅ All 11 routes built with real copy (Phase 1)
- ✅ Librarian chat UI with tool-use + floating bubble (Phase L.2)
- ✅ Contact form backend with per-IP rate limit
- ✅ Admin middleware with Basic Auth
- ✅ Resend notifier (env-gated)
- ✅ JSON-LD structured data
- ✅ Per-page OG images (7 routes)
- ✅ `/economy` page + gratitude-architecture capability

### From Cognitive OS Pivot (Apr 25)
- ✅ Dream YAML sandbox concept + nightly consolidation pipeline
- ✅ Corpus Callosum Bus design
- ✅ Jaynes Voice Audit concept
- ✅ Neurotransmitter Vectors design
- ✅ Polyglot Core Matrix documented

---

## 3. What's Still Open (Cherry-Picked from All Sources)

### 🔴 Production Blockers — Must Fix Before Any Deploy

These come from the April audit. They are not "nice to have." They are safety/correctness issues.

| ID | Finding | Source | Why It Blocks |
|----|---------|--------|---------------|
| F-01 | Root `VERSION` says `15.8.0`, core says `22.2.0` | `CODE_QUALITY_REVIEW` | Version mismatch is confusing; root VERSION is 3+ years stale |
| F-02 | 28 `except Exception` blocks in `unified.py` (was 6 in April audit; grew to 28) | `CODE_QUALITY_REVIEW` + current grep | Silent failures in memory store = data corruption risk, especially with multi-user on horizon |
| F-03 | Gana Forge signature is deterministic SHA-256 (no secret) | `CODE_QUALITY_REVIEW` | Security theater; marketplace economy requires real trust |
| F-05 | Stale artifacts in repo root (`excavation.log`, `llms-full.txt`) | `CODE_QUALITY_REVIEW` | These shouldn't be in version control |
| F-06 | `EmbeddingEngine` leaks SQLite connections (no close/ctx manager) | `CODE_QUALITY_REVIEW` | FD leak; browser WASM will be unforgiving |
| F-12 | CORS `allow_origins=["*"]` on HTTP MCP server | `CODE_QUALITY_REVIEW` | Cross-origin risk with full memory+tool access |

### 🟠 Site & Consultancy Track (from `PHASE_ROADMAP.md` + `SESSION_STATE.md`)

| # | Task | Phase | Status | Blocker |
|---|------|-------|--------|---------|
| 2.1 | Cal.com setup — 30-min Discovery call | Site Phase 2 | ❌ Not done | Lucas |
| 2.4 | Deploy to Hetzner | Site Phase 2 | ❌ Not done | Lucas (SSH + DNS) |
| 2.5 | DNS: point `whitemagic.dev` at Cloudflare → Hetzner | Site Phase 2 | ❌ Not done | Lucas |
| 2.6 | Keep old Squarespace at `old.whitemagic.dev` | Site Phase 2 | ❌ Not done | Lucas |
| 2.9 | Plausible or Umami analytics | Site Phase 2 | ❌ Not done | Decision + account |
| 2.10 | LinkedIn + GitHub profile updates | Site Phase 2 | ❌ Not done | Lucas |
| 3.x | Three anchor blog posts | Site Phase 3 | ❌ Not done | Content (Lucas) |
| 4.1–4.6 | Outreach + first contracts | Site Phase 4 | ❌ Not done | Lucas time |
| P1.1 | `wasm-pack build --target web` succeeds | PWA Phase 1 | ❌ Not done | Engineering |
| P1.2–P1.8 | Full PWA substrate (blank canvas) | PWA Phase 1 | ❌ Not done | Engineering |
| — | OpenRouter API key in production env | Infrastructure | ❌ Not done | Lucas |
| — | Upstash Redis REST credentials | Infrastructure | ❌ Not done | Lucas |
| — | Stripe payment links | Infrastructure | ❌ Not done | Lucas |

### 🟡 Platform Track (from `STRATEGIC_ROADMAP_V23.md`)

| # | Task | Phase | Status |
|---|------|-------|--------|
| — | Resolve 30 skipped tests (LD_PRELOAD, Rust/Zig builds, fixtures) | V23 Phase 1 | ❌ Not done |
| — | Archive 20 skipped tests (polyglot bridges, network) | V23 Phase 1 | ❌ Not done |
| — | Implement 4 critical stubs (homeostasis, consciousness, hemisphere) | V23 Phase 1 | ❌ Not done |
| — | WASM Runtime: SQLite WASM + OPFS | V23 Phase 2 | ❌ Not done |
| — | WASM Runtime: ONNX embedding model in browser | V23 Phase 2 | ❌ Not done |
| — | Interactive Galaxy: drag nodes, draw edges, resonance nav | V23 Phase 3 | ❌ Not done |
| — | Multi-User: auth, galaxy isolation, API keys | V23 Phase 4 | ❌ Not done |
| — | WebSocket bidirectional sync | V23 Phase 4 | ❌ Not done |
| — | Static Haskell linking (or Rust replacement) | V23 Phase 5 | ❌ Not done |

### 🟢 Strategic / Deferred (from `STRATEGIC_ROADMAP.md` + `SESSION_SUMMARY.md`)

| # | Task | Source | Status | Rationale |
|---|------|--------|--------|-----------|
| — | Enterprise/Chinese fork (`whitemagic-core`) | `STRATEGIC_ROADMAP.md` | ⏸️ Deferred | No enterprise customers yet; build when inbound exists |
| — | Mem0/Zep integration | `SESSION_SUMMARY.md` | ❌ Rejected | Architectural regression; native 5D system is the differentiator |
| — | Grimoire registry bug fix (Southern/Northern swap) | `SESSION_SUMMARY.md` | ❌ Not done | 10-min fix; affects quadrant-aware boosts |
| — | Aspirational tool audit (~30-40% fictional tools in Grimoire) | `SESSION_SUMMARY.md` | ❌ Not done | 2-3 days; needed for auto-cast |
| — | Grimoire deduplication (remove `.md` from `core/whitemagic/grimoire/`) | `SESSION_SUMMARY.md` | ❌ Not done | 30-min fix |
| — | Northern Quadrant expansion (Ch 22-28 stubs) | `SESSION_SUMMARY.md` | ❌ Not done | 1-2 days |

---

## 4. Duplications & Conflicts Resolved

### Timeline Conflict
- `STRATEGIC_ROADMAP.md` (Apr) says v22.1 is next → v22.2 was already shipped
- `STRATEGIC_ROADMAP_V23.md` (May 26) says v23.0.0 target → **This is the correct current target**
- `PHASE_ROADMAP.md` says "60-90 days to first paid engagement" (from Apr 19) → Expired; reset

### Polyglot Status Conflict
- `polyglot/STATUS.md` says Koka "Experimental", Mojo "Deferred"
- `core/POLYGLOT_STATUS.md` says Koka "Production", Mojo "Advanced"
- **Resolution**: `polyglot/STATUS.md` is canonical. `core/POLYGLOT_STATUS.md` is stale and should be archived.

### MCP Server Count
- `STRATEGIC_ROADMAP.md` says "2.4MB seed binary" — this is accurate (Rust MCP server)
- `SCOPING_BROWSER_FIRST_DECIDED.md` says two separate agents (Librarian + PWA) — this is the product surface, not the MCP server count
- **Resolution**: One MCP server (the Rust seed binary) serves the platform. The Librarian is a separate OpenRouter-backed agent on the site. The PWA uses WASM local transport. These are product surfaces, not additional MCP servers.

### Test Count Drift
- `AGENTS.md` and many public docs say 2,216 (frozen release baseline)
- `SESSION_SUMMARY.md` and live runs say 2,243 (current audit baseline)
- `STRATEGIC_ROADMAP_V23.md` says 2,280 (aspirational target after resolving skips)
- **Resolution**: Use Option C from May 20 decision — distinguish frozen release baseline (2,216) from current live baseline (2,243). Update docs that present live numbers. Don't retroactively change release notes.

---

## 5. What to Archive

| Document | Archive Action | Redirect To |
|----------|---------------|-------------|
| `docs/CODE_QUALITY_REVIEW_2026-04-15.md` | Add header: superseded by V23 Quality Gates | `STRATEGIC_ROADMAP_V23.md` §Quality Gates |
| `core/docs/STRATEGIC_ROADMAP.md` | Add header: superseded by V23 roadmap | `STRATEGIC_ROADMAP_V23.md` |
| `docs/plans/ROADMAP.md` | Add header: superseded by V23 + PHASE_ROADMAP | `STRATEGIC_ROADMAP_V23.md` (platform) + `PHASE_ROADMAP.md` (site) |
| `docs/archive/V22_2_ROADMAP.md` | Already in archive; add "COMPLETE" header | `SESSION_SUMMARY.md` for history |
| `core/POLYGLOT_STATUS.md` | Add header: stale; canonical is `polyglot/STATUS.md` | `polyglot/STATUS.md` |

---

## 6. Metrics Consolidation

| Metric | Frozen Release (v22.0) | Current Live (v22.2) | V23 Target |
|--------|------------------------|----------------------|------------|
| Tests passing | 2,216 | 2,243 | 2,310+ |
| Tests skipped | 67 | 67 | ~20 |
| Tool surface | 484 callable, 456 dispatch, 28 Ganas | Same | Same |
| Stubs | 0 | 0 | 0 |
| Python files | ~819 | ~819 | — |
| Lines of Python | ~182K | ~195K (per STRATEGIC_ROADMAP) | — |
| CI jobs | 8 | 8 + doc-drift + stub-audit | — |
| Version | v22.0.0 | v22.2.0 | v23.0.0 |

---

**End of Consolidation**
