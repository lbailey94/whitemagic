# Resonance & 5D Holographic Memory Coordinates

**Working title**: "Resonance: Associative Memory Retrieval via 4D/5D Holographic Coordinates"
**Target length**: 2000–3500 words (technical)
**Paired repo**: `whitemagic-resonance` (new, split from core)
**Status**: 🟡 Stub · **Priority**: P3 (novel but needs rigor)
**Source material**: `docs/5D_COORDINATE_GUIDE.md`, `holographic_coords` schema, `resonance_model` ADR

---

## Thesis (one sentence)

Instead of retrieving memories purely by vector similarity or graph traversal, assign each memory a position in a small continuous 4D/5D coordinate space and retrieve by proximity in that space — this is cheap, interpretable, and captures associative patterns that pure cosine similarity misses.

## Key points to develop

1. **The retrieval quality gap.** Dense vectors find semantically similar content; graph traversal finds explicitly-linked content. Neither captures "these two memories feel related because of a shared emotional moment, even though they're not lexically or structurally similar."
2. **The coordinate model.** Each memory gets `(x, y, z, w)` or `(x, y, z, w, t)` where axes correspond to (emotional valence, novelty, specificity, topic-embedding-first-component, temporal_distance). Learned or heuristic.
3. **Proximity retrieval.** KD-tree or Ball-tree on low-dim coords = O(log n) retrieval at scale. Cheap.
4. **The "holographic" framing.** Every memory contains traces of every other memory via these coordinates — small perturbations in input shift many memories' coordinates by small amounts. Useful property for update patterns.
5. **Comparison to HNSW / FAISS.** This isn't a replacement for them — it's an additional retrieval channel, fusible via RRF.
6. **Benchmarks.** Same as Felt Memory essay but focused on the coord subsystem specifically.

## Open questions (honest)

- Is 4D/5D actually enough dimensions, or is this just a compressed version of higher-dim vector space? (Possibly the latter. Benchmark will tell.)
- Are the axes interpretable enough to justify the coordinate framing over raw PCA? (If yes, big win for debuggability.)
- Can this be composed with embeddings rather than substituting? (Yes, via RRF.)

## Publish venue options

- Blog post + repo README
- Workshop paper if benchmarks support a claim
- Cross-reference from Felt Memory essay

## Draft log

- [ ] Split coord subsystem into `whitemagic-resonance` repo
- [ ] Ablation study: retrieval with coords vs without
- [ ] Draft
