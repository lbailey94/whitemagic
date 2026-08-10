# WhiteMagic v5 — Progress & Phase Status

**Last updated**: August 9, 2026 (v5.6.0 — 15 crates, 211 tools, 3,377 tests, ~131,000 LOC, 0 clippy warnings, 0 dependency vulnerabilities, 0 lock panics. ACS compliance surface + prescience claims ledger shipped. Counts verified: `cargo test --workspace` all green, `wm doctor` on the live store)

---

## Phase 0: Foundation — COMPLETE

All deliverables verified, 101 tests passing, zero compiler warnings.

| Deliverable | Status | Notes |
|---|---|---|
| Cargo workspace with 8 crates | Done | wm-core, wm-memory, wm-dispatch, wm-consciousness, wm-governance, wm-mcp, wm-polyglot, wm-tools |
| Core trait definitions | Done | `Tool`, `Gana`, `EffectRow`, `ToolStats`, `Context`, `Args`, `Output` |
| 28 Gana enum with all variants | Done | `#[repr(u8)]`, sanskrit names, descriptions, `from_index`, `all()` |
| Brain-wave state machine | Done | 5 states (Gamma/Beta/Alpha/Theta/Delta) + `BrainWaveTracker` with ring buffer |
| Basic error types | Done | `CoreError` with 11 variants, `is_retryable()`, `is_governance()` |
| Project README and AGENTS.md | Done | |
| `.gitignore`, `rustfmt.toml`, `clippy.toml` | Done | |
| Copy reusable Rust code from v2 | Done | 65 source files in `v2-reference/` |
| Integration test skeleton | Done | 4 test files, 80 integration tests + 21 unit tests = 101 total |
| `#![deny(unsafe_code)]` except wm-polyglot | Done | |
| Rust edition 2024, MSRV 1.85+ | Done | |
| Workspace-level dependencies | Done | |
| justfile build targets | Done | |

---

## Phase 0.5: Vertical Slice (MCP Server) — COMPLETE

106 tests passing. Minimal MCP server running end-to-end.

- **LMDB store**: put, get, delete, scan, count, get_raw, put_raw
- **12 tools + 1 meta-tool**: memory.create, memory.read, memory.list, memory.delete, memory.query, memory.search, memory.associate, memory.associations, gnosis, tools.list, karma.report, dharma.status, wm
- **MCP server**: JSON-RPC over stdio, 3 methods (initialize, tools/list, tools/call)
- **CLI binary**: `wm serve --store <path>`

---

## Phase 1: LMDB Memory Store — COMPLETE

134 tests passing. Full memory store with all planned deliverables.

| Deliverable | Status | Notes |
|---|---|---|
| Content-hash deduplication | Done | SHA-256 via `sha2` crate, `put_dedup()`, `find_by_content_hash()` |
| Cross-galaxy association links | Done | `AssociationStore` in `associations.rs`, composite key (source+target), find_from/find_to |
| Embedding storage | Done | Raw f32 in Embeddings galaxy, `put_embedding()`/`get_embedding()`/`delete_embedding()` |
| Write batching | Done | `put_batch()` — atomic multi-write in single LMDB transaction |
| Query API | Done | `MemoryQuery` with tag/importance/temporal filters, `query()` method |
| Memory lifecycle | Done | `Lifecycle` in `lifecycle.rs` — consolidation (boost + decay) + mindful forgetting |
| Memory builder methods | Done | `with_tags()`, `with_importance()`, `with_embedding()`, `record_access()`, `decay_importance()` |

### New Files
- `crates/wm-memory/src/associations.rs` — AssociationStore + Association type
- `crates/wm-memory/src/lifecycle.rs` — Lifecycle, LifecycleConfig, ConsolidationResult, ForgettingResult

### New Dependencies
- `sha2 = "0.10"` — SHA-256 content hashing (replaces placeholder hasher)

---

## Phase 2: Tantivy Full-Text Search — COMPLETE

140 tests passing. BM25-scored FTS with Tantivy 0.22.

| Deliverable | Status | Notes |
|---|---|---|
| Tantivy index integration | Done | `SearchEngine` in `search.rs`, mmap'd directory, OnCommitWithDelay reload |
| Schema: memory_id, galaxy, content, tags, timestamp | Done | STRING for exact match, TEXT for BM25, STORED for retrieval |
| BM25 scoring | Done | TopDocs collector with QueryParser |
| Add/delete/commit document API | Done | `add_document()`, `delete_document()`, `commit()` with reader reload |
| Search with galaxy filter | Done | `search_in_galaxy()` — post-filter by galaxy field |
| Search returning UUIDs | Done | `search_ids()` for MemoryStore integration |
| 6 FTS tests | Done | Basic search, tag search, galaxy filter, delete, empty index, UUID return |

### Tantivy API Notes
- Tantivy 0.22 uses `TantivyDocument` as concrete type (not generic `Document`)
- `Value` trait must be in scope for `as_str()` on `OwnedValue`
- `STRING` flag for exact-match fields (replaces `INDEXED` from older versions)
- Reader must call `reload()` after commit for search visibility
- Only one `IndexWriter` can exist at a time (Lockfile)

---

## Phase 3: Dispatch Pipeline — COMPLETE

185 tests passing. Full governance-gated dispatch pipeline with rate limiting, circuit breaking, Dharma evaluation, and karma tracking.

| Deliverable | Status | Notes |
|---|---|---|
| Rate limiter | Done | `SlidingWindow` atomics, per-tool + global RPM, burst allowance, per-tool overrides |
| Circuit breaker | Done | 3-state (Closed/Open/HalfOpen), `Instant` monotonic, `RwLock` registry, configurable thresholds |
| Dharma gate | Done | `ActionVerdict` enum (Observe/Advise/Correct/Intervene/Panic), BrainWave-derived maturity, homeostasis-aware strict mode |
| Karma ledger | Done | SHA-256 hash chain, u64 sequential keys, LMDB persistence (Galaxy::Karma), Guna classification (Sattvic/Rajasic/Tamasic) |
| Context fields | Done | `karma_debt: f32`, `intent_score: f32` added to `Context` |
| Pipeline wiring | Done | 7-stage chain: effect check → Dharma gate → rate limit → circuit breaker → tool call → karma record → stats |
| Integration tests | Done | 8 pipeline integration tests covering all gates |

### Pipeline Order
1. **Effect check** — `EffectRow::is_available_in(brain_wave)` → fast reject in low-power states
2. **Dharma gate** — `DharmaGate::evaluate()` → `ActionVerdict` (Panic/Intervene blocks, Correct/Advise warns)
3. **Rate limit** — `RateLimiter::try_acquire()` → per-tool sliding window + global RPM
4. **Circuit breaker** — `CircuitBreakerRegistry::is_open()` → fast-fail on repeated failures
5. **Tool call** — `tool.call(ctx, args)`
6. **Karma record** — `KarmaLedger::record()` → declared vs actual writes, SHA-256 chain to LMDB
7. **Stats** — `ToolStats::record_success/failure()` + circuit breaker feedback

### Key Design Decisions
- **Dharma maturity from BrainWave**: Gamma=5, Beta=4, Alpha=3, Theta=2, Delta=1. Strict mode active in Theta/Delta or when homeostasis health < 0.3
- **Homeostasis**: CPU load + memory pressure → health score. Stressed systems block destructive actions
- **Karma debt**: Cached in `Context`, synced post-dispatch. Sattvic=0, Rajasic=0.2 (wasteful), Tamasic=1.0 (deceptive)
- **Karma persistence**: u64 big-endian keys in Galaxy::Karma, chain head + next ID in metadata keys

### New Dependencies
- `sha2 = "0.10"` in wm-governance (karma ledger hashing)
- `lmdb = "0.8"` in wm-governance (cursor iteration for scan)
- `tempfile = "3"` in wm-dispatch and wm-governance (dev-dependency for tests)

---

## Phase 4 Prep: Pipeline → MCP Server Integration — COMPLETE

186 tests passing. Full governance pipeline wired into the MCP server, end-to-end verified.

**Status**: Superseded by Tool Catalog Expansion below (192 tests).

| Deliverable | Status | Notes |
|---|---|---|
| ToolRegistry rewrite | Done | `Arc<RegistryInner>`, `Clone`, immutable, returns owned `Arc<dyn Tool>`. `ToolRegistryBuilder` for bulk registration |
| `dispatch_by_name()` | Done | Convenience method on `DispatchPipeline` for registry-based dispatch |
| MCP server wiring | Done | `McpServer` holds `DispatchPipeline`. `handle_tools_call` routes through full 7-stage chain |
| `with_defaults` | Done | Constructs `KarmaLedger` backed by LMDB store, full pipeline with rate limiter + circuit breaker + Dharma gate |
| End-to-end verification | Done | initialize, tools/list, wm(thought=), wm(route=) all tested live. Karma + memory persistence across restarts confirmed |

### Benchmark Results

| Metric | Value |
|---|---|
| Pipeline dispatch | 1,692 ns/call |
| Direct tool call | 581 ns/call |
| Pipeline overhead | 1,111 ns/call (~1.1µs) |
| v2 Python middleware | ~200,000 ns/call |
| Improvement | ~180x |

### Live Test Results (2026-08-01)

| Test | Result |
|---|---|
| `initialize` handshake | Server info + capabilities returned |
| `tools/list` | `wm` fractal tool with full input schema |
| `wm(thought="remember...")` | NLU routing → `memory.create` → LMDB write + karma record |
| `wm(route="gnosis")` | Explicit routing → system health with galaxy counts |
| `wm(route="memory.list")` | Memory listing from LMDB |
| `wm(route="tools.list")` | Tool enumeration from embedded registry |
| Karma persistence | 7 karma entries across 2 server sessions — SHA-256 chain persists in LMDB |
| Memory persistence | 2 codex memories across server restarts |

### Key Files Changed

- `crates/wm-dispatch/src/registry.rs` — Rewritten with `Arc<RegistryInner>`, `ToolRegistryBuilder`
- `crates/wm-dispatch/src/pipeline.rs` — Added `dispatch_by_name()` method
- `crates/wm-mcp/src/server.rs` — `McpServer` now holds `DispatchPipeline`, `with_defaults` constructs full governance chain
- `crates/wm-tools/src/lib.rs` — `register_all` and `register_meta_tools` updated to new immutable registry API

---

## Tool Catalog Expansion — COMPLETE

192 tests passing. Expanded from 6 to 13 tools + `wm` meta-tool. All tools route through the full 7-stage governance pipeline.

| Tool | Gana | Description |
|---|---|---|
| `memory.create` | Encampment | Write to LMDB galaxy with tags + content hash |
| `memory.read` | WinnowingBasket | Read by UUID from galaxy |
| `memory.list` | WinnowingBasket | Scan galaxy with limit |
| `memory.delete` | Encampment | Delete by UUID from galaxy |
| `memory.query` | WinnowingBasket | Filter by tags, importance range, temporal range |
| `memory.search` | WinnowingBasket | Tantivy BM25 full-text search with optional galaxy filter |
| `memory.associate` | Net | Create cross-galaxy association link between memories |
| `memory.associations` | Net | Find incoming/outgoing associations for a memory |
| `gnosis` | Root | System health snapshot (galaxy counts, version, store path) |
| `tools.list` | Ghost | List all registered tools with Gana + descriptions |
| `karma.report` | Willow | Karma ledger status: total debt, chain head, recent entries, per-tool breakdown |
| `dharma.status` | ExtendedNet | Dharma gate homeostasis, health score, sutra descriptions |
| `wm` | Horn | Fractal meta-tool with NLU routing (thought=) and explicit routing (route=) |

### Key Changes

- `register_all` signature updated to accept optional `SearchEngine`, `KarmaLedger`, `DharmaGate` — enabling subsystem-aware registration
- `McpServer::with_defaults` now opens Tantivy index alongside LMDB, passes karma + dharma to `register_all`
- NLU `classify()` expanded with routing for delete, search, query, associate, associations, karma, dharma
- 6 new tests added (4 in wm-core, 9 in wm-consciousness, 4 in wm-dispatch) + 12 new NLU routing tests
- End-to-end verified: all 13 tools tested through live MCP server with karma + memory persistence

### Live Test Results (Expanded Catalog)

| Test | Result |
|---|---|
| `wm(route="karma.report")` | Karma ledger status with chain head, entry count, per-tool debt |
| `wm(route="dharma.status")` | Homeostasis snapshot with health score, sutra descriptions |
| `wm(route="memory.query")` | Tag/importance filtering with metadata-rich results |
| `wm(route="memory.associations")` | Association graph query (incoming/outgoing) |
| `wm(route="memory.delete")` | Delete by UUID with not_found handling |
| `wm(thought="show me the karma report")` | NLU routing → `karma.report` with confidence 1.0 |

### Tool Catalog Growth

| Milestone | Tools | Tests |
|---|---|---|
| Phase 0.5 (vertical slice) | 5 + wm | 106 |
| Phase 3 (dispatch pipeline) | 5 + wm | 185 |
| Phase 4 Prep (pipeline → MCP) | 5 + wm | 186 |
| Tool Catalog Expansion | 12 + wm | 192 |
| Phase 4 (Eco Mode) | 13 + wm | 209 |

---

## Phase 4: Brain-Wave Eco Mode — COMPLETE

All deliverables implemented and tested. 209 tests passing (up from 192).

| Deliverable | Status | Notes |
|---|---|---|
| `BrainWaveTracker::next_transition_duration()` | Done | Computes sleep time until next state transition for `tokio::select!` |
| `BrainWaveTracker::idle_duration()` | Done | Time since last event |
| `BrainWaveConfig::from_env()` | Done | Parses `WM_GAMMA_RATE`, `WM_ALPHA_IDLE`, `WM_THETA_IDLE`, `WM_DELTA_IDLE` |
| `SubsystemFlags` | Done | 9 per-state subsystem activation flags (memory_read, memory_write, search, karma, dharma, citta, dream, embeddings, inference) |
| `EcoModeMetrics` | Done | Time-in-state, transition counts, total events, JSON serialization |
| `EcoModeController` expansion | Done | Metrics, subsystem flags, env config, transition tracking |
| `ToolRegistry::available_in()` | Done | Filters tools by brain-wave state compatibility |
| `ToolRegistry::available_count()` | Done | Count of available tools per state |
| `McpServer::run_async()` | Done | `tokio::select!` event loop with stdin + brain-wave timer |
| CLI `wm serve` uses tokio runtime | Done | `wm serve` now uses `run_async()` with tokio |
| CLI `wm stats` command | Done | Shows brain-wave state, idle, events, subsystem flags |
| `Context` uses eco mode brain-wave | Done | `handle_tools_call` creates `Context::new(self.eco_mode.current())` |
| Tests | Done | +17 new tests (4 in wm-core, 9 in wm-consciousness, 4 in wm-dispatch) |

### New Test Count: 209

| Crate | Tests | Change |
|---|---|---|
| wm-core | 68 | +4 (next_transition, idle_duration) |
| wm-memory | 33 | Unchanged |
| wm-dispatch | 45 | +4 (available_in, available_count) |
| wm-consciousness | 22 | +9 (subsystem flags, metrics, eco mode) |
| wm-tools | 14 | Unchanged |
| wm-governance | 21 | Unchanged |
| wm-mcp | 5 | Updated for &mut self handle() |
| **Total** | **209** | +17 from Phase 4 |

---

## Phase 5: Consciousness Systems — COMPLETE

All deliverables implemented and tested. 239 tests passing (up from 209).

| Deliverable | Status | Notes |
|---|---|---|
| `CittaVector` (16D, ndarray + SIMD) | Done | `f32x4` SIMD magnitude, decay, valence, coherence, JSON |
| `CittaDimension` enum (16 dimensions) | Done | Clarity, Focus, Energy, Calm, Joy, Curiosity, Confidence, Openness, Patience, Determination, Creativity, Empathy, Discernment, Gratitude, Equanimity, Presence |
| Coherence measurement | Done | Auto-measure after significant events, configurable threshold (default 0.7) |
| `CoherenceReading` | Done | Score, valence, magnitude, timestamp, significance flag |
| Smarana (memory retention) | Done | Tracks recalls/misses, retention score (0.0–1.0) |
| Presence detection | Done | Active/idle tracking, activity ratio, time accounting |
| Apotheosis engine | Done | Composite score (effectiveness + coherence + retention), trend detection, improving flag |
| `CittaHeartbeat` | Done | Event-driven post-dispatch hook, updates citta vector on tool call completion |
| `DreamCycle` runner | Done | 12 phases sequential execution, `PhaseResult` tracking, `DreamResult` |
| `DreamPhase` descriptions | Done | All 12 phases with name() and description() |
| `SleepConsolidation` | Done | Tracks consolidated/skipped turns, memory IDs |
| Dream cycle Theta trigger | Done | `should_run(BrainWave::Theta)`, integrated into MCP server post-dispatch |
| MCP server integration | Done | `CittaHeartbeat` fires on every `tools/call`, dream cycle triggers on Theta |
| CLI `wm stats` expanded | Done | Shows citta, smarana, apotheosis, dream cycle status |
| Tests | Done | +30 new tests (18 citta, 10 dream, 2 integration) |

### Test Count: 239

| Crate | Tests | Change |
|---|---|---|
| wm-core | 68 | Unchanged |
| wm-memory | 33 | Unchanged |
| wm-dispatch | 45 | Unchanged |
| wm-consciousness | 40 | +18 (citta vector, dimensions, coherence, smarana, presence, apotheosis, heartbeat) +10 (dream cycle, phases, consolidation) +2 (eco mode from Phase 4) |
| wm-tools | 14 | Unchanged |
| wm-governance | 21 | Unchanged |
| wm-mcp | 5 | Updated for citta/dream integration |
| **Total** | **239** | +30 from Phase 5 |

---

## Test Coverage Summary

| Crate | Tests | Notes |
|---|---|---|
| wm-core | 148 | Core types, Gana, brain-wave, holographic coords, Context fields, proptest, attestation, security |
| wm-memory | 311 | LMDB store, Tantivy FTS, associations, lifecycle, enriched model, indexes, semantic encoding, mandala, vector store, recovery, validator |
| wm-dispatch | 104 | Rate limiter, circuit breaker, pipeline, registry, available_in, proptest, conservative dispatch, compartment enforcement |
| wm-consciousness | 394 | Citta vector, dream cycle, eco mode, smarana, apotheosis, harmony gating, autonomous cycles, spiral tracker, neural features, strategy, constellation, depth gauge, pattern-dream bridge, Wu Xing, cerebellum, limbic, redteam |
| wm-tools | 458 | Tool implementations + NLU routing (166 profiles + 12 prefix routes) + missing-arg hints + all expansion tools (v4, selfmodel, bicameral, drive, RSI, sensorimotor, transaction) |
| wm-governance | 91 | Dharma gate, karma ledger, resource rules, strict config, policy engine |
| wm-substrate | 163 | HarmonyVector, SubstrateMonitor, /proc + /sys reading, SensorimotorBus, ReflexLoop, anomaly detection, homeostatic loop |
| wm-polyglot | 66 | Julia (jlrs), Haskell (FFI), Zig (C ABI), Koka (C ABI) |
| wm-mcp | 80 | Server integration, CLI commands, PyO3 bridge, input validation, E2E tests |
| wm-reflex | 49 | Reflex dispatch table, safety bitmask, 8 builtin handlers, benchmark |
| wm-timescale | 37 | 5-tier event bus, hooks, brain-wave gating, budget enforcement |
| wm-workspace | 54 | Salience scoring, spotlight arbitration, event bus, ring buffer |
| wm-selfmodel | 79 | Metric tracking, forecasting, alerts, confidence calibration |
| wm-bicameral | 495 | Dual-hemisphere debate, corpus callosum, consensus gate, LLM right hemisphere, LlamaLeftHemisphere, BitNet right hemisphere, inference router, tri-model, edge rules, grammar schemas, gated engine, resource governor, context optimizer, routing metrics, speculative decoder, meta-harness, dense encoding, inference tuner |
| wm-drive | 50 | 5 drives, 9 event kinds, drive bias, decay toward baseline, Autonomic event source, cross-pollination matrix |
| wm-autonomic | 31 | BitMamba daemon, salience processing, autonomic layer, telemetry buffering |
| wm-resonance | 61 | Gan Ying Bus, event persistence, 229 event types |
| wm-sangha | 100 | Peer discovery, signal broadcast, locks, chat, TCP transport |
| wm-simulation | 47 | Monte Carlo, forecasting, counterfactual, Sobol |
| **Total** | **2,818** | All passing, 0 clippy warnings, fmt clean |

---

## v4 vs v2 Full Comparison

### What v4 Has That v2 Doesn't

- **Rust-native performance**: Zero Python overhead in the hot path — ~1.1µs pipeline overhead vs ~200µs in v2 (~180x improvement)
- **LMDB instead of SQLite**: 100x faster reads (mmap vs page cache), 10x faster writes
- **Effect row system**: Compile-time effect declarations with Koka-style semantics
- **7-stage governance pipeline**: Effect check → Dharma gate → rate limit → circuit breaker → tool call → karma record → stats — all in ~1.1µs
- **Brain-wave eco mode**: 5-state machine with zero monitoring overhead (v2 has 16 sleeping threads)
- **Atomic tool stats**: Lock-free, real-time effectiveness tracking
- **Holographic coordinates in Rust**: 6D composite keys with encode/decode and distance
- **Property-based tests**: proptest for roundtrip and invariant verification
- **Clean crate separation**: 9 crates with clear dependency graph
- **SHA-256 karma chain**: Immutable, LMDB-persisted hash chain with per-tool debt tracking and Guna classification (Sattvic/Rajasic/Tamasic)
- **Dharma gate with homeostasis**: Context-aware ethical evaluation that adapts strictness based on brain-wave state and system health
- **Tantivy BM25 search**: Pure-Rust full-text search integrated as a first-class tool (`memory.search`)
- **Hardware-aware governance (v3.4)**: `wm-substrate` reads real `/proc` + `/sys` metrics; brain-wave transitions gated by hardware health (Tiferet); resource budgets, novelty detection, purpose requirements, human review (Yama); full transparency via Gnosis Portals
- **Governed autonomous cycles (v3.4)**: 4 cognitive cycles (connect, compress, emergence, prune) — all health-gated, budget-limited, proposal-only, Gnosis-logged, novelty-suspended
- **Outward spiral detection (v3.4)**: Prevents circular thinking by tracking scope expansion; auto-suspends after 3 identical outputs
- **Secondary LMDB indexes**: O(1) content-hash lookup, O(log n) tag/importance/temporal range queries
- **Semantic coordinate encoding**: Anchor-based TF projection (3 semantic axes: Logic↔Emotion, Micro↔Macro, Time↔Space)
- **Advanced neural features**: Spreading activation, surprise gate, ripple tagging, neuromodulation, metaplasticity
- **Strategy synthesis**: Clusters memories by tag overlap, synthesizes meta-insight memories, cross-galaxy sleep consolidation
- **Dynamic galaxy management**: Project-scoped galaxies alongside the fixed 14

### What v2 Has That v3 Needs

| v2 Capability | v2 Size | v3 Target | Phase |
|---|---|---|---|
| 877+ tool handlers | ~100K lines Python | wm-tools crate | Phase 9 (126/877 ported, Tiers 1–7 complete) + v4 (15 tools) + selfmodel/bicameral/drive (7 tools) = 141 total |
| 28 Gana meta-tool MCP surface | `run_mcp_lean.py` (570 lines) | wm-mcp crate | Phase 8 |
| `wm` fractal meta-tool | `meta_tool.py` (3276 lines) | wm-mcp/wm-tools | Phase 9 |
| PRAT tool→Gana mapping | `prat_mappings.py` (985 lines, ~500 tools mapped) | wm-core or wm-tools | Phase 3 |
| Full-text search (FTS5) | SQLite FTS5 | Tantivy | ✅ Phase 2 COMPLETE |
| Vector search (HNSW) | Python HNSW + FastEmbed | LanceDB or Rust HNSW | Phase 7 (next) |
| Dharma governance | `dharma/` (55K rules.py) | wm-governance | ✅ Phase 6 + A-F COMPLETE |
| Karma ledger (Merkle chain) | `karma_ledger.py` (27K) | wm-governance | ✅ Phase 6 COMPLETE |
| Citta consciousness (16D) | `citta_vector.py` (14K) | wm-consciousness | ✅ Phase 5 COMPLETE |
| Dream cycle (12 phases) | `dream_daemon.py` + `sleep_consolidation.py` | wm-consciousness | ✅ Phase 5 COMPLETE |
| Memory consolidation | `consolidation.py` (43K) | wm-memory | ✅ Phase 1 + 6.5 COMPLETE |
| Mindful forgetting | `mindful_forgetting.py` (18K) | wm-memory | ✅ Phase 1 + 6.1 COMPLETE |
| Association mining | `association_miner.py` (32K) | wm-memory | ✅ Phase 1 + 6.2 COMPLETE |
| Constellation detection | `constellations.py` (38K) | wm-memory | ✅ Phase 6.6 COMPLETE |
| Session recording | `session_recorder.py` (23K) | wm-memory | ✅ Phase 5.4 COMPLETE |
| Circuit breaker | `circuit_breaker.py` (20K) | wm-dispatch | ✅ Phase 3 COMPLETE |
| Rate limiter | `rate_limiter.py` (11K) | wm-dispatch | ✅ Phase 3 COMPLETE |
| Param validator | `param_validator.py` (7K) | wm-dispatch | ✅ Phase 3 COMPLETE |
| Monte Carlo simulation | wm-evolution (14 Rust files) | wm-polyglot | Phase 7 |
| Predictive coding | wm-neuro (4 Rust files) | wm-consciousness | Phase 5 |
| Zig TRN gate | `zig_bridge.rs` + `zig_ffi.rs` | wm-polyglot | Phase 7 |
| ~10,000 tests | 200+ test files | wm-* tests | Phase 10 |

### What v3 Drops from v2

- SQLite entirely → LMDB
- FTS5 → Tantivy
- Python middleware chain (22 stages, ~200µs/call) → Rust 7-stage governance pipeline (~1.1µs/call, ~180x improvement)
- Subprocess polyglot bridges → In-process embedding/FFI
- HNSW Python implementation → LanceDB
- FastEmbed/ONNX as primary → Candle (Rust), ONNX as fallback
- 16 sleeping threads → Single tokio runtime with work-stealing
- Polling-based background loops → Event-driven wake
- Python singleton registry → Rust ownership + Arc

---

## v3.0 Verification — COMPLETE

**Date**: August 1, 2026 22:15 UTC

### Test Results: 239 all passing

| Crate | Tests | Status |
|---|---|---|
| wm-core | 68 | ✅ |
| wm-memory | 33 | ✅ |
| wm-dispatch | 45 | ✅ |
| wm-consciousness | 40 | ✅ |
| wm-governance | 21 | ✅ |
| wm-tools | 14 | ✅ |
| wm-mcp | 5 | ✅ |

### Live MCP Server: All endpoints verified

- `initialize` → server info + capabilities ✅
- `tools/list` → `wm` fractal meta-tool ✅
- `tools/call` with `thought=` → NLU routing ✅
- `tools/call` with `route=` → explicit dispatch (gnosis, karma, dharma, memory) ✅
- Karma ledger recording on every dispatch ✅
- Citta heartbeat fires post-dispatch ✅
- Brain-wave eco mode active ✅

### Benchmarks

- **Pipeline overhead**: 512ns/call (release build, budget: 5000ns)
- **Binary size**: 8.0 MB (statically linked, pure Rust)
- **Lines of Rust**: 30,992 across 9 crates
- **Dependencies**: 63

### CLI Commands

- `wm serve` → async tokio MCP server ✅
- `wm stats` → full consciousness dashboard ✅
- `wm doctor` → health check (LMDB, Tantivy, citta, dream, tools) ✅
- `wm quickstart` → 6-step guided setup ✅
- `wm polyglot` → polyglot runtime status ✅

### v2 Research Summary

Researched v2 codebase at `/home/lucas/Desktop/WHITEMAGIC`:

| Component | Lines | Notes |
|---|---|---|
| v2 Python core | 446K | 848 unique tools, 28 Gana, 14 galaxies |
| v2 Rust bridge | 95K | Holographic index, MC simulation, neuro, WASM |
| v2 tools subsystem | 90K | Handlers, registry, dispatch, middleware |
| WHITEMAGIC-CORE | 7K | Simplified 70-tool version with XP leveling |

Key algorithms identified for porting: memory consolidation (1142 lines),
mindful forgetting (498 lines), association miner (770 lines), sleep
consolidation (528 lines), constellation detection (974 lines), holographic
coordinates (300 lines, already in Rust), citta vector subspaces (393 lines),
coherence 8-dimension metric (460 lines), dream cycle full logic (1859 lines).

### v3.1 Plan

7 phases planned (see STRATEGY.md §16 for details):

1. **Phase 5.1**: Wire dream cycle to LMDB memory store ✅ COMPLETE
   - New: `retention.rs` (5-signal RetentionEngine), `miner.rs` (AssociationMiner with Jaccard overlap)
   - All 12 dream phases process real LMDB memories via `DreamContext`
   - Sleep consolidation pathways, content_hash dedup, association mining, mindful forgetting
   - 19 new tests, dream cycle benchmarks: 72ms (10 mems), 154ms (50), 375ms (200)
2. **Phase 5.2**: Brain-wave-aware tool listing & dispatch ✅ COMPLETE
   - `tools/list` filters by `eco_mode.current()` via `ToolRegistry::available_in()`
   - Delta: empty list (dormant), Theta: read-only, Alpha: read-only, Beta/Gamma: all tools
   - `gnosis` response includes `brain_wave` state + `available_tools` count
   - `tools.list` tool filters by `ctx.brain_wave`, includes `brain_wave` in response
   - 7 new tests (254 total, up from 239)
3. **Phase 5.3**: Citta → Context feedback loop ✅ COMPLETE
   - `Context` gains `citta_coherence` and `citta_valence` fields
   - Dispatch pipeline coherence gate: refuses writes when coherence < 0.3
   - `CittaHeartbeat::karma_feedback()` — Sattvic → +joy, Tamasic → −joy
   - `EcoModeController::apply_presence()` — activity ratio modulates transitions
   - `CittaHeartbeat::retirement_threshold()` — apotheosis score sets bar (0.05–0.15)
   - 11 new tests (265 total, up from 254)
4. **Phase 5.4**: Tool catalog expansion (13 → 50) ✅ COMPLETE
   - New file: `crates/wm-tools/src/expansion.rs` — 42 new tools across 10 categories
   - Memory ops: consolidate, decay, batch_read, update, tag, stats, hybrid_recall, count, tags
   - Session: start, checkpoint, recall, end, list
   - Consciousness: citta.status, citta.reflect, citta.coherence, dream.status, dream.trigger
   - Tools management: effectiveness_report, retire
   - Patterns: pattern.search, salience.spotlight, serendipity.surface
   - Constellation: detect, list
   - Galaxy: stats, export, import
   - Karma: history, clear
   - Dharma: rules, audit, profiles
   - Agents: register, list, heartbeat
   - Tasks: distribute, status
   - System: health, config, flush
   - Association mining: associate_mine
   - 12 new tests (277 total, up from 265)
5. **Phase 5.5**: NLU router expansion — COMPLETE
   - Expanded `classify()` from 7 to 40+ patterns covering all expansion tools
   - Expanded `extract_payload` from 3 to 10 tool patterns (memory.delete, memory.search, memory.count, session.start, session.end, agent.register, task.distribute)
   - Reordered patterns: specific matches before general ones (session before search, karma.history before karma, etc.)
   - 39 new NLU routing tests (66 total in wm-tools, up from 27)
6. **Phase 5.6**: CLI completion — COMPLETE
   - `wm doctor`: health check — LMDB store, galaxy counts, Tantivy index, brain-wave state, subsystem flags, citta coherence, dream cycle, tool registry
   - `wm quickstart`: 6-step guided setup — create memories, list, search, galaxy stats, consciousness dashboard, tool count
   - `wm polyglot`: status report for Julia/Haskell/Zig/Koka runtimes with build instructions
   - Added `store()` and `registry()` accessors to `McpServer`
7. **Phase 5.7**: Holographic memory coordinates — COMPLETE
   - `Coordinate5D` struct: 5D spatial coordinate (x, y, z, w, v) with SHA-256 content encoding
   - `Zone` enum: Core, InnerRing, MidRing, OuterRing, FarEdge — radial classification
   - `encode(text)`: deterministic hash → 5D position; `encode_with_context(text, temporal, importance)`
   - `find_nearby()`: spatial query returning sorted results within radius
   - `distance_to()` and `semantic_distance_to()` (weighted) metrics
   - Integrated `coord5d` field into `MemoryMetadata`, auto-populated in `Memory::new`
   - `MemoryStore` integration:
     - `put_semantic()` — encodes content into 5D coordinate before storage
     - `find_similar()` — semantic similarity search (encode query → scan → sort by distance)
     - `semantic_encoder()` — access the encoder for ad-hoc encoding
   - 20 new tests (469 total, up from 449): axis polarity, determinism, case
     insensitivity, similar-text proximity, coordinate range, mixed content,
     put_semantic integration, find_similar nearest-first, limit, empty galaxy
   - 0 clippy warnings, fmt clean

**Test count**: 339 tests (up from 277), 0 failures, 0 clippy warnings
**Success criteria**: 350+ tests (339 achieved), 50+ tools ✅, dream cycle reads/writes LMDB ✅,
brain-wave filtering on tools/list ✅, citta coherence affects dispatch ✅,
5D holographic coordinates ✅, spatial queries ✅.

---

## v3.2 Quality & CI — COMPLETE

All deliverables implemented and verified. 339 tests passing, 0 clippy warnings, fmt clean.

### Clippy Cleanup

Reduced from 400+ warnings to **0 warnings** across all crates.

| Category | Action | Files |
|---|---|---|
| Auto-fix (mechanical) | `cargo clippy --fix` for redundant closures, clones, imports | All crates |
| Workspace lints | Configured `pedantic` + `nursery` with targeted allows for non-actionable style lints | `Cargo.toml` |
| `&mut self` → `&self` | 11 dream phase methods that don't mutate | `dream.rs` |
| `&mut self` → `&self` | `load_state` only reads through interior mutability | `karma_ledger.rs` |
| `&self` → `self` | `Guna::as_str` is `const fn` on `Copy` type | `karma_ledger.rs` |
| `unwrap_or` → `unwrap_or_else` | Lazy evaluation for `json!({})` | `expansion.rs`, `server.rs` |
| Pass-by-value → pass-by-ref | `register_all`, `register_meta_tools`, `register_expansion` now take `&ToolRegistry` | `lib.rs`, `expansion.rs`, `server.rs` |
| `#[must_use]` | Added to `ToolRegistry::register()` | `registry.rs` |
| Flag variable → boolean expr | Replaced `let mut needs_fix = false` + 3 if-blocks with single expression | `dream.rs` |
| Unused `mut` | Removed from `KarmaLedger::new()` | `karma_ledger.rs` |
| Unused collection | Removed `ids` vector never read after population | `wm.rs` |
| PI literal → constant | `3.14159` → `std::f32::consts::PI` | `taxonomy.rs` |
| Missing semicolon | Added `;` to last statement in if block | `miner.rs` |
| `#[allow(dead_code)]` | Applied to useful-but-currently-unused methods (`total_memory_count`, `test_registry`, `Guna::as_str`) | `dream.rs`, `lib.rs`, `karma_ledger.rs` |
| `#[allow(clippy::should_implement_trait)]` | Intentional `default()` method on `EcoModeController` | `eco_mode.rs` |
| Loop → iterator | `for i in 0..5` → `for (i, entry) in entries.iter().enumerate()` | `karma_ledger.rs` |

### Criterion Benchmark Suite

Three benchmark files across two crates (plus existing dream cycle bench):

| Benchmark | Crate | What it measures |
|---|---|---|
| `dream_bench` | wm-consciousness | Dream cycle throughput with 10/50/200 memories |
| `store_bench` | wm-memory | LMDB put (100/1000 writes), get (single/batch), scan (10/100/1000), Tantivy search (4 queries) |
| `pipeline_bench` | wm-dispatch | Pipeline dispatch with/without karma ledger, registry lookup |

Run with: `cargo bench`

### GitHub Actions CI

File: `.github/workflows/ci.yml`

| Job | What it does |
|---|---|
| **fmt** | `cargo fmt --all -- --check` |
| **clippy** | `cargo clippy --all-targets -- -D warnings` (warnings are errors) |
| **test** | `cargo test --all-targets` |
| **bench-compile** | `cargo bench --no-run` (ensures benchmarks compile) |

Uses `Swatinem/rust-cache@v2` for dependency caching. `RUSTFLAGS="-D warnings"` enforces zero-warning policy.

### Strict `clippy.toml`

| Setting | Value | Purpose |
|---|---|---|
| `cognitive-complexity-threshold` | 50 | Catch overly complex functions |
| `too-many-arguments-threshold` | 8 | Encourage struct parameters |
| `type-complexity-threshold` | 250 | Catch deeply nested types |
| `enum-variant-size-threshold` | 200 | Stack size matters in dispatch hot path |
| `too-many-lines-threshold` | 150 | Encourage function decomposition |
| `doc-valid-idents` | LMDB, Tantivy, LanceDB, MCP, JSON, RPC, SHA, UUID, NLU | Project-specific acronyms for doc linting |

---

## v3.3 Phase 6: Memory Intelligence — COMPLETE

Detailed plan in `docs/STRATEGY.md` §4 (v2 vs v3 Memory Gap Analysis) and
§Roadmap (Phase 6.1–6.8). Summary:

| Sub-phase | Title | Dependency | Status |
|---|---|---|---|
| 6.1 | Enriched Memory Model (MemoryType, neuro_score, emotional_valence, protection, provenance) | None (foundation) | ✅ COMPLETE |
| 6.2 | Typed Association Links + Hebbian Learning | 6.1 | ✅ COMPLETE |
| 6.3 | Semantic Coordinate Encoding (Tantivy TF-IDF bridge → LanceDB embeddings) | 6.1 (6.3-full needs LanceDB) | ✅ COMPLETE |
| 6.4 | Secondary LMDB Indexes (content hash, tags, importance, temporal) | None | ✅ COMPLETE |
| 6.5 | Strategy Synthesis + Sleep Consolidation (cross-galaxy transfer) | 6.1, 6.2 | ✅ COMPLETE |
| 6.6 | Constellation Detection (density clustering + drift tracking) | 6.3 | ✅ COMPLETE |
| 6.7 | Advanced Neural Features (spreading activation, surprise gate, ripple tagging, neuromodulation, metaplasticity) | 6.1, 6.2 | ✅ COMPLETE |
| 6.8 | Dynamic Galaxy Management (project-scoped galaxies) | None | ✅ COMPLETE |

**Phase 6.1 deliverables**: MemoryType enum (8 variants), 14 new MemoryMetadata fields
with serde backward compat, recall() with Hebbian dynamics, decay() with per-memory
half-life, 10 new builder methods, retention engine with 7 signals (added emotional +
neuro), lifecycle protection support. 373 tests (up from 339), 0 clippy warnings.

**Phase 6.2 deliverables**: LinkType enum (7 variants: Related, Extends, Contradicts,
Supersedes, Temporal, Causal, Cascade), Association Hebbian fields (link_type,
co_activation_count, last_activated_at, decay_half_life_days), activate() with
diminishing-returns boost, decay() with per-link half-life, should_prune() threshold,
with_half_life_days() builder, all callers updated (miner.rs, tools/lib.rs,
tools/expansion.rs), association_type String kept for backward compat. 391 tests
(up from 373), 0 clippy warnings.

**Phase 6 complete**: All 8 sub-phases (6.1–6.8) delivered. 521 tests, 0 clippy
warnings, fmt clean. Phase E (Grounded Autonomous Cycles) and Phase F (Outward
Spiral Mechanism) are next — all dependencies are satisfied.

### Phase 6.5: Strategy Synthesis + Sleep Consolidation — COMPLETE

- New module `wm-consciousness/src/strategy.rs` with `StrategySynthesizer`
- Clusters memories by tag overlap using Jaccard similarity + union-find
- Filters clusters by min size (3) and avg importance (0.5)
- Synthesizes compressed strategy memories (meta-insights) from clusters
- Promotes strategies to Codex galaxy with `MemoryType::Pattern`
- Sleep consolidation transfer routes: Sessions→Codex, Citta→Aria,
  Dreams→Research, Universal→Codex (importance-gated)
- Dream cycle consolidation phase upgraded to run strategy synthesis
- 8 new tests

### Phase 6.6: Constellation Detection — COMPLETE

- New module `wm-consciousness/src/constellation.rs` with `ConstellationDetector`
- Grid-based density clustering in 3D semantic coordinate space (x, y, z)
- Configurable grid resolution (default 5³ = 125 cells)
- Flood fill clustering with 6-face adjacency
- Constellation naming by dominant tags
- Drift tracking: compares constellation centroids and sizes across runs
- Dream cycle constellation phase upgraded from stub to real detection
- 8 new tests

### Phase 6.7: Advanced Neural Features — COMPLETE

- New module `wm-consciousness/src/neural.rs` with 5 neuroscience-inspired modules:
  1. **SpreadingActivation**: propagates activation through association graph
     with decay, max hops, min threshold — used in Oracle phase for hub detection
  2. **SurpriseGate**: novelty detection using content hash + semantic distance
  3. **RippleTagger**: marks high-activity memories for consolidation — integrated
     into Enrichment phase
  4. **Neuromodulator**: dopamine (boosts high-importance) + serotonin (stabilizes
     toward equilibrium) — integrated into Harmonize phase, skips low-importance
     memories to preserve decay results
  5. **Metaplasticity**: adaptive learning rate based on access count —
     more plastic for new memories, less for established ones
- 12 new tests

### Phase 6.8: Dynamic Galaxy Management — COMPLETE

- New module `wm-memory/src/galaxy_registry.rs` with `GalaxyRegistry`
- Extends fixed 14-galaxy taxonomy with dynamic project-scoped galaxies
- Custom galaxies stored as LMDB named databases alongside built-in ones
- Registry metadata: name, description, project scope, creation timestamp, read-only flag
- Operations: create, get, list, delete, galaxy_db (cached handle), exists, count
- Rejects conflicts with built-in galaxy names
- 11 new tests

### Phase 6.4: Secondary LMDB Indexes — COMPLETE

- New module `wm-memory/src/indexes.rs` with `IndexDbs` struct
- 4 secondary index sub-databases in LMDB:
  - `idx_content_hash`: O(1) content-hash → UUID lookup (replaces O(n) scan)
  - `idx_tags`: DUP_SORT, galaxy-scoped tag → UUID lookup
  - `idx_importance`: DUP_SORT, big-endian f32 for range queries
  - `idx_temporal`: DUP_SORT, big-endian i64 for time-range queries
- Keys: `galaxy_db_name + 0x00 + value_bytes` (galaxy-scoped sorting)
- `put`, `put_batch`, `delete` maintain indexes atomically in same transaction
- `query()` uses indexed fast paths for single-dimension queries (tag, importance
  range, time range), falls back to scan for multi-dimensional queries
- `find_by_content_hash` now O(1) via index (was O(n) scan)
- 18 new tests (449 total, up from 431), 0 clippy warnings, fmt clean

### Phase 6.3: Semantic Coordinate Encoding — COMPLETE

- New module `wm-memory/src/semantic.rs` with `SemanticEncoder` and `SemanticScores`
- Replaces SHA-256 hash-based `Coordinate5D::encode()` with anchor-based TF projection
- Three semantic axes (ported from v2's anchor embedding + PCA concept):
  - **x**: Logic (0.0) ↔ Emotion (1.0) — 25 anchor terms per pole
  - **y**: Micro (0.0) ↔ Macro (1.0) — 22 anchor terms per pole
  - **z**: Time (0.0) ↔ Space (1.0) — 22 anchor terms per pole
- Tokenizes text using Tantivy `SimpleTokenizer` + `LowerCaser` (same pipeline as
  the search index) for consistent term extraction
- Sublinear TF scaling: `1 + ln(freq)` to avoid dominance by repeated terms
- Smoothed axis scoring: `(pos + 0.5) / (neg + pos + 1.0)` → neutral text returns 0.5
- `Coordinate5D::from_semantic()` constructor added to wm-core
- `MemoryStore` integration:
  - `put_semantic()` — encodes content into 5D coordinate before storage
  - `find_similar()` — semantic similarity search (encode query → scan → sort by distance)
  - `semantic_encoder()` — access the encoder for ad-hoc encoding
- 20 new tests (469 total, up from 449): axis polarity, determinism, case
  insensitivity, similar-text proximity, coordinate range, mixed content,
  put_semantic integration, find_similar nearest-first, limit, empty galaxy
- 0 clippy warnings, fmt clean

---

## v3.4 Governed Autonomy Roadmap — Phases A-D COMPLETE

Detailed plan in `docs/STRATEGY.md` §Governed Autonomy and on desktop:
`whitemagic-v3-governed-autonomy-plan.md`.

Investigation of v2's uncontrolled background activity (see desktop:
`whitemagic-v2-autonomous-activity-investigation.md`) revealed that v2 ran a
4-tier consciousness loop continuously with no resource awareness, consuming
2.4GB RAM and 110% CPU, producing 59,411 memories across 47 galaxies (11GB
SQLite). The process resisted SIGTERM due to GIL deadlock. v3 now implements
governed autonomy with hardware-aware resource gating, ethical rules, and full
transparency.

### Phase A: Harmony Vector (Lakshmi) — ✅ COMPLETE

**New crate**: `wm-substrate` with `HarmonyVector`, `SubstrateMonitor`,
`ThermalState`, `BatteryState`, `GunaTag`.

- Reads real `/proc/loadavg`, `/proc/meminfo`, `/sys/class/thermal/`,
  `/sys/class/power_supply/` on Linux
- `HarmonyVector`: CPU load, memory pressure, swap usage, thermal state,
  battery state, disk I/O, Guna classification, timestamp
- `SubstrateMonitor`: ring buffer history, configurable capacity
- `From<HarmonyVector> for Homeostasis` conversion in `wm-governance`
- `harmony.vector` + `harmony.history` MCP tools (Gana::Dipper) with NLU routing
- `McpServer` holds `SubstrateMonitor`, calls `refresh_homeostasis()` on every request
- `with_defaults()` samples hardware immediately on startup
- 19 new tests

### Phase B: Resource Gating (Tiferet) — ✅ COMPLETE

**Method**: `EcoModeController::apply_harmony(health_score)` in `wm-consciousness`.

- Health < 0.3 (stressed): caps brain-wave at Alpha — no high-power states
- Health < 0.5 (strained): caps at Beta — no Gamma bursts
- Health >= 0.5: no restriction
- Forces descent when current state exceeds the cap
- Accelerates descent when stressed but already in Alpha
- Never forces ascent — only gates downward
- MCP server calls `apply_harmony` after `apply_presence` on every request,
  using real health score from `DharmaGate::homeostasis()`
- 6 new tests

### Phase C: Dharma Resource Rules (Yama) — ✅ COMPLETE

**New module**: `wm-governance/src/resource_rules.rs`

- `ResourceRules` engine with 4 governance mechanisms:
  - **Resource budgets**: Rate-limits writes/spawns/network per minute, scaled by
    health score and brain-wave state (Delta=0, Theta=1/4, Alpha=1/2)
  - **Novelty requirement**: Blocks repetitive actions (same tool + same args hash)
    after configurable max repeats — directly prevents v2's circular thinking
  - **Purpose requirement**: Autonomous actions must declare a purpose
  - **Human review**: Autonomous actions require explicit human approval
- `ResourceRulesConfig`: Configurable limits, novelty window, max repeats,
  require_human_review flag
- `ResourceVerdict`: Allow / BudgetExceeded / NotNovel / RequiresHumanReview / NoPurpose
- `BudgetUsage`: Transparency snapshot for monitoring
- `ResourceRules` integrated into `McpServer` (held as `Arc<ResourceRules>`)
- 14 new tests

### Phase D: Gnosis Portals — ✅ COMPLETE

**New tools**: `gnosis.status`, `gnosis.history`, `gnosis.explain` (Gana::ThreeStars)

- `gnosis.status`: Full governance transparency — homeostasis, resource rules
  current budget usage, substrate snapshot, all governance layer statuses
- `gnosis.history`: Historical harmony vector data with summary stats
  (avg CPU, memory, health score)
- `gnosis.explain`: Explains governance decisions for any tool — returns
  Dharma verdict + Resource verdict + human-readable explanation
- NLU routing for all three tools (gnosis, transparency, governance status,
  explain governance, why blocked/allowed, audit history)
- All registered when dharma + substrate + resource_rules are available

### Remaining Governance Phases

| Phase | Name | Mandala OS Concept | Deps | Status |
|---|---|---|---|---|
| E | Grounded Autonomous Cycles — consolidation, emergence, retention (all gated) | Lila | D, Phase 6.3 | ✅ COMPLETE |
| F | Outward Spiral Mechanism — circular thinking detection + suspension | — | E | ✅ COMPLETE |

### Phase E: Grounded Autonomous Cycles (Lila) — ✅ COMPLETE

**New module**: `wm-consciousness/src/autonomous.rs` with `AutonomousCycleRunner`

Four governed cognitive cycles that operate on memory:
1. **Connect** (`consolidation.connect`): Propose typed associations for disconnected
   memories using semantic similarity (`find_similar`). Link type inferred from tag
   overlap (Jaccard). Requires human review.
2. **Compress** (`consolidation.compress`): Propose merging semantically overlapping
   memory pairs. Primary = higher importance. Requires human review.
3. **Emergence** (`emergence.scan`): Detect tag/topic emergence patterns across all
   galaxies. Aggregates tag frequencies, filters by min frequency. No human review
   needed (no destructive action).
4. **Prune** (`retention.prune`): Identify memories ready for forgetting using
   composite retention score (importance × 0.4 + neuro_score × 0.3 + recency × 0.3).
   High-importance memories require human review.

All cycles:
- Declare a purpose
- Check Harmony Vector health score (gate: min 0.3)
- Have time and memory budgets
- Produce actionable proposals (not direct mutations)
- Log to Gnosis (Substrate galaxy)
- Suspend after 3 consecutive identical outputs (novelty detection)

**New tools**: 4 MCP tools with NLU routing
- `consolidation.connect`, `consolidation.compress`, `emergence.scan`, `retention.prune`
- NLU keywords: "connect memories", "link disconnected", "compress memories",
  "merge memories", "emergence scan", "emerging tags", "prune memories",
  "ready to forget", etc.

**Wiring**: `register_all` and `register_expansion` updated to accept
`AssociationStore` and `SpiralTracker`. MCP server `with_defaults` creates
shared `Arc<Mutex<SpiralTracker>>` and passes to all autonomous tools.

- 25 new tests (546 total, up from 521)

### Phase F: Outward Spiral Mechanism — ✅ COMPLETE

**New module**: `wm-consciousness/src/spiral.rs` with `SpiralTracker`

Prevents circular thinking by tracking scope expansion of autonomous cycle outputs:
- **SpiralTracker**: Records cycle outputs, computes spiral direction per cycle
- **novelty_score**: Jaccard-based set novelty (0.0 = identical, 1.0 = fully novel)
- **SpiralDirection**: Outward (expanding), Stable, Inward (circling)
- **SpiralReport**: Full report with per-cycle data, overall direction, avg novelty
- **Automatic suspension**: After 3 consecutive identical outputs, cycle suspended
- **Recovery**: Novel output clears stale novelty history and unsuspends

**New tool**: `spiral.report` MCP tool with NLU routing
- NLU keywords: "spiral report", "spiral status", "autonomy report",
  "circular thinking", "expansion report", "novelty report"

**Integration**: All 4 autonomous cycle tools record results into shared
`SpiralTracker` via `Arc<Mutex<>>`. The `spiral.report` tool reads the tracker
and returns the full spiral report as JSON.

- 22 new tests (568 total, up from 546)

**Design principles**: Intentional, Efficient, Transparent, Deep, Actionable,
Spiraling Outward. See `whitemagic-v3-governed-autonomy-plan.md` for full spec.

---

## Phase 7: Polyglot Integration — COMPLETE

Full FFI framework with all 4 language backends. Feature-gated, optional, Rust-native fallback.

| Deliverable | Status | Notes |
|---|---|---|
| Julia bridge (jlrs) | Done | Embedded in-process, feature `wm-polyglot/julia` |
| Haskell bridge (FFI) | Done | Compiled to native library, C ABI |
| Zig bridge (C ABI) | Done | Compiled to native library, C ABI |
| Koka bridge (C ABI) | Done | Compiled to native library, C ABI |
| `polyglot.status` tool | Done | Shows runtime availability |
| NLU routing | Done | "polyglot status", "language runtimes" |
| Tests | Done | 51 tests in wm-polyglot |

**Architecture**: Each language backend is behind a feature flag. `#![forbid(unsafe_code)]` relaxed to `#![allow(unsafe_code)]` in wm-polyglot only (FFI boundary). All bridges use a common `PolyglotRuntime` trait.

- 51 new tests (619 total, up from 568)

---

## Phase 8: PyO3 + Python MCP Shell — COMPLETE

Thin Python MCP shell delegating all logic to Rust core via PyO3 bindings.

| Deliverable | Status | Notes |
|---|---|---|
| PyO3 bridge module | Done | `crates/wm-mcp/src/pyo3_bridge.rs`, feature `python` |
| Python extension module | Done | `whitemagic_v4` importable from Python |
| `handle_request()` API | Done | JSON-RPC string in, JSON-RPC string out |
| Python MCP server | Done | `python/whitemagic_v4_server.py` (~200 lines) |
| ONNX embedding fallback | Done | Optional via `fastembed` (graceful skip if not installed) |
| HuggingFace tokenizer | Done | Optional via `transformers` (graceful skip if not installed) |
| MCP config templates | Done | Claude Desktop, Cursor, Windsurf, pure Rust |
| `wm brain-wave` CLI | Done | Shorthand for brain-wave state |
| Tests | Done | 7 new tests in wm-mcp (handle_request, tool_count, galaxy_counts) |

**Key decisions**:
- PyO3 uses `abi3-py38` for Python 3.8+ compatibility
- `crate-type = ["rlib", "cdylib"]` for Python extension
- `#![deny(unsafe_code)]` at crate level, `#![allow(unsafe_code)]` in pyo3_bridge only
- Python is optional — pure Rust MCP server (`wm serve`) works without any Python
- Shared library named `libwm_mcp.so` — symlink to `whitemagic_v4.so` for Python import

**Python API**:
```python
import whitemagic_v4
server = whitemagic_v4.Server("/path/to/lmdb")
response = server.handle_request('{"jsonrpc":"2.0","id":1,"method":"tools/list"}')
status = server.status()  # JSON: brain_wave, citta, dream, galaxy_counts
```

**MCP protocol verified end-to-end**:
- `initialize` → protocolVersion 2024-11-05, serverInfo v3.4.0
- `tools/list` → `wm` meta-tool with inputSchema
- `tools/call` with NLU routing → correct tool dispatch
- Latency: ~3.3ms/request (21 requests in 70ms)

### New Files
- `crates/wm-mcp/src/pyo3_bridge.rs` — PyO3 bindings (`PyServer` class)
- `python/whitemagic_v4_server.py` — Python MCP shell
- `python/requirements.txt` — Optional Python deps
- `python/README.md` — Build and configuration guide
- `python/mcp_config_claude_desktop.json` — Claude Desktop config
- `python/mcp_config_cursor.json` — Cursor config
- `python/mcp_config_windsurf.json` — Windsurf config
- `python/mcp_config_rust_native.json` — Pure Rust config (no Python)

### Modified Files
- `crates/wm-mcp/src/lib.rs` — Conditional PyO3 module, `deny(unsafe_code)`
- `crates/wm-mcp/src/server.rs` — `handle_request()`, `tool_count()`, `galaxy_counts()` + 7 tests
- `crates/wm-mcp/Cargo.toml` — `abi3-py38`, `crate-type = ["rlib", "cdylib"]`
- `crates/wm-mcp/src/bin/wm.rs` — `brain-wave` CLI subcommand
- `justfile` — `build-python`, `build-lancedb`, `serve-python`, `doctor`, `brain-wave` targets

- 7 new tests (687 total, up from 680 — includes NLU router upgrade +6, vector search +6 from prior session)

### Per-Crate Test Counts (687 total at end of Phase 8)
| Crate | Tests |
|---|---|
| wm-core | 80 |
| wm-memory | 141 |
| wm-dispatch | 49 |
| wm-consciousness | 180 |
| wm-tools | 111 |
| wm-governance | 36 |
| wm-substrate | 19 |
| wm-mcp | 14 |
| wm-polyglot | 51 |
| **Total** | **687** |

---

## Post-Phase 8: Fuzz Testing, Cross-Platform CI, Mandala Compartments — COMPLETE

### Fuzz Testing
- 5 cargo-fuzz targets: `nlu_classify`, `dharma_evaluate`, `rate_limiter`, `json_rpc_parse`, `effect_row`
- 22 proptest tests across 4 crates (wm-core, wm-memory, wm-dispatch, wm-tools)
- `fuzz/Cargo.toml` with libfuzzer-sys, `fuzz/rust-toolchain.toml` pins nightly
- CI `proptest` job with `PROPTEST_CASES=4096`

### Cross-Platform CI
- `ci.yml`: fmt, clippy, test-linux, test-macos, test-windows, bench-compile, proptest
- `benchmarks.yml`: triggers on push/PR/tags(v*), uploads results to GH release on tag
- Uses `Swatinem/rust-cache@v2` for dependency caching

### Mandala Compartments
- New module `crates/wm-memory/src/mandala.rs` with 4 security tiers
- **MandalaLevel**: Research (256MB), Sandbox (256MB), Production (1GB), Secure (4GB, read-only default)
- **Compartment**: isolated MemoryStore + SearchEngine + AssociationStore per compartment
- **MandalaManager**: opens/closes/manages multiple compartments, verifies isolation
- `ResourceRulesConfig::strict()` added to wm-governance for Secure compartment governance
- 17 new tests

---

## Optimization Session — COMPLETE (Aug 2, 2026)

6 optimizations applied, 733 tests (up from 726), 0 clippy warnings.

### 1. Tantivy Index Sync (HIGH)
- `MemoryCreateTool`, `MemoryDeleteTool`, `MemoryUpdateTool` now index/de-index/re-index in Tantivy
- Errors are non-fatal (LMDB op succeeds even if Tantivy fails)
- Live test: search returns 3 results for "rust" with BM25 scores

### 2. Brain-Wave Startup State (HIGH)
- Server starts in Delta but transitions to Beta on first event via `BrainWaveTracker::recompute`

### 3. NLU Routing Confidence (HIGH)
- Added stopword filtering (80+ words), simple English stemmer (-ies, -ing, -ed, -es, -s)
- Expanded keyword profiles with synonyms, boosted primary keywords
- Added `PREFIX_ROUTES` table: 12 command verbs get 1.3-1.5x score multiplier
- Result: 10/10 correct routing in live tests, avg confidence 0.469 (up from 0.365)

### 4. karma.history Empty List Fix (MEDIUM)
- Root cause: `KarmaHistoryTool` used `MemoryStore::scan()` (rmp_serde) but karma entries are `KarmaEntry` (serde_json)
- Rewrote to use `KarmaLedger::recent()` and new `KarmaLedger::clear_old()`
- Added `delete_raw` to `MemoryStore`, 4 regression tests

### 5. --store CLI Flag (MEDIUM)
- `doctor`, `stats`, `brain-wave` subcommands accept `--store <path>` to override default

### 6. NLU Error Handling — Missing Args (MEDIUM)
- `WmMetaTool::call` checks `required_arg()` before dispatching
- Returns structured error with `hint` field containing usage example
- 2 new tests

### Live Performance Test Results

| Metric | Value |
|---|---|
| Server startup | 33ms |
| Tool listing | 2.0ms (68 tools) |
| Avg memory create | 56ms (includes Tantivy indexing) |
| Memory read | 2.7ms |
| Avg NLU confidence | 0.469 |
| Avg NLU route+dispatch | 7.2ms |
| Batch (20 reqs) | 30.7ms avg, 42.6ms p95 |
| Full-text search | 3.6ms |
| Gnosis | 2.8ms |

### Per-Crate Test Counts (733 total)
| Crate | Tests |
|---|---|
| wm-core | 87 |
| wm-memory | 164 |
| wm-dispatch | 55 |
| wm-consciousness | 180 |
| wm-tools | 120 |
| wm-governance | 43 |
| wm-substrate | 19 |
| wm-mcp | 14 |
| wm-polyglot | 51 |
| **Total** | **733** |

---

## Phase 9: Tool Porting — IN PROGRESS

### Tier 1: Knowledge Graph + Graph Traversal + Galaxy Management — ✅ COMPLETE

10 new tools ported, bringing total from 68 to 78. 777 tests (up from 733), 0 clippy warnings, fmt clean.

**Knowledge Graph** (`crates/wm-tools/src/expansion/knowledge_graph.rs`):
- `kg.extract` (Gana::Net) — Extracts entities from memory content using capitalized-word heuristics, creates typed associations between memories sharing entities
- `kg.query` (Gana::Net) — Queries graph for an entity, returns matching memories and their associations
- `kg.top` (Gana::HairyHead) — Ranks entities by memory count (hub/god node detection)

**Graph Traversal** (`crates/wm-tools/src/expansion/graph.rs`):
- `graph.walk` (Gana::HairyHead) — BFS traversal on association graph with depth limit
- `graph.community` (Gana::HairyHead) — Label propagation community detection
- `graph.propagate` (Gana::HairyHead) — Activation spreading from seed memories with decay

**Galaxy Management** (`crates/wm-tools/src/expansion/galaxy.rs`):
- `galaxy.transfer` (Gana::Neck) — Move memories between galaxies (with optional tag filter)
- `galaxy.merge` (Gana::Neck) — Copy + deduplicate memories from source to destination galaxy
- `galaxy.snapshot` (Gana::Void) — Capture galaxy state into Journals galaxy as JSON snapshot
- `galaxy.restore` (Gana::Void) — Restore galaxy from a stored snapshot

**NLU**: 10 new ToolProfile entries (78 total), 11 new routing tests
**Registration**: All 10 tools registered in `expansion/mod.rs`
**Tests**: +44 new tests (wm-tools: 120 → 164)

### Tier 2: Ox (Archaeology & Learning) + ThreeStars (Reasoning) — ✅ COMPLETE

6 new tools ported, bringing total from 78 to 84. 795 tests (up from 777), 0 clippy warnings, fmt clean.

**Archaeology & Learning** (`crates/wm-tools/src/expansion/archaeology.rs`):
- `archaeology.search` (Gana::Ox) — Excavate memory layers by time depth and importance stratification
- `learning.pattern` (Gana::Ox) — Detect recurring patterns and themes via tag co-occurrence and keyword frequency
- `learning.suggest` (Gana::Ox) — Suggest learning paths based on memory gaps and importance clusters

**Reasoning** (`crates/wm-tools/src/expansion/reasoning.rs`):
- `reasoning.bicameral` (Gana::ThreeStars) — Analyze a topic from multiple perspectives using bicameral (pros/cons) reasoning
- `think` (Gana::ThreeStars) — Gather memory context and produce structured analysis with insights and questions
- `explain` (Gana::ThreeStars) — Explain a memory or topic by gathering context from related memories

**NLU**: 6 new ToolProfile entries (84 total)
**Registration**: All 6 tools registered in `expansion/mod.rs`
**Tests**: +18 new tests (wm-tools: 164 → 182)

### Tier 3: Horn (Pipeline & Skills) + Heart (Anomaly & State) — ✅ COMPLETE

8 new tools ported, bringing total from 84 to 92. 816 tests (up from 795), 0 clippy warnings, fmt clean.

**Pipeline & Skills** (`crates/wm-tools/src/expansion/pipeline.rs`):
- `pipeline.create` (Gana::Horn) — Create a named pipeline with steps stored in Sessions galaxy
- `pipeline.list` (Gana::Horn) — List all stored pipelines
- `pipeline.status` (Gana::Horn) — Get detailed status of a specific pipeline by name or ID
- `skill.invoke` (Gana::Horn) — Invoke a named skill from the Codex galaxy
- `skill.list` (Gana::Horn) — List all available skills in the Codex galaxy

**Anomaly & State** (`crates/wm-tools/src/expansion/anomaly.rs`):
- `anomaly.detect` (Gana::Heart) — Detect anomalies in memory importance, access patterns, and content using z-score
- `state.snapshot` (Gana::Heart) — Capture a snapshot of current system state into Journals galaxy
- `state.revert` (Gana::Heart) — Read a previous state snapshot for system comparison

**NLU**: 8 new ToolProfile entries (92 total)
**Registration**: All 8 tools registered in `expansion/mod.rs`
**Tests**: +21 new tests (wm-tools: 182 → 203)

### Tier 4: HairyHead (Correlation) + Wall (Boundary) — ✅ COMPLETE

4 new tools ported, bringing total from 92 to 96. 832 tests (up from 816), 0 clippy warnings, fmt clean.

**Correlation** (`crates/wm-tools/src/expansion/correlation.rs`):
- `correlation.analyze` (Gana::HairyHead) — Analyze statistical correlations between tags using phi coefficient
- `god.nodes` (Gana::HairyHead) — Identify hub entities that connect many memories across galaxies

**Boundary** (`crates/wm-tools/src/expansion/boundary.rs`):
- `anti_loop.check` (Gana::Wall) — Detect repetitive patterns indicating loops or stuck states
- `boundary.enforce` (Gana::Wall) — Enforce resource boundaries and report violations

**NLU**: 4 new ToolProfile entries (96 total)
**Registration**: All 4 tools registered in `expansion/mod.rs`
**Tests**: +15 new tests (wm-tools: 203 → 218)

### Tier 5: Net (Associations & Network) + Ghost (Consciousness) — ✅ COMPLETE

12 new tools ported, bringing total from 96 to 108. 858 tests (up from 832), 0 clippy warnings, fmt clean.

**Network** (`crates/wm-tools/src/expansion/network.rs`):
- `association.mine` (Gana::Net) — Cross-galaxy association mining using Jaccard keyword overlap
- `pattern.detect` (Gana::Net) — Detect hubs, bridges, and temporal chains in association graph
- `emergence.report` (Gana::Net) — Tag frequency distribution with dominant/emerging/rare classification
- `network.stats` (Gana::Net) — Global network statistics (nodes, edges, density, degree distribution)
- `network.centrality` (Gana::Net) — Degree centrality ranking (in/out/total) with normalized scores
- `network.clusters` (Gana::Net) — Connected component analysis using Union-Find

**Consciousness** (`crates/wm-tools/src/expansion/consciousness.rs`):
- `smarana.status` (Gana::Ghost) — Retention score from recall/miss events
- `smarana.trace` (Gana::Ghost) — Temporal trace of retention decay over time
- `apotheosis.check` (Gana::Ghost) — Self-improvement trend with composite score
- `citta.history` (Gana::Ghost) — Recent citta memory history with timestamps
- `dream.analyze` (Gana::Ghost) — Dream cycle analysis (triggers, consolidations, serendipity)
- `consciousness.depth` (Gana::Ghost) — Composite depth score from brain-wave, coherence, valence, richness

**NLU**: 12 new ToolProfile entries (108 total), 12 new routing tests
**Registration**: All 12 tools registered in `expansion/mod.rs`
**Tests**: +26 new tests (wm-tools: 218 → 244)

### Tier 6: Room (Agent Management) + Void (Galaxy Management) — ✅ COMPLETE

10 new tools ported, bringing total from 108 to 118. 884 tests (up from 858), 0 clippy warnings, fmt clean.

**Agent Management** (`crates/wm-tools/src/expansion/agents.rs`):
- `agent.trust` (Gana::Room) — Get/set trust level (0.0–1.0) for an agent
- `agent.descriptions` (Gana::Room) — Get/set description for an agent
- `agent.capabilities` (Gana::Room) — Get/set capabilities list for an agent
- `agent.heartbeat.history` (Gana::Room) — Retrieve heartbeat history for an agent
- `agent.deregister` (Gana::Room) — Remove an agent from the registry

**Galaxy Management** (`crates/wm-tools/src/expansion/galaxy.rs`):
- `galaxy.dashboard` (Gana::Void) — Comprehensive overview of all galaxies with counts, tags, importance
- `galaxy.backup` (Gana::Void) — Back up all memory galaxies into a single snapshot in Journals
- `galaxy.taxonomy` (Gana::Void) — List all 14 galaxies with descriptions, counts, and memory-galaxy flags
- `galaxy.purge` (Gana::Void) — Delete all memories from a specific galaxy
- `galaxy.health` (Gana::Void) — Check health of a specific galaxy or all galaxies

**NLU**: 10 new ToolProfile entries (118 total), 11 new routing tests
**Registration**: All 10 tools registered in `expansion/mod.rs`
**Tests**: +26 new tests (wm-tools: 244 → 270)

### Tier 7: WinnowingBasket (Memory Ops) + Dipper (Homeostasis) — ✅ COMPLETE

8 new tools ported, bringing total from 118 to 126. 922 tests (up from 884), 0 clippy warnings, fmt clean.

**Memory Operations** (`crates/wm-tools/src/expansion/memory_ops.rs`):
- `memory.sort` (Gana::WinnowingBasket) — Sort memories by importance, recency, or access count
- `memory.filter` (Gana::WinnowingBasket) — Filter memories by tags, date range, importance threshold
- `memory.deduplicate` (Gana::WinnowingBasket) — Find duplicates by content_hash or content similarity
- `memory.export` (Gana::WinnowingBasket) — Export memories in JSON, CSV, or Markdown format

**Homeostasis** (`crates/wm-tools/src/expansion/homeostasis.rs`):
- `homeostasis.check` (Gana::Dipper) — Current system health from SubstrateMonitor
- `homeostasis.adjust` (Gana::Dipper) — Weighted health score with adjustable parameters
- `homeostasis.history` (Gana::Dipper) — Historical health samples with statistics
- `homeostasis.alerts` (Gana::Dipper) — Active alerts for stressed metrics

**NLU**: 8 new ToolProfile entries (126 total), 8 new routing tests
**Registration**: All 8 tools registered in `expansion/mod.rs`; `register_expansion` now takes `Option<Arc<SubstrateMonitor>>`
**Tests**: +38 new tests (wm-tools: 270 → 308)

### Phase 9 Status: SUBSTANTIVELY COMPLETE (126 tools)

---

## v4 Tools Integration — COMPLETE

8 new tools bridging the v4 subsystems (wm-reflex, wm-timescale, wm-workspace) into the MCP server.

### Tools Added (8):

| Tool | Gana | Description |
|---|---|---|
| `reflex.dispatch` | Heart | Dispatch a reflex handler by ID with sensor args and optional payload |
| `reflex.status` | Heart | Show registered reflex handlers, safety mask, dispatch count, builtins |
| `workspace.spotlight` | Ghost | Show current spotlight holder, strength, salience, candidates |
| `workspace.events` | Ghost | List recent workspace events from the backlog ring buffer |
| `workspace.publish` | Ghost | Publish an event to the global workspace bus with salience scoring |
| `workspace.stats` | Ghost | Show workspace statistics (events published, spotlight transfers, per-core/type counts) |
| `timescale.status` | Dipper | Show timescale bus state (tier configs, brain-wave gating, tick/timeout counts) |
| `timescale.hooks` | Dipper | List hooks for a specific tier with performance stats |

### Integration Details:

- **New module**: `crates/wm-tools/src/expansion/v4.rs` — 8 tool implementations + `register_v4` function
- **MCP server**: `McpServer` struct extended with `reflex_table`, `timescale_bus`, `workspace` fields; `with_defaults` creates v4 subsystems and registers tools
- **NLU profiles**: 8 new profiles in `nlu.rs` + 3 new prefix routes (spotlight, publish, broadcast)
- **NLU tests**: 8 new routing tests + 9 v4 inputs added to unique patterns test
- **Dependencies**: wm-tools and wm-mcp Cargo.toml updated with wm-reflex, wm-timescale, wm-workspace
- **EffectRow**: All v4 tools use `EffectRow::pure()` (in-memory state operations)
- **Error handling**: `ReflexError` → `CoreError` via `.map_err()` (no `From` impl)

### Per-Crate Test Counts (1084 total)
| Crate | Tests |
|---|---|
| wm-core | 88 |
| wm-memory | 164 |
| wm-dispatch | 55 |
| wm-consciousness | 181 |
| wm-tools | 337 |
| wm-governance | 43 |
| wm-substrate | 19 |
| wm-mcp | 14 |
| wm-polyglot | 51 |
| wm-reflex | 48 |
| wm-timescale | 34 |
| wm-workspace | 51 |
| **Total** | **1084** |

---

## v4 Phase R4: Self-Model Crate — COMPLETE

**Date**: August 3, 2026
**Tests**: 1177 total (up from 1084), 137 tools (134 + 3 selfmodel), 0 clippy warnings, fmt clean.

### wm-selfmodel crate — Predictive introspection

| Deliverable | Status | Notes |
|---|---|---|
| MetricKind (8 variants) | Done | CpuLoad, MemoryPressure, Latency, Throughput, ErrorRate, Coherence, DiskIo, SwapUsage |
| MetricTracker | Done | Rolling window history, per-metric samples |
| ForecastEngine | Done | Linear regression (slope/intercept), R² confidence, horizon prediction |
| AlertEngine | Done | AlertLevel (Info/Warning/Critical), Comparison (Above/Below), AlertRule, evaluate_rule + check_alerts |
| ConfidenceCalibrator | Done | Overall system confidence (0.0–1.0) from metric stability + forecast accuracy |
| SelfModel | Done | Top-level aggregating struct with record_metric, forecast, check_alerts, snapshot, confidence |

### 3 MCP Tools:
1. `selfmodel.forecast` (TurtleBeak) — Forecast a metric or all metrics with configurable horizon
2. `selfmodel.alerts` (TurtleBeak) — Check active alerts with severity counts
3. `selfmodel.snapshot` (TurtleBeak) — Full self-model state snapshot (metrics, alerts, forecasts, confidence)

### Integration:
- `SelfModel` wired into `McpServer` struct as `Arc<Mutex<SelfModel>>` with accessor
- `with_defaults` and `test_server` updated to initialize and register self-model tools
- `wm-selfmodel` added to workspace Cargo.toml, wm-mcp and wm-tools Cargo.toml
- NLU profiles + prefix route ("forecast" → "selfmodel.forecast") in nlu.rs
- 6 NLU routing tests for self-model tools
- `self_model_confidence` field added to `Context` (default 0.5)
- Conservative dispatch warning in pipeline when confidence < 0.5

### Files Created:
- `crates/wm-selfmodel/` (Cargo.toml, src/lib.rs, src/metrics.rs, src/forecast.rs, src/alert.rs, src/confidence.rs)
- `crates/wm-tools/src/expansion/selfmodel.rs`

### Files Modified:
- `Cargo.toml` (workspace members + dependencies)
- `crates/wm-core/src/context.rs` (self_model_confidence field)
- `crates/wm-dispatch/src/pipeline.rs` (conservative dispatch warning)
- `crates/wm-tools/src/expansion/mod.rs`, `Cargo.toml`, `src/nlu.rs`
- `crates/wm-mcp/src/server.rs`, `Cargo.toml`
- `scripts/live_perf_test.py` (R4 test cases)

### Per-Crate Test Counts (1177 total)
| Crate | Tests |
|---|---|
| wm-core | 90 |
| wm-memory | 164 |
| wm-dispatch | 55 |
| wm-consciousness | 181 |
| wm-tools | 357 |
| wm-governance | 43 |
| wm-substrate | 19 |
| wm-mcp | 14 |
| wm-polyglot | 51 |
| wm-reflex | 48 |
| wm-timescale | 34 |
| wm-workspace | 51 |
| wm-selfmodel | 22 |
| **Total** | **1177** |

### Live Performance Test Results:
- 33/33 NLU routes correct (including 3 new self-model routes)
- 135 tools registered (134 + 1 wm meta-tool)
- Avg NLU routing+dispatch: 3.9ms
- Startup: 35.1ms
- Dispatch benchmarks improved: e_stop -19.7%, all_8_builtins -12.3%

---

## v4 Phase R5: Bicameral Reasoning — COMPLETE

**Date**: August 3, 2026
**Tests**: 1260 total (up from 1177), 139 tools (137 + 2 bicameral), 0 clippy warnings, fmt clean.

### wm-bicameral crate — Dual-hemisphere debate

| Deliverable | Status | Notes |
|---|---|---|
| LeftHemisphere | Done | Deterministic, evidence-based analysis with classify_evidence |
| RightHemisphere trait | Done | Pluggable trait with RightHemisphereStub (heuristic) + RightHemisphereFn (closure-based) |
| Corpus Callosum | Done | Bounded bidirectional message channel (Critique/Counter/Agreement/Query), bandwidth limits |
| Consensus Gate | Done | Multi-round debate orchestration, 6 Verdict types (Agreed/AgreedAfterDebate/LeftPrevailed/RightPrevailed/LeftOnly/Inconclusive) |
| BicameralEngine | Done | Config (max_rounds, timeout, callosum_bandwidth, right_enabled), left_only fallback |
| Types | Done | HemisphereInput, HemisphereOutput, Stance (Agree/Disagree/Uncertain), HemisphereSource |

### 2 MCP Tools:
1. `bicameral.reason` (ThreeStars) — Dual-hemisphere debate with evidence gathering from memories
2. `bicameral.status` (ThreeStars) — Engine config and hemisphere availability

### Integration:
- `BicameralEngine` wired into `McpServer` as `Arc<Mutex<BicameralEngine>>` with accessor
- `with_defaults` and `test_server` updated to initialize and register tools
- `wm-bicameral` added to workspace Cargo.toml, wm-mcp and wm-tools Cargo.toml
- NLU profiles + prefix routes ("bicameral", "deliberate") in nlu.rs
- 4 NLU routing tests

### Files Created:
- `crates/wm-bicameral/` (Cargo.toml, src/lib.rs, src/hemisphere.rs, src/callosum.rs, src/consensus.rs)
- `crates/wm-tools/src/expansion/bicameral.rs`

### Files Modified:
- `Cargo.toml` (workspace members + dependencies)
- `crates/wm-tools/src/expansion/mod.rs`, `Cargo.toml`, `src/nlu.rs`
- `crates/wm-mcp/src/server.rs`, `Cargo.toml`

---

## v4 Phase R7: Emotion & Drive Core — COMPLETE

**Date**: August 3, 2026
**Tests**: 1260 total (139 + 2 drive), 141 tools (139 + 2 drive), 0 clippy warnings, fmt clean.

### wm-drive crate — Intrinsic motivation system

| Deliverable | Status | Notes |
|---|---|---|
| 5 Drives | Done | Curiosity, Satisfaction, Caution, Energy, Social — each [0.0, 1.0] |
| 9 Event Kinds | Done | ToolSuccess, ToolError, NovelInput, LowConfidence, HighConfidence, ResourcePressure, ResourceRelief, SocialInteraction, Decay |
| DriveCore | Done | Process events → update drives, decay toward baseline, compute bias |
| DriveBias | Done | Exploration/conservative/lightweight/social weights + confidence |
| ToolCategory | Done | Enum for bias application targets |
| BiasConfig | Done | Influence strength, min_weight, apply_bias() method |
| DriveConfig | Done | Per-event boost/penalty values, baseline levels, decay_rate |

### 2 MCP Tools:
1. `drive.snapshot` (Ghost) — Current drive state + bias weights
2. `drive.event` (Ghost) — Inject drive event to update state

### Integration:
- `DriveCore` wired into `McpServer` as `Arc<Mutex<DriveCore>>` with accessor
- `with_defaults` and `test_server` updated to initialize and register tools
- `wm-drive` added to workspace Cargo.toml, wm-mcp and wm-tools Cargo.toml
- NLU profiles + prefix routes ("drive", "emotion") in nlu.rs
- 4 NLU routing tests

### Files Created:
- `crates/wm-drive/` (Cargo.toml, src/lib.rs, src/drive.rs, src/event.rs, src/bias.rs)
- `crates/wm-tools/src/expansion/drive.rs`

### Files Modified:
- `Cargo.toml` (workspace members + dependencies)
- `crates/wm-tools/src/expansion/mod.rs`, `Cargo.toml`, `src/nlu.rs`
- `crates/wm-mcp/src/server.rs`, `Cargo.toml`

---

## v4 Self-Model Deep Integration — COMPLETE

**Date**: August 3, 2026

The Self-Model is now actively wired into the dispatch pipeline, not just available as MCP tools:

- **SubstrateMonitor → SelfModel**: On every MCP request, `refresh_self_model()` records real hardware metrics (CPU load, memory pressure, latency, error rate) into the SelfModel
- **Self-model confidence → Context**: The `self_model_confidence` value is injected into `Context` before every dispatch, allowing tools to adapt behavior
- **Conservative dispatch**: When confidence < 0.5, the pipeline blocks writes (not just warns) — prefer cached results over potentially degraded operations
- **Dispatch metrics → SelfModel**: After each dispatch, latency and error rate are recorded into the self-model for forecasting

### Per-Crate Test Counts (1302 total)
| Crate | Tests |
|---|---|
| wm-core | 90 |
| wm-memory | 164 |
| wm-dispatch | 58 |
| wm-consciousness | 181 |
| wm-tools | 379 |
| wm-governance | 43 |
| wm-substrate | 19 |
| wm-mcp | 45 |
| wm-polyglot | 51 |
| wm-reflex | 48 |
| wm-timescale | 34 |
| wm-workspace | 51 |
| wm-selfmodel | 22 |
| wm-bicameral | 36 |
| wm-drive | 32 |
| **Total** | **1302** |

---

## v4 Deep Integration — COMPLETE

**Date**: August 3, 2026
**Tests**: 1263 (up from 1260), 0 clippy warnings, fmt clean.

Four deep integration tasks completed, wiring v4 subsystems into the dispatch pipeline:

### D1: Drive bias → dispatch pipeline
- 6 drive fields added to `Context` (drive_curiosity, drive_caution, drive_energy, drive_exploration_weight, drive_conservative_weight)
- Drive state injected into Context from DriveCore before each dispatch
- Two drive gates in `DispatchPipeline`:
  - **Caution gate**: warns on write operations when drive_caution > 0.85
  - **Energy gate**: warns on write operations when drive_energy < 0.15
- Both gates are warnings (not blocks) — complement self-model confidence gate
- 3 new pipeline tests

### D2: Bicameral consensus → high-stakes decisions
- After successful dispatch, if routed tool has write effects, bicameral reasoning runs
- Logs verdict, confidence, and rounds via tracing::info
- Bicameral review includes drive_caution and self_model_confidence in context

### D3: Timescale hooks → citta/dream cycles
- Two timescale hooks registered in `with_defaults`:
  - `citta_decay` on Reactive tier (10ms interval)
  - `drive_decay` on Planning tier (100ms interval)
- Timescale bus brain-wave state synced before each dispatch
- `bus.tick_all()` called after each dispatch and on async brain-wave transitions
- Dream cycle runs on async brain-wave transitions

### D4: Workspace events → drive updates
- After each dispatch: publish Reward/Error event to GlobalWorkspace from CoreId::Dispatch
- After dream cycle: publish NovelDetection event from CoreId::Dream
- Drive events fired post-dispatch: ToolSuccess/ToolError from Dispatch source
- Self-model confidence fed into drive system: LowConfidence (<0.5) or HighConfidence (>0.8)

### Architecture Flow (handle_tools_call):
```
 1. Inject citta coherence/valence → Context
 2. Inject self-model confidence → Context
 3. Inject drive state (curiosity, caution, energy, weights) → Context  [D1]
 4. Sync timescale bus brain-wave state                                   [D3]
 5. Dispatch (pipeline checks drive caution/energy gates)                 [D1]
 6. Record metrics in self-model
 7. Citta heartbeat
 8. Fire drive events (ToolSuccess/Error, LowConfidence/HighConfidence)   [D4]
 9. Publish workspace event (Reward/Error from Dispatch core)             [D4]
10. Bicameral consensus review (if routed tool has writes)               [D2]
11. Eco mode + harmony gates
12. Dream cycle (if Theta) → publish dream event to workspace            [D3/D4]
13. Timescale tick_all                                                   [D3]
```

---

## v4 LLM Right Hemisphere — COMPLETE

**Date**: August 3, 2026
**Tests**: 1302 (up from 1274, +28 migration tests), 0 clippy warnings, fmt clean.

### New file: `crates/wm-bicameral/src/llm.rs` (~450 lines)
- `LlmConfig`: API key, endpoint, model, timeout, max_tokens — configurable via env vars
- `LlmRightHemisphere`: Calls OpenAI-compatible chat completions API using `ureq`
- Env vars: `WM_LLM_API_KEY` (required to enable), `WM_LLM_ENDPOINT` (default: OpenAI), `WM_LLM_MODEL` (default: gpt-4o-mini), `WM_LLM_TIMEOUT_MS` (default: 5000)
- Sends structured system prompt asking for JSON response with conclusion, confidence, stance, key_points
- Parses LLM JSON response into `HemisphereOutput`; falls back to heuristic on parse failure
- Graceful degradation: if API call fails (network error, auth error, timeout), falls back to `fallback_output()` using evidence-count heuristics
- `from_env()` returns `None` when no API key → server falls back to `RightHemisphereStub`

### Wiring in `with_defaults`:
```rust
let right: Arc<dyn wm_bicameral::RightHemisphere> =
    if let Some(llm) = LlmRightHemisphere::from_env() {
        Arc::new(llm)
    } else {
        Arc::new(RightHemisphereStub::new())
    };
```

### Dependency: `ureq = { version = "3", features = ["json"] }`
- ureq v3 API: `ureq::config::Config::builder().timeout_global(...).build().new_agent()`
- `forbid(unsafe_code)` in wm-bicameral means env var mutation tests use direct config construction

---

## Live Performance Test (139 tools) — COMPLETE

**Date**: August 3, 2026

### Results:
| Metric | Value |
|--------|-------|
| Server startup | 37.6ms |
| Tool listing | 4.0ms |
| Avg memory create | 41.0ms |
| Memory read | 4.9ms |
| NLU routing | 45/45 correct, avg conf 0.842 |
| Avg NLU route+dispatch | 5.4ms |
| Full-text search | 5.1ms |
| Gnosis | 4.7ms |
| Integration | 16/44 passed (28 rate-limited — expected after 70+ wm calls) |

### NLU Routing: All 45 routes correct (including 14 new v4 tool routes)
- Bicameral: bicameral.reason, bicameral.status ✅
- Drive: drive.snapshot, drive.event ✅
- Workspace: workspace.spotlight, workspace.events, workspace.publish, workspace.stats ✅
- Timescale: timescale.status, timescale.hooks ✅
- Reflex: reflex.dispatch, reflex.status ✅

---

## v4 Benchmark Regression Test — COMPLETE

**Date**: August 3, 2026
**Result**: No regressions detected. Significant improvements across LMDB, Tantivy, and dispatch.

### Benchmark Results (cargo bench, release mode)

| Benchmark | Time | Change | Verdict |
|---|---|---|---|
| dream_cycle/10_memories | 55.3 ms | ~0% | No change |
| dream_cycle/50_memories | 163.0 ms | -1.4% | No change |
| dream_cycle/200_memories | 410.1 ms | ~0% | No change |
| dispatch_noop_with_karma | 780.0 µs | -5.1% | Improved |
| dispatch_noop_no_karma | 546.4 ns | +3.8% | No change |
| registry_get_by_name | 41.5 ns | -6.1% | Improved |
| registry_all | 34.0 ns | -3.1% | Improved |
| lmdb_put/100_writes | 118.9 ms | +8.3% | No change (noise) |
| lmdb_put/1000_writes | 988.8 ms | +3.8% | No change |
| lmdb_get_single | 1.75 µs | -21.7% | **Improved** |
| lmdb_get_batch_100 | 155.8 µs | -36.5% | **Improved** |
| lmdb_scan/limit_10 | 11.1 µs | -34.7% | **Improved** |
| lmdb_scan/limit_100 | 106.7 µs | -33.0% | **Improved** |
| lmdb_scan/limit_1000 | 1.14 ms | -31.1% | **Improved** |
| tantivy_search/rust | 38.2 µs | -26.1% | **Improved** |
| tantivy_search/memory | 38.9 µs | -28.2% | **Improved** |

### Summary
- **0 regressions** across all 16 benchmarks
- **10 improvements** (statistically significant, p < 0.05)
- LMDB read/scan improvements: 21-37% faster (likely from Rust compiler optimizations between runs)
- Tantivy search: 26-28% faster
- Dispatch with karma: 5% faster
- Registry lookups: 3-6% faster

---

## v4 Local AI Integration L1: BitMamba Autonomic Layer — COMPLETE

**Date**: August 4, 2026
**Tests**: 1353 total (up from 1302, +51 across L1+L2+L3), 0 clippy warnings, fmt clean.

### New crate: `wm-autonomic` (~900 lines)

| Deliverable | Status | Notes |
|---|---|---|
| `BitMambaDaemon` | Done | Subprocess management, JSON lines protocol (stdin/stdout), graceful shutdown on Drop |
| `SalienceProcessor` | Done | 4 signal types (Novelty, Anomaly, EmotionalShift, Background), EMA baseline, token history |
| `AutonomicLayer` | Done | Telemetry buffering, pulse inference, signal-to-drive/workspace routing |
| `DriveEventSource::Autonomic` | Done | Added to wm-drive event.rs |
| MCP server integration | Done | Telemetry feed after dispatch, salience pulse, drive + workspace event routing |

### Env vars:
- `WM_BITMAMBA_BIN`, `WM_BITMAMBA_MODEL`, `WM_BITMAMBA_TOKENIZER`, `WM_AUTONOMIC_ENABLED`

### Files Created:
- `crates/wm-autonomic/` (Cargo.toml, src/lib.rs)

### Files Modified:
- `Cargo.toml` (workspace members + dependencies)
- `crates/wm-drive/src/event.rs` (Autonomic variant)
- `crates/wm-mcp/Cargo.toml`, `crates/wm-mcp/src/server.rs` (autonomic field, telemetry forwarding, salience routing)

- 22 unit tests

---

## v4 Local AI Integration L2: LlamaLeftHemisphere — COMPLETE

**Date**: August 4, 2026

### New file: `crates/wm-bicameral/src/local_llm.rs` (~220 lines)

| Deliverable | Status | Notes |
|---|---|---|
| `LlamaConfig` | Done | Endpoint, model, temperature (0.2 default), timeout, max_tokens — env-configured |
| `LlamaLeftHemisphere` | Done | Implements `Hemisphere` trait, calls llama-server OpenAI-compatible API via ureq |
| `BicameralEngine` refactored | Done | `left: Box<dyn Hemisphere>` (was concrete `LeftHemisphere`) |
| `with_hemispheres` constructor | Done | Explicit left/right selection for testing |
| `bicameral.status` tool | Done | Reports left hemisphere backend name |
| Heuristic fallback | Done | Falls back to `LeftHemisphere::new()` when llama-server unavailable |

### Env vars:
- `WM_LLAMA_ENDPOINT`, `WM_LLAMA_MODEL`, `WM_LLAMA_TEMP`, `WM_LLAMA_TIMEOUT_MS`, `WM_LLAMA_MAX_TOKENS`

### Files Created:
- `crates/wm-bicameral/src/local_llm.rs`

### Files Modified:
- `crates/wm-bicameral/src/lib.rs` (module + exports, BicameralEngine refactored)
- `crates/wm-tools/src/expansion/bicameral.rs` (status tool reports left hemisphere name)

- 11 unit tests

---

## v4 Local AI Integration L3: BitNet Right Hemisphere — COMPLETE

**Date**: August 4, 2026

### New file: `crates/wm-bicameral/src/bitnet.rs` (~530 lines)

| Deliverable | Status | Notes |
|---|---|---|
| `BitNetConfig` | Done | HTTP endpoint, llama-cli path, model path, temperature (0.8 default), timeout, max_tokens |
| `BitNetRightHemisphere` | Done | Implements `RightHemisphere` trait |
| HTTP mode | Done | OpenAI-compatible API via `llama-server` (preferred, persistent server) |
| Subprocess mode | Done | Spawns `llama-cli` per inference call (no server needed) |
| High temperature | Done | 0.8 default for creative, divergent output |
| Graceful fallback | Done | Falls back to heuristic `fallback_output()` on failure |
| MCP server priority | Done | Right hemisphere: BitNet → LLM → stub |

### Env vars:
- `WM_BITNET_ENABLED`, `WM_BITNET_ENDPOINT`, `WM_BITNET_MODEL`, `WM_BITNET_LLAMA_CLI`, `WM_BITNET_MODEL_PATH`, `WM_BITNET_TEMP`, `WM_BITNET_TIMEOUT_MS`, `WM_BITNET_MAX_TOKENS`

### Files Created:
- `crates/wm-bicameral/src/bitnet.rs`

### Files Modified:
- `crates/wm-bicameral/src/lib.rs` (module + exports)
- `crates/wm-mcp/src/server.rs` (right hemisphere selection: BitNet → LLM → stub)

- 17 unit tests

### Per-Crate Test Counts (1428 total)
| Crate | Tests | Change |
|---|---|---|
| wm-core | 90 | — |
| wm-memory | 177 | +13 (L5: embedder) |
| wm-dispatch | 58 | — |
| wm-consciousness | 181 | — |
| wm-tools | 379 | — |
| wm-governance | 43 | — |
| wm-substrate | 19 | — |
| wm-mcp | 45 | — |
| wm-polyglot | 51 | — |
| wm-reflex | 48 | — |
| wm-timescale | 34 | — |
| wm-workspace | 51 | — |
| wm-selfmodel | 22 | — |
| wm-bicameral | 118 | +54 (L4: router 45 + router integration 9) |
| wm-drive | 32 | — |
| wm-autonomic | 22 | — |
| **Total** | **1428** | +74 from L4+L5+integration |

### Next Steps:
- All local AI integration phases (L1–L5) are complete ✅
- OrtEmbedder (fastembed-rs / ONNX Runtime) added, feature-gated under `onnx` ✅
- InferenceRouter wired into BicameralEngine::reason() with RoutingInfo ✅
- PyO3 bridge verified end-to-end (JSON-RPC initialize, tools/list, memory.create, memory.search) ✅
- Benchmarks: router classify (3.7µs), route (6µs), budget tracker (3ns), bicameral reason (5µs); embedder stub single (972ns), batch 256 (337µs) ✅
- Next: N-phases for deep local AI parity with v2 (see `docs/notes/next-phase-strategy-2026-08-04.md`)

---

## v4 Local AI Integration L4: Inference Router — COMPLETE

**Date**: August 4, 2026
**Tests**: 1418 total (up from 1353, +65 across L4+L5), 0 clippy warnings, fmt clean.

### New module: `crates/wm-bicameral/src/router.rs` (~1420 lines)

| Deliverable | Status | Notes |
|---|---|---|
| `InferenceTier` enum | Done | 5 tiers (EdgeRules, LocalLlamaCpp, LocalSmall, LocalLarge, Cloud) with ordering, escalate() |
| `ComplexityClassifier` | Done | 17 task patterns, 5 sensitivity patterns, 3 tool-call patterns, 3 multi-turn patterns, latency budget awareness |
| `ComplexityAssessment` | Done | tier, task_type, confidence, estimated_output_tokens, is_sensitive, needs_tool_calls, is_multi_turn, signals |
| `TokenBudgetTracker` | Done | EMA-based usage prediction, warning/critical thresholds, recommend_downgrade() |
| `InferenceRouter` | Done | Confidence cascading, TierHandler trait, force_tier override, cloud availability check, sensitive data protection |
| `RouterConfig` | Done | from_env() with 4 env vars |
| 45 unit tests | Done | Tier ordering, classification, sensitivity, cascading, budget, serialization |

### Files Created:
- `crates/wm-bicameral/src/router.rs`

### Files Modified:
- `crates/wm-bicameral/src/lib.rs` (module + exports)
- `crates/wm-bicameral/Cargo.toml` (regex dependency)
- `Cargo.toml` (workspace regex dependency)

### Environment Variables:
| Variable | Default | Description |
|---|---|---|
| `WM_ROUTER_CONFIDENCE_THRESHOLD` | `0.5` | Confidence threshold for tier escalation |
| `WM_ROUTER_MAX_ESCALATIONS` | `2` | Max tier escalations before giving up |
| `WM_ROUTER_CLOUD_AVAILABLE` | `1` | Whether cloud tier is available |
| `WM_ROUTER_TOKEN_BUDGET` | `100000` | Total token budget for session |

---

## v4 Local AI Integration L5: Local Embedder — COMPLETE

**Date**: August 4, 2026
**Tests**: 1428 total, 0 clippy warnings, fmt clean.

### New module: `crates/wm-memory/src/embedder.rs` (~420 lines)

| Deliverable | Status | Notes |
|---|---|---|
| `Embedder` trait | Done | embed_batch, embed, embed_query, dimension, is_available, backend_name |
| `HttpEmbedder` | Done | llama-server /v1/embeddings (OpenAI-compatible), env-configured |
| `StubEmbedder` | Done | SHA-256 hash-based pseudo-embeddings, deterministic, [-1,1] normalized |
| `EmbedderConfig` | Done | from_env() with 4 env vars |
| `create_embedder()` | Done | Factory: HttpEmbedder if configured, else StubEmbedder |
| 13 unit tests | Done | Stub embedder, HTTP config, URL building, trait objects, serialization |

### Files Created:
- `crates/wm-memory/src/embedder.rs`

### Files Modified:
- `crates/wm-memory/src/lib.rs` (module + exports)
- `crates/wm-memory/Cargo.toml` (ureq dependency)

### Environment Variables:
| Variable | Default | Description |
|---|---|---|
| `WM_EMBEDDER_ENDPOINT` | — | llama-server URL for embeddings (e.g. http://localhost:8080) |
| `WM_EMBEDDER_MODEL` | `local` | Model name for embeddings API |
| `WM_EMBEDDER_DIM` | `384` | Expected embedding dimensionality |
| `WM_EMBEDDER_TIMEOUT_MS` | `30000` | Request timeout in milliseconds |


---

## Pre-N Batch C: Architectural Modules — COMPLETE

**Date**: August 4, 2026
**Tests**: 1,618 total (+103 from 1,515), 0 clippy warnings, fmt clean.

Four architectural modules ported from v2 Python to v4 Rust:

| Module | v2 Source | v4 Location | Lines | Tests | Crate |
|---|---|---|---|---|---|
| Pattern-Dream Bridge | `synergies/pattern_dream_bridge.py` (108) | `wm-consciousness/src/pattern_dream_bridge.rs` | ~280 | 13 | wm-consciousness |
| Cross-Pollination Matrix | `gardens/cross_pollination.py` (167) | `wm-drive/src/cross_pollination.rs` | ~570 | 17 | wm-drive |
| Resource Governor | `inference/resource_governor.py` (358) | `wm-bicameral/src/resource_governor.rs` | ~820 | 34 | wm-bicameral |
| Wu Xing Engine | `wu_xing/__init__.py` (529) | `wm-consciousness/src/wu_xing.rs` | ~850 | 39 | wm-consciousness |

### Pattern-Dream Bridge
- Queues discovered patterns for subconscious dream cycle synthesis
- Groups patterns by type, generates `DreamSynthesis` with combined insights
- Uses `f64` epoch timestamps for serde compatibility

### Cross-Pollination Matrix
- Models cascading affective drive events between 5 intrinsic drives
- `CascadeRule` defines source→target drive triggers with threshold + boost
- `check_cascades()` returns `DriveEvent`s for `DriveCore` integration
- Resonance event logging for cross-drive influence tracking

### Resource Governor
- Adapts inference resource usage based on hardware metrics (CPU temp, memory pressure, swap, battery)
- Three modes: ECO (constrained), NORMAL, PERFORMANCE (unleashed)
- `ModeProfile` structs with idle timeouts, context size, parallelism, stop flags
- Mode transitions tracked with reasons and metrics history
- Decoupled from backend control — only provides profiles, doesn't enforce

### Wu Xing Engine (五行)
- Five Elements cognitive energy system: Wood (木), Fire (火), Earth (土), Metal (金), Water (水)
- Generating cycle (生): Wood→Fire→Earth→Metal→Water→Wood
- Overcoming cycle (克): Wood→Earth→Water→Fire→Metal→Wood
- Energy adjustments propagate through both cycles (boost generating target, suppress overcoming target)
- Balance score (variance-based), harmony score (blocked flow detection)
- Situation analysis via keyword matching with elemental guidance generation
- Rebalancing toward center when below harmony threshold


---

## N2: Edge Rule Engine — COMPLETE

**Date**: August 4, 2026
**Tests**: 1,653 total (+35), 0 clippy warnings.

### New module: `crates/wm-bicameral/src/edge_rules.rs` (~640 lines)

| Deliverable | Status | Notes |
|---|---|---|
| `CompiledRule` | Done | Pipe-separated keyword patterns, `matches()` with coverage + length scoring |
| `EdgeRuleEngine` | Done | In-memory rule matching, query cache, stats tracking |
| 18 built-in rules | Done | Greetings, version, help, offline, dharma, rust, memory, cascade, wu_wei, math, etc. |
| `EdgeRuleHandler` | Done | Thread-safe `TierHandler` impl wrapping engine in `Mutex` |
| `InferenceResult` | Done | Query, answer, confidence, method, latency, tokens_equivalent, from_cache |
| `EdgeStats` | Done | Total queries, cache/rule hit rates, fallback count, rules count |
| 35 unit tests | Done | Rule matching, scoring, caching, stats, handler integration, fallback |

### Integration
- `EdgeRuleHandler` implements `TierHandler` trait for `InferenceRouter` EdgeRules tier
- Returns `Err("no edge rule match")` when no rule matches, allowing router to escalate
- Custom rules can be added via `add_rule()` or `EdgeRuleHandler::with_rules()`


---

## N3: Grammar-Constrained JSON Output — COMPLETE

**Date**: August 4, 2026
**Tests**: 1,695 total (+42), 0 clippy warnings.

### New module: `crates/wm-bicameral/src/grammar_schemas.rs` (~980 lines)

| Deliverable | Status | Notes |
|---|---|---|
| 7 JSON Schema constants | Done | Entity extraction, security classification, safety evaluation, tool call, tool call list, content summary, code generation |
| 3 GBNF Grammar constants | Done | JSON object, tool call (embedded JSON), Python code |
| `SchemaName` enum | Done | 7 variants with `as_str()`, `schema()`, `parse_name()` |
| `GrammarName` enum | Done | 3 variants with `as_str()`, `grammar()`, `parse_name()` |
| Schema/grammar registry | Done | `get_schema()`, `get_grammar()`, `schema_map()`, `grammar_map()` |
| JSON Schema validator | Done | `validate_json()` checks required fields, types, numeric ranges |
| `ValidationError` enum | Done | InvalidJson, NotAnObject, MissingField, WrongType, OutOfRange |
| `ValidationResult` | Done | valid flag + error list |
| `extract_json()` | Done | Extracts JSON from LLM output text (markdown blocks, embedded) |
| `extract_and_validate()` | Done | Extract + validate in one call |
| 42 unit tests | Done | Schema parsing, validation, extraction, type checking, range checking |

### Schemas Provided
| Schema | Required Fields | Use Case |
|---|---|---|
| `entity_extraction` | entities, relations | Entity/relation extraction from text |
| `security_classification` | is_attack, confidence | Security threat detection |
| `safety_evaluation` | score, reasoning | Dharma safety assessment |
| `tool_call` | tool, args | Single tool call from agent loop |
| `tool_call_list` | tool_calls, final_answer | Multi-step agent planning |
| `content_summary` | summary | Content summarization with key points |
| `code_generation` | code | Code generation with metadata |

---

## N1: TriModelManager — Tri-Model Lifecycle Management — COMPLETE

**Date**: August 4, 2026
**Tests**: 1,757 total (+62), 0 clippy warnings.

### New module: `crates/wm-bicameral/src/tri_model.rs` (~1,600 lines)

| Deliverable | Status | Notes |
|---|---|---|
| `ModelKind` enum | Done | Autonomic, Left, Right — `#[repr(u8)]` for safe casting |
| `ModelState` enum | Done | Stopped, Running, Idle, Failed |
| `ModelComponent` struct | Done | State, request/error counts, last active, config |
| `TriModelConfig` | Done | Env var parsing (WM_LLAMA_BG_ENDPOINT, WM_LLAMA_FG_ENDPOINT, etc.) |
| `TriModelManager` | Done | Lifecycle: start/stop/restart per model, ensure_running, route_and_ensure |
| `LifecycleEvent` + `LifecycleEventType` | Done | Event emission with atomic counters |
| Idle watchdog | Done | `check_idle()` shuts down models past idle timeout |
| Health check | Done | `health_check()` detects failed models, auto-restart |
| `TriModelHandler` (implements `TierHandler`) | Done | Routes inference to appropriate model by tier, stub mode for testing |
| `summary()` | Done | CLI-displayable status string |
| 60 unit tests | Done | Lifecycle transitions, routing, idle watchdog, health check, handler, env config |

---

## N9: Router-Gated Hemisphere Execution — COMPLETE

**Date**: August 4, 2026
**Tests**: 1,780 total (+23), 0 clippy warnings.

### New module: `crates/wm-bicameral/src/gated.rs` (~660 lines)

| Deliverable | Status | Notes |
|---|---|---|
| `GateDecision` struct | Done | Tier, run_right, max_rounds, sensitive, reason |
| `RouterGate` | Done | Wraps `InferenceRouter`, classifies prompts into gate decisions |
| `GatedEngine` | Done | Bicameral engine with tier-gated hemisphere execution |
| EdgeRules gating | Done | Skip right hemisphere, return left-only |
| LocalLlamaCpp gating | Done | Fast 1-round debate |
| LocalSmall+ gating | Done | Full debate (configurable max rounds) |
| Sensitive data gating | Done | Local-only, no cloud routing |
| `TierHandlerRegistry` | Done | Registers TierHandlers for each tier from TriModelManager + EdgeRuleEngine |
| 23 unit tests | Done | Gate decisions, router gate classification, gated engine reasoning, registry |

---

## N10: OrtEmbedder Wired into Memory Recall — COMPLETE

**Date**: August 4, 2026
**Tests**: 1,800 total (+20), 0 clippy warnings.

### New module: `crates/wm-memory/src/recall.rs` (~770 lines)

| Deliverable | Status | Notes |
|---|---|---|
| `RecallResult` struct | Done | memory_id, galaxy, fused score, BM25 score, vector score, importance, content |
| `RecallConfig` | Done | BM25/vector/importance weights (0.5/0.3/0.2), env var parsing, weight normalization check |
| `RecallEngine` | Done | Hybrid search combining Tantivy BM25 + vector cosine similarity |
| Auto-embed at write time | Done | `store_with_embedding()` embeds content, stores memory + embedding, adds to vector store |
| Embedding cache | Done | Hash-based cache with LRU eviction (max 1000 entries) |
| Hybrid search | Done | `hybrid_search()` fuses BM25 + vector + importance with configurable weights |
| Pure vector search | Done | `vector_search()` — vector-only, no BM25 |
| Pure text search | Done | `text_search()` — BM25-only, no vector |
| Score fusion | Done | `fuse_results_inner()` — extracted for testability, normalizes BM25, fuses with weights |
| 20 unit tests | Done | Config, fusion logic, BM25-only, vector-only, both sources, sorting, truncation, normalization, cache, weights |
| Tantivy indexing | Done | IndexWriter wired into `store_with_embedding()` — documents indexed at write time, reader reloaded |
| 8 integration tests | Done | End-to-end `store_with_embedding` → `hybrid_search` round-trip, galaxy filter, cache, ranking |

---

## N5: Conversational Memory Search — COMPLETE

**Date**: August 4, 2026
**Tests**: 1,870 total (+21 from N5, +70 from N1-N3+N9+N10+Pre-N batches), 0 clippy warnings.

### New module: `crates/wm-memory/src/conversational.rs` (~800 lines)

| Deliverable | Status | Notes |
|---|---|---|
| `QueryClassification` | Done | Sensitivity detection, tool-call intent, multi-turn patterns, complexity score |
| `ConversationalConfig` | Done | Cache size, snippet length, default limit — env-configured |
| `ConversationalSearch` | Done | Wraps `RecallEngine` with LRU cache, classification, snippet extraction |
| LRU query cache | Done | Configurable size (default 128), eviction on capacity, cache hit/miss tracking |
| `SearchMetrics` | Done | Total queries, cache hits/misses, hit rate, avg/min/max latency, sub-50ms target check |
| `ConversationalResult` | Done | memory_id, galaxy, score, snippet, from_cache flag, latency_us |
| Snippet extraction | Done | Truncated content (default 200 chars) for UI display |
| `memory.chat` MCP tool | Done | Registered in `register_all`, NLU profile, `extract_payload` for conversational phrases |
| 21 unit tests | Done | Classification, caching, LRU eviction, snippet truncation, galaxy filtering, delegation, metrics |

### Integration
- `ConversationalSearch` constructed in `McpServer::with_defaults` using `RecallEngine` + `Embedder`
- `memory.chat` tool registered with `Gana::WinnowingBasket`, read-only `EffectRow`
- NLU profile in `nlu.rs` with keywords: chat, conversational, converse, talk, ask, discuss, explore, browse, hybrid
- `extract_payload` handles prefixes: "chat about", "ask about", "discuss", "explore", "converse about", plus fallback

### Environment Variables
| Variable | Default | Description |
|---|---|---|
| `WM_CONVERSATIONAL_CACHE_SIZE` | `128` | Max cached queries |
| `WM_CONVERSATIONAL_SNIPPET_LEN` | `200` | Max snippet length (chars) |
| `WM_CONVERSATIONAL_DEFAULT_LIMIT` | `10` | Default result limit |

---

## N4: Speculative Decoding — COMPLETE

**Date**: August 4, 2026
**Tests**: 1,905 total (+35 from N4), 0 clippy warnings.

### New module: `crates/wm-bicameral/src/speculative.rs` (~600 lines)

| Deliverable | Status | Notes |
|---|---|---|
| `SpeculativeConfig` | Done | Draft K, accept/verify thresholds, env-configured |
| `SpeculativeDecoder` | Done | Draft + verify handler pipeline, segment-level speculative decoding |
| `SpeculativeHandler` | Done | TierHandler impl for router integration |
| `SpeculativeStats` | Done | Total calls, draft/verify accepted/rejected, latency, token acceptance, estimated speedup |
| `SpeculativeResult` | Done | Output, confidence, method, draft_accepted, verified, latency, token counts |
| `speculative.decode` MCP tool | Done | Registered in `register_bicameral`, Gana::ThreeStars, read-only EffectRow |
| `speculative.stats` MCP tool | Done | Stats snapshot: acceptance rate, latency, speedup estimate |
| NLU profiles | Done | Keywords: speculative, decode, draft, verify, accelerate, speedup |
| `extract_payload` | Done | Prefixes: "speculative decode", "speculative", "decode", "draft and verify", "accelerate inference" |
| 35 unit tests | Done | Config, draft accepted, verify invoked, merged, fallback, stats, handler, similarity, merge, boundary tests |

### Integration
- `SpeculativeDecoder` wraps two `TierHandler` implementations (draft + verify)
- Draft handler: autonomic model (BitMamba) via `TriModelHandler`
- Verify handler: left model (llama.cpp) via `TriModelHandler`
- `SpeculativeHandler` implements `TierHandler` for transparent router integration
- `register_bicameral` accepts optional `Arc<SpeculativeDecoder>` for N4 tools

### Architecture
- Segment-level speculative decoding (adapted from token-level for v4's API)
- Draft generates full response → if confidence >= threshold, accept directly
- Otherwise verify model generates → similarity check decides draft_verified vs verify_only
- Both low confidence → merge outputs preserving unique draft information
- Fallback: draft failure → verify-only; both failure → error result

### Benchmarks
- `speculative_decode_draft_accepted`: ~312ns (draft only, no verify)
- `speculative_decode_with_verify`: ~2.13µs (draft + verify + similarity)
- `speculative_stats`: ~18ns (stats snapshot)

### Environment Variables
| Variable | Default | Description |
|---|---|---|
| `WM_SPEC_DRAFT_K` | `4` | Number of draft candidates |
| `WM_SPEC_DRAFT_THRESHOLD` | `0.85` | Min draft confidence to skip verify |
| `WM_SPEC_VERIFY_THRESHOLD` | `0.5` | Min verify confidence |
| `WM_SPEC_ENABLED` | `1` | Enable speculative decoding |
| `WM_SPEC_DRAFT_TIMEOUT_MS` | `500` | Draft model timeout (ms) |

---

## N6: LLM Meta-Harness — Cognitive Enhancement for Local LLMs — COMPLETE

### New module: `crates/wm-bicameral/src/meta_harness.rs` (~1,360 lines)

Cognitive enhancement strategies for local LLM calls:
- **5 EnhancementModes**: Direct, MemoryGrounded (RAG), SelfCorrecting (critique+revise), Ensemble (multi-sample voting), FullStack (all strategies)
- **MetaHarness** with pluggable memory + inference provider traits
- Heuristic critique (hedging detection, confidence estimation)
- Ensemble voting with consensus selection
- Self-correction with up to 3 revision rounds
- **HarnessStats** tracking per-mode usage, latency, confidence lift

### MCP Tools
- `meta.enhance` — Run enhanced inference with selected mode
- `meta.stats` — Show harness usage statistics

### Integration
- `register_bicameral` updated to accept `Option<Arc<MetaHarness>>`
- NLU profiles added for `meta.enhance` and `meta.stats`
- `extract_payload` support for `meta.enhance`

### Tests: 30 unit tests covering all modes, stats, config, edge cases

---

## N7: Dense Context Encoding — CJK Token Compression — COMPLETE

### New module: `crates/wm-bicameral/src/dense_encoding.rs` (~1,040 lines)

Compresses English text into CJK character representation for 2-3x token reduction:
- **DenseEncoder** with 50+ phrase mappings (English → CJK)
- Word-boundary aware replacement (no substring corruption)
- **Decode hint** prefix for self-documenting compressed text
- **Compression ratio** estimation using BPE-aware token counting
- Configurable via environment variables

### MCP Tools
- `dense.encode` — Compress text using CJK mapping
- `dense.decode` — Restore compressed text to approximate English

### Integration
- `register_bicameral` updated to accept `Option<Arc<DenseEncoder>>`
- NLU profiles added for `dense.encode` and `dense.decode`
- `extract_payload` support for `dense.encode`

### Environment Variables
| Variable | Default | Description |
|---|---|---|
| `WM_DENSE_ENCODING` | `0` | Enable dense encoding |
| `WM_DENSE_MIN_LENGTH` | `50` | Minimum text length to encode |

### Tests: 20 unit tests covering encoding, decoding, compression ratio, config, edge cases

---

## N11: Background Citta + Dream Cycle Activation — COMPLETE

### Goal: Activate the consciousness substrate that's built but dormant

The consciousness substrate was already fully implemented and wired:
- **CittaHeartbeat**: Fires on every tool dispatch (post-dispatch hook in server.rs)
  - Updates 16-dimension citta vector based on success/failure
  - Tracks smarana (memory retention), presence, apotheosis
  - Karma feedback loop (sattvic/tamasic)
- **DreamCycle**: 12-phase memory consolidation triggered on Theta brain-wave
  - Triage, Consolidation, Serendipity, Governance, Narrative, Kaizen, Oracle, Decay, Constellation, Prediction, Enrichment, Harmonize
  - Automatic trigger in `run_async` event loop on brain-wave transition
  - Manual trigger via `dream.trigger` MCP tool
- **SpiralTracker**: Records autonomous cycle outputs, computes novelty scores
  - Outward/Stable/Inward spiral direction
  - Auto-suspension after 3 identical consecutive outputs
- **EcoModeController**: Brain-wave state machine driving subsystem flags
  - Gamma → Beta → Alpha → Theta → Delta transitions
  - Drive decay on brain-wave transitions

### MCP Tools (already registered, NLU profiles added)
- `citta.status` — Citta vector, coherence, heartbeats
- `citta.reflect` — Self-reflection on recent interactions
- `citta.history` — Consciousness timeline
- `dream.status` — Dream cycle state and last result
- `dream.trigger` — Manually trigger a dream cycle
- `dream.analyze` — Analyze dream cycle results
- `smarana.status` — Memory retention metrics
- `smarana.trace` — Memory recall/miss trace
- `apotheosis.check` — Self-actualization score and trend
- `consciousness.depth` — Depth gauge reading
- `spiral.report` — Spiral direction and novelty report
- `consolidation.connect/compress` — Autonomous memory consolidation
- `emergence.scan` — Tag/topic emergence detection
- `retention.prune` — Mindful forgetting proposals

### NLU Profiles
- Added `extract_payload` support for `dream.trigger`
- All consciousness tools already had NLU profiles in the existing profile set

---

## N8: Hardware-Aware Inference Tuning — COMPLETE

**Date**: August 4, 2026
**Tests**: 1,948 total (+43), 0 clippy warnings.

### New module: `crates/wm-bicameral/src/inference_tuner.rs` (~1,100 lines)

| Deliverable | Status | Notes |
|---|---|---|
| `HardwareProfile` | Done | CPU model, cores, RAM, SIMD from /proc/cpuinfo + /proc/meminfo |
| `TunedConfig` | Done | n_ctx, n_threads, cache_type, parallel, spec_method, flash_attn, idle_timeout |
| `InferenceTuner` | Done | Cache persistence, recommend_config() maps hardware→config (constrained/standard/high-end) |
| `profile_to_governor_mode()` | Done | Integration with ResourceGovernor |
| `apply_to_llama_config()` | Done | Preserves endpoint/model, overrides tunable params |
| `WM_AUTO_TUNE=1` env var | Done | Triggers auto-tuning at startup |
| 43 unit tests | Done | Hardware detection, config recommendation, cache, governor integration, llama config override |

---

## N12: Idle-to-Default-Mode — Theta Dreaming — COMPLETE

**Date**: August 5, 2026
**Tests**: 1,968 total (+20), 0 clippy warnings.

### Changes to: `crates/wm-bicameral/src/tri_model.rs` (+~400 lines)

| Deliverable | Status | Notes |
|---|---|---|
| `ModelState::Dreaming` | Done | New state between Running and Stopped |
| `IdleMode` enum | Done | Shutdown (old behavior) or Dream (new default) |
| Two-tier `check_idle` | Done | Running → Dreaming (idle_timeout) → Stopped (deep_idle_timeout) |
| Warm wake | Done | `ensure_running()` snaps from Dreaming → Running instantly |
| 3 new lifecycle events | Done | DreamStarted, DreamEnded, WarmWake |
| Env vars | Done | `WM_LLAMA_FG_IDLE_MODE` (dream/shutdown), `WM_LLAMA_FG_DEEP_IDLE_TIMEOUT` (default 1800s) |
| 20 new tests | Done | Dreaming state transitions, warm wake, lifecycle events, idle mode config |

---

## N13: Sensorimotor Weave — C-ABI Hardware I/O Framework — COMPLETE

**Date**: August 5, 2026
**Tests**: 1,995 total (+27), 0 clippy warnings.

### New module: `crates/wm-substrate/src/sensorimotor.rs` (~750 lines)

| Deliverable | Status | Notes |
|---|---|---|
| `SensorDevice` trait | Done | read() → SensorFrame, zero-copy target, device metadata |
| `ActuatorDevice` trait | Done | send_command() → Result, safety validation, device metadata |
| `SensorimotorBus` | Done | Registry of sensors + actuators, dispatch routing, health check |
| `ReflexLoop` | Done | Sensor → reflex → actuator pipeline with cooldown, trigger threshold |
| `StubSensor` / `StubActuator` | Done | Test fixtures for headless development |
| `SensorFrame` / `ActuatorCommand` | Done | Stack-allocated frame types (f64 arrays, timestamps) |
| 27 unit tests | Done | Bus registration, sensor read, actuator dispatch, reflex loop, cooldown, health check, stub devices |

**Research basis**: copper-rs (sub-microsecond Rust robotics), dora-rs (dataflow IPC), v1's `embodiment.py`/`physical_metrics.py`. Framework designed for C-ABI FFI under `hardware` feature gate.

---

## N14: Cerebellar Forward Model — Timing & Error Correction — COMPLETE

**Date**: August 5, 2026
**Tests**: 2,015 total (+20), 0 clippy warnings.

### New module: `crates/wm-consciousness/src/cerebellum.rs` (~640 lines)

| Deliverable | Status | Notes |
|---|---|---|
| `LinearForwardModel` | Done | A·state + B·command + bias, predict(), train() with MSE error |
| `PredictionError` | Done | Expected vs actual, squared error, magnitude |
| `CerebellarController` | Done | Forward model + error history + sensory attenuation |
| `MotorTiming` | Done | Sequenced command scheduling with temporal calibration |
| `CerebellumConfig` | Done | Learning rate, history size, attenuation factor |
| 20 unit tests | Done | Forward model predict/train, controller, motor timing, error correction, sensory attenuation |

**Research basis**: Wolpert & Miall (1996) forward model theory, Nguyen et al. (2025) cerebellar circuit computations, Frontiers forward model unifying theory.

---

## N15: Limbic Deep Integration — Unified Emotional State — COMPLETE

**Date**: August 5, 2026
**Tests**: 2,064 total (+35), 0 clippy warnings.

### New module: `crates/wm-consciousness/src/limbic.rs` (~820 lines)

| Deliverable | Status | Notes |
|---|---|---|
| 8 `EmotionalValence` types | Done | Joy, Fear, Anger, Sadness, Curiosity, Satisfaction, Frustration, Compassion |
| `LimbicState` | Done | Valence vector with decay + opponent processing, total events, composite affect |
| `Neuromodulation` | Done | 6 cognitive parameters: exploration_rate, attention_focus, learning_sensitivity, risk_threshold, creativity_boost, social_weighting |
| `LimbicSystem` | Done | Event processing, history (VecDeque), neuromodulation computation, summary |
| `EmotionalEvent` | Done | Valence, intensity, source, description, timestamp |
| 35 unit tests | Done | Valence decay, opponent processing, neuromodulation, event processing, history, summary, edge cases |

**Research basis**: Limbic Co-Processor model (Zenodo 2025), Damasio's somatic markers, v1's `emotional_steering.py`/`emotional_memory.py`/`narrative_emotions.py`.

---

## N12-N15 Biological Alignment Cluster — Summary

All 4 biological alignment phases complete. Key achievements:
- **N12**: Models dream instead of shutting down — warm wake in ~2s vs cold restart ~10s
- **N13**: Framework for robotic embodiment via C-ABI sensor/actuator traits
- **N14**: Cerebellar forward model for predictive motor control with adaptive learning
- **N15**: Unified emotional state with neuromodulation of 6 cognitive parameters

**v1/v2 systems ported**: `embodiment.py` → N13, `emotional_steering.py` → N15, `emotional_memory.py` → N15, `physical_metrics.py` → N13, `homeostatic_loop.py` → N14, `unified_nervous_system.py` → N14/N15 integration patterns.

**All frameworks are expandable**: N13's traits can wrap real hardware, N14's linear model can be replaced with neural networks, N15's valence set can be extended. All testable on any machine via stubs.

---

## Integration Wiring: N16–N21 → MCP Server & Dispatch Pipeline — COMPLETE

**Date**: August 5, 2026
**Tests**: 2,343 total (+24 new tool tests), 0 clippy warnings.

### New MCP Tools (13 tools, 24 tests)

| Tool | Gana | Crate | Description |
|---|---|---|---|
| `bus.stats` | Heart | wm-resonance | Gan Ying Bus statistics |
| `bus.emit` | Heart | wm-resonance | Emit event to Gan Ying Bus |
| `bus.recent` | Heart | wm-resonance | Recent events from Gan Ying Bus |
| `sangha.peers` | Room | wm-sangha | List discovered peers |
| `sangha.discover` | Room | wm-sangha | Discover peers with capability filter |
| `sangha.signal` | Room | wm-sangha | Broadcast signal to peers |
| `sangha.chat` | Room | wm-sangha | Send/read chat messages |
| `sangha.locks` | Room | wm-sangha | Resource lock management |
| `sim.mc` | Mound | wm-simulation | Monte Carlo simulation |
| `sim.forecast` | Mound | wm-simulation | Time series forecasting |
| `sim.counterfactual` | Mound | wm-simulation | Counterfactual estimation |

### MCP Server State (`wm-mcp/src/server.rs`)

- Added `GanYingBus`, `PeerDiscovery`, `SignalBroadcast`, `SanghaChat`, `ResourceLockManager`, `HomeostaticLoop`, `AnomalyDetector` to `McpServer` struct
- All initialized in `with_defaults()`, `with_default_eco()`, and `test_server()`

### Cross-Subsystem Event Flows

1. **Gan Ying Bus dispatch integration**: Emits `ToolDispatchStart` before `pipeline.dispatch()`, `ToolDispatchSuccess` or `ToolDispatchError` after dispatch result
2. **Homeostatic Loop integration**: After timescale tick — samples substrate, runs `AnomalyDetector::check()`, runs `HomeostaticLoop::sample_cycle()`, emits `HarmonyStressDetected` events to Gan Ying Bus for any corrective actions

### Homeostasis Tools Updated (`wm-tools/src/expansion/homeostasis.rs`)

- `HomeostasisCheckTool` now accepts `HomeostaticLoop` + `AnomalyDetector`, runs `sample_cycle()` on each call, returns `homeostatic_actions` and `anomaly_alerts` in JSON output
- `HomeostasisAlertsTool` now accepts `AnomalyDetector`, includes z-score based anomaly alerts alongside threshold-based alerts
- `register_expansion` updated to pass `HomeostaticLoop` and `AnomalyDetector` through to tools

### Bug Fix

- Fixed flaky `wm-drive` `cross_pollination::tests::resonance_log_records_cascades` test: `energy: 0.8` triggered Energy cascade (threshold 0.8) alongside Curiosity cascade, causing non-deterministic `HashMap` iteration order. Fixed by setting `energy: 0.5` so only Curiosity cascade fires.

**Final metrics**: 2,359 tests + 9 doctests, 153 tools, ~92,500 LOC, 19 crates, 0 clippy warnings.

---

## E2E Integration Tests + Graceful Shutdown — COMPLETE

**Date**: August 4, 2026
**Tests**: 2,359 total (+16 over integration wiring), 0 clippy warnings.

### E2E Integration Tests (9 new, in `crates/wm-mcp/src/server.rs` test module)

| Test | What it verifies |
|---|---|
| `e2e_full_session_lifecycle` | initialize → tools/list → tools/call → memory persistence |
| `e2e_gan_ying_bus_records_dispatch_events` | ToolDispatchStart/Success events emitted on every dispatch |
| `e2e_error_recovery_after_malformed_json` | Server survives malformed JSON-RPC and keeps serving |
| `e2e_unknown_tool_then_valid_tool` | Error on unknown tool, then successful dispatch |
| `e2e_shutdown_emits_system_shutdown_event` | Graceful shutdown emits SystemShutdown to Gan Ying Bus |
| `e2e_homeostasis_tools_share_state_with_server` | Homeostasis tools and server share HomeostaticLoop + AnomalyDetector state; mutex not poisoned after dispatch |
| `e2e_multiple_sequential_dispatches` | Repeated dispatches remain consistent |
| `e2e_brain_wave_transitions_through_activity` | Brain-wave state advances with event activity |
| `e2e_tool_count_matches_registry` | Registry tool count floor (>= 100) guard |

### Graceful Shutdown

- `McpServer::shutdown()`: emits `SystemShutdown` event to Gan Ying Bus, runs final timescale tick to flush pending hooks, LMDB flushes via Drop
- Called at the end of the `run_async()` event loop (stdin EOF — the standard MCP stdio shutdown signal)

### Verified Benchmarks (criterion, release build)

| Metric | Value |
|---|---|
| Pipeline overhead | ~477 ns/call |
| Reflex dispatch (8 builtins) | ~233 ns |
| Reflex safety check (bitmask) | ~1.2 ns |
| Registry lookup / enumerate | ~37 ns / ~28 ns |
| Full server startup (153 tools) | ~37.7 ms |
| Stub embedding | ~1.33 µs |

---

## Production Hardening + Version Control — COMPLETE

**Date**: August 4, 2026
**Tests**: 2,365 + 9 doctests (+6 over E2E session: 3 bus persistence, 2 substrate platform, 1 E2E persistence), 0 clippy warnings, fmt clean on stable rustfmt.

### Git

- `git init` + initial commit; `.gitignore` fixed (Cargo.lock now tracked for reproducible binary builds; `.whitemagic/` data store ignored)
- All work committed; remote push complete (lbailey94/whitemagic-core, private)

### SIGTERM/SIGINT Graceful Shutdown (verified live)

- `run_async` selects on a pinned shutdown-signal future (SIGINT all platforms, SIGTERM on unix) alongside stdin and the brain-wave timer
- Signal → break → existing graceful shutdown (`SystemShutdown` bus event, final timescale tick, LMDB flush)
- **Bug found + fixed**: runtime drop hung on tokio's parked stdin blocking read after a signal exit; `rt.shutdown_timeout(500ms)` in `wm serve` bounds it
- Live verification: SIGTERM → `system_shutdown` event persisted → exit code 0 (v2 required SIGKILL)

### Gan Ying Bus Persistence

- `GanYingBus::enable_persistence(path)`: JSONL write-through on every event, ring buffer seeded from log tail on restart, 5 MiB log cap
- Wired in `with_defaults` → `<store>/resonance_events.jsonl`; verified live (26 events logged during tool exercise, shutdown event included)

### Non-Linux Degradation

- `SubstrateMonitor::sensors_available` flag (checks `/proc/loadavg` on Linux); startup warning when homeostasis runs in degraded neutral mode
- Principle: "unavailable" must never silently look like "healthy"

### CI Fix

- `rustfmt.toml` nightly-only options (`imports_granularity`, `group_imports`) removed; tree normalized with stable `cargo fmt --all` — CI fmt job now passes

### Live Tool Exercise (2026-08-04)

- Core catalog via running MCP server: memory CRUD + BM25 search round-trip, session lifecycle, citta, karma, dharma, homeostasis (real sensors: 90°C thermal critical correctly flagged), harmony, galaxy stats, agents, bicameral debate (3 rounds), drive bias, reflex status, workspace stats
- N16–N21 tools via fresh release binary: bus.stats/emit/recent, sangha.peers/discover/signal/chat/locks, sim.mc/forecast/counterfactual, homeostasis.check/alerts with `homeostatic_actions` + `anomaly_alerts`
- Note: the IDE-connected server process was started before the N16–N21 registration landed; restart the MCP server to pick up the current binary (153 tools)

### Strategy Update

- `STRATEGY.md` gains "Post-N Strategy: Foundation First" — depth over breadth, red-team the foundation, dogfood daily, honest degradation everywhere, no new subsystems until current ones survive reality
- **V2 Takedown**: `lbailey94/whitemagic-core` GitHub repo archived (2026-08-04). `lbailey94/whitemagic` GitHub repo archived (2026-08-05). PyPI releases yanked (12 total: 11 `whitemagic` + 1 `whitemagic-core`). Website `www.whitemagic.dev` replacement deferred (Vercel project needs framework settings update). See `STRATEGY.md` § V2 Takedown for full inventory.
- **Strategy sharpening** (adopted 2026-08-04):
  1. v2 as threat model — v2's failure modes (circular thinking, memory bloat, 110% idle CPU, silent fail-open) are the red-team test suite
  2. Distribution replacement — v4 replaces v2 on PyPI, GitHub, and the website; v2 public surfaces yanked for safety
  3. Migration quality gate — v2→v4 data migration is a release blocker (59,831 memories, tool ready with 45 tests, dry run verified)
  4. Both subsystems in parallel — Embodiment I/O (sensorimotor, completes CyberBrain) + Sangha Mesh transport (network, completes N17); Leo-Aquarius axis, intentionally parallel

---

## Security Hardening (D1, D4, D5, D6) — COMPLETE

**Date**: August 5, 2026
**Tests**: 2,547 + 9 doctests (up from 2,365 + 9), 0 clippy warnings, fmt clean.
**LOC**: ~100,000 across 19 crates.

Four security deliverables implementing defense-in-depth for the MCP protocol layer,
tool supply chain, input validation, and runtime policy governance.

### D1: MCP Input Validation Layer

**New module**: `crates/wm-mcp/src/input_validation.rs` (~390 lines)

| Deliverable | Status | Notes |
|---|---|---|
| `validate_request()` | Done | JSON-RPC 2.0 structure validation: jsonrpc version, method field, id type, params type |
| `validate_tool_call_params()` | Done | Tool name validation, string length limits (32KB), injection pattern detection in string params |
| `validate_tools_call()` | Done | Combined request + params validation for `tools/call` method |
| SSRF prevention in params | Done | URL-bearing params (key contains "url"/"endpoint"/"uri") checked via `is_url_safe()` |
| Path traversal prevention in params | Done | Path-bearing params (key contains "path"/"file"/"filename") checked via `is_path_safe()` |
| `ValidationResult` enum | Done | Valid / Invalid(reason) with `to_error_response()` for JSON-RPC error formatting |
| Size limits | Done | MAX_PARAMS_SIZE (64KB), MAX_STRING_LEN (32KB) |
| 14 unit tests | Done | Valid/invalid requests, missing fields, wrong types, oversized params, injection, SSRF, traversal |

**OWASP mapping**: LLM05 (Improper Output Handling / SSRF), LLM01 (Prompt Injection)

### D4: Tool Capability Attestation

**New module**: `crates/wm-core/src/attestation.rs` (~675 lines)

| Deliverable | Status | Notes |
|---|---|---|
| `ToolManifest` struct | Done | Tool name, version, publisher, description, effects, capabilities, trust level, human review flag, timestamp, HMAC signature |
| `EffectSummary` | Done | Compact effects representation (reads, writes, spawns) with `from_effect_row()` and `has_destructive_effects()` |
| HMAC-SHA256 signing | Done | `sign(key)` computes signature over all fields except signature itself; `verify(key)` checks integrity |
| `ToolAttestationRegistry` | Done | Registry of signed manifests keyed by tool name, with signing key and trust scope |
| Trust scope controls | Done | `TrustScope` enum (Trusted/Internal/External) restricts which tools external MCP servers can invoke |
| Provenance verification | Done | `register_signed()` verifies signature before accepting; `verify_provenance()` checks tamper resistance |
| Capability checking | Done | `has_capability()`, `requires_human_review()`, `is_destructive()` queries on manifests |
| 30+ unit tests | Done | Manifest creation, signing, verification, tamper detection, trust scope, registry operations, capability checks |

**Supply chain security**: Each tool declares its capabilities and effects in a signed manifest. External tools must be registered with verified provenance before invocation. Trust scopes prevent untrusted tools from accessing destructive capabilities.

### D5: Security Validation Utilities

**New module**: `crates/wm-core/src/security.rs` (~430 lines)

| Deliverable | Status | Notes |
|---|---|---|
| `is_url_safe()` | Done | SSRF prevention — blocks non-HTTP schemes, private IP ranges, loopback, link-local, metadata endpoints |
| `is_private_ip()` | Done | IPv4/IPv6 private range detection (const fn) |
| `is_path_safe()` | Done | Path traversal prevention — blocks `..`, null bytes, URL-encoded traversal (`%2e`, `%2f`, `%5c`) |
| `sanitize_path()` | Done | Removes dangerous sequences from file paths |
| `is_path_within_base()` | Done | Secondary check: verifies resolved path stays within base directory |
| `is_description_safe()` | Done | Prompt injection detection in tool descriptions (21 injection patterns) |
| `sanitize_description()` | Done | Replaces injection patterns with `[FILTERED]`, truncates to 4096 chars |
| `is_tool_name_valid()` | Done | Alphanumeric + dots/hyphens/underscores, max 128 chars |
| 16 unit tests | Done | SSRF (safe URLs, blocked schemes, localhost, private ranges, IPv6, metadata endpoints), path traversal (safe paths, parent traversal, null bytes, encoded traversal, sanitization, base containment), description sanitization (safe/unsafe, filtering, truncation), tool name validation |

**OWASP mapping**: LLM05 (SSRF), LLM01 (Prompt Injection via tool descriptions)

### D6: Policy Engine Updates

**Updated module**: `crates/wm-governance/src/policy.rs`

| Deliverable | Status | Notes |
|---|---|---|
| `PolicyEngine` struct | Done | Thread-safe wrapper (`RwLock<DharmaPolicy>`) for runtime-updatable Dharma policy |
| `update()` method | Done | Hot-swap policy at runtime without server restart |
| `update_from_json()` | Done | Update policy from JSON string (for remote management) |
| `check_resource_access()` | Done | Verify tool effects against policy: read-only allowed in all states, destructive blocked below maturity threshold, fabrication blocked in low brain-wave states |
| `policy()` accessor | Done | Read current policy state |
| `Default` impl | Done | Standard Dharma policy defaults (ahimsa enabled, satya enabled, maturity=3, etc.) |
| Test coverage | Done | Policy update, JSON update, resource access (read/destructive/fabrication), all brain-wave states |

**Governance enhancement**: PolicyEngine enables runtime governance updates without server restart. Resource access checks enforce brain-wave-aware permissions — destructive operations are blocked in low-maturity states (Delta/Theta), and fabrication (writing to galaxies the tool didn't read from) is blocked in low brain-wave states.

### Per-Crate Test Counts (2,547 + 9 doctests total)

| Crate | Tests | Change |
|---|---|---|
| wm-core | 131 | +41 (security + attestation) |
| wm-memory | 259 | — |
| wm-dispatch | 83 | — |
| wm-consciousness | 373 | — |
| wm-tools | 414 | — |
| wm-governance | 80 | +37 (policy engine + red-team) |
| wm-substrate | 118 | — |
| wm-mcp | 71 | +57 (input validation + RSI + E2E) |
| wm-polyglot | 51 | — |
| wm-reflex | 48 | — |
| wm-timescale | 34 | — |
| wm-workspace | 51 | — |
| wm-selfmodel | 73 | — |
| wm-bicameral | 490 | — |
| wm-drive | 50 | — |
| wm-autonomic | 22 | — |
| wm-resonance | 61 | — |
| wm-sangha | 93 | — |
| wm-simulation | 45 | — |
| **Total** | **2,547 + 9 doctests** | +182 since last report |

---

## RSI: Recursive Self-Improvement Phases 1–3 — COMPLETE

**Date**: August 5, 2026
**Tests**: 2,547 total, 0 clippy warnings.
**Tools**: 158 (153 + 5 RSI)

### Phase 1: Usage-Driven Improvement

**New module**: `crates/wm-tools/src/expansion/rsi.rs`

- `friction.log` tool — Creates structured friction memories in Codex galaxy with tags `rsi:friction`, `rsi:severity:*`, `rsi:category:*`, `rsi:tool:*`
- `friction.review` tool — Queries and summarizes friction entries with category/severity filters
- `friction.auto_log` tool — Programmatic API for auto-logging `ToolDispatchError` events
- Auto-logging wired into `McpServer::handle_tool_call` — dispatch errors automatically create friction entries

### Phase 2: Codebase-Grounded Improvement

- `CycleType::Improve` added to autonomous cycle enum (now 6 cycles total)
- `ImprovementProposal` struct: Groups friction entries by (category, target), generates concrete recommendations
- `improve.scan` cycle: Scans Codex for `rsi:friction` entries, groups by pattern (2+ entries), proposes actions
- `improve.proposals` MCP tool: Triggers improve.scan cycle on demand
- Anti-circular: Signature includes target + category + pattern_count for SpiralTracker

### Phase 3: Adversarial Self-Testing

- `CycleType::Redteam` added to autonomous cycle enum
- `RedteamProposal` struct: Adversarial test proposals with attack vectors, pseudocode, risk levels
- `redteam.scan` cycle: Static catalog of 10 attack vectors across governance, karma, mandala, dispatch, spiral, memory
- `redteam.proposals` MCP tool: Triggers redteam.scan cycle on demand
- Prioritizes uncovered vectors and systems mentioned in friction entries
- Anti-circular: Signature includes target_system + attack_vector for SpiralTracker

### MCP Server Wiring

- `FrictionAutoLogTool` integrated into `McpServer` struct
- Auto-logs on dispatch errors in `handle_tool_call`
- All 3 constructors updated: `with_default_eco`, `with_defaults`, `test_server`
- MCP config updated: `/home/lucas/.codeium/windsurf/mcp_config.json` now uses v4 `wm serve`

### Autonomous Cycle Types (7 total)

1. **Connect** — Propose typed associations for disconnected memories
2. **Compress** — Propose merging semantically overlapping memory pairs
3. **Emergence** — Detect tag/topic emergence patterns across galaxies
4. **Prune** — Identify memories ready for forgetting
5. **Improve** — Scan friction entries, propose codebase improvements (RSI Phase 2)
6. **Redteam** — Adversarial self-testing with attack vector catalog (RSI Phase 3)
7. **Sensorimotor** — Poll sensors, evaluate reflexes, execute actuator commands (Embodiment I/O)

### Security Hardening — All 33 Attack Surfaces Tested

All 33 manifest attack surfaces across 18 crates are now marked `tested = true`. 13 previously untested surfaces were hardened with validation, error handling, and regression tests:

| Crate | Surface | Defense |
|-------|---------|---------|
| wm-memory | recall weight manipulation | Env var weights clamped to [0,1], NaN/Infinity rejected, auto-normalization |
| wm-consciousness | dream unbounded generation | PatternDreamBridge queue capped at 1024 (DoS prevention) |
| wm-polyglot | julia FFI null pointer | Empty/oversized input validation, path traversal rejection |
| wm-substrate | harmony vector manipulation | HarmonyVector::sanitized() clamps NaN/Infinity, rejects impossible temps |
| wm-dispatch | registry duplicate registration | Warning logged on duplicate tool name (shadowing detection) |
| wm-mcp | server malformed JSON-RPC | Tests for empty, null, missing-method inputs |
| wm-reflex | rule injection | Warning logged on re-registration at occupied slot |
| wm-workspace | unauthorized access | Salience::sanitized() handles NaN/Infinity in score components |
| wm-bicameral | LLM/BitNet/TriModel endpoint injection | Endpoint URL validation — only http:// and https:// accepted |
| wm-drive | drive manipulation | Already clamped to [0,1] — verified with existing test |
| wm-autonomic | salience signal poisoning | Token input validation — empty and >10K token arrays rejected |
| wm-sangha | chat message injection | Content sanitized — control chars stripped, 4096 char cap |
| wm-simulation | counterfactual parameter injection | NaN/Infinity filtered from input time series |

---

## Embodiment I/O: Real Linux Hardware Drivers — COMPLETE

**Date**: August 5, 2026
**Tests**: 2,768 + 9 doctests, 0 clippy warnings, fmt clean.
**Tools**: 169 (158 + 10 sensorimotor + 1 sensorimotor.scan)

### New Sensor Drivers (4)

| Sensor | Source | Description |
|---|---|---|
| `CpuUsageSensor` | `/proc/stat` | Aggregate CPU usage % (0–100) via idle/total delta tracking |
| `DiskUsageSensor` | `df -P` | Disk usage % for a mount point (avoids unsafe statvfs) |
| `NetworkThroughputSensor` | `/proc/net/dev` | Bytes/sec throughput per interface, auto-detects default iface |
| `CpuFreqSensor` | `/sys/devices/system/cpu/cpuN/cpufreq/` | Per-core CPU frequency in MHz |

### New Actuator Backend (1)

| Actuator | Target | Description |
|---|---|---|
| `SysfsActuator` | `/sys` files | Writes scaled values to sysfs (fan PWM, LED brightness). Supports `scale` multiplier, `e_stop()` writes 0 |

### Actuator Discovery (2 functions)

- `discover_fan_actuators()` — scans hwmon0–7, pwm1–4
- `discover_led_actuators()` — scans 9 common LED names (capslock, numlock, power, charging, etc.)

### Enhanced `linux_hardware_bus()`

Now registers all discovered sensors (thermal, battery, loadavg, mem_pressure, CPU usage, network, disk, CPU freq ×16) and all discovered actuators (fan PWMs, LEDs).

### Files Modified

- `crates/wm-substrate/src/sensorimotor.rs` — 4 new sensors, 1 new actuator, 2 discovery functions, enhanced `linux_hardware_bus()`, 21 new tests
- `crates/wm-substrate/Cargo.toml` — added `tempfile` dev-dependency

### Per-Crate Test Count Changes

| Crate | Before | After | Change |
|---|---|---|---|
| wm-substrate | 118 | 163 | +45 (new sensors/actuators + redteam hardening from prior session) |

---

## Autonomous Sensorimotor Cycle — COMPLETE

**Date**: August 5, 2026
**Tests**: 2,768 + 9 doctests, 0 clippy warnings, fmt clean.
**Tools**: 169 (158 + 10 sensorimotor + 1 sensorimotor.scan)
**Autonomous Cycles**: 7 (was 6)

### `CycleType::Sensorimotor`

New autonomous cycle type that polls sensors, evaluates reflex rules, executes actuator commands, and generates `SensorimotorProposal` records.

| Component | Description |
|---|---|
| `CycleType::Sensorimotor` | 7th autonomous cycle variant, `requires_human_review() = false` |
| `CycleContext::with_sensorimotor()` | Builder method to attach `SensorimotorBus` + `ReflexLoop` |
| `SensorimotorProposal` | Per-sensor result: sensor_id, kind, value, reflex_triggered, actuator_id, command_value |
| `CycleResult::sensorimotor` | `Vec<SensorimotorProposal>` with serde skip-if-empty |
| `run_sensorimotor()` | Polls sensors → evaluates reflexes → sends commands → builds proposals |

### `sensorimotor.scan` MCP Tool

- Gana::Encampment, read-only effects
- Accepts optional `health_score` arg
- Creates `CycleContext` with sensorimotor attachments
- Records result in spiral tracker
- NLU profile + prefix route (`sensorimotor` → `sensorimotor.scan`)

### MCP Server Integration

- `dispatch_count: AtomicU64` field on `McpServer`
- Runs sensorimotor cycle every 10 dispatches automatically
- Emits `ReflexFired` events to Gan Ying Bus when reflexes trigger

### Autonomous Cycle Types (7 total)

1. **Connect** — Propose typed associations for disconnected memories
2. **Compress** — Propose merging semantically overlapping memory pairs
3. **Emergence** — Detect tag/topic emergence patterns across galaxies
4. **Prune** — Identify memories ready for forgetting
5. **Improve** — Scan friction entries, propose codebase improvements (RSI Phase 2)
6. **Redteam** — Adversarial self-testing with attack vector catalog (RSI Phase 3)
7. **Sensorimotor** — Poll sensors, evaluate reflexes, execute actuator commands

### Files Modified

- `crates/wm-consciousness/src/autonomous.rs` — CycleType::Sensorimotor, CycleContext extension, SensorimotorProposal, run_sensorimotor(), 5 new tests
- `crates/wm-consciousness/src/lib.rs` — export SensorimotorProposal
- `crates/wm-consciousness/Cargo.toml` — added wm-substrate dependency
- `crates/wm-tools/src/expansion/autonomous.rs` — SensorimotorScanTool
- `crates/wm-tools/src/expansion/mod.rs` — registration + exports
- `crates/wm-tools/src/nlu.rs` — NLU profile + prefix route
- `crates/wm-mcp/src/server.rs` — dispatch_count, periodic sensorimotor execution

### Per-Crate Test Count Changes

| Crate | Before | After | Change |
|---|---|---|---|
| wm-consciousness | 373 | 394 | +21 (sensorimotor cycle + redteam hardening from prior session) |
| wm-tools | 414 | 440 | +26 (sensorimotor tool + integration wiring from prior session) |
| wm-mcp | 71 | 74 | +3 (sensorimotor wiring) |

### Updated Per-Crate Test Counts (2,768 + 9 doctests total)

| Crate | Tests |
|---|---|
| wm-core | 144 |
| wm-memory | 311 |
| wm-dispatch | 86 |
| wm-consciousness | 394 |
| wm-tools | 440 |
| wm-governance | 87 |
| wm-substrate | 163 |
| wm-mcp | 74 |
| wm-polyglot | 66 |
| wm-reflex | 49 |
| wm-timescale | 37 |
| wm-workspace | 54 |
| wm-selfmodel | 79 |
| wm-bicameral | 495 |
| wm-drive | 50 |
| wm-autonomic | 31 |
| wm-resonance | 61 |
| wm-sangha | 123 (with transport feature) |
| wm-simulation | 47 |
| **Total** | **2,773 + 9 doctests** |

---

## RSI Phase 2: Outward Spiral — IN PROGRESS

**Started**: August 6, 2026. See `docs/notes/rsi-phase2-strategy-2026-08-06.md` for full strategy.

### WS-1: Rich Friction Envelope — ✅ COMPLETE

**Changes** (~200 LOC across 4 crates):
- `wm-core/src/tool.rs`: Added `Default` derive to `ToolStatsSnapshot`, re-exported from `lib.rs`
- `wm-tools/src/expansion/rsi.rs`: New `DispatchTelemetry` struct (15 fields), `log_error()` now takes `&DispatchTelemetry` and embeds telemetry as JSON in friction content, new `log_anomaly()` for successful dispatches with anomalous metrics
- `wm-mcp/src/server.rs`: Constructs `DispatchTelemetry` from dispatch path data, anomaly detection on successes (high latency, low effectiveness, high karma debt)
- `wm-consciousness/src/autonomous.rs`: `run_improve()` parses telemetry JSON from friction content, groups by 3 new dimensions (brain_wave, confidence_band, effectiveness_quartile)

**New tests**: `dispatch_telemetry_serialization_roundtrip`, `friction_auto_log_anomaly_creates_entry` (+2 tests)

**Test count**: 2,768 → 2,770 (+2)

### WS-2: Friction Deduplication — ✅ COMPLETE

**Changes** (~120 LOC across 2 crates):
- `wm-tools/src/expansion/rsi.rs`: `friction_hash()` function (deterministic hash of tool+category+severity+error prefix), `find_existing_friction()` helper, `extract_dup_count()` helper. Both `log_error()` and `FrictionLogTool::call()` now dedup: compute hash, scan for `rsi:hash:{hash}` tag, increment `rsi:dup:{count}` and update `rsi:last_seen:{timestamp}` on existing entry, or create new with `rsi:dup:1`. `friction.review` now shows `duplicate_count` and `last_seen` in entries.
- `wm-consciousness/src/autonomous.rs`: `run_improve()` extracts `duplicate_count` from tags, weights pattern strength by sum of duplicate counts (single entry with dup_count >= 3 now triggers proposals)

**New tests**: `friction_dedup_log_error_increments_count`, `friction_dedup_log_tool_increments_count`, `friction_hash_is_deterministic` (+3 tests)

**Test count**: 2,770 → 2,773 (+3)

### WS-3: Karma-to-Friction Bridge — ✅ COMPLETE

**Changes** (~150 LOC across 3 crates):
- `wm-governance/src/karma_ledger.rs`: Added `record_friction_signal(tool)` (+0.01 debt) and `record_friction_resolved(tool)` (-0.05 debt) methods with chain integrity
- `wm-mcp/src/server.rs`: Added `karma_ledger: Option<Arc<KarmaLedger>>` field, wired friction signal recording after `log_error()`, checks `total_debt()` threshold (>0.5 medium, >0.8 high) to log governance friction entries with deduplication
- `wm-tools/src/expansion/rsi.rs`: Made `friction_hash` public, added `friction_hash_exists` helper, `#[must_use]` on `friction_hash`

**New tests**: `friction_signal_adds_small_debt`, `friction_resolved_reduces_debt`, `friction_resolved_does_not_go_negative`, `friction_signal_chain_stays_valid` (+4 tests)

**Test count**: 2,773 → 2,777 (+4)

### WS-4: Proactive Improvement Surfacing — ✅ COMPLETE

**Changes** (~120 LOC across 3 crates):
- `wm-mcp/src/server.rs`: Dispatch-based trigger — Improve cycle runs every 50 dispatches or on Theta/Delta brain-wave transition. Proposals stored as Codex memories with `rsi:proposal:active` tag + `rsi:proposal:sig:{category}:{target}:{severity}` signature. Workspace `AttentionRequest` event emitted with high salience
- `wm-tools/src/expansion/rsi.rs`: New `ActiveProposalsTool` (`improve.active_proposals`) — retrieves active proposals from Codex with category, severity, target, signature, content preview
- `wm-consciousness/src/autonomous.rs`: `run_improve()` now scans existing `rsi:proposal:active` signatures and skips proposals with matching `category:target:severity` to avoid duplicates

**New tests**: `active_proposals_tool_retrieves_proposals` (+1 test)

**Test count**: 2,777 → 2,778 (+1)

### WS-5: Friction Resolution Verification — ✅ COMPLETE

**Changes** (~250 LOC across 2 crates):
- `wm-tools/src/expansion/rsi.rs`: New `FrictionResolveTool` (`friction.resolve`) — tags entries with `rsi:resolved`, `rsi:resolved_method:{method}`, `rsi:resolved_at:{timestamp}`, calls `karma_ledger.record_friction_resolved()`, emits workspace `Reward` event. Regression detection in both `FrictionLogTool::call()` and `log_error()`: if hash matches a resolved entry, creates new entry with `rsi:regression` tag, escalated severity, `rsi:regression_of:{id}` link. `friction.review` now shows `resolved`, `resolved_at`, `resolved_method`, `is_regression` per entry, plus top-level `resolved` count and `regressions` count
- `wm-governance/src/karma_ledger.rs`: `record_friction_resolved()` already added in WS-3

**New tests**: `friction_resolve_tool_tags_resolved`, `friction_resolve_already_resolved_returns_early`, `regression_detection_in_log_error_creates_new_entry` (+3 tests)

**Test count**: 2,778 → 2,781 (+3)

### RSI Phase 3: Adversarial — E2E Test + Benchmarks + Dynamic Redteam — ✅ COMPLETE (2026-08-06)

**Goal**: Close the RSI loop with a full end-to-end integration test, benchmark the RSI pipeline, and add dynamic adversarial tools that synthesize test vectors from friction history.

**Changes**:
- `crates/wm-mcp/src/server.rs`: Added `e2e_rsi_outward_spiral_full_loop` test — exercises the complete outward spiral: friction.log → dedup → friction.review → friction.resolve → regression detection → final review with resolved+regression counts (+1 test)
- `crates/wm-tools/benches/rsi_bench.rs`: New criterion benchmark suite — `friction_hash` (~243 ns), `log_error_new_entry` (~17 ms with tempdir), `log_error_dedup` (1ms at 100 entries), `friction_log_tool_call` (~1.45 ms)
- `crates/wm-tools/Cargo.toml`: Added criterion dev-dependency and `rsi_bench` bench target
- `crates/wm-tools/src/expansion/rsi.rs`: New `RedteamFromFrictionTool` (`redteam.from_friction`) — scans resolved+regression friction entries, synthesizes regression test pseudocode. Resolved entries → high-risk regression tests; regressions → critical-risk adversarial vectors
- `crates/wm-tools/src/expansion/rsi.rs`: New `RedteamCoverageReportTool` (`redteam.coverage_report`) — runs redteam cycle, produces per-system coverage summary (covered/uncovered/friction counts, risk scores, coverage %)
- `crates/wm-tools/src/expansion/mod.rs`: Exported `RedteamFromFrictionTool` and `RedteamCoverageReportTool`

**New tests**: `e2e_rsi_outward_spiral_full_loop`, `redteam_from_friction_generates_regression_tests`, `redteam_from_friction_detects_regressions`, `redteam_coverage_report_returns_summary` (+4 tests)

**Test count**: 2,781 → 2,785 (+4)

---

## Safety Features: Destructive Confirmation + Transaction Snapshot/Rollback + Compartment Access Control — COMPLETE

**Date**: August 7, 2026
**Tests**: 2,818 (up from 2,785), 0 clippy warnings, fmt clean.
**Tools**: 176 (173 + 3 transaction tools)
**LOC**: ~112,300

### Destructive Tool Confirmation

**New field**: `destructive: bool` on `EffectRow` in `crates/wm-core/src/effects.rs`

**Dispatch pipeline gate** (step 4b in `crates/wm-dispatch/src/pipeline.rs`):
- Tools with `destructive: true` are blocked unless `"confirm": true` is present in tool arguments
- Returns `CoreError::Governance` with message containing "destructive" and "confirm"
- 3 new pipeline tests: blocked without confirm, allowed with confirm, non-destructive unaffected

**8 destructive tools**: `memory.delete`, `galaxy.purge`, `galaxy.transfer`, `galaxy.restore`, `memory.consolidate`, `memory.deduplicate`, `system.flush`, `karma.clear`

### Transaction Snapshot/Rollback

**New file**: `crates/wm-tools/src/expansion/transaction.rs` (~360 lines)

| Tool | Gana | Description |
|---|---|---|
| `transaction.begin` | Encampment | Snapshots all memory galaxies into Journals, stores backup ID in shared `TransactionState` (`Arc<Mutex<Option<String>>>`) |
| `transaction.commit` | Encampment | Clears transaction state, keeping all changes |
| `transaction.rollback` | Encampment | Restores all galaxies from snapshot (destructive, requires `confirm: true`) |

**Integration**:
- `TransactionState` threaded through `register_expansion` → `register_all` → `McpServer`
- All 3 constructors updated: `with_default_eco`, `with_defaults`, `test_server`
- 3 NLU profiles added in `nlu.rs` (166 total TF-IDF profiles)
- `eval_all_tools.py` updated with transaction tool entries
- 6 unit tests: begin/commit workflow, begin/rollback restores data, double-begin error, commit without begin error, rollback without begin error, rollback requires confirm

### Compartment-Based Access Control

**New fields on `Context`**: `compartment: Compartment`, `user_id: Option<String>`

**Galaxy access enforcement** via `can_access_galaxy()` and `can_write_galaxy()`:
- `sandbox` — Tutorial, Research only
- `production` — all memory galaxies
- `secure` — all galaxies including system galaxies

**MCP server wiring**: `Context` populated from MCP request `_meta` metadata

### Per-Crate Test Count Changes

| Crate | Before | After | Change |
|---|---|---|---|
| wm-core | 144 | 144 | — |
| wm-memory | 311 | 311 | — |
| wm-dispatch | 86 | 89 | +3 (destructive confirmation tests) |
| wm-consciousness | 394 | 394 | — |
| wm-tools | 440 | 458 | +18 (transaction tools + NLU profiles) |
| wm-governance | 87 | 91 | +4 |
| wm-substrate | 163 | 163 | — |
| wm-mcp | 74 | 76 | +2 |
| wm-polyglot | 66 | 66 | — |
| wm-reflex | 49 | 49 | — |
| wm-timescale | 37 | 37 | — |
| wm-workspace | 54 | 54 | — |
| wm-selfmodel | 79 | 79 | — |
| wm-bicameral | 495 | 495 | — |
| wm-drive | 50 | 50 | — |
| wm-autonomic | 31 | 31 | — |
| wm-resonance | 61 | 61 | — |
| wm-sangha | 100 | 100 | — |
| wm-simulation | 47 | 47 | — |
| **Total** | **2,785** | **2,818** | +33 |

---

## v5 Strategy Implementation — COMPLETE

Detailed plan in `STRATEGY_V5.md`. All 7 phases complete.

### Phase 1: Foundation (Async + Crate Merge) ✅
- **Crate merge**: 19 → 14 (wm-cognitive absorbs wm-consciousness, wm-reflex, wm-timescale, wm-drive, wm-resonance, wm-autonomic)
- **Async dispatch**: `async fn dispatch`, `#[async_trait]` Tool, `.await` at all call sites
- **Async MCP server**: `handle_request`, `handle`, `handle_tools_call` all async
- **3,009 tests**, 0 clippy warnings, fmt clean

### Phase 2: Embedding NLU Router ✅ (shadow mode)
- **`EmbeddingRouter`** (`wm-tools/src/embedding_router.rs`): cosine similarity against pre-computed tool embeddings
- **OATS** (Outcome-Aware Tool Selection): offline embedding refinement from success/failure centroids
- **Shadow mode**: embedding router primary, TF-IDF fallback runs alongside
- **31 new tests**
- Step 2.8 (remove TF-IDF) deferred until production accuracy validation

### Phase 3: Learned Inference Router ✅ (shadow mode)
- **`LearnedRouter`** (`wm-bicameral/src/learned_router.rs`): embedding k-NN (k=5) + conformal calibration
- **`EdgeRuleGenerator`**: auto-promotes high-frequency simple responses to compiled edge rules
- **29 new tests**
- Step 3.5 (remove regex) deferred until production accuracy validation

### Phase 4: Imagination Engine ✅
- **`WorldModel`**, **`ScenarioEngine`**, **`ScenarioEvaluator`**, **`SimulationBridge`**, **`ImaginationConfigurator`**
- 3 MCP tools: `imagine.scenario`, `imagine.predict`, `imagine.reflect`
- Dream cycle Oracle phase enhanced with counterfactual replay
- `CycleType::Research` (8th autonomous cycle), daemon `--research-interval`

### Phase 5: Self-Play Training Loop ✅
- **`SelfPlayLoop`** (`wm-bicameral/src/self_play.rs`, ~1,650 lines): proposer → solver → verifier → training data collection
- 3 MCP tools: `selfplay.run`, `selfplay.status`, `selfplay.export`
- Daemon `--selfplay-interval` flag
- 27 new tests, 1 benchmark (`self_play_bench`)

### Phase 6: Mutable Structures ✅
- **`GanaRegistry`**: Gana taxonomy drift based on co-usage patterns
- **`DynamicGalaxyRegistry`**: dynamic galaxy creation from memory clustering
- **`LearnedDreamCycle`**: learned dream cycle phase selection (12-phase effectiveness tracking)
- **`LearnedCycleStrategy`**: learned autonomous cycle strategies (4 strategies)
- 31 new tests

### Phase 7: Polish & Verification ✅
- **Mutable structures wiring**: All 4 mutable structures integrated into live pipeline
  - `GanaRegistry` → `DispatchPipeline` via `with_gana_registry()`
  - `LearnedDreamCycle` → `DreamCycle` via `with_learned()`
  - `LearnedCycleStrategy` → `AutonomousCycleRunner` via `with_learned()`
  - `GanaRegistry` + `DynamicGalaxyRegistry` → `McpServer` via `Arc<Mutex<>>`
- **Persistence**: All mutable structures save/load JSON state on daemon startup/shutdown
- **E2E integration tests**: GanaRegistry recording, DynamicGalaxyRegistry access, LearnedDreamCycle attachment, full pipeline integration, persistence roundtrip
- **All benchmarks passing**: dream, reflex, RSI, self-play, router, pipeline, mutable structures

### v5.2.1: Karma Ledger Optimization & Benchmarks

#### Karma Write-Behind Batching
- `KarmaLedger` buffers `record()` calls in memory, flushes via single LMDB transaction (`flush_threshold=16`)
- **Benchmark results** (criterion, release profile):

| Benchmark | Time | Notes |
|---|---|---|
| `karma_record_batched` | 97.7 µs | Batched (threshold=16) |
| `karma_record_synchronous` | 1.07 ms | Synchronous (threshold=0) |
| `karma_flush_16_entries` | 314.7 µs | Single batch flush of 16 entries |
| `dispatch_noop_with_karma` | 168.2 µs | Full pipeline + karma record |
| `dispatch_noop_no_karma` | 1.25 µs | Pipeline overhead without karma |

- **10.9x throughput improvement** (batched vs synchronous)

#### Mutable Structure Benchmarks (13 criterion benchmarks)

| Benchmark | Time |
|---|---|
| `gana_registry_record_usage` | 228 ns |
| `gana_registry_record_co_usage` | 1.02 µs |
| `gana_registry_co_usage_count` | 171 ns |
| `gana_registry_analyze_drift` | 80 ns |
| `gana_registry_serialize` | 1.13 µs |
| `gana_registry_deserialize` | 1.61 µs |
| `dream_cycle_record_phase` | 488 ns |
| `dream_cycle_phases_to_run` | 457 ns |
| `dream_cycle_update_phase_order` | 568 ns |
| `dream_cycle_serialize` | 3.71 µs |
| `dream_cycle_deserialize` | 5.45 µs |
| `cycle_strategy_record_cycle` | 362 ns |
| `cycle_strategy_cycles_to_run` | 29 ns |
| `cycle_strategy_update_priority_order` | 390 ns |
| `cycle_strategy_serialize` | 3.97 µs |
| `cycle_strategy_deserialize` | 3.81 µs |

#### Daemon Karma Flush on Shutdown
- Added explicit `karma_ledger.flush()` call in `run_daemon` graceful shutdown
- Root cause: `KarmaLedger::Drop` flushes, but daemon holds `Arc<KarmaLedger>` — `Drop` doesn't fire until server is dropped, which is outside `run_daemon`'s scope

#### E2E Integration Test
- `pipeline_karma_batched_e2e`: 20 tool dispatches (10 honest + 10 wasteful), verifies pending buffer, total_debt accuracy (2.0), chain integrity after flush, persistence across ledger instances

#### Debug Test Fix
- `benchmark_pipeline_overhead` assertion gated to `#[cfg(not(debug_assertions))]` — debug builds have unoptimized async/await overhead (~16µs) that exceeds the 5µs budget

### Final v5 Metrics
- **14 crates**, **185 tools**, **~128,500 LOC**
- **3,168 tests**, 0 clippy warnings, fmt clean
- All 7 phases complete
