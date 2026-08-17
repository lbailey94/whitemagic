# WhiteMagic v6 Strategy

**Status:** Foundation slice in progress
**Branch:** `v6-dev`
**Reference baseline:** commit `b3cec87` (WMv5 release foundation)
**Research:** [`docs/V6_MEMORY_RESEARCH.md`](docs/V6_MEMORY_RESEARCH.md)
**Accuracy roadmap:** [`docs/V6_ACCURACY_PERFORMANCE_ROADMAP.md`](docs/V6_ACCURACY_PERFORMANCE_ROADMAP.md)
**Performance plan:** [`docs/V6_EPISODIC_PERFORMANCE_PLAN.md`](docs/V6_EPISODIC_PERFORMANCE_PLAN.md)
**Holographic position:** [`docs/V6_HOLOGRAPHIC_MEMORY.md`](docs/V6_HOLOGRAPHIC_MEMORY.md)

## Product Objective

Build cognitive scaffolding for local agents: durable episodic memory,
high-recall evidence retrieval, bounded context compilation, reusable skills,
and governed knowledge evolution.

V6 will not claim literal infinite context or universal perfect recall. It will
provide effectively unbounded persistent memory and measurable near-perfect
recall on declared finite evaluations.

## Compatibility Rules

- WMv5 remains the stable behavioral reference and regression oracle.
- Existing canonical memory IDs must remain importable.
- Raw source evidence must survive derived-memory failure.
- V5 MCP routes remain unchanged until a V6 route has an acceptance test.
- The v5 50-question retrieval benchmark remains mandatory for every recall
  change.
- V6 development must not silently alter the v5 release baseline.

## Foundation Phases

### V6.0 Typed Memory Contract

- `EpisodicRecord` for lossless source events.
- Typed provenance and source attribution.
- Evidence references with support, contradiction, derivation, and supersession.
- Explicit active, superseded, revoked, archived, and erased states.
- Versioned episodic serialization.
- Append-only source IDs with atomic lifecycle transitions.

### V6.1 Recall Planner

- Raw-log lexical retrieval as the first compatibility path.
- Session and temporal narrowing.
- Candidate deduplication by canonical ID.
- Query-specific selection of lexical, dense, temporal, graph, and skill views.
- Bounded associative expansion from retrieval anchors.

### V6.2 Context Compiler

- Evidence packs with citations and provenance.
- Contradiction and stale-memory handling.
- Query-specific token budgets.
- Explicit separation of observed, derived, speculative, and revoked content.

### V6.3 Consolidation and Skills

- Semantic-segment consolidation instead of eager per-turn rewriting.
- Stable profile and fact views plus demand-driven active facts.
- Verified failure lessons and executable procedural memories.
- Dream-cycle replay prioritized by surprise, utility, error, and conflict.

### V6.4 Security and Locality

- Explicit offline mode with no network calls.
- Authenticated memory scopes for multi-user deployments.
- Encrypted content and index storage.
- Fail-closed release of stale, revoked, private, or model-excluded evidence.

## Acceptance Gates

- No reduction in WMv5 R@5 on the fixed retrieval benchmark.
- Candidate presence reaches 95%, then 99%, on declared evaluations.
- Every current claim can expose its source evidence and validity state.
- Superseded or revoked records cannot support current answers.
- Restart and migration preserve raw records and IDs.
- Private and model-excluded records never enter released evidence.
- BM25-only query p95 remains below the declared local SLO.
- Learned retrieval policies remain shadow-only until paired evaluation passes.

## First Implementation Slice

The first V6 code slice adds the typed episodic contract and a dedicated LMDB
`episodic_records` database behind `MemoryStore::episodic()`. It is additive:
the existing v5 `Memory` model, MCP routes, and retrieval behavior remain
unchanged. Explicit `memory.create`, `memory.batch_create`, and session marker
writes are mirrored into the episodic lane using the v5 memory ID. Automatic
observation capture remains opt-in, and the episodic copy applies conservative
token-level redaction for obvious key/value secrets. The next slice will add a
raw-log retrieval experiment and compare it against the v5 reference using the
existing evaluator.

## Initial Retrieval A/B

The first direct comparison used the same `target/release/wm` build, fresh
stores, 50 LongMemEval-S single-session questions, candidate limit 100, and
the existing non-official turn-level evaluator.

| Metric | V5 compatibility route | V6 episodic route |
|---|---:|---:|
| R@1 | 0.64 | 0.62 |
| R@5 | 0.82 | 0.80 |
| R@10 | 0.82 | 0.88 |
| MRR | 0.7150 | 0.6929 |
| Candidate presence | 0.78 | 0.94 |
| Expected-session presence | 0.84 | 0.96 |
| Query p50 | 74.0 ms | 80.2 ms |
| Query p95 | 103.0 ms | 105.1 ms |
| Ingest average | 2.730 s | 2.734 s |

This is an exploratory result, not an accepted quality improvement. V6 finds
the answer-bearing records much more often, but the initial token-overlap
scorer ranks them less effectively. Paired per-question changes were R@1
6 wins / 7 losses, R@5 4 wins / 5 losses, and R@10 6 wins / 3 losses.

The next experiment is selective scoring over the broad episodic candidate set:
coverage, exact phrase, role/session, temporal proximity, and source validity
must be combined without weakening the high candidate recall.

### Scorer follow-up

Aligning episodic tokenization with the v5 path by stripping stopwords and
applying conservative stemming improved the same v6 route to R@1/R@5/R@10
`0.66/0.86/0.94`, MRR `0.7403`, candidate presence `0.96`, and expected-session
presence `0.98`. Against the v5 compatibility control, paired wins/losses were
R@1 `5/4`, R@5 `4/2`, and R@10 `6/0`.

This is the first accepted v6 accuracy improvement. It is not yet a complete
acceptance because raw LMDB scanning and deterministic scoring increased query
p50 to `122.3 ms` and p95 to `226.6 ms`. The next phase should add an indexed
candidate path or bounded cache to recover the local latency target without
giving back the recall gain.
