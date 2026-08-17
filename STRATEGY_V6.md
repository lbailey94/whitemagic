# WhiteMagic v6 Strategy

**Status:** Foundation slice in progress
**Branch:** `v6-dev`
**Reference baseline:** commit `b3cec87` (WMv5 release foundation)
**Research:** [`docs/V6_MEMORY_RESEARCH.md`](docs/V6_MEMORY_RESEARCH.md)

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
