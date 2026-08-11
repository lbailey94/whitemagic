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

## Embedder A/B — 2026-08-11 (nomic-embed vs bge-small, same corpus)

Both models ran the same 115-query corpus through the identical improved
router (registry descriptions + margin fallback). bge-small-en-v1.5 q8_0
(384-dim, 37MB) vs nomic-embed-text-v1.5 Q4_K_M (768-dim, 84MB):

| Metric | nomic-embed | bge-small |
|---|---|---|
| Embed dim | 768 | 384 |
| Router init batch (228 descs) | ~45-56s CPU | ~30s CPU |
| Per-query dispatch latency | ~410 ms | ~334 ms |
| Raw disagreement rate | ~55% | ~59% |
| Correct on 27-query judged set | 13 | 12 |
| Destructive misroutes | none | none |

**Verdict: near-tie on quality; bge-small wins operationally.** It is the
documented canonical model (FastEmbed/BGE-Small-EN-V1.5 per the local-AI
mapping docs), matches the codebase's default `WM_EMBEDDER_DIM=384`, is
half the size, and ~20% faster. Both models share the same fundamental
limitation: top-1 cosine over prose descriptions collapses intent-fuzzy
queries onto arbitrary tools — the fix is intent-anchored descriptions
(task 1), which benefits either model equally.

## Intent-Anchored Descriptions — 2026-08-11 (third run, same corpus)

Two more changes, measured on a 56-query judged dispatch set (correct
routes):

| Config | Correct |
|---|---|
| nomic-embed + prose descriptions | 28/56 |
| bge-small + prose descriptions | 31/56 |
| **bge-small + intent anchors** | **34/56** (38 counting `?`-status rows that were actually correct: selfplay.run/status/export, nlu.shadow_report) |

Changes:
1. **`INTENT_ANCHORS`** (`embedding_router.rs`): per-tool natural phrasings
   appended to the embedded text — `"<name>: <description> — users say:
   <anchors>"`. Anchors cover the failure families from the shadow runs
   (memory/session/karma/friction/claims/web/research/selfplay/sim/system).
   Applied via `anchored_descriptions()` in the meta-tool's registry path.
2. **Prefix bonus removed from the anchored path**: the TF-IDF
   `PREFIX_ROUTES` bonus ("list" → memory.list ×1.3) fought the anchors —
   "list tools" was boosted toward memory.list despite `tools.list`
   carrying the exact anchor. Now `apply_prefix_bonus` is `true` only for
   the legacy keyword-profile constructor; anchored descriptions encode
   verb mapping natively.

**Fixed by anchors**: "list tools"/"list all tools" → `tools.list`,
"fetch this webpage"/"fetch the url and summarize" → `web.fetch`,
"what is the brain wave state" → `state.snapshot`, "record this session
turn" → `session.record`, "review the friction log" → `friction.review`,
"show my karma" → `karma.report`, handoff/claims/session families.

**Still failing** (no anchor can fully fix — description-quality or
TF-IDF-margin issues): "search the web for rust benchmarks" → memory.search
("search" dominates), "keep this note in memory" → memory.list,
"run a simulation" → margin-fallback to pipeline.status (TF-IDF wins the
near-tie, and TF-IDF is wrong), "create a new galaxy" → session.start.

## Router Fixes — 2026-08-11 (afternoon)

1. **Missing descriptions synthesized** (`anchored_descriptions`): 45 tools
   (~20% of the registry) had no explicit `description()`, so they fell back
   to their Gana's generic text — all conformal.*, selfmodel.*, and several
   others embedded to one of 28 shared vectors. The margin calculation
   collapsed on whole families. Tools with the Gana fallback now get a
   synthesized description from their dotted name ("conformal.monitor" →
   "conformal monitor — conformal monitor operations and status").
2. **mc.* family descriptions added**: all 5 `mc.*` tools in
   `bayesian_tools.rs` (surrogate/optimize/rare_event/sde/superforecaster)
   and `simulation.calibrate` had no descriptions — identical vectors →
   guaranteed near-ties. Given proper descriptions.
3. **OATS persistence wired** (`save_mutable_state` → `mutable_oats.json`,
   restored in `load_mutable_state`): the router's outcome-aware refinement
   now survives restarts. Regression test `e2e_oats_persistence_roundtrip`.
4. **Test isolation fix**: `with_defaults(tmp.path())` in tests put
   `self_model.json` etc. in the shared `/tmp` — cross-test pollution made
   `e2e_mutable_state_persistence_roundtrip` flaky. Tests now use a nested
   store dir (`test_store_path`).
5. **Verified margin behavior**: "run a simulation" → sim.mc 0.74 with
   margin 0.011 — the fallback fires because sim.mc vs runner-up is a real
   near-tie, not a description artifact. TF-IDF's low-confidence picks
   (pipeline.status 0.23) still win these. A confidence floor on the
   fallback was tried and reverted — net regression on the judged set.

Measured on the corrected 56-query judged set (real registry tools only):
nomic 31, bge 33, anchored+synthesized 38 (42 counting correct `?`-status
rows: selfplay.run/status/export, nlu.shadow_report).

**Infrastructure (2026-08-11)**:
- Dispatch rate limiter configurable: `RateLimiterConfig` +
  `WM_DISPATCH_GLOBAL_RPM` / `WM_DISPATCH_TOOL_RPM` / `WM_DISPATCH_BURST` /
  `WM_DISPATCH_TOOL_OVERRIDES` (`wm serve` logs the active limits). Defaults
  unchanged (300/60/10). Collector now runs 115/115 queries with no losses.
- Live shadow collection: `whitemagic-embedder.service` systemd user unit
  (bge-small on :8081, auto-restart) + `scripts/live_shadow_serve.sh`
  (serve against the live store with embedder + raised dispatch limits) +
  `python/mcp_config_rust_native.json` pointed at the live store with
  embedder env. Every real MCP session now accumulates shadow stats,
  persisted to `<store>/lmdb/mutable_shadow_stats.json` on shutdown.

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
