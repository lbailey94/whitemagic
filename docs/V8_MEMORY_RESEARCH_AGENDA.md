# V8 Memory Research Agenda — Synthesis of Field Research + WM Heritage

**Status**: draft agenda (2026-08-28). Grounded in the mid-2026 agent-memory literature (Letta/MemGPT lineage, temporal KG systems like Zep/Graphiti, the "agent OS substrate" framing) and WM's own shipped systems (V6 holographic memory, conformal prediction, dream cycles, Gan Ying causality).

**Positioning**: WM is already a substrate ("persistent state for many agents, indefinitely") with governance the field lacks. V8 should deepen memory science without losing that moat.

---

## 1. Memory hierarchy: make the tiers explicit (working → episodic → semantic)

- Today: LMDB memories + importance scores + galaxies. The tier transitions are implicit.
- V8: label every memory with tier; define **consolidation policies** (what moves up, what decays, what compresses). The dream cycle already does consolidation — formalize it as the *only* path between tiers.
- Research anchors: MemGPT/Letta paging; biological replay during sleep (matches your dream phases); the SOSP AgenticOS "long-lived state abstractions for episodic memory" topic — you predate it, now write it up properly.

## 2. Temporal knowledge graph on top of the galaxy model

- Galaxies = spatial organization. Add **edge memory**: typed temporal edges (worked_on → session → project, mentions → topic, at → time) so recall can traverse relations, not just similarity.
- Research anchors: Graphiti/Zep episodic edges; Mem0-style per-entity extraction (but keep entity memory local).
- Incremental path: a `memory.relate` tool that stores typed edges in LMDB; traversal joins BM25/vector recall as a third fusion phase (see VECTOR_SEARCH_ROADMAP phase weights).

## 3. Trust-scored ingestion (prompt-injection defense at the write path)

- Today: dharma filters inbound messages; trust scores gate dispatch. But a poisoned memory that gets *stored* is a persistent attack.
- V8: provenance + trust attached to every memory write (source, context, cross-checked claims); low-trust memories degrade faster and rank lower in recall. Claims ledger calibration (Brier/gap) is the natural grading mechanism — reuse it.

## 4. Retrieval: three-phase fusion with conformal gates

- Today: BM25 (tantivy) + optional vector (RecallEngine) + importance weight; conformal prediction exists in wm-bicameral.
- V8: (a) batch embedding + weight tuning (per VECTOR_SEARCH_ROADMAP quick wins); (b) rerank stage (episodic rerank exists for ingest — extend to query time); (c) conformal *retrieval sets* — return recall results with calibrated confidence intervals, so agents know when memory is unsure. That's a differentiator nobody else ships.

## 5. Consolidation quality metrics

- The daemon runs 8 autonomous cycles; there's no objective quality score for consolidation.
- V8: benchmark suite from V6_BENCHMARK_DESIGN + a "memory loss" metric (post-consolidation recall delta) and a "compression ratio vs fidelity" trade-off chart. Feed results back into LearnedDreamCycle (already learns phase effectiveness — extend to consolidation policies).

## 6. Standards interop (MCP + A2A)

- MCP: WM is a server; also act as an MCP *client* so agents' memories federate.
- A2A: Sangha already does signed inter-agent messaging — publish the mapping to A2A so external agents can join the mesh with the bad-apple rule intact.
- SSE transport (in flight, planning/SSE_TRANSPORT_PLAN.md) makes WM a network-callable substrate — prerequisite for both.

## 7. Substrate positioning & public evidence

- The field now defines "agent OS" as the substrate layer (CortexPrism mid-2026 survey; AgenticOS workshop). WM qualifies — but has no paper, no write-up.
- V8 artifact: a position paper / benchmark post ("memory substrate with built-in governance") — Violet-style: publish the architecture, invite red teaming. Predates-claims get dated evidence (v7 shipped 2026-02-07; governance primitives from the 2025 MandalaOS design; Gan Ying/gardens from the 2025 Python lineage).

## Priority order

1. §3 trust-scored ingestion (security wins first — Violet doctrine)
2. §1 tier labels + consolidation policies (cheapest, biggest recall win)
3. §4c conformal retrieval sets (differentiator)
4. §2 temporal edges (largest effort)
5. §6 standards, §7 positioning, §5 metrics
