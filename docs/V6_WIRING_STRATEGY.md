# V6 Full Activation Strategy

**Date:** 2026-08-18
**Status:** Planning
**Goal:** Wire all v6 subsystems together, close integration gaps, and validate
with incremental benchmarks before the full 500q LongMemEval-S run.

## Current Wiring State

### Already Connected

| From | To | How | Status |
|---|---|---|---|
| McpServer | MemoryStore | `with_defaults()` opens LMDB | ✅ |
| McpServer | SearchEngine | Tantivy index at `store_path/tantivy` | ✅ |
| McpServer | RecallEngine | `create_embedder()` → `RecallEngine::new()` | ✅ (stub fallback) |
| McpServer | BicameralEngine | BitNet → LLM → stub right hemisphere | ✅ |
| McpServer | DreamCycle | Daemon wires `DreamContext` with imagination | ✅ |
| McpServer | AutonomousCycleRunner | Daemon wires `CycleContext` with sensorimotor | ✅ |
| McpServer | ScenarioEngine | `init_imagination()` in `with_defaults` | ✅ |
| Daemon | LearnedCycleStrategy | Load/save `mutable_learned_cycles.json` | ✅ |
| Daemon | LearnedDreamCycle | Load/save `mutable_learned_dream.json` | ✅ |
| DreamCycle | MemoryStore | `DreamContext` reads/writes memories | ✅ |
| DreamCycle | ScenarioEngine | Oracle phase counterfactual replay | ✅ |
| AutonomousCycles | MemoryStore | Improve/Redteam scan Codex galaxy | ✅ |
| EpisodicStore | EpisodicKeys | Typed key extraction at ingest | ✅ |
| EpisodicStore | QueryPlanner | 7-class query classification at search | ✅ |
| EpisodicStore | Role-aware scoring | Coverage grace + role_boost | ✅ |

### Missing Links (The Gaps)

| # | Gap | Impact | Effort |
|---|---|---|---|
| G1 | Episodic retrieval doesn't use embedder/vector store | No semantic reranking, hardcoded aliases only | Medium |
| G2 | Dream cycle association mining doesn't propose entity aliases | No adaptive entity system | Medium |
| G3 | Bicameral engine doesn't rerank episodic candidates | No LLM judgment on rank 2-3 near-misses | Medium |
| G4 | OrtEmbedder (ONNX) not enabled in default build | No local embeddings without llama-server | Low |
| G5 | Episodic retrieval path is separate from RecallEngine | Two parallel retrieval systems, not unified | Medium |
| G6 | Self-play loop doesn't test retrieval quality | No autonomous retrieval improvement | High |
| G7 | Inference router not ported from Python WM | No 5-tier complexity-based routing | High |
| G8 | No benchmark harness for 100q/500q runs | Can't validate beyond 50q | Medium |

## Implementation Plan

### Phase 1: Enable Local Embeddings (G4)

**Goal:** Make the OrtEmbedder available in the default build so semantic
similarity is possible without an external llama-server.

**Changes:**
1. Enable `onnx` feature in `wm-memory/Cargo.toml` (or make it a default feature)
2. Verify `OrtEmbedder` loads BGE-small-en-v1.5 (130MB, 384 dims, CPU-friendly)
3. Set `WM_EMBEDDER_BACKEND=onnx` in benchmark environment
4. Verify `create_embedder()` returns OrtEmbedder, not StubEmbedder

**Test gate:** `cargo build --features onnx` succeeds, embedder produces real
384-dim vectors, `embedder_is_real()` returns true.

**Risk:** ONNX Runtime adds a build dependency. Mitigation: keep `onnx` as an
opt-in feature, not default.

### Phase 2: Vector Reranking for Episodic Retrieval (G1, G5)

**Goal:** Add a semantic reranking layer on top of the deterministic episodic
scorer. The deterministic base ensures 100% candidate recall; the vector layer
reorders the top-N by semantic similarity to the query.

**Design:**
```
EpisodicStore::search()
  → deterministic scoring (current) → top-20 candidates
  → vector reranking (new) → embed query + top-20 content
  → hybrid_score = α * deterministic_score + (1-α) * cosine_sim
  → return top-10 by hybrid_score
```

**Changes:**
1. Add `EpisodicStore::search_with_rerank()` method that:
   - Calls existing `search()` to get top-20 deterministic candidates
   - Embeds the query and each candidate's content using the `Embedder` trait
   - Computes cosine similarity between query embedding and each candidate
   - Combines: `hybrid = α * norm(deterministic) + (1-α) * cosine`
   - Returns top-10 by hybrid score
2. Add `EpisodicStore::with_embedder()` to attach an embedder
3. Start with α = 0.7 (deterministic-heavy) and tune via A/B
4. Gate behind a config flag so deterministic-only remains the default

**Why this matters:** This is the "general purpose abbreviation and acronym
resolver." Embeddings naturally capture that "undergrad" and "Bachelor's degree"
are semantically related — no hardcoded alias table needed. This also addresses
the R@1=80% near-misses: when two turns have similar deterministic scores, the
vector layer breaks ties by semantic relevance to the query.

**Test gate:** 50q A/B with reranking enabled. Acceptance:
- R@5 >= 1.00 (must not regress)
- R@1 >= 0.80 (must not regress)
- MRR >= 0.89 (must not regress)
- Latency p50 < 200ms (embedding 20 candidates + 1 query)

### Phase 3: Adaptive Entity Aliases from Dream Cycle (G2)

**Goal:** The dream cycle's Serendipity and Consolidation phases already mine
associations between memories. Wire those discoveries back into the episodic
key extractor as proposed entity aliases.

**Design:**
```
DreamCycle::Serendity phase
  → discovers co-occurrence patterns (e.g. "undergrad" ↔ "degree")
  → writes proposal as a Memory with tag "alias:proposal"
  → EpisodicKeys::load_adaptive_aliases() reads proposals on startup
  → aliases are applied at ingest and query time
```

**Changes:**
1. Add `EpisodicKeyExtractor::with_adaptive_aliases()` that loads alias proposals
   from the memory store
2. Dream cycle Serendipity phase: when it detects high co-occurrence between
   an entity key and a non-key term, write a `MemoryType::Insight` record with
   tag `alias:proposal` and JSON content `{"term": "undergrad", "canonical": "degree", "confidence": 0.85}`
3. On startup, `EpisodicStore` loads alias proposals with confidence > 0.7
4. Proposals are advisory — they extend the hardcoded alias table, not replace it

**Test gate:** Run dream cycle on the 50q haystack, verify it proposes at least
2 aliases that match known gaps. 50q A/B with adaptive aliases. Acceptance:
- R@5 >= 1.00
- R@1 >= 0.80

### Phase 4: Bicameral Reranking for Rank 2-3 Near-Misses (G3)

**Goal:** When the deterministic + vector reranking still has close scores for
the top candidates, use the left hemisphere (low-temp, deterministic) to judge
which candidate best answers the query.

**Design:**
```
EpisodicStore::search_with_rerank()
  → deterministic top-20 → vector rerank top-10
  → if top-2 scores are within δ (e.g. 0.05)
  → bicameral left hemisphere evaluates: "Given query Q, which turn better answers it: A or B?"
  → left hemisphere returns judgment → final reorder
```

**Changes:**
1. Add `EpisodicStore::with_bicameral()` to attach a `BicameralEngine`
2. Add a `rerank_with_bicameral()` method that:
   - Takes the query and top-N candidates
   - Constructs a `HemisphereInput` with the query as topic and candidate texts as evidence
   - Calls `left_hemisphere.analyze()` (low temp, deterministic)
   - Uses the confidence + stance to break ties
3. Gate behind config: only fires when top-2 score gap < δ
4. Only works when `LlamaLeftHemisphere` is configured (falls back to no reranking)

**Why this matters:** The 10 remaining R@1 misses are all rank 2-3 — the
evidence is found but a competing turn edges it out. The left hemisphere is
designed for exactly this: analytical, reproducible judgment. This is the
cognitive-memory synergy — the reasoning system evaluates the retrieval
system's output.

**Test gate:** 50q A/B with bicameral reranking (requires llama-server). Acceptance:
- R@1 >= 0.82 (at least 1 near-miss resolved)
- R@5 >= 1.00
- Latency p50 < 500ms (adds one LLM call for close-score cases only)

### Phase 5: Benchmark Harness for 100q and 500q (G8)

**Goal:** Build a benchmark runner that can handle 100q and 500q LongMemEval-S
subsets with the same metrics (R@1, R@5, R@10, MRR, latency).

**Changes:**
1. Extend the existing 50q benchmark script to accept a question count parameter
2. Add category-aware reporting (single-session-user, multi-session, temporal,
   knowledge-update, abstention)
3. Add per-category breakdown to the output
4. Support loading the full 500q LongMemEval-S dataset
5. Add a `--categories` flag to run specific subsets

**Test gate:** Run 100q (single-session-user + one other category). Verify
metrics are computed correctly and per-category breakdown works.

### Phase 6: Unified Retrieval Path (G5)

**Goal:** Connect the episodic retrieval path with the `RecallEngine` so they
share the embedder, vector store, and search infrastructure.

**Changes:**
1. `EpisodicStore` accepts an optional `Arc<RecallEngine>` for vector operations
2. When RecallEngine is present, episodic search uses it for embedding + vector
   similarity instead of a separate embedder
3. The `RecallEngine`'s `embedder_is_real()` check gates whether vector
   reranking is active
4. This unifies the embedder configuration — one place to configure, both
   retrieval paths benefit

**Test gate:** 50q A/B with unified path. Acceptance: same metrics as Phase 2.

### Phase 7: Self-Play Retrieval Testing (G6, experimental)

**Goal:** Use the `SelfPlayLoop` to generate synthetic query-memory pairs and
test retrieval quality. Failed retrievals become friction entries for the
Improve cycle.

**Changes:**
1. Add a `SelfPlayTaskType::RetrievalTest` variant
2. `TaskProposer` generates queries from existing episodic memories (pick a
   memory, generate a natural-language question about it)
3. `TaskSolver` runs the query through `EpisodicStore::search()`
4. `SelfVerifier` checks if the source memory is in the top-K results
5. Failed retrievals are logged as `rsi:friction` entries with category
   `retrieval` and target `episodic`
6. The Improve cycle picks these up and proposes improvements

**Test gate:** Run 10 self-play cycles. Verify friction entries are created for
failed retrievals. This is experimental — no acceptance gate on retrieval
metrics, just verify the loop runs and produces useful friction data.

## Execution Order

```
Phase 1 (enable ONNX)          ── 1-2 hours
  ↓
Phase 2 (vector reranking)     ── 3-4 hours
  ↓
  Test: 50q A/B                ── 30 min
  ↓
Phase 5 (benchmark harness)    ── 2-3 hours (can parallelize with Phase 3)
  ↓
  Test: 100q run               ── 1 hour
  ↓
Phase 3 (adaptive aliases)     ── 3-4 hours
  ↓
  Test: 50q A/B + dream cycle  ── 30 min
  ↓
Phase 4 (bicameral reranking)  ── 3-4 hours
  ↓
  Test: 50q A/B with LLM       ── 30 min
  ↓
Phase 6 (unified path)         ── 2-3 hours
  ↓
  Test: 100q run               ── 1 hour
  ↓
Phase 7 (self-play, optional)  ── 4-6 hours
  ↓
  Test: 500q full run          ── 2-4 hours
```

## Benchmark Progression

| Run | Questions | Configuration | Purpose |
|---|---|---|---|
| 50q baseline | 50 | Deterministic only | Current state reference |
| 50q + vectors | 50 | + ONNX embedder, vector reranking | Measure semantic gain |
| 100q + vectors | 100 | + 100q harness, 2 categories | Validate beyond single category |
| 50q + aliases | 50 | + adaptive aliases from dream cycle | Measure alias gain |
| 50q + bicameral | 50 | + left hemisphere reranking | Measure LLM reranking gain |
| 100q full stack | 100 | All phases enabled | Integration validation |
| 500q full run | 500 | All phases enabled | Final validation |

## Acceptance Gates for Full Activation

Before the 500q run, all of these must hold:

1. **R@5 >= 0.98 on 100q** (at least 2 categories)
2. **R@1 >= 0.80 on 100q** (no regression from 50q)
3. **Latency p50 < 300ms** with all reranking enabled
4. **No hardcoded aliases** that weren't in the original 50q benchmark (adaptive
   aliases must come from the dream cycle, not manual additions)
5. **Embedder is real** (OrtEmbedder or HttpEmbedder, not StubEmbedder)
6. **Dream cycle runs without errors** on the benchmark haystack
7. **All cargo tests pass** (`cargo test` — 3,504 tests)
8. **Clippy clean** (`cargo clippy --all-targets` — 0 warnings)

## Architecture After Wiring

```
┌─────────────────────────────────────────────────────────────────────┐
│                      v6 Retrieval Pipeline                          │
│                                                                     │
│  Query → QueryPlanner (7-class)                                     │
│        → EpisodicStore::search()                                    │
│           → deterministic scoring (typed keys + role + grace)       │
│           → top-20 candidates                                       │
│        → Vector Reranking (Phase 2)                                 │
│           → embed query + 20 candidates (OrtEmbedder BGE-small)     │
│           → hybrid = α·deterministic + (1-α)·cosine                 │
│           → top-10 candidates                                       │
│        → Bicameral Reranking (Phase 4, when scores close)           │
│           → left hemisphere evaluates top-2 candidates              │
│           → final reorder                                           │
│        → top-K results                                              │
│                                                                     │
│  Background (daemon):                                               │
│    Dream Cycle → Serendipity phase                                  │
│      → mines co-occurrence patterns                                 │
│      → proposes adaptive entity aliases (Phase 3)                   │
│      → aliases loaded on next startup                               │
│                                                                     │
│    Self-Play Loop (Phase 7, experimental)                           │
│      → generates synthetic queries from memories                    │
│      → tests retrieval → logs friction on failure                   │
│      → Improve cycle proposes fixes                                 │
└─────────────────────────────────────────────────────────────────────┘
```

## Key Design Principles

1. **Deterministic base is the floor.** Every neural enhancement (vector
   reranking, bicameral judgment) is an optional layer on top. If the embedder
   is unavailable or the LLM is down, the system falls back to the
   deterministic scorer with R@5=100%.

2. **No regression allowed.** Each phase has an acceptance gate that requires
   R@5 and R@1 to not drop below current levels. If a phase causes regression,
   it's reverted.

3. **Incremental validation.** We test at 50q after each phase, then 100q
   before the full 500q. No phase is validated only at 500q.

4. **Adaptive over hardcoded.** The adaptive alias system (Phase 3) replaces
   the need for manual alias entries. New users, new topics, new organizations
   are handled by the dream cycle's association mining, not by hand-coding.

5. **Latency budget.** Each phase has a latency budget. The deterministic base
   is 107ms p50. Vector reranking adds ~50-100ms (embedding 20 short texts).
   Bicameral reranking adds ~200-500ms but only fires on close-score cases.
   Total budget: p50 < 300ms with all layers active.

## What This Unlocks

After full activation, WhiteMagic v6 will have:

- **Deterministic retrieval** at R@5=100% with zero model dependency (the floor)
- **Semantic reranking** via local ONNX embeddings (no cloud, no GPU)
- **Adaptive entity resolution** via dream cycle association mining (scales to
  any user/domain without manual aliases)
- **Cognitive reranking** via bicameral left hemisphere (LLM judgment on
  ambiguous cases)
- **Self-improving retrieval** via self-play friction logging (the system
  discovers its own retrieval failures and proposes fixes)

This is the synergy: the memory system provides the evidence, the cognitive
system evaluates and improves it, and the local inference stack makes it all
run on a laptop without a GPU.
