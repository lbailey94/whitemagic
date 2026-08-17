# V6 Holographic Memory Position

**Date:** 2026-08-17
**Status:** Architectural position for future experiments

## Short Conclusion

The old galactic/holographic system should be retained as a structured
cognitive prior and visualization layer, not restored as the primary semantic
retriever.

The current LMDB substrate is better for durable source records, exact IDs,
provenance, validity, privacy, and indexed retrieval. The old holographic
model is better for explicit temporal, importance, spatial, lifecycle, and
associative features that ordinary text retrieval does not represent well.

V6 should combine them rather than choose one.

## Old Galactic Model

Earlier WhiteMagic versions provided:

- Multiple galaxies as cognitive or project namespaces.
- Radial zones such as core, inner ring, outer ring, and far edge.
- Temporal, importance, consciousness, and relational axes.
- Holographic coordinate visualization and nearby-memory queries.
- Weighted associations, Hebbian strengthening, spreading activation, and
  constellations.
- Dream-cycle consolidation, decay, resonance, and reconsolidation concepts.

These features made memory state inspectable and provided useful priors for
retention and associative recall.

## What Was Weak

The current Rust coordinate implementation exposes an important limitation:

- `Coordinate5D::encode()` derives semantic axes from SHA-256 bytes.
- Hash coordinates are deterministic but have no semantic locality.
- Similar content does not reliably land near similar coordinates.
- Galaxy membership is a namespace or access partition, not proof of semantic
  similarity.
- Radial zones are useful lifecycle labels, but not a replacement for search.

The old 6D model also mixed several distinct concepts into one geometric
space: semantic similarity, time, importance, vitality, consciousness, and
galaxy affinity. Those dimensions should be typed fields or scoring signals in
v6, not assumed to be one physically meaningful metric.

## What the Current LMDB Substrate Improves

WMv5 and v6 now provide:

- Durable LMDB records with canonical UUIDs.
- Mmap-backed persistence and explicit transactions.
- Tantivy lexical indexes and optional dense vectors.
- Typed association edges with temporal and causal relations.
- Explicit provenance, validity, privacy, and model-exclusion fields.
- A canonical episodic lane with a term-to-ID sidecar index.
- Rebuildable projections rather than opaque derived state.

LMDB is not an array store in the numerical sense. It is a durable key-value
environment whose serialized records and secondary indexes provide the source
substrate. Dense vectors and coordinates are projections over those records.

## V6 Integration Model

### Canonical Record

Keep raw episodic content and lifecycle state in LMDB. Never make a coordinate,
summary, vector, or graph edge the only copy of evidence.

### Semantic Projection

Replace hash-derived semantic axes with one of these measured options:

1. Local embedding projection into a low-dimensional visualization space.
2. Deterministic TF-IDF or feature projection when no model is available.
3. Hash coordinates retained only as stable opaque placement, never as a
   semantic score.

### Cognitive Axes

Represent old dimensions separately:

- Semantic similarity from lexical or dense retrieval.
- Temporal relevance from event and ingestion timestamps.
- Importance from explicit user or system signals.
- Vitality from recall and utility history.
- Association strength from typed graph edges.
- Validity from active, superseded, revoked, archived, or erased state.

### Galactic Views

Treat galaxies and radial zones as queryable views for lifecycle and context
management. They can influence candidate selection or context packing, but they
must not silently override source evidence or current validity.

### Associative Retrieval

Use the current typed association graph and spreading activation as the direct
successor to the old living graph. Retrieval should seed the graph from lexical
or dense anchors, expand a bounded number of hops, and then return canonical
source records.

### HRR Research

HRR or holographic binding remains a worthwhile differentiator for pattern
completion, but it should be an experimental projection. It needs a synthetic
associative benchmark before it is allowed into the default retrieval path.

## Proposed Experiments

1. Compare SHA-derived coordinates, TF-IDF projections, and embedding
   projections as candidate tie-breakers on the fixed v6 benchmark.
2. Add temporal and importance features only to temporal and preference query
   classes, not as blanket rank boosts.
3. Use radial zones as context-pack and retention views, not search relevance.
4. Seed bounded spreading activation from top episodic candidates and measure
   multi-hop recall separately.
5. Bind synthetic question-answer and entity-event pairs with HRR and test
   associative completion against lexical and dense baselines.

## Port Decision

Port the algorithms and semantics, not the old tool surface or taxonomy
verbatim:

- Port: spreading activation, typed links, temporal decay, reconsolidation,
  working-memory budgeting, causal mining, and preference inference.
- Rebuild: semantic coordinates, query planning, session views, and evidence
  release.
- Preserve: LMDB canonical records, sidecar indexes, provenance, validity,
  privacy filtering, and explicit MCP boundaries.
- Defer: full 6D/HRR production indexing until it demonstrates improvement
  without latency or recall regressions.
