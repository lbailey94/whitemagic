# Research Note: Agent Memory — Temporal Supersession, Conflict, Abstention, Reranking

**Date:** 2026-08-20
**Method:** arXiv API survey, follow-up to `V6_PHASE4_RESEARCH.md`.
**Purpose:** Update the MemoraStrict roadmap (T1/T6, T8, T10, T2) and Phase 4B
reranking plan with the current state of the art before implementation.

All papers below were confirmed on arXiv on 2026-08-20. Summaries are from
abstracts; none have been deep-read yet.

## T1/T6: Temporal Supersession

### ScrubJay-MEM — type-conditioned perishability (2608.04746, Aug 2026)
- Each memory encoded as a What–Where–When tuple with an estimated
  perishability π_i and utility horizon τ_i; auto-classified per-memory decay
  coefficient; retroactive revision at O(1) LLM calls.
- **Critical caveat**: "Gains narrow under stronger backbones and **reverse on
  fact-consolidation tasks**" — decay helps perishable facts (events) only.
- **Implication for us**: confirms our recency-decay reversion results. Any
  perishability must be *per fact type* (we have `EpisodicKind` + typed keys
  to hang this on), never a blanket scoring-layer decay.

### Post-Retrieval Assembly (2606.01435, updated Aug 2026)
- Separates evidence extraction (semantic matching into a candidate
  representation) from policy execution (the answer policy) in
  post-retrieval assembly. On MemoryAgentBench FactConsolidation: reaches
  82%/93% single-hop vs a prior best of 54%.
- **Key attribution finding**: "Most of the gain comes from separating
  evidence identification from final policy execution rather than from the
  freshness operator itself."
- LongMemEval check: no significant advantage (26/45 vs 29/45, McNemar
  p=0.45) — "bounding the result to current-value questions with explicit
  version metadata."
- **Implication for us**: validates both (a) our planned post-retrieval
  resolution layer for T1, and (b) our conclusion that LongMemEval cannot
  measure temporal-supersession work. MemoraStrict T1/T6 is the right target.

### Governed Persistent Memory (2608.12476, Aug 2026)
- Bitemporal state-transition model: source-bound admission, derived
  lifecycle state, current public barriers, fail-closed structured release.
- Five executable clauses: ledger integrity, source binding, conflict
  isolation, non-revival after retraction/deletion, exact claim closure over
  a fresh view at one verified head.
- **Implication for us**: the "derived lifecycle state" idea (superseded/
  retracted/deleted computed from the bitemporal record, not stored ad hoc)
  is a clean contract for T1/T6 read-time resolution.

### STALE / StateAuditor (2608.01619, Aug 2026)
- The "implicit policy adaptation gap": agents *know* stored state is
  outdated yet still plan around the old value. Fix audits from stored state
  to draft; only provenance- and chronology-verified transitions trigger
  repair — "what is verified is provenance and chronology — not semantic
  supersession."
- **Implication for us**: read-time resolution should prefer deterministic
  chronology (session sequence/timestamps) over semantic similarity when
  picking the current value.

## T8: Contradiction Detection

### TANGLE — irreducible conflict benchmark (2608.13921, Aug 2026)
- 541 instances across 40 personas: context-partitioned, behavior-oscillation,
  and source-contradiction conflicts. Core framing: conflicts are often
  *genuinely unresolvable* — the right behavior is recognizing
  underdetermination, preserving alternatives, seeking clarification, and
  acting without forcing a definitive answer. Fixed rules are insufficient.
- **Implication for us**: T8 conflict flagging must *present* the conflict
  (both values + provenance) rather than silently pick a winner.

### TOKI — bitemporal operator algebra (2606.06240, Jun 2026)
- Contradiction resolution is write-time concurrency control. Four production
  heuristics (last-writer-wins, evidence-weighted merge, await-confirmation,
  per-rule policy) typed as bitemporal operators with isolation
  preconditions; the losing fact is preserved in an audit row. Every baseline
  that keeps an LLM judge on the write path admits at least one write-time
  anomaly (replay inconsistency, belief-drift skew, audit erasure).
- **Implication for us**: our write-audit journal is the right substrate; a
  conflict write should record both claims (audit-row pattern), and any
  adjudication must be keyed-loggable for replay.

### MELD — distributed memory merging (2608.16357, Aug 2026)
- Five-outcome claim admission (insert, merge, relate, conflict, reject)
  decided from scoped claim-key identity + embedding similarity + an NLI
  verdict, under context and freshness gates. "A detected contradiction is
  preserved for later adjudication, never silently resolved."
- **Implication for us**: the five-outcome admission is a good ingestion-time
  contract; the claim-key identity idea matches our typed index keys. Also
  relevant to the Sangha mesh long-term.

## T2: Abstention

- **CommitDistill** (2605.18284): deterministic, embedding-free, local-only
  memory for git histories with a *calibrated silence threshold* (θ=2.5) on
  TF-IDF scores that abstains on out-of-distribution queries. Close
  philosophical sibling to our local-first stance; suggests calibrating our
  `min_score`/`min_coverage` against corpus statistics rather than guessing.
- **RSCB-MC** (2604.27283): risk-sensitive contextual bandit framing for
  coding-agent memory injection; abstention is a first-class safety action,
  false-positive injection penalized more than missed reuse. Validates
  abstention as a *product* feature for coding agents specifically.
- **Kumiho** (2603.17244): 97.5% adversarial refusal accuracy via formal
  belief-revision semantics (AGM postulates) over a versioned graph memory.
- **GroupMemBench** (2605.14498): multi-party memory benchmark; abstention is
  one of six categories; **a simple BM25 baseline matches or exceeds most
  agent memory systems** — further validation of our lexical-first design.
- **RE-call** (prior): 48.1% false-abstain on near-misses — remains an open
  problem field-wide; keep abstention opt-in.

## Phase 4B: Reranking

### ConvMemory v1/v2 (2605.28062, 2606.10842)
- **v2 pattern is exactly our situation**: a fine-tuned cross-encoder that
  *only reorders a protected top-10 candidate set* — Recall@10/Hit@10 are
  preserved *by construction* while MRR rises (+0.073) and H@1 (+0.10) on
  LoCoMo. Since our R@5/R@10 are already 1.00, a protected-top-K rerank can
  only improve R@1/MRR — it is structurally regression-free on recall.
- Honest negative attribution: the learned temporal window is *not*
  temporally specific — the mechanism is cheap cross-encoder distillation
  over fused dense+lexical features. Do not expect temporal structure to be
  learned implicitly.
- v2 sits 0.013 MRR below a full-pool mxbai-rerank-large reference at far
  lower cost — cascade pattern is cost-effective.

### MemReranker (2605.06132)
- Reasoning-aware reranking family (0.6B/4B, Qwen3-Reranker distillation)
  targeting exactly our miss categories: temporal constraints, causal
  reasoning, coreference resolution; multi-teacher pairwise calibration
  fixes miscalibrated relevance scores. 0.6B matches 4B/8B open models and
  GPT-4o-mini on key metrics at 10–20% of large-model latency.

### opsem replication (2606.04194, known)
- Off-the-shelf web-search cross-encoders (ms-marco-MiniLM) *hurt*
  conversational queries (−6.9 pp). A conversational-trained reranker or an
  LLM judge is required; do not drop in a web reranker.

### Cognis (2604.19771)
- Production open-source stack: OpenSearch BM25 + Matryoshka vectors fused
  by RRF + BGE-2 cross-encoder rerank + temporal boosting; context-aware
  ingestion with version tracking. SOTA claims on LoCoMo + LongMemEval.
  Useful existence proof for the full cascade.

## Also Noted

- **Supra Cognitive Modes** (2607.19096): per-query routed modes (lexical/
  dense lookup, graph multi-hop, stratified synthesis) over one shared
  substrate — architecturally similar to our query-class planner; reports
  86.00% LongMemEval (n=500), 68.61% adversarial abstention.
- **ChronoMem** (2607.27773): semantic version control + rollback for agent
  memory (snapshots per write, natural-language rollback) — resonates with
  our transaction snapshots; future direction for memory versioning.
- **Auto-Dreamer** (2605.20616): offline consolidation learned via RL (GRPO),
  12× smaller active memory bank — relevant to T5/dream-cycle consolidation
  later, not now.
- **MemForest** (2605.23986): write-efficient hierarchical temporal index;
  LongMemEval-S 81.8% pass@1 (Qwen3-30B). Read-side focus; our write path is
  already fast at this scale.
- **Agent Memory systems characterization** (2606.06448): phase-aware cost
  profiling (construction/retrieval/generation) across 10 systems; 10 system
  recommendations incl. freshness-latency tradeoffs. Good methodology
  citation for MemoraStrict's cost metrics.

## Revised Conclusions for the Roadmap

1. **T1/T6 (do next, as planned, post-retrieval)**: query-type-aware
   resolution layer for explicit "current/latest" queries, using
   deterministic chronology (session sequence + timestamps) — not semantic
   supersession (StateAuditor) and not scoring decay (ScrubJay reversals,
   our own reversion results). Consider a derived lifecycle state per fact
   group (GPM) so "current" resolution is a lookup, not a computation.
   LongMemEval neutrality is *expected* (p=0.45 replication); MemoraStrict
   T1/T6 is the acceptance gate.
2. **T8 (read-time flagging, TANGLE semantics)**: surface conflicts with
   both values + provenance; never silently resolve. TOKI's audit-row pattern
   maps onto our write-audit journal if we later add write-time adjudication.
   MELD's five-outcome admission is the ingestion-time contract to grow into.
3. **T2 (calibrate, stay opt-in)**: calibrate `min_score`/`min_coverage`
   against corpus statistics (CommitDistill's calibrated silence threshold
   is the model); false-abstain remains the known field-wide risk (RE-call).
4. **Phase 4B (protected top-K rerank)**: rerank only the deterministic
   top-10 (recall preserved by construction — ConvMemory v2 pattern). Use a
   conversational-trained reranker or the bicameral LLM judge, never an
   off-the-shelf web reranker (opsem −6.9 pp). Acceptance: LongMemEval 50q
   R@1 ≥ 0.86 held with MRR improvement, plus MemoraStrict no-regression.
5. **Benchmark strategy validated**: GroupMemBench's BM25-beats-memory-systems
   result and the Post-Retrieval Assembly LongMemEval null both confirm the
   pivot to MemoraStrict for capability measurement.
