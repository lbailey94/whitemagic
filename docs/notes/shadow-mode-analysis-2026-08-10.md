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

**Step 2.8 remains correctly deferred.** The infrastructure is production-ready, but no shadow mode data exists because no real embedder has been deployed. The decision to retire TF-IDF should be made after:

- At least 1,000 shadow mode queries (10x the minimum threshold)
- Disagreement rate consistently < 15% (below the 20% gate, with margin)
- Manual review of top disagreement pairs to verify embedding router is correct (not TF-IDF) on disagreements
- OATS refinement has been applied and validated

## Key Files

- `crates/wm-tools/src/embedding_router.rs` — `EmbeddingRouter`, `ShadowModeStats`, OATS
- `crates/wm-tools/src/lib.rs` — `WmMetaTool::classify_with_router()` (shadow mode logic)
- `crates/wm-tools/src/expansion/nlu_tools.rs` — `NluShadowReportTool` MCP tool
- `crates/wm-mcp/src/server.rs` — `save_mutable_state()` / `load_mutable_state()` (persistence)
- `crates/wm-memory/src/embedder.rs` — `create_embedder()` (embedder selection)
