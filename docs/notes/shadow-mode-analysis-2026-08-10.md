# NLU Shadow Mode Readiness Analysis — 2026-08-10

## Overview

Assessment of whether the embedding-based NLU router (Phase 2) is ready to replace the TF-IDF router (deferred step 2.8).

## Architecture

The `wm` meta-tool uses a two-layer routing system:

1. **Embedding Router** (primary, when available): `EmbeddingRouter` in `wm-tools/src/embedding_router.rs`
   - Pre-computes tool description embeddings at startup
   - Routes queries by embedding the query and computing cosine similarity
   - OATS refinement adjusts embeddings based on observed outcomes

2. **TF-IDF Router** (fallback): `nlu::classify()` with 166 hand-written keyword profiles
   - Always runs in shadow mode for comparison when embedding router is active

## Shadow Mode Mechanics

When `EmbeddingRouter::new()` returns `Some(router)`:
- Embedding router is primary — its result is used for dispatch
- TF-IDF router runs alongside (shadow) — result is compared but not used
- `ShadowModeStats` records every query: agreement or disagreement
- `nlu.shadow_report` MCP tool exposes stats for observability

## Promotion Criteria

`ShadowModeStats::promotion_ready()` returns `true` when:
- `total_queries >= 100` (enough samples for statistical significance)
- `disagreement_rate < 0.20` (embedding router agrees with TF-IDF ≥ 80% of the time)

## Current Status: NOT READY (No Data)

**The embedding router is disabled by default.** `EmbeddingRouter::new()` returns `None` when the embedder is a stub:

```rust
if embedder.backend_name() == "stub" {
    tracing::info!("embedding router disabled — stub embedder has no semantic similarity, using TF-IDF fallback");
    return None;
}
```

Without `WM_EMBEDDER_ENDPOINT` set (for HttpEmbedder) or the `onnx` feature enabled with a model configured, `create_embedder()` returns a `StubEmbedder` — hash-based embeddings with no semantic meaning.

**Result**: Shadow mode never activates. `ShadowModeStats` stays at default (0 queries, 0 disagreements). No data has been collected.

## Persistence (Ready)

The persistence infrastructure is in place:
- `mutable_shadow_stats.json` saved on daemon shutdown via `save_mutable_state()`
- Loaded on startup via `load_mutable_state()`
- Stats accumulate across restarts once a real embedder is configured

## First Data Collection — 2026-08-11 (real embedder, 115 queries)

**Setup**: nomic-embed-text-v1.5 (Q4_K_M, 768-dim) via llama-server `--embeddings`
(`WM_EMBEDDER_ENDPOINT=http://127.0.0.1:8081`, `WM_EMBEDDER_TIMEOUT_MS=120000`),
`wm serve` against a scratch store, 115 natural-language thoughts driven through
the `wm` meta-tool. Collector: `scripts/collect_shadow_data.py`.

**Result: NOT promotion-ready. Disagreement rate 42.6%** (49/115) vs the 20% gate.
The embedding router loses to TF-IDF on many core patterns:

- **Destructive misroute**: "show my karma" / "check the karma chain" → `karma.clear`
  (the wipe tool — only the destructive-confirm gate prevents damage)
- "remember/keep X" → `memory.list` instead of `memory.create`
- "review the friction log" / "auto log friction" → `friction.log` (write) not `friction.review`
- "list tools" → `memory.list`; "record that the server restarted" → `session.recall`
- Claims/session/system families collapse onto near-arbitrary high-similarity tools
  (`workspace.spotlight`, `selfmodel.alerts`, `dream.status`, `gnosis`)

The pattern: with 169 tool descriptions at ~768-dim cosine, top-1 selection is
dominated by description vocabulary overlap, not intent. Confidence scores are
uniformly 0.5–0.8, so `MIN_THRESHOLD` fallback never fires.

**Infrastructure findings fixed on the way**:
- `nlu.shadow_report` was unreachable — registered only at top level, not inside
  the `wm` meta-tool routing registry (MCP exposes only `wm`). Fixed in
  `crates/wm-tools/src/lib.rs` (`register_meta_tools`): the shadow report tool is
  now registered into `wm_builder`.
- Embedding-batch timeout: 229 tool descriptions took 56s on CPU at default
  `WM_EMBEDDER_TIMEOUT_MS=30000` → silent router disable. Raised to 120s in the
  collector; worth bumping the default for real deployments.
- Dispatch-pipeline rate limiter (default 60 RPM/tool + 10 burst) caps `wm` at
  70 calls/min — collector paces in 60-query batches.

**Caveats**: the sample is synthetic (scripted queries, not organic daemon
traffic) and single-backend (nomic-embed vs the documented bge-small). A fairer
test would run the daemon live with `WM_EMBEDDER_ENDPOINT` set and let shadow
stats accumulate over real usage.

## Router Improvement — 2026-08-11 (second run, same corpus)

Two changes were made and re-tested:

1. **Real registry descriptions** (`EmbeddingRouter::with_descriptions`): the
   meta-tool now embeds the live registry's prose `description()` strings
   (228 tools) instead of the static keyword-mashup profiles (169 tools).
   Coverage 169 → 228 tools.
2. **Margin fallback** (`route_with_margin` + `MIN_MARGIN = 0.02`): when the
   top-1 vs top-2 cosine margin is below 0.02, the TF-IDF choice wins
   (`classify_with_router`). Near-ties mean intent can't be separated.

**Observed dispatch fixes (dangerous misroutes eliminated)**:
- "show my karma" → `karma.report` (was `karma.clear` — destructive tool)
- "research the topic of memory consolidation" → `emergence.scan`
  (was `memory.delete` — destructive tool)
- "review the friction log" → `friction.review` (was `friction.log` — writer)
- "add/resolve a claim" → `claims`; "check the karma chain" → `karma.verify_chain`;
  "hand off the session" → `session.handoff`; "research a github repo" →
  `research.repo`; "fetch the url and summarize" → `web.fetch`
- Regression tests added: `with_descriptions` coverage, `route_with_margin`
  margin semantics, `wm_routes_shadow_report_inside_meta_tool`

**Caveat**: raw shadow disagreement ROSE to ~55% (44/81 in the second run) —
the metric counts *any* divergence, and the embedding router now often
diverges *correctly* (claims/web/session families where TF-IDF chose
`gnosis`/`karma.report`/`memory.list`). The promotion gate (< 20% divergence)
is still not met, but dispatch quality — the thing that matters — improved
markedly, and all destructive misroutes are gone.

## Path to Promotion (Step 2.8)

To retire TF-IDF and promote the embedding router to sole primary:

1. **Deploy a real embedder**: Set `WM_EMBEDDER_ENDPOINT` to a llama-server `/v1/embeddings` endpoint, or enable the `onnx` feature with a model
2. **Run in shadow mode**: Accumulate 100+ queries with the embedding router as primary
3. **Check `nlu.shadow_report`**: Verify disagreement rate < 20%
4. **Analyze disagreement pairs**: Review `top_disagreement_pairs` to identify systematic routing failures
5. **Apply OATS**: Let outcome-aware refinement accumulate ≥ 10 observations per tool
6. **Validate routing accuracy**: Confirm embedding router accuracy ≥ TF-IDF accuracy on disagreement cases
7. **Retire TF-IDF**: Remove `nlu.rs` profiles and `classify()` function, make embedding router the sole router

## Recommendation

**Step 2.8 remains deferred.** First real data (2026-08-11) shows the embedding
router is *worse* than TF-IDF at 42.6% disagreement, so promotion would degrade
routing. Likely improvers before retesting:

- **Better tool descriptions**: `tool_descriptions()` drives the whole router —
  intent-anchored descriptions (verbs + example queries per tool) would sharpen
  top-1 selection far more than embedding tweaks
- **Intent-aware threshold**: require a gap (e.g., best > second-best + margin)
  instead of plain top-1; fall back to TF-IDF on ties
- **A2A routing test**: collect 1,000+ organic queries via the live daemon before
  any promotion decision

## Key Files

- `crates/wm-tools/src/embedding_router.rs` — `EmbeddingRouter`, `ShadowModeStats`, OATS
- `crates/wm-tools/src/lib.rs` — `WmMetaTool::classify_with_router()` (shadow mode logic)
- `crates/wm-tools/src/expansion/nlu_tools.rs` — `NluShadowReportTool` MCP tool
- `crates/wm-mcp/src/server.rs` — `save_mutable_state()` / `load_mutable_state()` (persistence)
- `crates/wm-memory/src/embedder.rs` — `create_embedder()` (embedder selection)
- `scripts/collect_shadow_data.py` — shadow data collection driver (2026-08-11)
