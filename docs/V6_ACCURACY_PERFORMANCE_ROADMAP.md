# V6 Accuracy and Performance Roadmap

**Date:** 2026-08-17
**Status:** Candidate backlog with proposed gates
**Accuracy reference:** R@1 `0.74`, R@5 `0.98`, R@10 `0.98`, MRR `0.8400`
**Latency reference:** episodic p50 `214.0 ms`, p95 `430.3 ms` (coverage grace + number scan overhead)

## Current Diagnosis

The v6 episodic path now finds the correct evidence reliably, but remaining
quality errors fall into distinct classes:

- Semantic vocabulary mismatch: `doctor` versus `Dr. Patel`.
- Multi-hop aggregation across sessions.
- Temporal and update questions.
- Preferences that are implicit rather than stated.
- Answer ranking among several records with similar query coverage.
- Long-tail latency from process startup and ingestion outliers.

The v6 design should use a different remedy for each class rather than one
larger generic reranker.

## High-Priority Accuracy Work

### 1. Specific Index-Time Keys ✅

Implemented in `wm-memory/src/episodic_keys.rs`. Typed deterministic keys:
person, date, location, org, domain, preference, entity. Each key has a
category, source span, and confidence. Wired into episodic sidecar ingest and
search as a bounded key bonus. 50q A/B: candidate presence 0.96 → 1.00.

### 2. Query-Class Planner ✅

Implemented in `wm-memory/src/query_planner.rs`. Seven classes: ExactFact,
Temporal, KnowledgeUpdate, MultiHop, Preference, Procedure, Summary. Each
class selects bounded candidate limits and key weights. 50q A/B: R@1 0.66 →
0.68, MRR 0.7403 → 0.7559.

### 3. Dual Granularity Retrieval

Maintain both:

- Turn-level canonical records for exact evidence.
- Session or semantic-segment records for multi-turn context and aggregation.

Session records must be derived sidecars with links to canonical turns. They
must never replace or duplicate the public source memories.

### 4. Associative Completion

Use the existing typed association graph and spreading activation after the
first retrieval anchor:

1. Retrieve lexical or dense anchors.
2. Expand two or three hops through temporal, causal, supersession, and
   session edges.
3. Re-score the expanded evidence using the query class.
4. Stop when evidence coverage is sufficient.

This maps directly to HippoRAG and RippleMem while reusing WhiteMagic’s
existing association primitives.

### 5. Temporal and Validity Scoring

Add bitemporal fields and query-conditioned time scoring. A newer fact should
not merely receive a generic recency boost; it should supersede an older fact
only when the same subject/key and authority rules support that transition.

TEPA and Governed Persistent Memory make revocation, stale state, and
non-revival first-class operations. This should be implemented before broad
LLM-generated summaries.

### 6. Preference and Skill Memories

Create typed, confidence-bearing derived records for:

- Explicit preferences.
- Repeated implicit preferences.
- Validated procedures.
- Failure lessons.
- Tool-call conventions.

Preference inference should remain separate from factual recall, and implicit
preferences should never outrank explicit user statements without evidence.

## Optional Research Paths

### Sparse Neural Expansion

SPLADE suggests sparse learned term expansion while preserving inverted-index
efficiency. This is attractive if a small local encoder can produce sparse
keys at ingest time. It should be evaluated against deterministic keys first.

### Late Interaction

ColBERTv2 provides token-level late interaction with compressed multi-vector
representations. It may improve rank-1 quality, but storage and local model
cost make it a later optional adapter, not the default v6 path.

### Hypothetical Query Documents

HyDE can generate a hypothetical answer-shaped document before dense search.
It may help semantic mismatch, but it introduces model latency and hallucinated
query content. Keep it opt-in behind a local-model budget and compare against
deterministic entity keys.

### Self-Reflective Retrieval

Self-RAG supports retrieving only when needed and critiquing evidence and
generation. V6 can implement the architecture without training reflection
tokens: a local or remote reader may request another retrieval pass when
evidence coverage or citation checks fail.

### HRR Associative Recall

Earlier WhiteMagic versions contain holographic and HRR concepts. Bindings for
question-answer or entity-event relationships could provide associative
pattern completion beyond lexical matching. This is a differentiating research
direction, but it needs a small synthetic benchmark before production indexing.

## Performance Work

### Immediate

- Separate process-start latency from in-process search latency.
- Add warm and cold benchmark variants.
- Batch episodic term-index updates for `memory.batch_create`.
- Track index generation and cache hit/miss rates.
- Add a query result cache with validity and visibility-aware keys.

### Later

- Warm sidecar readers at server startup only when configured.
- Background sidecar compaction and rebuild.
- Parallel candidate record loading for larger budgets.
- Optional dense vectors only after lexical and sidecar behavior is stable.
- Quantized local reranking or late interaction behind an explicit latency
  budget.

## Earlier WhiteMagic Port Candidates

| Earlier system | V6 use | Priority |
|---|---|---:|
| Specific keyword extraction V2 | Typed index-time keys | P0 |
| `search_planner` | Query-class retrieval planner | P0 |
| Holographic coordinates | Temporal/semantic candidate features | P1 |
| `spreading_activation` | Bounded associative completion | P1 |
| `causal_miner` | Multi-hop and causal queries | P1 |
| `temporal_kg` | Updates and time-aware validity | P1 |
| `working_memory` | Evidence-pack budgeting and attention | P1 |
| `reconsolidation` | Recall-triggered, source-bound updates | P1 |
| `preference inference` | Dedicated preference lane | P1 |
| HRR/hologram binding | Associative pattern completion | P2 |
| Cross-encoder reranker | Optional bounded adapter only | P2 |
| LLM query rewriting | Optional, latency-budgeted | P3 |

## Acceptance Rules

- No candidate or scorer change may reduce R@5 below `0.86` on the fixed 50q
  v6 protocol.
- Accuracy gains must be reported by query class, not only aggregate R@k.
- Performance changes must report cold, warm, in-process, and MCP timings.
- Index-time keys must include source spans and confidence.
- Derived memories must preserve canonical source IDs.
- Revoked, private, and model-excluded records must remain unreleasable.
- Any model-based expansion must be optional and bounded by a latency budget.

## Research Sources

- [SPLADE](https://arxiv.org/abs/2107.05720)
- [ColBERTv2](https://arxiv.org/abs/2112.01488)
- [HyDE](https://arxiv.org/abs/2212.10496)
- [Self-RAG](https://arxiv.org/abs/2310.11511)
- [LongMemEval](https://arxiv.org/abs/2410.10813)
- [HippoRAG](https://arxiv.org/abs/2405.14831)
- [RippleMem](https://arxiv.org/abs/2608.13334)
- [TEPA](https://arxiv.org/abs/2608.07429)
- [Governed Persistent Memory](https://arxiv.org/abs/2608.12476)
- Earlier WhiteMagic evidence: `WMdocs/benchmarks/LONGMEMEVAL_OPTIMIZATION_ROADMAP.md`
- Earlier port inventory: `WMdocs/whitemagic-v4/v2-reference/README.md`
