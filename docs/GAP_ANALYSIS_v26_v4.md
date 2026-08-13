# WhiteMagic v4 vs v2 — Comprehensive Gap Analysis

> Archived v4 comparison. It is retained for migration history; current v5
> release decisions belong in [`RELEASE_READINESS.md`](RELEASE_READINESS.md).

**Last updated**: August 7, 2026 (Safety features: destructive tool confirmation + transaction snapshot/rollback + compartment-based access control)
**Status**: v5.2.1 — All 7 phases complete (0–8, A–F, R1–R7, L1–L5, Pre-N A/B/C, N1–N21) + integration wiring + E2E tests + graceful shutdown + security hardening + RSI + Embodiment I/O + Safety features + NLU router + learned inference router + imagination engine + self-play loop + mutable structures + persistence. 3,231 tests, 184 tools, ~130,461 lines of Rust across 14 crates. clippy warnings: 0 (after 2 early-drop lints fixed), fmt clean. Under version control (git).

---

## 1. Executive Summary

WhiteMagic v4 is a ground-up Rust rewrite of the v2 cognitive operating system (Python + Rust bridge). v4 has achieved **full parity** on all core cognitive patterns (memory model, consciousness, governance, dream cycle, neural features) and **exceeds v2** in performance, resource efficiency, and governance safety. The remaining gaps are:

1. **Tool catalog breadth** — 176/877 tools ported (~20.1%, Tiers 1–7 + v4 subsystem + N16-N21 + RSI + sensorimotor + transaction tools — substantively complete)
2. ~~**Vector search**~~ — ✅ Complete (in-memory VectorStore + LanceDB feature-gated + `memory.vector.search` tool)
3. ~~**Polyglot acceleration**~~ — ✅ Complete (wm-polyglot with Julia/Haskell/Zig/Koka bridges, 51 tests)
4. ~~**Python MCP shell**~~ — ✅ Complete (PyO3 bindings, Python MCP shell, config templates)
5. **Test volume** — 2,818 vs v2's ~10,000 — quality over quantity (property, fuzz, E2E, criterion benches, security, red-team)
6. ~~**Fuzz testing**~~ — ✅ Complete (5 cargo-fuzz targets + 22 proptest tests)
7. ~~**Cross-platform CI**~~ — ✅ Complete (Linux, macOS, Windows)
8. ~~**Mandala compartments**~~ — ✅ Complete (4 security tiers, isolated stores)
9. ~~**v4 CyberBrain phases R1–R7**~~ — ✅ Complete (reflex, timescale, workspace, selfmodel, bicameral, substrate, drive)
10. ~~**Deep integration**~~ — ✅ Complete (drive bias → dispatch, bicameral → writes, timescale → citta/dream, workspace → drive)
11. ~~**LLM right hemisphere**~~ — ✅ Complete (OpenAI-compatible via ureq, env-configured, graceful fallback)
12. ~~**Local AI integration (L1–L3)**~~ — ✅ Complete (BitMamba autonomic layer, LlamaLeftHemisphere, BitNet right hemisphere)
    - L1: `wm-autonomic` crate — BitMamba daemon subprocess, salience processing, drive/workspace integration
    - L2: `LlamaLeftHemisphere` — llama.cpp-backed left hemisphere via OpenAI-compatible API
    - L3: `BitNetRightHemisphere` — local 1.58-bit model for creative reasoning (HTTP + subprocess modes)
    - L4: `InferenceRouter` — complexity-aware routing with 5 tiers, confidence cascading, token budget tracking, sensitivity detection (45 tests). **Wired into `BicameralEngine::reason()`** with `RoutingInfo` in `ConsensusResult` (9 new tests)
    - L5: `OrtEmbedder` via `fastembed-rs` (ONNX Runtime, feature-gated `onnx`) + `HttpEmbedder` + `StubEmbedder` — fully local embeddings, no server dependency (13 tests)
    - PyO3 bridge verified end-to-end: Python MCP shell handles JSON-RPC initialize, tools/list (141 tools), memory.create, memory.search
    - Benchmarks: router classify (4–5µs), route with handlers (5–8µs), budget tracker (3ns), bicameral reason with router (4µs); embedder single (890ns stub), batch 256 (231µs)
13. ~~**N1–N21 phases**~~ — ✅ Complete (biological alignment, collective intelligence, simulation substrate)
14. ~~**Integration wiring (N16–N21)**~~ — ✅ Complete (Gan Ying Bus events, Homeostatic Loop, Anomaly Detector, Sangha Mesh, Simulation tools all wired into MCP server and dispatch pipeline)
15. ~~**End-to-end integration testing**~~ — ✅ Complete (10 E2E tests in `wm-mcp/src/server.rs`: session lifecycle, bus events, error recovery, homeostasis state sharing, brain-wave transitions, shutdown event, bus persistence)
16. ~~**Production hardening**~~ — ✅ Complete (2026-08-05): SIGTERM/SIGINT graceful shutdown, Gan Ying Bus JSONL persistence, non-Linux sensor degradation, stable-rustfmt, git. LMDB corruption recovery implemented (integrity check, auto-repair, quarantine, map-size growth — 18 tests).
17. ~~**Security hardening (D1/D4/D5/D6)**~~ — ✅ Complete (2026-08-05): MCP input validation (SSRF, path traversal, injection detection), tool capability attestation (HMAC-signed manifests, trust scopes), security validation utilities, policy engine (runtime-updatable Dharma policy). 60+ new tests.
18. ~~**RSI (Recursive Self-Improvement)**~~ — ✅ Complete (2026-08-06): Friction logging + auto-log, codebase-grounded improvement proposals, adversarial self-testing (22+ attack vectors). Phase 2 Outward Spiral: rich friction envelope (WS-1), deduplication (WS-2), karma-friction bridge (WS-3), proactive improvement surfacing (WS-4), friction resolution verification with regression detection (WS-5). Phase 3 Adversarial: E2E outward spiral test, RSI pipeline benchmarks, `redteam.from_friction` (regression test synthesis from resolved friction), `redteam.coverage_report` (per-system coverage gaps). 9 RSI tools, 2 autonomous cycle types.

---

## 2. Quantitative Comparison

### Codebase Size

| Metric | v4 | v2 |
|---|---|---|
| Primary language | Rust | Python |
| Lines of code | ~112,000 | ~351K (239K Python + 112K Rust) |
| Crates/Modules | 19 crates | ~124 Python modules + Rust subcrates |
| Source files | ~75 .rs files | ~29,680 .py + 3,851 .rs files |
| Functions | ~2,000 | ~10,000+ |

### Performance

| Metric | v4 | v2 | Improvement |
|---|---|---|---|
| Pipeline overhead | ~1.1µs/call | ~200µs/call | **180x** |
| Read latency | 0.01ms (LMDB mmap) | 1-3ms (SQLite) | **100x** |
| Write latency | 2ms (LMDB batch) | 23ms (SQLite WAL) | **10x** |
| Startup time | 8ms (LMDB) | 140ms (SQLite) | **17x** |
| Idle CPU | 0% (Delta mode) | 110% (polling threads) | **∞** |
| RAM usage | ~few MB | 2.4 GB | **~100x** |
| Binary size | 14 MB (static) | Requires Python runtime | Self-contained |
| Background threads | 0 (tokio work-stealing) | 16 sleeping threads | **16 fewer** |
| Disk writes | 0.2-0.6 GB/day | 2-6 GB/day | **10x** |

### Testing

| Metric | v4 | v2 |
|---|---|---|
| Test count | 2,818 | ~10,000 |
| Test files | 38 files with tests | 200+ test files |
| Clippy warnings | 0 | N/A |
| Fuzz tests | 5 targets + 22 proptest | Not yet |
| Property tests | proptest (roundtrip, invariant) | Some |
| Benchmarks | Criterion (pipeline, LMDB, Tantivy, dream, router, embedder) | Python timeit |
| CI | GitHub Actions (fmt + clippy + test-linux + test-macos + test-windows + bench-compile + proptest) | Unknown |

---

## 3. Feature Parity Matrix

### ✅ Fully Ported (v2 → v3)

| Feature | v2 Implementation | v3 Implementation | Notes |
|---|---|---|---|
| 28 Gana taxonomy | Python enum | Rust enum, `#[repr(u8)]` | All 28 variants |
| 14-galaxy memory | SQLite sub-DBs | LMDB named databases | + dynamic galaxies (6.8) |
| 6D holographic coords | Python + Rust | Rust `HolographicCoords` | |
| 5D spatial coords | Python (anchor + PCA) | Rust `Coordinate5D` + `SemanticEncoder` | TF projection, 3 semantic axes |
| Memory CRUD | SQLite | LMDB (mmap, zero-copy) | |
| Content-hash dedup | Python SHA-256 | Rust SHA-256 | O(1) via index (6.4) |
| Cross-galaxy associations | SQLite | LMDB `AssociationStore` | |
| Typed links (7 LinkTypes) | Python | Rust `LinkType` enum | |
| Hebbian learning | Python | Rust `activate()` + `decay()` | Diminishing returns |
| Memory types (8) | Python enum | Rust `MemoryType` enum | |
| Neuro-score dynamics | Python | Rust `recall()` + `decay()` | Hebbian boost, exponential decay |
| Novelty score | Python | Rust `novelty_score` + `SurpriseGate` | |
| Emotional valence | Python | Rust `emotional_valence` + `emotional_weight` | |
| Memory protection | Python flags | Rust `is_protected` | |
| Privacy controls | Python flags | Rust `is_private` + `model_exclude` | |
| Provenance | Python | Rust `source` + `source_trust` | |
| Multi-agent coherence | Python | Rust `version` + `agent_id` | |
| Mindful forgetting | Python (498 lines) | Rust `Lifecycle` + `RetentionEngine` | 7-signal retention |
| Memory consolidation | Python (1142 lines) | Rust dream cycle + `StrategySynthesizer` | |
| Sleep consolidation | Python (528 lines) | Rust 4 transfer routes | Sessions→Codex, Citta→Aria, etc. |
| Association mining | Python (770 lines) | Rust `AssociationMiner` (Jaccard) | |
| Constellation detection | Python (974 lines) | Rust `ConstellationDetector` | Grid clustering + drift tracking |
| Strategy synthesis | Python | Rust `StrategySynthesizer` | Jaccard + union-find |
| Secondary indexes | SQLite indexes | Rust LMDB DUP_SORT (4 indexes) | O(1) hash, O(log n) range |
| Full-text search | SQLite FTS5 | Tantivy BM25 | Pure Rust, 2x faster |
| Dharma governance | Python (55K rules.py) | Rust `DharmaGate` + `ResourceRules` | + hardware-aware gating |
| Karma ledger | Python (27K) | Rust `KarmaLedger` (SHA-256 chain) | LMDB-persisted |
| Citta consciousness (16D) | Python (14K) | Rust `CittaVector` (ndarray + SIMD) | |
| Coherence measurement | Python (460 lines) | Rust `CoherenceReading` | |
| Smarana (retention) | Python | Rust `Smarana` | |
| Presence detection | Python | Rust `Presence` | |
| Apotheosis engine | Python (956 lines) | Rust `ApotheosisEngine` | |
| Dream cycle (12 phases) | Python (1859 lines) | Rust `DreamCycle` | Event-triggered (Theta) |
| Citta heartbeat | Python polling | Rust post-dispatch hook | Event-driven |
| Citta → Context feedback | Python | Rust coherence gate + karma feedback | |
| Brain-wave eco mode | Python (16 threads) | Rust `EcoModeController` (tokio::select!) | Zero CPU idle |
| Rate limiter | Python (11K) | Rust `SlidingWindow` (atomics) | |
| Circuit breaker | Python (20K) | Rust `CircuitBreakerRegistry` | |
| Param validator | Python (7K) | Rust serde deserialization | Compile-time typed |
| Session recording | Python (23K) | Rust session tools (5) | |
| Spreading activation | Python (460 lines) | Rust `SpreadingActivation` | |
| Ripple tagging | Python (259 lines) | Rust `RippleTagger` | |
| Neuromodulation | Python (286 lines) | Rust `Neuromodulator` | Dopamine + serotonin analogs |
| Metaplasticity | Python (190 lines) | Rust `Metaplasticity` | |
| Dynamic galaxies | Python | Rust `GalaxyRegistry` | LMDB-backed |

### ✅ v3 Exceeds v2

| Feature | v2 | v4 | Advantage |
|---|---|---|---|
| Hardware-aware governance | None | `wm-substrate` reads `/proc` + `/sys` | Real hardware metrics gate cognition |
| Resource gating (Tiferet) | None | `apply_harmony()` gates brain-wave by health | Stressed systems auto-throttle |
| Resource rules (Yama) | None | Budgets, novelty, purpose, human review | Prevents v2's circular thinking |
| Gnosis transparency | None | `gnosis.status/history/explain` | Full governance auditability |
| Governed autonomous cycles | Uncontrolled 4-tier loop | 4 governed cycles (connect/compress/emergence/prune) | Health-gated, proposal-only, novelty-suspended |
| Outward spiral detection | None (fell into circular thinking) | `SpiralTracker` with auto-suspension | Prevents 59K memory bloat |
| Effect-typed dispatch | None | `EffectRow` compile-time declarations | Koka-style effect safety |
| Atomic tool stats | Python counters | Rust `AtomicU64` lock-free | No lock contention |
| Event-driven eco mode | 16 polling threads | `tokio::select!` zero-CPU | No idle CPU |
| NLU router | Python pattern matching | Rust 141 profiles with TF-IDF cosine similarity + stemmer + stopwords | |
| CLI tools | Python scripts | `wm serve/doctor/quickstart/stats/brain-wave/polyglot` | Single binary |
| Vector search | Python HNSW + FastEmbed | In-memory VectorStore + LanceDB feature-gated | Pure Rust, lazy loading |
| PyO3 bindings | Python primary | PyO3 bridge + Python MCP shell (optional) | Rust-first, Python optional |
| Polyglot FFI | Subprocess spawning | In-process embedding (jlrs) + C ABI bridges | Zero subprocess overhead |

### ❌ Missing in v3 (Not Yet Ported)

| Feature | v2 Size/Description | v3 Status | Priority | Phase |
|---|---|---|---|---|
| **Tool catalog** | 877+ tools across 28 Gana | 176 tools (~20.1%, Tiers 1–7 + v4 + N16-N21 + RSI + sensorimotor + transaction) | **High** | Phase 9 ✅ |
| ~~**Vector search**~~ | Python HNSW + FastEmbed | ✅ In-memory VectorStore + LanceDB feature-gated | **Done** | ✅ |
| ~~**Polyglot: Julia**~~ | MC simulation, quantum geometry, drift detection | ✅ wm-polyglot with jlrs | **Done** | ✅ |
| ~~**Polyglot: Zig**~~ | TRN hard gate (ultra-low-latency) | ✅ wm-polyglot with C ABI | **Done** | ✅ |
| ~~**Polyglot: Haskell**~~ | Topological verification, DAG cycle checks | ✅ wm-polyglot with FFI | **Done** | ✅ |
| ~~**Polyglot: Koka**~~ | Effect-typed Dharma rules, karma verification | ✅ wm-polyglot with C ABI | **Done** | ✅ |
| ~~**PyO3 bindings**~~ | Python MCP shell for ONNX/HuggingFace | ✅ PyO3 bridge + Python MCP shell | **Done** | ✅ |
| **PRAT mappings** | 852 tool→Gana mappings (985 lines) | Not ported | **Medium** | Phase 9 |
| **Mandala compartments** | Research/sandbox/production/secure | ✅ 4 security tiers, isolated stores | **Done** | ✅ |
| ~~**Transaction firewall**~~ | Spend limits, rate limiting, allowlist | ✅ Resource rules + rate limiter + input validation | **Done** | ✅ |
| **Predictive coding** | wm-neuro (4 Rust files) | Not ported | **Low** | Post-v4 |
| **Monte Carlo simulation** | wm-evolution (14 Rust files) | Not ported | **Medium** | Post-v4 |
| ~~**Migration tool**~~ | SQLite→LMDB data transfer | ✅ 45 tests, 59,831 memories migrated | **Done** | ✅ |
| **Embodiment layer** | N/A | Framework built (N13/N14), hardware validation pending | **High** | v4 R6 hardware — parallel with Sangha transport |
| ~~**Right hemisphere LLM**~~ | N/A | ✅ LlmRightHemisphere + BitNetRightHemisphere | **Done** | ✅ |
| ~~**Drive bias in dispatch**~~ | N/A | ✅ DriveCore wired to dispatch pipeline | **Done** | ✅ |
| ~~**Timescale hooks**~~ | v2 TimescaleSync | ✅ Bus wired to citta/dream cycles | **Done** | ✅ |
| ~~**Fuzz testing**~~ | N/A | ✅ 5 cargo-fuzz targets + 22 proptest | **Done** | ✅ |
| ~~**Cross-platform CI**~~ | N/A | ✅ Linux, macOS, Windows | **Done** | ✅ |

---

## 4. v2 Tool Catalog Breakdown (852 tools across 28 Gana)

This is the breakdown of v2's PRAT mappings by Gana, showing where v3's tool porting effort should focus:

| Gana | v2 Tools | v3 Tools Ported | Gap | Priority |
|---|---|---|---|---|
| Ox (archaeology, learning) | 46 | 3 (archaeology.search, learning.pattern, learning.suggest) | 43 | Low |
| Void (galaxy dashboard, backup, export) | 43 | 12 (galaxy.stats/export/import/transfer/merge/snapshot/restore/dashboard/backup/taxonomy/purge/health) | 31 | Low |
| Heart (anomaly detection, state) | 37 | 3 (anomaly.detect, state.snapshot, state.revert) | 34 | Medium |
| ThreeStars (explanation, reasoning) | 36 | 6 (gnosis.status/history/explain, reasoning.bicameral, think, explain) | 30 | Low |
| Horn (pipelines, cascades, skills) | 35 | 6 (wm meta-tool, pipeline.create/list/status, skill.invoke/list) | 29 | Low |
| HairyHead (code communities, correlation) | 35 | 6 (kg.top, graph.walk/community/propagate, correlation.analyze, god.nodes) | 29 | Low |
| Wall (anti-loop, boundary, dharma audit) | 33 | 5 (dharma.audit/rules/profiles, anti_loop.check, boundary.enforce) | 28 | Low |
| Roof (mandala creation, shelter) | 33 | 0 | 33 | Low |
| Net (association mining, emergence) | 33 | 9 (associate_mine, emergence.scan/report, kg.extract, association.mine, pattern.detect, network.stats/centrality/clusters) | 24 | Low |
| Ghost (citta, consciousness, smarana) | 33 | 11 (citta.status/reflect/coherence, dream.status/trigger, smarana.status/trace, apotheosis.check, citta.history, dream.analyze, consciousness.depth) | 22 | Low |
| Room (agent management) | 31 | 8 (agent.register/list/heartbeat/trust/descriptions/capabilities/heartbeat.history/deregister) | 23 | Low |
| Neck (galaxy sync, mesh, broker) | 31 | 2 (galaxy.transfer, galaxy.merge) | 29 | Low |
| Mound (foresight, simulation) | 30 | 0 | 30 | Low |
| WinnowingBasket (memory recall, search) | 29 | 14 (create/read/list/delete/query/search/associate/associations/nearby/hybrid_recall/sort/filter/deduplicate/export) | 15 | Low |
| Tail | 29 | 0 | 29 | Low |
| Star (capabilities, dream, serendipity) | 29 | 2 (serendipity.surface, dream.trigger) | 27 | Low |
| Dipper (cognitive action, homeostasis) | 29 | 6 (harmony.vector/history, homeostasis.check/adjust/history/alerts) | 23 | Low |
| StraddlingLegs (session, context) | 28 | 5 (session.start/checkpoint/recall/end/list) | 23 | Low |
| Girl (consciousness token economy) | 28 | 0 | 28 | Low |
| Encampment (memory creation, fast write) | 28 | 2 (memory.create, memory.consolidate) | 26 | Low |
| Stomach | 27 | 0 | 27 | Low |
| TurtleBeak (task distribution) | 26 | 2 (task.distribute/status) | 24 | Low |
| Root (cache management) | 24 | 2 (gnosis, system.health) | 22 | Low |
| Wings | 23 | 0 | 23 | Low |
| ExtendedNet (ethics, dharma) | 23 | 3 (dharma.status/rules/audit) | 20 | Low |
| Chariot (perception, navigation) | 23 | 0 | 23 | Low |
| Abundance (dream cycle, lifecycle) | 22 | 2 (memory.decay, memory.consolidate) | 20 | Low |
| Willow (karma) | 19 | 3 (karma.report/history/clear) | 16 | Low |
| **Total** | **852** | **176** | **~676** | |

### v2 Tool Categories (from registry_defs/)

v2 organizes tools into ~63 registry definition files covering:

- **Acceleration** — GPU/accelerator management
- **Agent** — Multi-agent coordination, trust, descriptions
- **Archaeology** — Memory archaeology, pattern learning
- **Browser** — Web browsing, URL fetching
- **Codebase** — Code analysis, graph building
- **Cognitive extensions** — Extended cognition features
- **Dreaming** — Dream cycle tools
- **Economy** — Token economy, bounties
- **Edge** — Edge computing
- **Fragment** — Memory fragment management
- **Galaxy** — Galaxy management, sharing, packaging
- **Garden** — Memory garden, cultivation
- **Governance** — Dharma, karma, audit
- **Grimoire** — Knowledge spells, recipes
- **Homeostasis** — System health, balance
- **Immune** — Security, threat detection
- **Intelligence** — IQ testing, cognitive assessment
- **Knowledge** — Knowledge graph, synthesis
- **Learning** — Pattern learning, skill building
- **Living graph** — Dynamic graph management
- **Mandala** — Compartment management
- **Metrics** — System metrics, monitoring
- **Oracle** — Prediction, foresight
- **Orchestration** — Multi-tool orchestration
- **Pipeline** — Pipeline building, execution
- **Polyglot** — Language runtime management
- **Quantum** — Quantum-inspired computing
- **Research** — Research tools, web search
- **Sandbox** — Isolated execution
- **Sangha** — Community, collaboration
- **Security bounty** — Bug bounty scanning
- **Session** — Session management
- **Simulation** — Monte Carlo, what-if
- **Strata** — Layered memory management
- **Synthesis** — Memory synthesis, compression
- **Trust** — Trust scoring, reputation
- **Wiki** — Knowledge wiki
- **+ unauthored variants** — Autonomous versions of many tools

---

## 5. v3 Architecture Advantages

### What v3 Does Better

1. **Performance**: 180x faster dispatch, 100x faster reads, 10x faster writes
2. **Resource efficiency**: Zero idle CPU, ~100x less RAM, 10x less disk I/O
3. **Governance safety**: Hardware-aware, resource-budgeted, novelty-gated, human-in-loop
4. **Circular thinking prevention**: SpiralTracker auto-suspends repetitive autonomous cycles
5. **Transparency**: Gnosis portals expose all governance decisions
6. **Event-driven**: No polling threads, no sleeping threads, no zombie processes
7. **Type safety**: Rust's type system + effect rows vs Python's runtime typing
8. **Deployment**: Single 7.9MB binary vs Python + dependencies + venv

### What v3 Deliberately Drops

- SQLite → LMDB (mmap zero-copy)
- FTS5 → Tantivy (pure Rust, 2x faster)
- Python middleware (22 stages, 200µs) → Rust pipeline (7 stages, 1.1µs)
- Subprocess polyglot → In-process embedding/FFI
- HNSW Python → LanceDB (pending)
- FastEmbed/ONNX primary → Candle (pending) + ONNX fallback
- 16 sleeping threads → Single tokio runtime
- Polling loops → Event-driven wake
- Python singleton registry → Rust ownership + Arc

---

## 6. Roadmap: Closing the Gaps

### Priority 1: ~~Vector Search (LanceDB)~~ — ✅ COMPLETE
- ✅ In-memory `VectorStore` with cosine similarity search over LMDB embeddings
- ✅ LanceDB integration (feature-gated under `lancedb`) for disk-based ANN
- ✅ `memory.vector.search` MCP tool with NLU routing
- ✅ Hybrid search ready (Tantivy FTS + vector search)

### Priority 2: ~~Polyglot Integration (Phase 7)~~ — ✅ COMPLETE
- ✅ Julia via jlrs (Monte Carlo, quantum geometry, drift detection)
- ✅ Zig via C ABI (TRN hard gate)
- ✅ Haskell via GHC .so (topological verification)
- ✅ Koka via C ABI (effect-typed Dharma rules)
- ✅ All optional, feature-gated, Rust-native fallback

### Priority 3: Tool Catalog Expansion (Phase 9)
- Port PRAT mappings (852 tool→Gana assignments)
- Phase 9 Tiers 1–7 complete: 126 cognitive tools + 15 v4/subsystem + 13 N16-N21 + 9 RSI + 10 sensorimotor + 3 transaction = 176 total
- Remaining ~718 v2 tools are Python-era artifacts, thin wrappers, or domain-specific — diminishing returns
- Estimated effort for full parity: ~50K lines for low cognitive value
- Strategy: depth over breadth — await dogfooding evidence before porting more

### Priority 4: ~~PyO3 Bindings (Phase 8)~~ — ✅ COMPLETE
- ✅ Feature-gated PyO3 bindings in wm-mcp
- ✅ Python MCP shell (~200 lines) for ONNX/HuggingFace
- ✅ MCP config templates for Claude Desktop, Cursor, Windsurf
- ✅ Pure Rust MCP server also works without Python

### Priority 5: Quality (Phase 10)
- ~~Fuzz testing (cargo-fuzz)~~ ✅
- ~~Cross-platform CI (macOS, Windows)~~ ✅
- Benchmark on release tags
- Migration tool (SQLite → LMDB)
- Live performance test with 141 tools

---

## 7. Session-by-Session Whittling Guide

For future sessions, use this checklist to track progress:

### Vector Search
- [x] Add `lancedb` dependency to wm-memory
- [x] Implement `VectorStore` struct (in-memory + LanceDB)
- [x] Wire into `MemoryStore`
- [x] Hybrid search (Tantivy + vector search)
- [x] `memory.vector.search` MCP tool
- [x] NLU routing for vector search
- [x] Tests (+15: 9 vector store + 6 NLU/tool)

### Polyglot
- [x] Julia bridge (jlrs)
- [x] Zig bridge (C ABI)
- [x] Haskell bridge (GHC .so)
- [x] Koka bridge (C ABI)
- [x] `polyglot.status` tool upgrade
- [x] Tests (+51)

### PyO3 + Python MCP Shell
- [x] PyO3 bridge module (`pyo3_bridge.rs`)
- [x] Python extension module (`whitemagic_v4`)
- [x] `handle_request()` API
- [x] Python MCP server (`whitemagic_v4_server.py`)
- [x] ONNX embedding fallback (optional)
- [x] HuggingFace tokenizer (optional)
- [x] MCP config templates (Claude Desktop, Cursor, Windsurf)
- [x] `wm brain-wave` CLI subcommand
- [x] Tests (+7)

### Tool Catalog (by Gana, highest gap first)
- [x] Tier 1: kg.extract, kg.query, kg.top (knowledge graph)
- [x] Tier 1: graph.walk, graph.community, graph.propagate (graph traversal)
- [x] Tier 1: galaxy.transfer, galaxy.merge, galaxy.snapshot, galaxy.restore (galaxy management)
- [x] Tier 2: archaeology.search, learning.pattern, learning.suggest (Ox)
- [x] Tier 2: reasoning.bicameral, think, explain (ThreeStars)
- [x] Tier 3: pipeline.create/list/status, skill.invoke/list (Horn)
- [x] Tier 3: anomaly.detect, state.snapshot, state.revert (Heart)
- [x] Tier 4: correlation.analyze, god.nodes (HairyHead)
- [x] Tier 4: anti_loop.check, boundary.enforce (Wall)
- [x] Tier 5: association.mine, pattern.detect, network.stats/centrality/clusters (Net) + smarana.status/trace, apotheosis.check, citta.history, dream.analyze, consciousness.depth (Ghost)
- [x] Tier 6: agent.trust/descriptions/capabilities/heartbeat.history/deregister (Room) + galaxy.dashboard/backup/taxonomy/purge/health (Void)
- [x] Tier 7: memory.sort/filter/deduplicate/export (WinnowingBasket) + homeostasis.check/adjust/history/alerts (Dipper)
- [x] After Tier 7 (~126 tools): Declare Phase 9 substantively complete
- [x] v4 tools: reflex.dispatch/status, workspace.spotlight/events/publish/stats, timescale.status/hooks (8 tools)
- [x] v4 selfmodel: selfmodel.forecast/alerts/snapshot (3 tools)
- [x] v4 bicameral: bicameral.reason/status (2 tools)
- [x] v4 drive: drive.snapshot/event (2 tools)
- [x] v4 sensorimotor: sensorimotor.scan (1 tool)
- [x] v4 transaction: transaction.begin, transaction.commit, transaction.rollback (3 tools)
- [ ] Remaining ~715 v2 tools: Python-era artifacts, thin wrappers, domain-specific — skip

### Quality
- [x] Fuzz testing setup
- [x] Cross-platform CI
- [x] Live performance test (96 tools, 27 NLU routes, all correct)
- [x] Live performance test (135 tools, 33 NLU routes, all correct)
- [x] Live performance test (139 tools, 45 NLU routes, all correct — including 14 v4 tool routes)
- [x] Galaxy::memory_galaxies() fix for special-purpose galaxy deserialization
- [x] Migration tool (28 tests — galaxy mapping, type mapping, dry run, tags, galaxy filter, multi-galaxy)
- [x] Benchmark regressions (no regressions — improvements in LMDB get/scan, Tantivy search, dispatch, registry)

### v4 CyberBrain Phases
- [x] R1: wm-reflex (reflex dispatch table, safety bitmask, 8 builtins)
- [x] R2: wm-timescale (5-tier event bus, hooks, brain-wave gating)
- [x] R3: wm-workspace (salience arbitration, spotlight, event bus)
- [x] R4: wm-selfmodel (metrics, forecasting, alerts, confidence calibration)
- [x] R5: wm-bicameral (dual-hemisphere debate, corpus callosum, consensus gate)
- [x] R6: wm-substrate (hardware metrics, Harmony Vector — already existed)
- [x] R7: wm-drive (5 drives, 9 event kinds, drive bias, decay)
- [x] Self-Model deep integration (SubstrateMonitor → SelfModel → Context → dispatch)
- [x] Deep integration: drive bias → dispatch pipeline (caution gate, energy gate)
- [x] Deep integration: bicameral consensus → high-stakes decisions (all write-effect dispatches)
- [x] Deep integration: timescale hooks → citta/dream cycles
- [x] Right hemisphere LLM integration (OpenAI-compatible via ureq)
- [x] Embodiment layer (real Linux sensor drivers + actuator backends + autonomous sensorimotor cycle)
- [x] Local AI integration (L1: BitMamba autonomic, L2: LlamaLeftHemisphere, L3: BitNet right hemisphere, L4: InferenceRouter wired into BicameralEngine, L5: OrtEmbedder via fastembed-rs)

### N-Phases (Next-Phase Local AI & Cognitive Activation) — ALL COMPLETE

See `docs/notes/archive/next-phase-strategy-2026-08-04.md` for full details.

| Feature | v2 | v4 Current | Priority | Phase |
|---|---|---|---|---|
| **TriModelManager** | Twin local models (background + foreground) | Single endpoint per hemisphere | **High** | N1 ✅ |
| **Edge rule engine** | PatternEngine, 85% zero-token queries | EdgeRules tier defined, no handler | **High** | N2 ✅ |
| **Grammar-constrained JSON** | Pre-built schemas for structured LLM output | Free-form text only | **High** | N3 ✅ |
| **Speculative decoding** | Draft + verify model pipeline (1.5-2.1x) | None | **Medium-High** | N4 ✅ |
| **Conversational memory search** | Sub-50ms hybrid vector + FTS pipeline | Tool dispatch path | **High** | N5 ✅ |
| **LLM meta-harness** | RAG + self-correction + ensemble | Simple bicameral debate | **Medium-High** | N6 ✅ |
| **Dense context encoding** | Chinese-char token compression (2-3x) | None | **Low-Medium** | N7 ✅ |
| **Hardware-aware inference tuning** | Auto-tuner with kernel benchmarks | Static env config | **Medium** | N8 ✅ |
| **Router-gated hemisphere execution** | Router classifies but doesn't gate | Classifies + records, no gating | **High** | N9 ✅ |
| **OrtEmbedder in memory recall** | FastEmbed + HNSW wired into search | OrtEmbedder exists, not wired | **High** | N10 ✅ |
| **Active consciousness cycles** | 16 polling threads, always running | Infrastructure built, dormant | **Medium** | N11 ✅ |
| **Idle-to-default-mode** | N/A | ModelState::Dreaming, warm wake | **Medium** | N12 ✅ |
| **Sensorimotor weave** | N/A | Real Linux drivers: CPU usage, disk, network, CPU freq sensors + sysfs fan/LED actuators + autonomous sensorimotor cycle | **Medium** | N13 ✅ |
| **Cerebellar forward model** | N/A | LinearForwardModel, MotorTiming | **Medium** | N14 ✅ |
| **Limbic deep integration** | N/A | 8 valences, neuromodulation | **Medium** | N15 ✅ |
| **Gan Ying Bus** | N/A | 229 event types, 9 categories | **High** | N16 ✅ |
| **Sangha Mesh** | N/A | PeerDiscovery, SignalBroadcast, Locks, Chat, TCP JSON-RPC transport | **High** | N17 ✅ |
| **Radiant Layer** | N/A | ResourceInventory, GiftToken, TaskRouter | **Medium** | N18 ✅ |
| **Homeostatic Loop** | N/A | sample_cycle, ActionLevel, DimensionThreshold | **High** | N19 ✅ |
| **Anomaly Detection** | N/A | Z-score sliding windows, Yin-Yang tracker | **High** | N20 ✅ |
| **Simulation Substrate** | Monte Carlo suite | MC, forecasting, counterfactual, Sobol | **Medium** | N21 ✅ |

### Integration Wiring — COMPLETE

- ✅ Gan Ying Bus emits `ToolDispatchStart`/`ToolDispatchSuccess`/`ToolDispatchError` on every tool call
- ✅ Homeostatic Loop runs post-dispatch: samples substrate → anomaly detection → `sample_cycle()` → emits `HarmonyStressDetected` events
- ✅ Homeostasis tools updated to use `HomeostaticLoop` + `AnomalyDetector`
- ✅ 13 new MCP tools (bus.stats/emit/recent, sangha.peers/discover/signal/chat/locks, sim.mc/forecast/counterfactual)
- ✅ Flaky `wm-drive` cross_pollination test fixed

### Security Hardening (D1/D4/D5/D6) — COMPLETE

- ✅ D1: MCP input validation (`wm-mcp/src/input_validation.rs`) — JSON-RPC structure, tool call params, SSRF, path traversal, injection detection, size limits (14 tests)
- ✅ D4: Tool capability attestation (`wm-core/src/attestation.rs`) — HMAC-SHA256 signed manifests, trust scopes (Trusted/Internal/External), provenance verification, tamper detection (30+ tests)
- ✅ D5: Security validation utilities (`wm-core/src/security.rs`) — SSRF prevention, path traversal prevention, prompt injection detection (21 patterns), tool name validation, path sanitization (16 tests)
- ✅ D6: Policy engine (`wm-governance/src/policy.rs`) — runtime-updatable Dharma policy, brain-wave-aware resource access checks, fabrication blocking
- ✅ OWASP mapping: LLM01 (Prompt Injection), LLM05 (SSRF)

### RSI: Recursive Self-Improvement — COMPLETE

- ✅ Phase 1: `friction.log`, `friction.review`, `friction.auto_log` — auto-logs dispatch errors as structured friction memories
- ✅ Phase 2: `improve.proposals` + `CycleType::Improve` — scans friction entries, groups by pattern, generates improvement proposals
- ✅ Phase 3: `redteam.proposals` + `CycleType::Redteam` — 22+ attack vectors across governance, karma, mandala, dispatch, spiral, memory, mcp, association, bicameral, resonance, timescale, sangha, homeostasis, selfmodel, tools, autonomic, polyglot, core
- ✅ Phase 2 Outward Spiral (WS-1–WS-5): Rich friction envelope (15+ telemetry fields), deduplication (friction_hash + dup_count), karma-friction bidirectional bridge, proactive improvement surfacing (autonomous every 50 dispatches), friction resolution verification with regression detection
- ✅ Phase 3 Adversarial: E2E outward spiral integration test, RSI pipeline criterion benchmarks, `redteam.from_friction` (regression test synthesis from resolved friction), `redteam.coverage_report` (per-system coverage gaps + risk scores)
- ✅ 12 RSI MCP tools (9 friction/improve/redteam + 3 transaction), 2 new autonomous cycle types (now 7 total: Connect, Compress, Emergence, Prune, Improve, Redteam, Sensorimotor)
- ✅ MCP server wiring: `FrictionAutoLogTool` integrated, auto-logs on dispatch errors, karma-friction bridge, autonomous improve cycle

### Safety Features — COMPLETE

- ✅ Destructive tool confirmation: `EffectRow.destructive` field, dispatch pipeline blocks destructive tools unless `"confirm": true` in args. 8 destructive tools tagged.
- ✅ Transaction snapshot/rollback: `transaction.begin` (snapshot all galaxies), `transaction.commit` (clear state), `transaction.rollback` (restore from snapshot, destructive). Shared `TransactionState` (`Arc<Mutex<Option<String>>>`) threaded through MCP server.
- ✅ Compartment-based access control: `Context.compartment` + `Context.user_id` from MCP request `_meta`. `can_access_galaxy()` + `can_write_galaxy()` enforce sandbox/production/secure tiers.
- ✅ 3 new transaction tools, 3 NLU profiles (166 total), 14 new tests across wm-dispatch, wm-tools, wm-governance, wm-mcp

### Embodiment I/O — COMPLETE

- ✅ 4 real Linux sensor drivers: `CpuUsageSensor` (/proc/stat), `DiskUsageSensor` (df), `NetworkThroughputSensor` (/proc/net/dev), `CpuFreqSensor` (sysfs cpufreq)
- ✅ 1 real Linux actuator backend: `SysfsActuator` (writes to /sys files for fan PWM, LED brightness)
- ✅ Actuator discovery: `discover_fan_actuators()`, `discover_led_actuators()`
- ✅ Enhanced `linux_hardware_bus()` auto-registers all discovered sensors + actuators
- ✅ `CycleType::Sensorimotor` — polls sensors, evaluates reflexes, executes commands, generates `SensorimotorProposal` records
- ✅ `sensorimotor.scan` MCP tool with NLU routing
- ✅ MCP server runs sensorimotor cycle every 10 dispatches, emits `ReflexFired` events to Gan Ying Bus

---

*This document is a living gap analysis. Update it as features are ported and gaps are closed.*
