# Vector Search Roadmap

**Created:** 2026-08-14
**Status:** Core wiring complete. Quick wins and tuning opportunities below.

## What's Wired (Completed 2026-08-14)

### Architecture

`RecallEngine` is constructed once in `McpServer::with_defaults()` and shared
via `Arc<RecallEngine>` across:

- `ConversationalSearch` — conversational memory search with caching
- `MemoryCreateTool` — auto-embeds on write via `store_with_embedding()`
- `MemoryBatchCreateTool` — auto-embeds each item on write
- `MemoryHybridRecallTool` — hybrid BM25 + vector fusion via `hybrid_search()`

### Activation

Set `WM_EMBEDDER_ENDPOINT` to a llama-server with `--embeddings`:

```bash
llama-server -m bge-small-en-v1.5.gguf --embeddings --port 8081
export WM_EMBEDDER_ENDPOINT=http://localhost:8081
```

Without this env var, `StubEmbedder` is used, `recall_for_tools = None`, and
all tools fall back to pure BM25 — identical to pre-wiring behavior.

### Configuration

| Env var | Default | Description |
|---------|---------|-------------|
| `WM_EMBEDDER_ENDPOINT` | (none) | HTTP endpoint for llama-server embeddings |
| `WM_RECALL_BM25_WEIGHT` | 0.5 | Weight for BM25 text score in fusion |
| `WM_RECALL_VECTOR_WEIGHT` | 0.3 | Weight for vector cosine similarity |
| `WM_RECALL_IMPORTANCE_WEIGHT` | 0.2 | Weight for memory importance |

Weights are clamped to [0, 1] and normalized to sum to 1.0.

### Fusion Formula

```
score = bm25_weight * normalized_bm25 + vector_weight * cosine_sim + importance_weight * importance
```

`hybrid_search()` retrieves `limit * 3` results from both BM25 and vector
search, fuses them by memory ID, and returns the top `limit` by fused score.

### Files Changed

- `crates/wm-memory/src/recall.rs` — added `embedder_is_real()`
- `crates/wm-memory/src/conversational.rs` — changed to `Arc<RecallEngine>`
- `crates/wm-mcp/src/server.rs` — construct `Arc<RecallEngine>`, pass to tools
- `crates/wm-tools/src/lib.rs` — `MemoryCreateTool`, `MemoryBatchCreateTool`
  accept `Option<Arc<RecallEngine>>`, use `store_with_embedding()` when available
- `crates/wm-tools/src/expansion/memory_ops.rs` — `MemoryHybridRecallTool`
  accepts `Option<Arc<RecallEngine>>`, runs `hybrid_search()` as Phase 0
- `crates/wm-tools/src/expansion/mod.rs` — `register_expansion` passes
  `recall` to `MemoryHybridRecallTool`

### Verification

- `cargo build` — clean
- `cargo build --release` — clean
- `cargo clippy --all-targets` — 0 warnings
- `cargo test -p wm-memory -p wm-tools -p wm-mcp` — 626 passed, 0 failed

## Quick Wins (This Afternoon)

### QW1: Batch Embedding in `memory.batch_create`

**Effort:** ~30 min
**Impact:** ~10x faster batch ingest with embedder

Currently `batch_create` calls `store_with_embedding()` per item, which calls
`embed()` one at a time. The `Embedder` trait already has `embed_batch()`.
Wire `batch_create` to collect all content, call `embed_batch()` once, then
store + index each memory with its pre-computed embedding.

### QW2: Benchmark Script Switch to `memory.hybrid_recall`

**Effort:** ~15 min
**Impact:** Activates hybrid path in LongMemEval benchmark

The benchmark script (`scripts/longmemeval_benchmark.py` or similar) currently
uses `memory.search` (pure BM25). Switching to `memory.hybrid_recall` would
activate the hybrid BM25 + vector path when an embedder is available, giving
immediate recall quality data.

### QW3: Fusion Weight Grid Search

**Effort:** ~1 hour (requires running benchmark)
**Impact:** Optimize fusion weights for LongMemEval

Run the benchmark with different `WM_RECALL_BM25_WEIGHT` /
`WM_RECALL_VECTOR_WEIGHT` / `WM_RECALL_IMPORTANCE_WEIGHT` combinations and
compare R@1, R@5, MRR. Candidate grid:

| bm25 | vector | importance | Hypothesis |
|------|--------|------------|------------|
| 0.5  | 0.3    | 0.2        | Current default |
| 0.7  | 0.2    | 0.1        | BM25-dominant |
| 0.3  | 0.5    | 0.2        | Vector-dominant |
| 0.4  | 0.4    | 0.2        | Balanced |
| 0.6  | 0.3    | 0.1        | BM25-heavy, low importance |

## Ranking Improvements (R@1 → R@5 Gap)

1. ~~**OR with token-coverage as primary strategy**~~ ✅ Done (v5.8.0-rc2):
   OR is now the default with stemming-aware token-coverage floor (≥2/3 for
   3+ term queries) and coverage-ratio score boost. The two-phase
   conjunction→relaxed-OR fallback is eliminated.

2. **BM25 field weight tuning** — Content field vs tags field weighting. Tags
   contain role/session metadata that may over-inflate or under-weight certain
   matches.

3. **Query expansion** — Add synonyms or related terms to queries before search
   (e.g., via word embeddings or a synonym dictionary).

4. **Re-ranking with cross-encoder** — After hybrid retrieval, re-rank top-K
   with a cross-encoder model for finer semantic matching. Requires a second
   model endpoint or ONNX runtime.

## Search Strategy

5. **Multi-turn answer detection** — Some answers span multiple turns. Index
   sliding windows of 2-3 consecutive turns as additional "composite" documents.

6. **Per-category strategy tuning** — LongMemEval has 6 categories
   (single-session-user, multi-session-user, etc.). Different categories may
   benefit from different search strategies or fusion weights.

7. ~~**Relaxed conjunction**~~ ✅ Subsumed by item 1: OR + token-coverage
   floor (≥2/3 for 3+ term queries) provides the "at least N terms must
   match" behavior without a separate conjunction mode.

## Embedding Infrastructure

8. **ONNX Runtime embedder** — `wm-memory` has an `onnx` feature with
   `OrtEmbedder` (using `fastembed-rs`). This would give fully local embeddings
   without a llama-server dependency. Requires enabling the feature and building
   with `--features onnx`.

9. **Embedding model selection** — Default is 384-dim (MiniLM/bge-small). Larger
   models (768-dim bge-base, 1024-dim bge-large) may improve recall at cost of
   latency. The `WM_EMBEDDER_ENDPOINT` approach already supports any model
   served by llama-server.

10. **Vector store persistence** — Currently `VectorStore::new()` creates an
    in-memory store. Vectors are re-embedded on restart. For large stores,
    persisting vectors to LanceDB (feature-gated) would avoid re-embedding
    costs.

## Performance

11. **Tantivy segment merging** — Tune merge policy for bulk-ingest workloads
    to reduce segment count after batch commits.

12. **Pre-warmed reader** — After `batch_create` commit, the reader reload is
    synchronous. Could pre-warm in background.

13. **Parallel question processing** — Run multiple questions concurrently with
    separate temp stores (I/O bound, not CPU bound).

14. **Incremental benchmark** — Cache ingested sessions across questions that
    share the same haystack (LongMemEval reuses sessions across questions).

## Benchmark Integration

15. **Use `memory.hybrid_recall` instead of `memory.search`** — The benchmark
    script currently uses `memory.search` (pure BM25). Switching to
    `memory.hybrid_recall` would activate the hybrid path when an embedder is
    available. (See QW2 above.)

16. **Session-level vs turn-level indexing** — Currently each turn is a
    separate memory. Consider session-level aggregation or composite documents.
