# V6 Phase 4 Research: LongMemEval Retrieval Improvement

**Prepared:** 2026-08-19
**Purpose:** Literature review and competitive analysis to guide Phase 4
recall improvements beyond the 86% R@1 baseline.

## Current Standing

| System | S-variant R@5 | Approach |
|--------|-------------|----------|
| **Relay** (#1) | 97.0% | Hybrid BM25 + semantic (RRF) → cross-encoder reranker → gradient time-window → structured metadata |
| **Redis (Remis+Instruct)** | 86.1% QA | Hybrid BM25 + dense on raw chunks + LLM-extracted facts (dual store) |
| **WhiteMagic v6** (us) | 100% R@5, 86% R@1 | Pure lexical coverage scoring + enrichment + reverse enrichment |

Our R@5=100% is the best published. Our R@1=86% is competitive without
embeddings or LLM in the loop. The gap is R@1 — we find the answer but
don't always rank it first.

## Literature Findings

### LongMemEval Paper (Wu et al., 2025)

- **Finding 1**: Turn-level granularity beats session-level (we already do this)
- **Finding 2**: **Key expansion** — extracting user facts/keyphrases and adding
  them as index keys — gives **+4% recall@k**. Biggest lever we haven't tried.
- **Finding 3**: Time-aware indexing helps temporal reasoning (+7-11%)
- **Finding 4**: Reading accuracy matters (Chain-of-Note, JSON format) — QA, not retrieval

### Training-Free Fusion Paper (opsem, 2026)

- On **LongMemEval-S specifically**: BM25 already saturates. Dense fusion gain
  over BM25 is **small and not significant** (+0.67 pp R@1, p=0.43).
  → Confirms our pure-lexical approach is well-suited for this benchmark.
- Cross-encoder reranker (ms-marco-MiniLM) **hurts** on conversational queries
  (-6.9 pp). Off-the-shelf web-search rerankers are out-of-distribution.
- Late interaction (max-sim over turns) helps on multi-hop/temporal but trails
  BM25 on adversarial. Fusion is the hedge.
- Practical recommendation: (i) turn-level late interaction, (ii) fuse with BM25
  at score level, (iii) prefer stronger encoder, (iv) **do not add cross-encoder
  without validating on target distribution**.

### Relay (#1 on LongMemEval)

Four load-bearing components:
1. **Hybrid retrieval**: BM25 + semantic embeddings via reciprocal rank fusion
2. **Cross-encoder reranker**: Top-K → cross-encoder scores (query, doc) pairs
   jointly. This is where S-variant jumps from mid-80s to 97%.
3. **Gradient time-windowing**: Soft recency decay, not hard clip
4. **Structured metadata**: Decisions, topics, artifact types as queryable dimensions

Uses Xenova/all-MiniLM-L6-v2 (384-dim, ONNX, local) — same model family as our
`.fastembed_cache/` BGE-small.

### Redis Remis+Instruct (86.1% QA)

- **Remis**: Splits sessions at topic shifts → chunks with dense + BM25.
  Neighboring chunks expand retrieved context.
- **Instruct**: LLM-extracted facts (create/update/delete individual facts)
- **Combined**: Raw excerpts + extracted facts → answer model draws from both
- Key insight: Raw chunks preserve quotes/names/dates/numbers that extractors omit

### Zep (Graphiti)

- Temporal knowledge graph engine
- Dynamic, non-lossy fact updates with validity periods
- 94.8% on DMR benchmark (vs MemGPT 93.4%)
- 18.5% accuracy improvement on LongMemEval, 90% latency reduction

## Phase 4 Approaches (Ranked by Potential)

### 4A: Key Expansion (highest potential)

**Why**: LongMemEval paper's own Finding 2. Asymmetric — adds index keys to
answer turns that competing turns don't have.

**What**: At index time, extract keyphrases and entity names from each turn.
Add as typed keys in `episodic_keys.rs`.

**How**:
1. Rule-based: Capitalized words → entity keys, numbers → numeric keys,
   pattern matching for dates/durations/locations
2. LLM-based: Bicameral left hemisphere extracts user facts per turn
3. Hybrid: Rule-based for entities/numbers, enrichment for concepts

**For our 7 misses**:
- Q42: Answer mentions "Hawaii" → entity key "hawaii" → query "trip family week"
  doesn't match, but the key creates an additional retrieval pathway
- Q38: Answer mentions "IKEA" → entity key "ikea"
- Q7: Answer mentions "Serenity Yoga" → entity keys "serenity", "yoga"

**Risk**: Over-extraction could help competing turns too. Must be targeted
(entities, numbers, dates — not common nouns).

**Target**: R@1 86% → 90%+

### 4B: Embedding Similarity Reranking (high potential)

**Why**: Relay's cross-encoder is the biggest single lever for S-variant.
We already have BGE-small downloaded and LanceDB wired.

**What**: After deterministic scoring produces top-20 candidates, rerank by
cosine similarity between query embedding and content embedding.

**How**:
1. Enable ONNX embedder (BGE-small, already in `.fastembed_cache/`)
2. Embed all episodic records at index time (batch embedding already wired)
3. At search time: embed query, compute cosine vs top-20 candidates, rerank
4. Hybrid score: `α * deterministic_score + (1-α) * cosine_similarity`

**Critical**: The opsem paper says off-the-shelf cross-encoders hurt. But:
- They tested ms-marco-MiniLM (web-search trained), not BGE (general purpose)
- Embedding similarity reranking is lighter than cross-encoder and may be
  more robust to distribution shift
- Must validate on our 50q before committing

**Target**: R@1 86% → 92%+ (if embeddings help break near-ties)

### 4C: Topic-Shift Chunking (medium potential)

**Why**: Redis/Remis achieves 86.1% with topic-shift chunking + neighboring
chunks. Different from our failed window indexing because it creates new
index entries rather than adding symmetric bonuses.

**What**: Detect topic boundaries within sessions. Create chunk-level index
entries that combine 2-3 adjacent turns on the same topic.

**How**:
1. Simple heuristic: topic shift when cosine similarity between adjacent
   turn embeddings drops below threshold
2. Or: keyword overlap heuristic (if <20% term overlap between adjacent
   turns, start new chunk)
3. Index chunks alongside individual turns (additive, not replacement)

**Why different from Phase 3 window indexing**: Window indexing added a
symmetric score bonus to existing turns. Topic-shift chunking creates *new*
documents with combined content, producing different retrieval pathways.

**Target**: R@1 86% → 88-90% (helps multi-turn answers)

### 4D: Gradient Time-Windowing (medium potential)

**Why**: Relay uses soft recency decay. Our session_boost was discrete and
caused regressions, but a continuous decay might be gentler.

**What**: Apply a small recency weight based on session position in the
conversation history.

**How**: `score += decay_factor * (session_index / total_sessions)` where
decay_factor is small (0.01-0.02). Unlike session_boost, this is continuous
and doesn't create discrete jumps.

**Risk**: May not help if answer sessions aren't systematically more recent
than competing sessions.

### 4E: Structured Metadata Indexing (lower priority)

**Why**: Relay indexes decisions, topics, artifact types as queryable
dimensions.

**What**: Extend episodic keys with topic tags, artifact types, and decision
markers extracted from content.

**How**: Use existing `episodic_keys.rs` infrastructure to add:
- Topic keys (e.g., "fitness", "shopping", "travel")
- Decision keys (e.g., "chose", "bought", "decided")
- State keys (e.g., "completed", "planned", "cancelled")

## Recommended Execution Order

1. **4A (Key Expansion)** — highest expected value, pure Rust, no dependencies
2. **4B (Embedding Reranking)** — high value, needs embedder activation
3. **4C (Topic-Shift Chunking)** — medium value, needs embedder for topic detection
4. **4D (Gradient Time-Window)** — quick to try, low risk
5. **4E (Structured Metadata)** — lower priority, incremental

Each phase should be validated on 50q with per-case analysis before proceeding.
