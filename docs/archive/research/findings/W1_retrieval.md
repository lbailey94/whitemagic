# W1 — Retrieval & ranking (Gen1 v26 observable behavior)

**Status:** findings · 2026-09-17 · read-only research; assigns no verdicts. Companion to
`PHASE4_WAVE1_FINDINGS.md`. Repo root for citations: `og_whitemagic/` @ v26.0.3 (`4d5be091`).
Row target: *Retrieval & ranking* (CLEANLY→compile · E2, E3 — `PHASE3_DECOMPOSITION.md:50`).
Question per `PHASE4_GEN1_TREE.md` §4.2: which observable behaviors are still unearned in
Gen3's `recall`? (Gen3 side not read in this pass; statuses below are Gen1 observations only.)

## Observed behavior (cites)

- **Model + dims (verified constants):** `MODEL_NAME = "BAAI/bge-small-en-v1.5"`,
  `EMBEDDING_DIM = 384`; the MiniLM-L6-v2 name appears only in the module docstring
  (`core/whitemagic/core/memory/embeddings.py:9,73-76`). Runtime loader order: llama-server
  `LlamaCppEmbedder` (dim auto-detected) → FastEmbed `LocalEmbedder("BAAI/bge-small-en-v1.5")`
  (`embeddings.py:204-256`). The tree row's "MiniLM-L6-v2 384d" is the docstring, not the constant.
- **HNSW facts (verified parameters):** hnswlib `space="cosine"`, `ef_construction=200, M=32`,
  search `ef=100`; index built only when ≥5 vectors; persisted as `hnsw_index.bin` +
  `hnsw_ids.json`; a cold-DB twin index exists (`embeddings.py:586-601,608-609,616-644,655-694`).
  Vectors are pre-normalized so dot product == cosine (`embeddings.py:96-98`); numpy/Rust-AVX2
  brute force is the fallback (`embedding_similarity.py:27-63`).
- **"16,219 embeddings, 0.26 ms" is docs-sourced, not reproducible here:** it occurs in 3 v26 doc
  files (`WHITEMAGIC_GEN1_v26_DOCS/core/llms.txt:11`,
  `.../test/Simulation_Orchestrator_Integration__852401d6.md:555`, `.../test/Unified_Onboarding_Flow__65a4e323.md:78`);
  no live Gen1 memory dir or `hnsw_index.bin` exists on this host (`find` → none) →
  **UNVERIFIED live; provenance = docs corpus.**
- **Multi-channel planner is the default hybrid path:** `search_hybrid(use_planner=True)` →
  `SearchQueryPlanner.execute` (`core/whitemagic/core/memory/unified.py:736-757`). 8 declared
  stages (command: `rg -c '^    [A-Z_]+ = "' core/memory/retrieval_plan.py` → **8**): lexical
  FTS5, semantic HNSW, spatial 5D, entity, constellation, graph walk, reranking; final score =
  Σ `w_i/(rrf_k+rank+1)`, k=60; defaults lexical 1.0 · semantic 1.0 · spatial 0.5 · entity 0.3 ·
  graph 0.4 · over_fetch ×3 · `max_candidates=500`
  (`search_planner.py:165-208,415-424`; `retrieval_plan.py:27-37,89-110`). Cross-galaxy HNSW hits
  merge into the semantic channel via their own RRF (`search_planner.py:178-198`).
- **Second-pass rerank is multiplicative on the RRF score:** `final = rrf × (1 + adj)` with
  `adj = 0.25·entity + 0.15·recency + 0.20·importance + 0.15·lexical_precision`; entity boost is
  an associations-table lookup; recency = `2^(−age/30d) − 0.5` clamped to ±0.15
  (`entity_reranker.py:126-164,197-204,245-292`).
- **Cross-encoder is a 0.6/0.4 blend with a live heuristic fallback:** model
  `BAAI/bge-reranker-base` loads on a background daemon thread (never blocks the hot path; first
  queries run heuristic); heuristic = unigram .40 / semantic-density .45 / bigram .10 / trigram
  .05, blended with bi-encoder score or rank prior `0.9 − 0.05·idx`; model pair cap
  `max(top_k,10)`, content ≤2000 chars (`cross_encoder_reranker.py:38,48-114,180-231,243-326`).
- **Service search chain (`memory.search` route):** backend FTS → cross-encoder → answer-aware
  (+0.15/hint, capped +0.3 onto `similarity_score`) → multi-hop RRF (primary ×2) → conversation
  rerank → trim; each stage fails soft under a 5 s budget `WM_SEARCH_POSTPROCESS_BUDGET_S`
  (`service/search_service.py:45-100`; `answer_aware.py:95-166`; `multi_hop.py:144-158`).
- **Conversation reranker:** 7 additive bonuses (command:
  `rg -c 'W_[A-Z_]+ = 0\.' conversation_reranker.py` → **7**), e.g. W_ENTITY .15, W_ANSWER_TYPE
  .12, W_SEMANTIC .10; **gated** on conversation structure (`conv_*`/`sess_*` tags or metadata) —
  no structure detected → input returned unchanged (`conversation_reranker.py:63-69,191-196,238-281`).
- **`dedup_threshold: 0.85` is tag-set Jaccard dedup inside the Rust pipeline, not an embedding
  near-dup filter:** `search_similar` passes `enable_dedup=True, dedup_threshold=0.85` plus
  importance 0.3 / recency 0.1 (`service/search_service.py:229-238`); Rust `stage_dedup` keeps
  the higher-scored candidate when tag Jaccard ≥ threshold; empty-tag candidates are skipped
  (`core/whitemagic-rust/src/search/retrieval_pipeline.rs:51-52,196-236`; pipeline default 0.8
  at `:466`). Same pipeline: `score = 0.6·score + 0.3·importance + 0.1·e^(−age/30)` then 5D
  proximity blend `1/(1+3·dist)` when coords exist (`:155-193`). Reachable only on the
  `search_similar` Rust path, not in `memory.search`.
- **Abstention 0.50 is opt-in and standalone:** relevance = 0.5·cosine + 0.3·keyword-overlap +
  0.2·min(1, 10·RRF); abstain iff top < threshold; clamp [0, 0.8]; docstring claims TPR 100 % /
  FPR 0 % on a swept 500-memory benchmark (`abstention_gate.py:14-16,34-36,68,116-153,204-218`).
  Wired only in the memory tool handler when `abstention_threshold` kwarg or
  `WM_ABSTENTION_THRESHOLD` env is set (`tools/handlers/memory.py:406-423`) — not a
  `memory.search` default.
- **HRR: circular convolution is write-side; retrieval uses qFHRR as an integer pre-filter.**
  `hrr.bind/unbind` are FFT circular convolution/correlation with deterministically seeded
  relation vectors (`hrr.py:5-7,100-165,195-211`); the write path binds content embedding ×
  `"OBJECT"` vector and tries to cache via `whitemagic.core.memory.hrr_cache`
  (`enrichment/pipeline.py:86-114`; `unified.py:403-419`) — **that module does not exist in the
  v26 tree** (`ls core/memory/hrr_cache.py` → absent), so the write-side HRR bind has no consumer
  found here. Retrieve path: `CoreAccessLayer._hrr_prefilter` quantizes all embeddings with
  qFHRR **bits=8** (class default is 4 — `qfhrr.py:51`) and filters candidates by LUT similarity
  before the vector channel (`core/intelligence/core_access.py:772-895,919-950`); on failure it
  falls back to plain search, and can reuse HRR scores as the vector channel (`:960-963`).
- **Spatial/5D channel is not HRR:** holographic coords come from `CoordinateEncoder`
  (embedding → mean-centering / anchors / PCA), stored 6D as
  `holographic_coords(x,y,z,w,v,u)`; the tree row's "HRR coords" conflates two organs
  (`core/intelligence/hologram/encoder.py:111+`; `holographic_coords.py:19-38`).
- **Graph-walk hot path:** transition prob = 0.4·semantic + 0.3·gravity + 0.2·recency +
  0.1·(1−staleness); path score = product of edge probs; parallel BFS for ≥4 seeds;
  monkey-patched into `graph_walker` at import (`graph_walker_hot_path.py:118-140,256-320,336-377`).
- **FAMA coupling (extends earlier extraction):** fresh facts +0.15 / superseded −0.20, scaled by
  fact confidence (`temporal_kg.py:49-50,286-321`); the rerank adjustment adds `0.10 × fama`
  (`entity_reranker.py:269-277`) so net effect is `×(1 + 0.10·fama)`; `temporal_filter` (opt-in
  kwarg) removes superseded memory IDs before return (`tools/handlers/memory.py:425-427,511-525`).

## Selection history

v26 accreted one ranking organ per feature wave (Gap A cross-encoder, §8.7.1 conversation, v24.3
entity/rerank, v15.1 5D, Phase-6 planner) and stitched them as an ordered, fail-soft chain of
tuned constants (0.25/0.15/0.20/0.15, 0.6/0.4, 0.85, 0.50). The planner was kept alongside the
legacy inline path "until ranking parity and latency comparisons are complete"
(`unified.py:783-787`) — duplication never resolved. The ratified decomposition folded the modes
and made ranking policy **behavior under test** (excluded from the A/B); no Gen2 planners imported
(`PHASE3_DECOMPOSITION.md:50`; `DEPENDENCY_MANIFEST.md:54`).

## Candidate Gen3 expression / manifest notes

Pass row: CLEANLY → compile; expression `recall` + earned ordering (R/strata). Per the §4.2
question, these Gen1 observable behaviors are the candidate "unearned" list to test against Gen3
`recall` (none evaluated here): (1) rank-based multi-channel fusion with weighted RRF k=60;
(2) multiplicative second-pass rerank (entity/recency/importance/lexical); (3) blended
cross-encoder with 0-token heuristic fallback; (4) conversation-gated additive bonuses;
(5) tuned abstention floor (already errata-noted in the disclosure row); (6) tag-Jaccard dedup at
0.85; (7) qFHRR 8-bit candidate pre-filter. Any import still needs ancestor · wire · acceptance ·
owner per the manifest rule.

## Adversarial cases (for the frozen spec)

1. **Stage-order score mutation:** answer-aware rewrites `similarity_score`
   (`answer_aware.py:164-167`), cross-encoder and conversation rerankers later read
   `similarity_score`/`blended_score` (`cross_encoder_reranker.py:218-231`;
   `conversation_reranker.py:169-176`) — same pipeline, different ordering depending on which
   optional stages degrade; test with each stage independently disabled.
2. **Tag-Jaccard 0.85 drops legitimate distinct memories** (two different decisions sharing
   project/type/topic tags) while paraphrase near-dups with different tags survive; empty-tag
   candidates are never deduped (`retrieval_pipeline.rs:208-227`).
3. **Cross-encoder warm-up non-determinism:** until the background model load completes the
   heuristic orders results; after it, model-blended scores can reorder; ties fall back to
   original index and the tail beyond `max(top_k,10)` keeps bi-encoder order
   (`cross_encoder_reranker.py:281-326`).
4. **Heuristic CE stopword list includes domain words** ("research", "recent", "study",
   "analysis", "framework", …) — queries made only of those words score density 0
   (`cross_encoder_reranker.py:163-177`).
5. **FAMA absence is neutral, supersession is opt-in:** no facts reads 0.0 and the default path
   can still rank a superseded fact first; only `temporal_filter` excludes them
   (`entity_reranker.py:269-277`; `tools/handlers/memory.py:511-525`).

## Ablation ideas

- Planner vs `_legacy_search_hybrid` switch (v26 shipped both, `unified.py:759-787`): measure
  ordering delta and latency; the legacy label already states parity was never confirmed.
- Disable each service-chain stage independently and the `0.10 × fama` term; map which signals
  carry ordering vs which are decoration.
- No-dedup vs tag-Jaccard 0.85 on a shared-tag corpus; count legitimate-result loss, not just
  duplicates removed.
- HRR prefilter on/off, and qFHRR bits 4 vs 8 (the codebase only ever asks for 8;
  `core_access.py:817,870`); plus graph walk product-of-probabilities vs channel-off (weight 0)
  for multi-hop queries.

## Open questions

- Which DB snapshot produced "16,219 embeddings / 0.26 ms"? No Gen1 index exists on this host — UNVERIFIED live.
- Was `abstention_gate` ever reachable in default shipped flows, or only via explicit
  kwarg/env? Only the handler wiring was found this pass.
- Did any shipped route exercise `hybrid_recall`'s HRR prefilter (default `True`) in practice,
  and at what recall cost? No in-repo benchmark found for this path.
- Was `hrr_cache` ever shipped elsewhere (module absent in v26 → write-side HRR bind appears
  unconsumed)? And which of the seven behaviors Gen3 `recall` already earns — Gen3 side not
  read here, so the "unearned" question stays open by construction.
