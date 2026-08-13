# Evening Analysis: Agentic CPU:GPU Shift, Hierarchical Memory & Release Strategy

**Created:** August 12, 2026 (evening session)
**Source:** Reddit thread (AMD @ OCP APAC 2026) + codebase review of WMv5, whitemagic-v4, WHITEMAGIC-CORE (v26 Python), and v2-reference
**Purpose:** Record how the industry signals from the thread relate to WhiteMagic, and the recommended focus areas before any public release.

---

## 1. The Thread

Two signals from a Reddit thread on AMD's OCP APAC 2026 talk:

1. **CPU:GPU ratio shift.** Agentic AI is increasing CPU demand alongside GPU usage — orchestration, tool calls, memory management, and control logic are CPU-bound. The traditional ~1:4 ratio may move toward 1:2 or even 1:1.
2. **Hierarchical memory (top comment, Ormusn2o).** Instead of context window + compaction + RAG/.md files, use multi-tier context: a working context window, "quick memory" (KV kept in fast memory), and cold storage (tens of millions of tokens). Mix tiers per query. Avoids long-context degradation, cheaper than a huge context window. "Reinventing CPU cache levels, but for context" (Hellrage), with the caveat that context is serialized — it must be recreated, not inserted at random addresses.

---

## 2. How WhiteMagic Relates

### 2.1 WhiteMagic is the CPU-side of agentic AI, already built

~131k LOC of Rust doing exactly what AMD described: tool dispatch pipeline (effect check → destructive confirm → dharma → rate limit → tool → stats), 229 tools, NLU routing, karma ledger, governance, sangha mesh, dream cycles, self-play. None of it touches a GPU. The LLM is deliberately kept small — the MCP server exposes a single `wm` meta-tool so the model does almost no orchestration.

Evidence of the shift implemented, not just argued:
- 5-tier inference router in `wm-bicameral` (edge rules → heuristic → stub → LLM → bitnet), learned via k-NN + conformal calibration
- `EdgeRuleHandler` — Tier 0 rule-based inference with zero tokens, explicitly moving work off the GPU
- `LearnedRouter` auto-promotes high-frequency simple responses to edge rules

### 2.2 WhiteMagic is a software implementation of the hierarchical memory comment

| Thread's tier | WhiteMagic analog |
|---|---|
| Current context window | LLM client context, kept lean via single meta-tool |
| Quick memory (hot) | `PredictiveCache` — LRU + Markov chain pre-warming (prefetch of likely-next memories) |
| Cold storage | LMDB persistent store, 14 named galaxies (taxonomy preserved since v2) |
| Retrieval / tier mixing | `hybrid_search` — fused BM25 (Tantivy) + vector cosine (LanceDB) + importance weighting |
| Offline KV processing | 12-phase dream cycle — sleep consolidation, retention pruning, oracle predictions |
| "Not needing .md files" | Journals/Sessions galaxies + merkle anchors for deterministic task state |

Two nuances worth remembering:

- **Compaction + hierarchy, not either/or.** `DenseEncoder` in `wm-mcp/src/cyberbrain.rs` does CJK-based context compression — the thing the thread argues against — but WM keeps it alongside the tiered store. Both are used: compact what's hot, tier everything else.
- **The serialized-work caveat.** Context can't be randomly inserted; it must be recreated. WM's answer: `HolographicCoords` (galaxy + sector + temporal + radial + angular addressing) + association mining — reconstruction by navigation rather than linear scan.

### 2.3 Evolution across versions

- **v26 (Python, SQLite):** galaxy taxonomy + FTS5. SQLite per-galaxy DBs.
- **v4 (Rust, 18 crates):** predictive cache, Tantivy, bicameral stack, resonance/drive/timescale.
- **v5 (Rust, 15 crates, 229 tools, 3,391 tests):** the hierarchy became *learned* — LearnedDreamCycle reorders consolidation phases, DynamicGalaxyRegistry auto-creates galaxies, OATS refines retrieval from outcomes, NLU shadow mode with promotion readiness metrics.

The project has been climbing the same hierarchy curve the thread describes, with the learning baked in.

**Bottom line:** AMD and the thread describe where the industry is going; WhiteMagic is a working existence proof of that architecture — CPU-heavy orchestration with a multi-tier learned memory hierarchy — with the GPU behind an MCP boundary.

---

## 3. Release Readiness — The Honest Assessment

Open items from `docs/NEXT_SESSION.md` (2026-08-11) are exactly the things that should block a public release:

- NLU shadow mode: **42.6% disagreement** with TF-IDF (threshold 20%); not promotion-ready
- Dangerous misroutes observed, e.g. `"show my karma"` → `karma.clear` (embedding router)
- Rate limiter defaults (60 RPM + 10 burst) throttle the `wm` meta-tool in real use
- Claims ledger: 32 claims, 12 pending, calibration **+0.215 overconfident** (Brier 0.078)

229 tools / 15 crates is a beautiful archive and a terrible v1.

---

## 4. Recommended Focus (Priority Order)

### 4.1 Fix the fuzzy boundary first — it's a safety incident waiting to happen

1. **Hard-gate destructive tools from fuzzy routing.** The 8 destructive tools (`memory.delete`, `galaxy.purge`, `galaxy.transfer`, `galaxy.restore`, `memory.consolidate`, `memory.deduplicate`, `system.flush`, `karma.clear`) plus `transaction.rollback` should require exact `route=` match + `confirm: true`. Make it structurally impossible for NLU to reach them — not a router-quality matter.
2. **Router improvement:** rewrite `tool_descriptions()` in `embedding_router.rs` with intent-anchored descriptions (verbs + example queries); margin-based selection (best vs second-best gap) with TF-IDF fallback on ties.
3. **Retest with shadow collector** (`scripts/collect_shadow_data.py`); target < 20% disagreement. Promotion decision needs ≥1,000 organic queries with `WM_EMBEDDER_ENDPOINT` set.

### 4.2 Ship a product, not a planet

- **Lead with the differentiated thing:** the tiered memory (predictive cache → search → LMDB, dream consolidation, merkle-anchored journals). "One MCP server that gives your agent a learned memory hierarchy" is a sentence; "229 tools" is not.
- **Curated release profile:** tool allowlist config for the public default; full surface behind a feature flag.
- **Zero-config onboarding:** stub/TF-IDF defaults so `wm serve` works out of the box; embedder endpoint optional.

### 4.3 Use the claims ledger as the differentiator

The ledger (32 claims, Brier scorecard, overconfident by +0.215) is genuinely novel and defensible — but finish the calibration first. Don't publish the overconfidence.

### 4.4 What NOT to do next

- Do not port more v26 tools — ~90% were redundant by the gap analysis; each new tool multiplies router misroute surface.
- Do not expand sangha/self-play/mesh surfaces pre-release — no external user runs a mesh day one.

---

## 5. Bottom Line

Not blocked on features — blocked on **safety of the fuzzy boundary** and **shape of the product**. Fix the destructive-tool gate + router (days, not weeks), build a curated release profile and zero-config quickstart, finish claims calibration — then release as "a memory hierarchy for agents," not "a cognitive OS with 229 tools." If the hesitation persists after that, it's probably not about readiness anymore.
