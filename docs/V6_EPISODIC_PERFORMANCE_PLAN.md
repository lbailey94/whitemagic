# V6 Episodic Performance Plan

**Status:** Phase 0 measurement starting
**Branch:** `v6-dev`
**Accuracy reference:** `a2bac29`
**Latency reference:** v6 episodic p50 `122.3 ms`, p95 `226.6 ms`, p99
`639.9 ms` under the MCP benchmark protocol

## Objective

Preserve the accepted v6 episodic recall gains while returning retrieval toward
WMv5-class latency. The current v6 scorer scans and tokenizes the complete
episodic LMDB lane for every query. That is an experimental implementation
choice, not the intended v6 architecture.

## Non-Negotiable Invariants

- Canonical episodic records remain the source of truth.
- Sidecar index failure never loses or rejects a raw record.
- Record IDs remain stable across rebuilds and migration.
- Private and model-excluded records never enter the public sidecar index.
- Revoked and superseded records are filtered against current LMDB state.
- v5 `memory.search` behavior and benchmark results remain unchanged.
- Accuracy gates are evaluated before performance claims.

## Phase 0: Measurement

Add an in-process benchmark separate from MCP process startup. Measure:

- Append latency, single record and batch.
- Search latency at 100, 1,000, 10,000, and 100,000 records.
- Candidate count and rerank count.
- Cold-reader and warm-reader latency.
- Query cache hit and miss latency.
- Memory and index size.

Retain the end-to-end 50-question benchmark for product behavior. The two
timing layers must not be conflated.

## Phase 1: Canonical-ID Sidecar Index

Create a dedicated episodic Tantivy index with:

- Stored canonical episodic ID.
- Indexed redacted content.
- Indexed non-sensitive retrieval metadata.
- Timestamp and sequence fields.
- No duplicate source documents.

LMDB remains authoritative for content, visibility, validity, provenance, and
final release filtering. The sidecar produces broad candidate IDs; the store
resolves current records before returning them.

Index consistency policy:

1. Append the raw LMDB record first.
2. Add the public projection to the sidecar.
3. Record an index-health failure if projection fails.
4. Rebuild the sidecar from LMDB on demand or during repair.
5. Fall back to the current scan path while the sidecar is degraded.

This intentionally avoids pretending that LMDB and Tantivy form one atomic
transaction.

## Phase 2: Bounded Selective Scoring

Use the sidecar to retrieve a bounded candidate set, then score only that set
with the accepted normalized scorer. Candidate scoring may use:

- Stemmed query coverage.
- Exact phrase and answer-bearing term density.
- Session and temporal relevance.
- Source validity and provenance confidence.
- Query-type-specific weights.

The scorer must not scan all records or perform unbounded graph expansion on
the request path.

## Phase 3: Warmth and Caching

- Keep a warm Tantivy reader for the episodic sidecar.
- Cache normalized query terms.
- Cache short-lived query results with an index-generation key.
- Invalidate or advance the generation on append and rebuild.
- Batch sidecar commits for batch memory writes.
- Precompute normalization at append time where it reduces query work.

Cache keys must include query, limit, historical-mode, visibility scope, and
index generation. A cache hit must never bypass current privacy or validity
checks.

## Phase 4: Fault, Privacy, and Migration Tests

- Raw append succeeds when sidecar indexing fails.
- Rebuild restores all public canonical IDs.
- Private and model-excluded records are absent from the public index.
- Revocation removes records from current results without deleting history.
- Restart preserves the sidecar generation and raw records.
- V5 stores migrate without changing existing memory IDs.
- Concurrent readers remain safe during sidecar rebuild.

## Acceptance Gates

The optimization is accepted only if the same 50-question protocol maintains
or improves:

- R@1 `>= 0.66`
- R@5 `>= 0.86`
- R@10 `>= 0.94`
- MRR `>= 0.7403`
- Candidate presence `>= 0.96`

And it reaches these latency goals on the same benchmark machine:

- Query p50 `< 100 ms`
- Query p95 `< 150 ms`
- In-process warm search p50 `< 20 ms` at the 10,000-record scale

If recall falls, retain the previous implementation behind the experimental
route and reject the optimization. If end-to-end latency improves but
in-process latency does not, report the process-start boundary separately.

## Phase 0 and Phase 1 Results

The initial in-process scan-and-score curve was approximately `0.425 ms` at
100 records, `3.26 ms` at 1,000, and `40.4 ms` at 10,000. The term-to-ID
sidecar reduced the same measurements to approximately `0.093 ms`, `1.42 ms`,
and `12.95 ms` without changing recall.

The 50-question end-to-end benchmark retained R@1/R@5/R@10 `0.66/0.86/0.94`,
MRR `0.7403`, candidate presence `0.96`, and expected-session presence `0.98`.
Query p50 improved from `122.3 ms` to `79.3 ms`; p95 remains noisy at
`210.6 ms` because the benchmark includes fresh MCP process startup. The
sidecar is accepted for the experimental v6 route. Tail latency and ingest
batching remain open optimization work.

## Deferred Ideas

- Dense vector fusion until lexical sidecar performance is understood.
- Full graph construction on every write.
- Automatic LLM-generated context for every episodic record.
- Learned reranker promotion before deterministic scorer stability.
- Encrypted Tantivy projection until the public/private index boundary is
  specified; private records must not be placed in the public index meanwhile.
