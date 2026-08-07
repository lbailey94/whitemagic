# Strategic Gap Analysis: v4 Tool Catalog vs v2

**Date**: August 3, 2026
**Updated**: August 4, 2026 (OrtEmbedder + Router Integration + PyO3 Verified + Benchmarks — 141 tools, 1428 tests, 16 crates)
**Context**: After completing v4 phases R1–R7, deep integration (drive bias, bicameral consensus, timescale hooks, workspace events), LLM right hemisphere integration, and local AI integration L1–L5 (BitMamba autonomic, LlamaLeftHemisphere, BitNet right hemisphere, InferenceRouter wired into BicameralEngine, OrtEmbedder via fastembed-rs). PyO3 bridge verified end-to-end. Benchmarks for router + embedder.

---

## Executive Summary

v2 has ~877 tools across 28 Gana. v4 has 141 tools (126 cognitive + 15 v4/subsystem). Closing the full gap would require ~50K lines of Rust for diminishing returns — many v2 tools are Python-era artifacts, thin wrappers, or domain-specific tools with limited cognitive value.

**Recommendation**: Phase 9 is **substantively complete** at 126 cognitive tools. v4 CyberBrain phases R1–R7 are complete (17 crates, 1302 tests). Deep integration complete (drive bias → dispatch, bicameral → high-stakes, timescale → citta/dream, workspace → drive). LLM right hemisphere complete (OpenAI-compatible via ureq, env-configured, graceful fallback). Shift focus to local AI integration (BitMamba, llama.cpp) and migration tooling.

---

## v2 Tool Categories: Value Assessment

### High Value (Port Next)

| Category | v2 Tools | v3 Status | Why It Matters |
|---|---|---|---|
| **Net** (associations, emergence) | 33 | 9 ported (Tier 5 ✅), ~24 gap | Core memory graph operations — association mining, pattern detection, network analysis all implemented |
| **Ghost** (consciousness, smarana) | 33 | 11 ported (Tier 5 ✅), ~22 gap | smarana.status/trace, apotheosis.check, citta.history, dream.analyze, consciousness.depth all implemented |
| **Room** (agent management) | 31 | 8 ported (Tier 6 ✅), ~23 gap | agent.trust/descriptions/capabilities/heartbeat.history/deregister all implemented |
| **Void** (galaxy management) | 43 | 12 ported (Tier 6 ✅), ~31 gap | galaxy.dashboard/backup/taxonomy/purge/health all implemented |

### Medium Value (Port If Time Permits)

| Category | v2 Tools | v3 Status | Why It Matters |
|---|---|---|---|
| **WinnowingBasket** (memory recall) | 29 | 14 ported (Tier 7 ✅), ~15 gap | Core memory ops mostly done; sort/filter/deduplicate/export all implemented |
| **Star** (capabilities, serendipity) | 29 | 2 ported, ~27 gap | `serendipity.surface` exists; remaining are dream-adjacent |
| **Dipper** (cognitive action) | 29 | 6 ported (Tier 7 ✅), ~23 gap | `harmony.vector/history` + `homeostasis.check/adjust/history/alerts` all implemented |
| **Abundance** (dream cycle) | 22 | 2 ported, ~20 gap | Dream cycle infrastructure exists; tools are control surfaces |
| **Tail** | 29 | 0 ported | Needs investigation — likely utility tools |
| **Root** (cache management) | 24 | 2 ported, ~22 gap | `gnosis`, `system.health` exist; remaining are cache ops |

### Low Value (Skip or Stub)

| Category | v2 Tools | Why Skip |
|---|---|---|
| **Acceleration** | ~20 | GPU management — v3 uses Candle/ONNX, no GPU orchestration needed |
| **Browser** | ~15 | Web browsing — external concern, not cognitive OS core |
| **Codebase** | ~20 | Code analysis — IDE concern, not OS concern |
| **Economy** | ~15 | Token economy — v2 experiment, no v3 equivalent planned |
| **Edge** | ~10 | Edge computing — infrastructure concern |
| **Security bounty** | ~10 | Bug bounty — domain-specific, not core |
| **Wiki** | ~10 | Knowledge wiki — Codex galaxy covers this |
| **Quantum** | ~10 | Quantum-inspired — polyglot bridges cover this |
| **Sangha** | ~10 | Community — multi-user, not single-OS |
| **Intelligence** | ~10 | IQ testing — assessment, not operation |

---

## Tier 5: Net + Ghost (12 tools) — ✅ COMPLETE

**Status**: Implemented August 3, 2026. 108 tools, 858 tests, 0 clippy warnings.

**Net tools** (`crates/wm-tools/src/expansion/network.rs`):
- `association.mine` — Cross-galaxy association mining using Jaccard keyword overlap ✅
- `pattern.detect` — Detect hubs, bridges, and temporal chains in association graph ✅
- `emergence.report` — Tag frequency distribution with dominant/emerging/rare classification ✅
- `network.stats` — Global network statistics (nodes, edges, density, degree distribution) ✅
- `network.centrality` — Degree centrality ranking (in/out/total) with normalized scores ✅
- `network.clusters` — Connected component analysis using Union-Find ✅

**Ghost tools** (`crates/wm-tools/src/expansion/consciousness.rs`):
- `smarana.status` — Retention score from recall/miss events ✅
- `smarana.trace` — Temporal trace of retention decay over time ✅
- `apotheosis.check` — Self-improvement trend with composite score ✅
- `citta.history` — Recent citta memory history with timestamps ✅
- `dream.analyze` — Dream cycle analysis (triggers, consolidations, serendipity) ✅
- `consciousness.depth` — Composite depth score from brain-wave, coherence, valence, richness ✅

**Implementation notes**:
- Added `Apotheosis::history()` getter to `wm-consciousness/src/citta.rs`
- 12 new NLU profiles with conflict-aware keyword tuning
- NLU conflict fixes: lowered `association.mine` keywords to avoid conflict with `memory.associate_mine`; removed "community" from `network.clusters` to avoid conflict with `graph.community`
- 26 new tests (14 network + 12 consciousness)

## Tier 6: Room + Void (10 tools) — ✅ COMPLETE

**Status**: Implemented August 3, 2026. 118 tools, 884 tests, 0 clippy warnings.

**Room tools** (`crates/wm-tools/src/expansion/agents.rs`):
- `agent.trust` — Trust scoring for registered agents ✅
- `agent.descriptions` — Get/set agent capability descriptions ✅
- `agent.capabilities` — List agent capabilities and skills ✅
- `agent.heartbeat.history` — Heartbeat history for an agent ✅
- `agent.deregister` — Remove an agent from the registry ✅

**Void tools** (`crates/wm-tools/src/expansion/galaxy.rs`):
- `galaxy.dashboard` — Comprehensive galaxy overview with health metrics ✅
- `galaxy.backup` — Backup a galaxy to a file ✅
- `galaxy.taxonomy` — Show taxonomy/classification of memories in a galaxy ✅
- `galaxy.purge` — Purge memories matching criteria from a galaxy ✅
- `galaxy.health` — Health check for a specific galaxy ✅

## Tier 7: WinnowingBasket + Dipper (8 tools) — ✅ COMPLETE

**Status**: Implemented August 3, 2026. 126 tools, 922 tests, 0 clippy warnings.

**WinnowingBasket tools** (`crates/wm-tools/src/expansion/memory_ops.rs`):
- `memory.sort` — Sort memories by importance, recency, access count ✅
- `memory.filter` — Filter memories by complex criteria (tags, date range, importance) ✅
- `memory.deduplicate` — Find and merge duplicate memories ✅
- `memory.export` — Export memories in various formats (JSON, CSV, Markdown) ✅

**Dipper tools** (`crates/wm-tools/src/expansion/homeostasis.rs`):
- `homeostasis.check` — Check all homeostasis metrics ✅
- `homeostasis.adjust` — Adjust harmony vector weights ✅
- `homeostasis.history` — Historical homeostasis readings ✅
- `homeostasis.alerts` — Current alerts and warnings ✅

---

## Phase 9: SUBSTANTIVELY COMPLETE

At 126 tools across all major Gana, v3 has:
- Full memory CRUD + advanced query
- Knowledge graph + graph traversal
- Archaeology, learning, reasoning, explanation
- Pipeline + skill management
- Anomaly detection + state management
- Correlation + boundary enforcement
- Association mining + network analysis
- Consciousness introspection
- Agent management
- Galaxy management + backup
- Homeostasis monitoring
- Dream cycle control
- Governance (dharma, karma, gnosis)

**Remaining ~726 v2 tools** are either:
- Python-era artifacts (browser, codebase, economy, edge, security)
- Thin wrappers/aliases of existing functionality
- Domain-specific tools with limited cognitive OS value
- Multi-user/community features not applicable to single-OS deployment

---

## Performance Test Results (Aug 3, 2026 — 126 tools)

### Test Environment
- Release build, `/tmp/wm-perf-test` store
- 126 tools registered, 30 NLU routing tests (Tier 5-7), 29 integration tests

### Results Summary

| Metric | Value | vs Aug 2 (68 tools) | vs Aug 3 (96 tools) |
|--------|-------|---------------------|---------------------|
| Server startup | 94.7ms | 33ms → 95ms (larger registry) | 34.9ms → 94.7ms |
| Tool listing | 1.5ms | 2.0ms | 2.4ms → 1.5ms |
| Avg memory create | 31.0ms | 56ms (faster!) | 41.3ms → 31.0ms |
| Memory read | 54.0ms | 2.7ms (cold cache) | 2.9ms → 54.0ms (cold) |
| NLU routing | 30/30 correct ✅ | 10/10 correct | 27/27 correct |
| Avg NLU confidence | 0.914 | 0.469 (huge improvement!) | 0.483 → 0.914 |
| Avg NLU route+dispatch | 2.9ms | 7.2ms | 4.9ms → 2.9ms |
| Batch | skipped (prior: ~31ms avg) | 30.7ms avg | 31.0ms avg |
| Full-text search | 7.2ms (2 results) | 3.6ms (3 results) | 4.2ms → 7.2ms |
| Gnosis | 2.1ms | 2.8ms | 3.5ms → 2.1ms |
| Integration | 29/29 passed ✅ | N/A | N/A |
| `wm doctor` | 126 tools, all healthy | 68 tools | 96 tools → 126 tools |

### NLU Routing — All 30 Tier 5-7 test inputs routed correctly
- Tier 5 Net (6): association.mine, pattern.detect, emergence.report, network.stats, network.centrality, network.clusters ✅
- Tier 5 Ghost (6): smarana.status, smarana.trace, apotheosis.check, citta.history, dream.analyze, consciousness.depth ✅
- Tier 6 Room (5): agent.trust, agent.descriptions, agent.capabilities, agent.heartbeat.history, agent.deregister ✅
- Tier 6 Void (5): galaxy.dashboard, galaxy.backup, galaxy.taxonomy, galaxy.purge, galaxy.health ✅
- Tier 7 WinnowingBasket (4): memory.sort, memory.filter, memory.deduplicate, memory.export ✅
- Tier 7 Dipper (4): homeostasis.check, homeostasis.adjust, homeostasis.history, homeostasis.alerts ✅

### Integration Tests — 29/29 passed
All Tier 5-7 tools successfully dispatched and returned success status end-to-end through the MCP server. Agent tests required pre-registering a test agent.

### Key Observations
- NLU confidence jumped from 0.469 to 0.914 — stopword filtering, stemmer, and expanded keyword profiles made a dramatic difference
- Rate limiter (70 RPM for wm) required test restructuring: batch test skipped, only 30 new NLU tests
- Brain-wave state reached Gamma after load — 124 tools available in gnosis
- `wm doctor` confirms 126 tools, all systems healthy

### Previous Bug (Aug 3, 96-tool test): Galaxy::all() Deserialization Error

**Root cause**: New tools (Tiers 2–4) used `Galaxy::all()` when scanning memories, which includes special-purpose galaxies (Karma, Dharma, Associations, Embeddings) that store non-Memory data. `MemoryStore::scan()` deserializes as `Memory`, causing `"invalid type: integer 123, expected struct Memory"` errors.

**Fix**: Added `Galaxy::memory_galaxies()` returning only the 10 galaxies that store `Memory` records. Updated all tools in archaeology.rs, reasoning.rs, anomaly.rs, correlation.rs, boundary.rs, constellation.rs, patterns.rs, and graph.rs.

**Impact**: 7 tools went from error → success (archaeology.search, learning.pattern, anomaly.detect, state.snapshot, correlation.analyze, anti_loop.check, boundary.enforce).

---

## v2 Tool Categorization

**Full categorization**: See `v2-tool-categorization-2026-08-03.md` for the complete 725-tool analysis across 22 categories.

### Porting Priority Summary

| Tier | Priority | Tool Count | Categories |
|------|----------|------------|------------|
| Tier 8 | High | 40 | Consciousness extras, Swarm, Simulation, Dream/Watcher, Scratchpad |
| Tier 9 | Medium | 32 | Skill lifecycle, Memory lifecycle, Governance, Pattern library, Galaxy extras |
| Tier 10 | Low | 6 | Cache, Karma chain, Replay |
| Skip | — | 647 | Security, Web, Code analysis, Distributed, Quantum, Marketplace, Gardens, War Room, Grimoire, Mandala/Shelter |

---

## Conclusion

v4 at 139 tools is functionally capable across all major cognitive OS domains, with CyberBrain architecture (reflex, timescale, workspace, selfmodel, bicameral, drive). Deep integration is complete: drive bias gates in dispatch, bicameral consensus on write operations, timescale hooks for citta/dream decay, workspace events feeding drive updates. LLM right hemisphere integrated via OpenAI-compatible API. The live performance test confirms:
- 45/45 NLU routing correct (avg confidence 0.842) — including all 14 v4 tool routes
- 16/16 integration tests passed before rate limiting (28 rate-limited — expected after 70+ wm calls)
- Sub-6ms NLU routing + dispatch
- 1302 tests, 0 clippy warnings, fmt clean

**Phase 9 Status**: SUBSTANTIVELY COMPLETE (126 cognitive tools, Tiers 1–7).
**v4 Status**: R1–R7 + Deep Integration + LLM Right Hemisphere ALL COMPLETE (17 crates, 139 tools, 1302 tests).
**Next priorities**: Local AI integration (BitMamba autonomic layer, llama.cpp left hemisphere), migration tool.
