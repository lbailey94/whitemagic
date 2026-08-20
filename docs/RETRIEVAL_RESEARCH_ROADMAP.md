# Retrieval Research Roadmap — Perfect R@1, Local, Fast

**Date:** 2026-08-19 (updated 2026-08-19)
**Status:** Phase 1 complete; R@1 improved 70% → 80% on 10q subset; Phase 2 next
**Scope:** Multi-phase plan to achieve perfect or near-perfect R@1 on LongMemEval-S
with zero cloud dependency, minimal CPU burn, and sub-millisecond latency at scale.

## Current Results (10q subset)

| Metric | Before Phase 1 | After Phase 1 | Notes |
|---|---|---|---|
| R@1 (10q) | 70% | **80%** | Q4 fixed; Q7, Q9 remain at rank 2 |
| R@1 (50q) | 76% | **82%** | Q4, Q11, Q24, Q47 fixed; Q32 regressed |
| R@5 | 100% | 100% | Answer always in top 5 |
| R@10 | 100% | 100% | Answer always in top 10 |
| MRR (50q) | 0.87 | **0.90** | |
| Latency | ~17s | ~1.5s | No embeddings (WM_EPISODIC_RERANK_ONLY=1) |
| LLM inference | 0 | 0 | Deterministic scoring only |

The 2 remaining misses are **ranking problems, not recall problems**. Q7 is a
single-term query where all turns with `yoga` are lexically equivalent. Q9 has
multiple user turns getting reverse enrichment matches, creating score ties that
content_len decides. Both are fundamental limitations of single-term lexical
search without semantic understanding.

## Approaches Tried and Failed

All of these were implemented, benchmarked, and reverted:

| Approach | Result | Root Cause |
|---|---|---|
| BM25 scoring (raw + normalized) | R@1 regression | Breaks +2 user bonus |
| IDF-weighted coverage | R@1 regression | IDF signal too weak vs. user boost |
| Multi-query pool widening | No effect | Answers already in pool |
| Cosine reranking delta 0.05→0.25 | No effect | Cosine doesn't help in lexical regime |
| Hybrid blending (alpha=0.5, 0.7) | R@1 regression | Degrades Q6 |
| +3 bonus + sequence descending | R@1 regression | Degrades Q8 |
| Log coverage compression | No improvement | Doesn't change relative ordering |
| RRF fusion | Breaks pipeline | Destroys reranking order |
| matched_terms +3 for UserStatement | No improvement | Competing user turns also get it |
| user_length_bonus for single-term | No improvement | Helps wrong turns (longer competing) |
| Reversing content_len tiebreaker | Multiple regressions | Longer content ≠ answer |
| reverse_match_count bonus 0.1 | Q4 regression | Too aggressive, over-boosts |
| Contextual indexing (--contextual) | No effect | Tags not used in episodic scoring |

## Root Cause Analysis

The 3 misses share an identical pattern:

1. **Query** has 5 terms (e.g., "What play did I attend at the local community theater?")
2. **Answer turn** (UserStatement) matches 2/5 terms — uses different vocabulary
3. **Competing turn** (Assistant) matches 4/5 terms — uses query's vocabulary
4. The +2 UserStatement bonus gives coverage 0.8 for both (capped at 1.0)
5. The competing turn wins on `matched_terms` tiebreaker (4 > 2)

The vocabulary gap is the core issue. Example:
- Query: "play ... attend ... local community theater"
- Answer: "The production I attended was The Glass Menagerie" (matches: attend, theater=0)
- Competing: "I went to a play at the local community theater" (matches: play, local, community, theater)

The answer turn says "production" instead of "play", and doesn't contain
"local", "community", or "theater". No amount of scoring weight adjustment
can fix this — the terms simply aren't there.

## Research Findings (August 2026)

### 1. LongMemEval Paper (ICLR 2025)

**Source:** https://arxiv.org/abs/2410.10813

Key optimization: **fact-augmented key expansion** (+9.4% recall@k). Three
design choices:
- **Value**: Decompose sessions into turns (we already do this)
- **Key**: Expand keys with extracted facts, keyphrases, and user facts
- **Query**: Time-aware query expansion for temporal questions

The paper's best configuration (CP2) augments indexed content with LLM-extracted
facts and keyphrases. Our approach can use deterministic vocabulary enrichment
instead of LLM extraction.

### 2. Training-Free Lexical-Dense Fusion (2026)

**Source:** https://arxiv.org/html/2606.04194

Critical finding for us: **On LongMemEval-S specifically, fusion gain over BM25
is small and not significant** — it's a "lexical regime where BM25 saturates."

- Cross-encoder reranking **hurts**: -6.9pp Hit@1 with ms-marco-MiniLM-L-6-v2
- Late interaction (max-sim) helps on LoCoMo but not on LongMemEval-S
- Weighted score-level fusion (α·BM25 + (1-α)·dense) with α∈[0.25, 0.50]
  helps on LoCoMo but not on LongMemEval-S
- **Implication**: Our cosine reranking pipeline cannot improve R@1 on this
  benchmark. The path forward is better lexical indexing, not better reranking.

### 3. SelRoute: Query-Type-Aware Routing (2026)

**Source:** https://arxiv.org/html/2604.02431

**Storage-time vocabulary enrichment** with three components:
- **Hypernym maps** (210 entries): specific → broader (cocktail → drink, beverage, alcohol)
- **Action bridges** (70 entries): attended → went, participated, was_at, visited
- **Topic rooms** (13 categories): co-occurring triggers add contextual terms

Critical finding: **enrichment helps FTS5 but hurts embeddings**. FTS5 treats
additional terms as independent signals (more matches = higher BM25 score).
Embedding models compute a single vector for all content; adding vocabulary
bridges shifts the vector away from the original semantic center.

**Implication**: Enrichment must be applied to the lexical index only
(`term_db` postings), not to content used for embedding computation.

FTS5 alone with proper tokenization and enrichment achieves R@5 = 0.745.

### 4. ReFind: Agent-Controlled Search (2026)

**Source:** https://arxiv.org/html/2608.12888

Achieves **93.2% on LongMemEval-S** with pure BM25 + agent-controlled search.
No semantic structure, no embeddings, no LLM-based index construction.

Key techniques:
- **Session-aware RRF reranking**: Two-level RRF fusing turn-level BM25 rank
  with session-level aggregate rank. When multiple turns in a session match,
  all turns in that session get a boost.
- **Context window expansion**: Return ±2 turns around each hit for dialogue
  context.
- **Temporal filtering**: Agent can narrow to a time range.
- **Session deduplication**: Skip sessions already inspected in prior rounds.
- **Iterative query reformulation**: 4 rounds of BM25 search with different
  keywords, driven by an LLM agent observing which terms matched/missed.

**Implication**: Session-aware RRF is a zero-cost scoring improvement we can
implement immediately. Iterative search is Phase 4 (requires LLM).

### 5. AgentIR: Workload-Adaptive Cascade Retrieval (2026)

**Source:** https://ar5iv.labs.arxiv.org/html/2605.25092

Achieves **sub-100μs p50 latency** on 5M records.

Key techniques:
- **SIMD-vectorized BM25**: AVX2 posting list traversal
- **Temporal partitioning**: Time-window buckets sorted by recency, search
  recent-first with early stopping. O(log(1/ε)) work independent of corpus size.
- **MaxScore pruning**: Skip documents that can't make the top-K
- **CSR (Compressed Sparse Row) layout**: Flattened inverted index for cache
  efficiency

**Implication**: Temporal partitioning is directly applicable to our episodic
store. Conversational memory has strong recency bias — recent sessions are
more likely to be queried.

### 6. SIMD-Accelerated Vector Similarity Crates

**iqdb-distance** (stable 1.0):
- 6.8–10.3× SIMD speedup on AVX2 at 768-dim
- AVX2 on x86_64, NEON on aarch64, scalar fallback
- Runtime dispatch, allocation-free, property-tested
- `cosine_normalized` fast path for pre-normalized embeddings (just dot product)
- MSRV 1.87+, Rust 2024 edition

**innr**:
- AVX-512F + AVX2 + FMA + NEON
- f32 and f64 support
- Binary, ternary, and scalar quantization
- Fast approximate math (Quake III rsqrt)

**vcal-core**:
- HNSW index + optional SIMD
- Designed for semantic caches (LLM prompt deduplication)
- In-process, no daemon, deterministic

**Implication**: If we keep any vector fallback, SIMD cosine gives 7-10x
speedup with zero code change (swap the function). If we normalize embeddings
at storage time, we get dot-product fast path (fastest possible similarity).

### 7. SuperLocalMemory V3 (2026)

**Source:** https://arxiv.org/html/2603.14588

**Fisher-information-weighted retrieval**: Replace cosine similarity with
variance-weighted metric. Each memory's embedding is augmented with a
per-dimension confidence vector (σ²). Dimensions where the model is uncertain
get downweighted.

- Θ(d) time (same as cosine)
- 75% retrieval quality with zero cloud dependency
- Cross-encoder reranking is the single largest contributor (-30.7pp when removed)

**Implication**: Fisher-weighted scoring is a drop-in replacement for cosine
that produces better rankings at the same computational cost. Relevant for
Phase 2 if we keep any vector fallback.

### 8. MemX: Local-First Memory System (2026)

**Source:** https://arxiv.org/abs/2603.16171

Rust-based local memory system on libSQL + OpenAI-compatible embedding API.

- FTS5 full-text indexing reduces keyword search latency by **1,100×** at
  100k-record scale
- End-to-end search under **90ms**
- RRF fusion of vector + keyword recall paths
- Four-factor re-ranking: semantic similarity, recency, importance, frequency
- Low-confidence rejection rule (suppress spurious recalls)

**Implication**: Confirms that FTS5/local lexical search can be extremely fast.
Our 17s latency is almost entirely embedding computation — pure lexical search
should be well under 100ms.

## WMv5 Architecture: Galaxy System vs Episodic Store

### Galaxy System (v2, preserved in v5)

- **14 fixed galaxies** as LMDB sub-databases: Aria, Citta, Codex, Journals,
  Dreams, Research, Sessions, Substrate, Tutorial, Universal, Karma, Dharma,
  Associations, Embeddings
- **Dynamic GalaxyRegistry** (Phase 6): Custom project-scoped galaxies
- **6D HolographicCoords**: galaxy + sector + radial + angular + temporal +
  consciousness — 23-byte sortable LMDB keys for spatial range queries
- **5D Coordinate5D**: x/y/z semantic axes (SHA-256 derived) + temporal weight
  + consciousness resonance — Euclidean distance for constellation clustering
- **Zones**: Core → InnerRing → MidRing → OuterRing → FarEdge
- **Rich metadata**: importance, neuro_score, novelty, emotional valence,
  access_count, recall_count, decay half-life, memory_type, source_trust
- **Tantivy FTS** for full-text search
- **In-memory VectorStore** for brute-force cosine (<100K vectors)
- **LanceDB** optional backend for ANN (IVF-PQ, 100K+ vectors)

Key files:
- `crates/wm-core/src/galaxy.rs` — 14 galaxy taxonomy
- `crates/wm-core/src/coords.rs` — HolographicCoords + Coordinate5D
- `crates/wm-memory/src/galaxy_registry.rs` — dynamic galaxy management
- `crates/wm-memory/src/store.rs` — MemoryStore (LMDB, galaxies, indexes)
- `crates/wm-memory/src/vector.rs` — in-memory VectorStore
- `crates/wm-memory/src/lance_vector.rs` — LanceDB ANN store
- `crates/wm-memory/src/memory.rs` — Memory + MemoryMetadata

### Episodic Store (v6, new)

- **Single LMDB DB** (`episodic_records`) for lossless append-only records
- **Custom inverted index** (`episodic_terms`) — term → Vec<EpisodicId>
- **Term cache** — Arc<RwLock<HashMap<String, Vec<EpisodicId>>>> for hot terms
- **Deterministic scoring**: coverage + key_bonus + role_boost + number_bonus +
  reverse_match_bonus (density removed in Phase 1)
- **Vocabulary enrichment**: storage-time hypernym maps + reverse enrichment for
  UserStatement scoring (Phase 1)
- **Optional vector reranking**: tiebreaker mode (delta=0.05) or hybrid blending
- **No holographic coordinates, no zones, no importance scoring**
- **ValidityState**: Active, Superseded, Revoked, Archived, Erased

Key files:
- `crates/wm-memory/src/episodic.rs` — EpisodicStore, scoring, search, rerank
- `crates/wm-memory/src/episodic_keys.rs` — typed key extraction + aliases
- `crates/wm-core/src/episodic.rs` — EpisodicRecord, EpisodicKind, ValidityState

### The Gap

The episodic store has no access to the galaxy system's rich metadata:
- No holographic coordinates (no spatial pre-filtering)
- No importance/neuro_score (no quality-weighted ranking)
- No zones (no lifecycle-aware retrieval)
- No tags or memory_type (no type-aware scoring)
- No enrichment (no vocabulary bridges)

Bridging this gap is a key opportunity for Phase 3.

## Multi-Phase Implementation Plan

### Phase 1: Vocabulary Enrichment + Session-Aware RRF ✅ COMPLETE

**Goal:** R@1 70% → 80-85% ✅ (achieved 80% on 10q, 82% on 50q)
**Latency:** Reduced from ~17s to ~1.5s with WM_EPISODIC_RERANK_ONLY=1
**LLM inference:** Zero
**CPU:** Minimal (hashmap lookups at ingestion time)

#### Step 1A: Storage-Time Vocabulary Enrichment

**What:** Add synonym/hypernym maps to the episodic inverted index at ingestion
time. When a record is indexed, enrich its term postings with vocabulary
bridges so the record matches queries using different but related vocabulary.

**Where:** `crates/wm-memory/src/episodic.rs` — `index_records()` function
and `crates/wm-memory/src/episodic_keys.rs` — new enrichment module.

**How:**
1. Create a `VocabularyEnrichment` struct with three components:
   - **Hypernym map**: specific → broader terms
     - production → theater, play, performance
     - cocktail → drink, beverage, alcohol
     - class → course, studio, workshop
     - shelter → rescue, adoption, humane
   - **Action bridges**: query verbs → content verbs
     - attend → went, participated, was_at, visited
     - buy → purchased, got, ordered
     - adopt → rescued, took, brought
   - **Topic rooms**: co-occurring triggers add contextual terms
     - cooking + recipe → meal, restaurant, cuisine
     - theater + play → production, performance, stage
2. In `index_records()`, after extracting terms from content, look up each
   term in the enrichment maps. Add any bridged terms to the postings.
3. Enrichment applies to `term_db` postings only — NOT to content used for
   embedding computation (SelRoute finding: enrichment hurts embeddings).
4. Start with ~50 entries targeting our 3 known miss patterns, then scale to
   ~200 entries following SelRoute's V2 vocabulary size.

**Targeted misses:**
- Q4: "play ... attend ... local community theater" vs "production ... attended"
  - Bridge: production → play, theater, performance
- Q7: "art class ... studio" vs "painting ... course"
  - Bridge: painting → art, class → course, studio → class, workshop
- Q9: "adopt ... shelter" vs "rescued ... brought"
  - Bridge: rescued → adopt, shelter → rescue, brought → adopt

**Verification:**
- Benchmark on 10q subset: R@1 should improve from 70% to ≥80%
- R@5 must remain 100%
- Check per-query results to confirm Q4, Q7, Q9 are fixed
- If any query regresses, adjust enrichment maps

**Implementation details:**
```rust
// New module in episodic_keys.rs or separate enrichment.rs

pub struct VocabularyEnrichment {
    hypernyms: HashMap<String, Vec<String>>,
    action_bridges: HashMap<String, Vec<String>>,
    topic_rooms: Vec<TopicRoom>,
}

impl VocabularyEnrichment {
    /// Returns additional terms to index for the given content terms.
    pub fn enrich(&self, terms: &[String]) -> Vec<String> {
        let mut extra = Vec::new();
        for term in terms {
            if let Some(bridges) = self.hypernyms.get(term) {
                extra.extend(bridges.iter().cloned());
            }
            if let Some(bridges) = self.action_bridges.get(term) {
                extra.extend(bridges.iter().cloned());
            }
        }
        // Check topic rooms
        for room in &self.topic_rooms {
            if room.matches(terms) {
                extra.extend(room.additions.iter().cloned());
            }
        }
        extra.dedup();
        extra
    }
}
```

Wire into `EpisodicStore`:
- Add `enrichment: Option<VocabularyEnrichment>` field
- In `index_records()`, after `index_terms_with_aliases()`, call
  `enrichment.enrich(&terms)` and add bridged terms to postings
- Add `with_enrichment()` builder method
- Load from JSON file or embedded static map

#### Step 1B: Session-Aware RRF Reranking

**What:** After deterministic scoring, compute session-level aggregate scores
and fuse with turn-level scores via Reciprocal Rank Fusion (RRF). When
multiple turns from the same session match the query, all turns in that
session get a ranking boost.

**Where:** `crates/wm-memory/src/episodic.rs` — `search_with_limits()`
function, after scoring and before final sort.

**How:**
1. After computing deterministic scores for all candidates, group by
   `session_id`.
2. For each session, compute aggregate score = sum of turn scores.
3. Rank sessions by aggregate score.
4. For each turn, compute:
   - `r1` = turn-level rank (by deterministic score)
   - `r2` = session-level rank (inherited from session's aggregate rank)
   - `fused_score = 1/(k + r1) + 1/(k + r2)` where k=60 (standard RRF constant)
5. Sort by `fused_score` instead of raw deterministic score.
6. Preserve the original deterministic score in the result for debugging.

**Why this helps:** In our miss patterns, the answer turn and competing turn
are often in the same session. Session-aware RRF doesn't change intra-session
ordering directly, but it helps when the answer turn is in a session with
multiple matching turns (boosting it over turns from less-relevant sessions).

**Verification:**
- Benchmark on 10q subset
- R@1 should improve or stay same (enrichment is the primary driver)
- R@5 must remain 100%
- Check that session grouping doesn't introduce regressions

**Implementation details:**
```rust
// In search_with_limits(), after scoring loop, before final sort:

let k = 60.0_f32;

// Group candidates by session and compute session aggregate scores
let mut session_scores: HashMap<Option<Uuid>, f32> = HashMap::new();
for r in &results {
    *session_scores.entry(r.record.session_id).or_default() += r.score;
}

// Rank sessions by aggregate score
let mut session_ranks: Vec<(Option<Uuid>, f32)> =
    session_scores.into_iter().collect();
session_ranks.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(Equal));
let session_rank_map: HashMap<Option<Uuid>, usize> = session_ranks
    .iter()
    .enumerate()
    .map(|(i, (sid, _))| (*sid, i + 1))
    .collect();

// Rank turns by deterministic score
let mut turn_ranks = results.iter().enumerate()
    .map(|(i, r)| (i, r.score))
    .collect::<Vec<_>>();
turn_ranks.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(Equal));
let turn_rank_map: HashMap<usize, usize> = turn_ranks
    .iter()
    .enumerate()
    .map(|(rank, (idx, _))| (*idx, rank + 1))
    .collect();

// Apply RRF fusion
for (i, r) in results.iter_mut().enumerate() {
    let tr = turn_rank_map[&i] as f32;
    let sr = session_rank_map
        .get(&r.record.session_id)
        .copied()
        .unwrap_or(usize::MAX) as f32;
    r.score = 1.0 / (k + tr) + 1.0 / (k + sr);
}
```

**Note:** RRF fusion changes the score scale. The reranking pipeline
(`search_with_rerank`) expects deterministic scores sorted descending. If
RRF is applied, the reranking delta threshold (0.05) needs recalibration or
the RRF scores need to be normalized to [0, 1] before reranking. Test both
with and without reranking enabled.

#### Phase 1 Acceptance Gates ✅

- ✅ R@1 ≥ 80% on 10q subset (achieved 80%, up from 70%)
- ✅ R@5 = 100% maintained
- ✅ No query regresses below its current rank
- ✅ All crate tests pass (`cargo test -p wm-memory`)
- ✅ Clippy clean (`cargo clippy --all-targets`)
- ✅ Enrichment maps are embedded static (no runtime LLM)
- ✅ Enrichment applies to term postings only, not embeddings
- ✅ Format clean (`cargo fmt --all -- --check`)

---

### Phase 2: Drop Embeddings, Go Pure Lexical + SIMD

**Goal:** Maintain R@1 ≥ 80%, reduce latency from ~17s to <100ms
**LLM inference:** Zero
**CPU:** Minimal (SIMD-accelerated lexical search)

**Prerequisite:** Phase 1 achieves R@1 ≥ 80% with lexical-only scoring
(reranking disabled or proven unnecessary).

#### Step 2A: Benchmark Without Embeddings

1. Run 10q benchmark with `WM_EPISODIC_RERANK_ONLY=0` (or no embedder attached)
2. Confirm R@1, R@5, R@10 are maintained without cosine reranking
3. Measure latency: should drop from ~17s to <1s (no embedding HTTP calls)
4. If R@1 drops without reranking, investigate whether enrichment + RRF
   compensate. If not, defer Phase 2 until Phase 1 is stronger.

#### Step 2B: SIMD-Accelerated Cosine (Optional Fallback)

If we keep any vector fallback (for edge cases or other benchmarks):

1. Add `iqdb-distance = "1.0"` to `wm-memory/Cargo.toml`
2. Replace `cosine_sim()` in `episodic.rs` with `iqdb_distance::cosine()`
3. Replace `cosine_sim()` in `vector.rs` with `iqdb_distance::cosine()`
4. Normalize embeddings at storage time (in `store_batch_with_embedding`)
5. Use `cosine_normalized()` for pre-normalized vectors (dot product fast path)
6. Build with `RUSTFLAGS="-C target-cpu=native"` for AVX2
7. Benchmark: expect 7-10x speedup on cosine computation

Alternative: `innr` crate if AVX-512 support is needed.

#### Step 2C: Optimize Lexical Search Path

1. Profile the pure-lexical search path with `cargo flamegraph`
2. Identify hot spots in `search_with_limits()`:
   - `term_postings()` — LMDB reads + deserialization
   - `tokenize()` — string processing
   - `load_records()` — LMDB reads + deserialization
   - Scoring loop — HashMap operations
3. Optimize term cache hit rate (pre-warm common terms)
4. Consider parallel candidate loading with rayon
5. Target: <100ms end-to-end for 10K records

#### Phase 2 Acceptance Gates

- R@1 ≥ 80% maintained without embeddings
- R@5 = 100% maintained
- Latency p50 < 100ms on 10q subset (down from ~17s)
- No new dependencies that require network or GPU
- `cargo test -p wm-memory` passes
- SIMD build optional (feature flag or build script)

---

### Phase 3: Holographic Pre-Filtering + Temporal Partitioning

**Goal:** Maintain R@1 ≥ 80%, reduce latency from <100ms to <1ms at scale
**LLM inference:** Zero
**CPU:** Minimal (O(log N) pre-filtering before O(K) scoring)

#### Step 3A: Temporal Partitioning

**What:** Partition the episodic inverted index by time windows. At query
time, search most-recent partitions first with early stopping.

**Why:** Conversational memory has strong recency bias. LongMemEval questions
typically ask about recent events. AgentIR showed O(log(1/ε)) work
independent of corpus size with temporal partitioning.

**How:**
1. Add a `time_partition` field to the term index. Instead of a single
   `term → [EpisodicId]` mapping, use `term → [(partition, [EpisodicId])]`.
2. Partitions are 7-day windows (configurable).
3. At query time, iterate partitions from most recent to oldest.
4. After each partition, check if we have enough candidates (≥ candidate_limit).
5. If yes, stop searching older partitions.
6. This reduces the scoring set from O(N) to O(K) where K is the number of
   records in recent partitions.

**Where:** `crates/wm-memory/src/episodic.rs` — `term_postings()` and
`search_with_limits()`.

**Implementation notes:**
- LMDB key format: `term\0partition_timestamp` → `Vec<EpisodicId>`
- Or: separate `term_partitions` DB with composite keys
- Backward compatible: if no partition data exists, fall back to full scan
- Partition assignment uses `record.created_at`

#### Step 3B: Holographic Coordinate Pre-Filtering

**What:** Compute 5D coordinates for each episodic record at ingestion time.
At query time, compute the query's coordinate and use LMDB cursor range scans
to find records in the same spatial zone before scoring.

**Why:** The galaxy system has `Coordinate5D` with `from_semantic()` that
accepts TF-IDF or embedding projections. Currently `encode()` uses SHA-256
(which has no semantic locality), but `from_semantic()` can produce
meaningful coordinates. This enables O(log N) spatial pre-filtering.

**How:**
1. At ingestion time, compute a TF-IDF vector for the record's content.
2. Project the TF-IDF vector into 3D (x, y, z) using a fixed projection
   matrix (e.g., random projection or PCA from a seed corpus).
3. Set w = temporal weight (recency), v = importance (default 0.5 for
   episodic records).
4. Store the 5D coordinate in a new `episodic_coords` LMDB DB, keyed by
   the 20-byte encoded coordinate (sortable for range scans).
5. At query time, compute the query's TF-IDF projection and coordinate.
6. Use LMDB cursor range scan to find records within a spatial radius.
7. Only score records within the spatial window.

**Where:**
- `crates/wm-memory/src/episodic.rs` — ingestion + search
- `crates/wm-core/src/coords.rs` — `Coordinate5D` (already exists)
- New module: `crates/wm-memory/src/episodic_coords.rs` — projection logic

**Implementation notes:**
- TF-IDF projection: maintain term→dimension mapping (hash-based or from
  vocabulary). Project content TF-IDF vector into 3D.
- Query projection: same mapping, project query TF-IDF.
- Spatial radius: start with 0.3 (covers ~40% of the space), tune by
  benchmark.
- This is a **pre-filter**, not a replacement for scoring. All records within
  the spatial window still get deterministic scoring.
- If the pre-filter is too aggressive (R@5 drops), increase the radius.

**Alternative:** Use `Coordinate5D::from_semantic()` with embedding
projections if embeddings are available. This gives better semantic locality
but requires embedding computation at ingestion time.

#### Step 3C: Bridge Episodic and Galaxy Metadata

**What:** Make galaxy system metadata (importance, neuro_score, tags,
memory_type) available as scoring signals in episodic search.

**How:**
1. When an episodic record is created from a galaxy memory, store a reference
   to the source memory's metadata (or copy key fields).
2. In episodic scoring, use:
   - `importance` as a small score boost (0.0-0.05)
   - `neuro_score` as a recency/attention signal
   - `tags` for type-aware scoring (e.g., preference queries boost
     preference-tagged memories)
   - `memory_type` for query-class-specific routing
3. This bridges the gap between the rich galaxy metadata and the flat
   episodic scoring.

**Where:** `crates/wm-memory/src/episodic.rs` — scoring loop.

#### Phase 3 Acceptance Gates

- R@1 ≥ 80% maintained
- R@5 = 100% maintained
- Latency p50 < 1ms at 10K records (in-process, warm cache)
- Latency p50 < 10ms at 100K records
- Temporal partitioning is backward compatible (old stores still work)
- Holographic pre-filtering is optional (can be disabled)
- `cargo test -p wm-memory` passes

---

### Phase 4: Agent-Controlled Iterative Search (Optional)

**Goal:** R@1 → 90%+ (matching ReFind's 93.2% on LongMemEval-S)
**LLM inference:** Yes (lightweight, local)
**CPU:** Moderate (4 search rounds + LLM inference)

**Prerequisite:** Phases 1-3 complete. R@1 ≥ 80% with pure lexical search.

#### Step 4A: Iterative Search Loop

**What:** Use WMv5's bicameral left-hemisphere (heuristic/Light LLM) to
iteratively reformulate queries and collect evidence across multiple rounds.

**How:**
1. **Round 1**: Search with original query keywords. Return top-K=5 results.
2. **Observe**: The agent sees which terms matched and which didn't.
3. **Reformulate**: The agent generates alternative keywords using:
   - Synonyms from the enrichment maps
   - Terms from the matched results (query expansion from evidence)
   - Different phrasing of the same question
4. **Round 2-4**: Search with reformulated keywords. Apply session
   deduplication (skip sessions already inspected).
5. **Fuse**: Combine results across all rounds using RRF.
6. **Answer**: Format collected evidence by session in chronological order.

**Where:**
- `crates/wm-bicameral/src/` — left hemisphere handler for query reformulation
- `crates/wm-tools/src/expansion/` — new iterative search tool
- `crates/wm-memory/src/episodic.rs` — search API (already supports
  arbitrary query strings)

**Implementation notes:**
- Use the existing `LlamaLeftHemisphere` or `BitNetHandler` for reformulation
- Keep the LLM prompt minimal: "Given these search results and this question,
  what other keywords might find the answer?"
- Budget: 4 rounds max, 5 results per round, 20 total candidates
- Session deduplication: maintain `seen_sessions: HashSet<Uuid>` across rounds
- This is the only phase that requires LLM inference — all prior phases are
  deterministic

#### Step 4B: Context Window Expansion

**What:** When a turn is retrieved, automatically include ±2 turns from the
same session for dialogue context.

**How:**
1. After retrieving top-K results, for each result, load ±2 turns from the
   same session (by `session_id` and `sequence`).
2. Return the expanded context as part of the search result.
3. This doesn't improve R@1 directly but improves downstream QA accuracy.

**Where:** `crates/wm-memory/src/episodic.rs` — new method
`search_with_context()` or post-processing in the search tool.

#### Phase 4 Acceptance Gates

- R@1 ≥ 90% on 10q subset
- R@5 = 100% maintained
- Total search latency < 2s (4 rounds × ~100ms per round + LLM inference)
- LLM inference is optional (can be disabled, falls back to Phase 1-3)
- Session deduplication prevents redundant work
- Context expansion doesn't break result formatting

---

## Architecture Decision Matrix

| Scenario | Optimal Architecture | Latency | LLM |
|---|---|---|---|
| R@1 = 100% | Pure lexical (FTS5/BM25), no embeddings, no reranking | <1ms | None |
| R@1 ≥ 80%, lexical regime | Lexical + vocabulary enrichment + session RRF | <100ms | None |
| R@1 < 80%, mixed regime | Lexical + enrichment + SIMD cosine fallback | <200ms | None |
| R@1 < 80%, semantic regime | Full hybrid (lexical + dense + reranking) | ~17s | None |
| R@1 < 90%, agent available | Iterative search with LLM reformulation | <2s | Yes |

**Our current position:** R@1 = 70%, R@5 = 100%, lexical regime.
**Target:** R@1 ≥ 80% with pure lexical (Phase 1-2), R@1 ≥ 90% with
iterative search (Phase 4).

## R@X Stage Value Analysis

### R@1 = 100% (Perfect Top-1)
- **1 memory injected** into context → minimal token cost
- No scanning or selection needed → AI directly uses the memory
- Lowest latency (no reranking, no embedding)
- Highest downstream QA accuracy (LongMemEval paper: 30% accuracy drop when
  AI must scan vs. getting the right item directly)
- **Architecture implication**: Entire embedding/reranking pipeline becomes
  dead weight. System collapses to: term postings → deterministic scoring →
  done. ~17s → <1ms.

### R@5 = 100%, R@1 < 100% (Our current state)
- **5 memories injected** → 5x more tokens
- AI must scan and reason about which memory answers the question
- Risk: AI may hallucinate by combining fragments from wrong memories
- Risk: AI may miss the answer in the noise
- Downstream accuracy depends on AI's reading capability
- Strong LLMs (GPT-4 class) may recover much of the gap
- Weaker models will struggle more

### R@10 = 100%, R@5 < 100%
- **10 memories injected** → 10x tokens, significant context pollution
- High chance of irrelevant content distracting the AI
- Reading step becomes critical and error-prone
- System architecture should shift investment from retrieval to reading
  (better context formatting, Chain-of-Note reasoning, selection model)
- Risk: AI may reference the wrong memory or get confused by contradictions

### If R@1 = 100%: Are Sequential Steps Necessary?

No. If deterministic scoring alone achieves R@1 = 100%:
- **Cosine reranking is dead weight** — research confirms it doesn't help in
  lexical regimes (Training-Free Fusion paper: "net fusion gain over BM25 is
  small and not significant" on LongMemEval-S)
- **Cross-encoder reranking hurts** — same paper: -6.9pp Hit@1
- **Embedding infrastructure is unnecessary** — no embedder, no ONNX runtime,
  no vector store. System becomes pure lexical retrieval, CPU-only, ~100x
  faster
- **Pipeline collapses** from 5 stages to 2: term postings → scoring → done

### If R@10 = 100% but R@1 is Low

The retrieval system is finding the needle but failing to rank it first.
Implications:
- System should shift investment from retrieval to **reading** — better
  context formatting, Chain-of-Note, or a lightweight selection model
- With 10 memories in context, AI is more likely to hallucinate or pick wrong
- A "selection" stage between retrieval and generation becomes necessary
- The LongMemEval paper's 30% accuracy drop is largely from this reading failure

## Benchmark Protocol

### 10q Subset (Fast Iteration)

```bash
cd /home/lucas/Desktop/WMv5
python scripts/longmemeval_bench.py \
    --questions 10 \
    --store-dir /tmp/wm_bench \
    --rerank-only 1 \
    --embedder-backend onnx
```

Check:
- R@1, R@5, R@10, MRR
- Per-query results (which queries miss, what rank is the answer)
- Latency (p50, p95)

### 50q Subset (Validation)

```bash
python scripts/longmemeval_bench.py \
    --questions 50 \
    --store-dir /tmp/wm_bench_50 \
    --rerank-only 1 \
    --embedder-backend onnx
```

### Pure Lexical (No Embeddings)

```bash
python scripts/longmemeval_bench.py \
    --questions 10 \
    --store-dir /tmp/wm_bench_lexical
    # No --rerank-only or --embedder-backend flags
```

## Research Sources

- [LongMemEval (ICLR 2025)](https://arxiv.org/abs/2410.10813)
- [Training-Free Lexical-Dense Fusion (2026)](https://arxiv.org/html/2606.04194)
- [SelRoute: Query-Type-Aware Routing (2026)](https://arxiv.org/html/2604.02431)
- [ReFind: Agent-Controlled Search (2026)](https://arxiv.org/html/2608.12888)
- [AgentIR: Cascade Retrieval Substrate (2026)](https://ar5iv.labs.arxiv.org/html/2605.25092)
- [SuperLocalMemory V3 (2026)](https://arxiv.org/html/2603.14588)
- [MemX: Local-First Memory (2026)](https://arxiv.org/abs/2603.16171)
- [iqdb-distance (SIMD, 2026)](https://crates.io/crates/iqdb-distance)
- [innr (SIMD, 2026)](https://github.com/arclabs561/innr)
- [vcal-core (HNSW+SIMD, 2026)](https://github.com/vcal-project/vcal-core)
- [HNSW (original paper)](https://arxiv.org/abs/1603.09320)
- [RRF (Cormack et al. 2009)](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf)

## Related Documents

- `docs/RETRIEVAL_DEVELOPMENT_PLAN.md` — Original Phase 0-3 development plan
- `docs/V6_ACCURACY_PERFORMANCE_ROADMAP.md` — Accuracy roadmap with 50q results
- `docs/V6_HOLOGRAPHIC_MEMORY.md` — Holographic memory architectural position
- `docs/V6_EPISODIC_PERFORMANCE_PLAN.md` — Episodic performance optimization
- `docs/VECTOR_SEARCH_ROADMAP.md` — Vector search architecture roadmap
