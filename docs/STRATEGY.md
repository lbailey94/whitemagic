# WhiteMagic v4 — Architecture & Strategy

**Version**: 4.0.0
**Date**: 2026-08-07 (Safety features: destructive tool confirmation + transaction snapshot/rollback + compartment-based access control)
**Status**: v5.2.1 — All 7 phases complete (0–8, A–F, R1–R7, L1–L5, Pre-N A/B/C, N1–N21) + integration wiring + E2E tests + graceful shutdown + security hardening + RSI + Embodiment I/O + Safety features + NLU router + learned inference router + imagination engine + self-play loop + mutable structures + persistence. 3,231 tests, 184 tools (runtime-authoritative via `wm doctor`), ~130,461 lines of Rust across 14 crates. clippy warnings: 0 (after 2 early-drop lints fixed), fmt clean. Under version control (git).

---

## 1. Vision

WhiteMagic v4 is a ground-up rewrite of the cognitive operating system,
keeping the design patterns that work (28 Gana taxonomy, 14-galaxy memory,
Dharma governance, karma ledger, dream cycle, citta consciousness) while
replacing the implementation substrate entirely.

**The fundamental shift**: Rust is the primary runtime. Python is a thin
MCP protocol shell. Every polyglot language is compiled to a native library
or embedded in-process — zero subprocess spawning.

---

## 2. Design Principles

1. **Rust-first**: Every system that can be in Rust, is in Rust. Python
   exists only for MCP protocol I/O and ecosystem access (ONNX,
   HuggingFace tokenizer).

2. **Event-driven, not polling**: No background threads that wake up to
   check state. The OS wakes the process via epoll (stdin) or timerfd
   (scheduled tasks). Between events, CPU usage is zero.

3. **Effect-typed dispatch**: Inspired by Koka's effect system. Every tool
   declares its effects (reads memory, writes memory, invokes LLM, spawns
   process). The dispatch pipeline enforces these at compile time via Rust
   traits, and at runtime via the Dharma governance layer.

4. **Zero-copy memory**: LMDB memory-mapped database. Reading a memory is
   a pointer dereference into the mmap'd file. No serialization, no query
   planner, no lock contention.

5. **Fractal meta-tool**: Each of the 800+ tools is a self-contained Rust
   trait object with atomic self-tracked statistics. Tools that perform
   poorly are retired. Tools that are hot are promoted. The system learns
   its own usage patterns.

6. **Brain-wave eco mode**: Five states (Gamma/Beta/Alpha/Theta/Delta)
   driven by actual event rates, not a monitoring thread. Delta mode uses
   zero CPU — the process is literally asleep until the OS wakes it.

7. **Polyglot without subprocesses**: Julia embedded via jlrs, Koka/Haskell
   compiled to .so and linked, Zig via C ABI. No subprocess spawning, no
   zombie processes, no swap leaks.

8. **Honest resource accounting**: Every tool tracks its CPU time, memory
   touched, and disk I/O. The system can report its own resource footprint
   at any granularity.

---

## 3. Language Stack

```
┌──────────────────────────────────────────────────────┐
│                 Python (thin shell)                    │
│    MCP protocol · ONNX fallback · HuggingFace         │
│    ~500 lines, no business logic                      │
└────────────────────┬─────────────────────────────────┘
                     │ PyO3 (zero-copy)
┌────────────────────┴─────────────────────────────────┐
│              Rust (primary runtime)                     │
│                                                         │
│  tokio async runtime · rayon parallel · SIMD           │
│  LMDB memory store · Tantivy FTS · LanceDB vectors    │
│  28 Gana dispatch (effect-typed traits)                │
│  Brain-wave eco mode (event-driven, zero polling)      │
│  Dharma governance (compile-time effect verification)  │
│  Karma ledger (LMDB append-only)                       │
│  Citta consciousness (ndarray SIMD)                    │
│  Dream cycle (tokio tasks, event-triggered)            │
└──┬──────────┬──────────┬──────────┬───────────────────┘
   │ C ABI    │ C ABI    │ jlrs     │ C ABI
┌──┴────┐ ┌──┴────┐ ┌───┴────┐ ┌──┴────────────────────┐
│ Koka  │ │ Zig   │ │ Julia  │ │ Haskell               │
│ .kk   │ │ .zig  │ │ .jl    │ │ .hs                   │
│       │ │       │ │        │ │                       │
│ Effect│ │ TRN   │ │ Monte  │ │ Topological           │
│ verify│ │ gate  │ │ Carlo  │ │ verification          │
│ Dharma│ │ ultra │ │ quantum│ │ DAG cycle check       │
│ rules │ │ low   │ │ geometry│ │                      │
│ karma │ │ latency│ │ drift  │ │                      │
│ check │ │       │ │ detect │ │                      │
└───────┘ └───────┘ └────────┘ └───────────────────────┘
```

### Language Roles

| Language | Role | Integration | Rationale |
|---|---|---|---|
| **Rust** | Core runtime, memory, dispatch, I/O, consciousness | Native | Safety + speed + no runtime + tokio async + rayon parallel + SIMD |
| **Python** | MCP protocol, ONNX embeddings, HuggingFace | PyO3 (Rust calls Python) | MCP ecosystem, ONNX runtime, tokenizer libraries don't exist in Rust |
| **Koka** | Effect verification, Dharma rules, karma type checking | Compile to C, link as .so | Algebraic effect handlers, Perceus RC (no GC), FBIP in-place optimization |
| **Julia** | Monte Carlo, quantum geometry, drift detection | jlrs (embedded in-process) | JIT unmatched for numerical computing after warmup; jlrs gives async + persistent tasks |
| **Haskell** | Topological verification, DAG cycle checks | GHC → native .so | GADTs + type families strictly more powerful than Rust for formal verification |
| **Zig** | Ultra-low-latency TRN hard gate | C ABI, link directly | Zero hidden allocations, explicit memory control, compiles to C ABI |

### Why Not Koka As Primary?

Koka's effect system and Perceus RC are the right *ideas*, but:
- No async stdlib on the C backend (critical for MCP I/O)
- No ecosystem (LMDB bindings, HTTP, tokio equivalent)
- Single maintainer (bus factor of 1)
- Array performance lags (problem for SIMD vector ops)

**Solution**: Use Koka's effect row system as the *design model* for Rust
traits. Write Koka modules for the parts where effect typing matters most
(Dharma governance, karma verification). Compile them to C and link.

---

## 4. Memory Architecture

### Storage Stack

| Component | v2 (current) | v4 | Why |
|---|---|---|---|
| Key-value store | SQLite B-tree | **LMDB** | mmap'd zero-copy reads, 6-15x faster, 3-10x less write amplification |
| Vector index | HNSW (Python) | **LanceDB** (Rust) | Columnar, SIMD-accelerated, disk-based ANN, no Python overhead |
| Full-text search | FTS5 (SQLite) | **Tantivy** (Rust) | 2x faster than Lucene, sub-ms queries, mmap-friendly, BM25 + phrase |
| Embeddings | FastEmbed/ONNX | **Candle** (Rust) + ONNX fallback | Pure Rust ML eliminates ONNX runtime dependency for common models |

### LMDB Performance vs SQLite

| Metric | SQLite (WAL) | LMDB | Improvement |
|---|---|---|---|
| Random reads | 200K-500K ops/sec | 2-3M ops/sec | 6-15x |
| Sequential reads | — | 6M ops/sec | — |
| Writes | 50K-80K ops/sec | 500K ops/sec | 6-10x |
| P99 read latency | 12ms | 0.8ms | 15x |
| Startup time | 140ms | 8ms | 17x |
| Write amplification | 20-80KB/txn | 8KB/txn | 3-10x |
| Background threads | WAL checkpoint, VACUUM | None | — |

### 14-Galaxy Taxonomy → LMDB Sub-databases

Each galaxy becomes an LMDB named database (sub-DB within the same file):

| Galaxy | Purpose | Key scheme | Value format |
|---|---|---|---|
| aria | Artistic/creative memories | UUID | MessagePack |
| citta | Consciousness stream | Sequence number | MessagePack |
| codex | Knowledge/documents | Content hash | MessagePack |
| journals | Session journals | Session ID + turn | MessagePack |
| dreams | Dream cycle outputs | Dream ID + phase | MessagePack |
| research | Research notes | UUID | MessagePack |
| sessions | Session recordings | Session ID + seq | MessagePack |
| substrate | System state/config | Key string | Raw bytes |
| tutorial | Tutorial memories | UUID | MessagePack |
| universal | Cross-galaxy index | Holographic coords | Reference keys |
| karma | Karma ledger | Entry ID | MessagePack |
| dharma | Governance rules | Rule ID | MessagePack |
| associations | Cross-memory links | Source + target | Weight + metadata |
| embeddings | Vector embeddings | Memory UUID | f32 array (raw) |

### Holographic Coordinate System

v4 has a dual coordinate system:

**6D `HolographicCoords`** (galactic addressing):
```rust
struct HolographicCoords {
    galaxy: u8,           // Which of 14 galaxies
    sector: u16,          // Spatial sector within galaxy
    radial: f32,          // Radial distance from center
    angular: f32,         // Angular position
    temporal: u64,        // Temporal coordinate (timestamp)
    consciousness: f32,   // Consciousness resonance frequency
}
```

**5D `Coordinate5D`** (spatial indexing):
```rust
struct Coordinate5D {
    x: f32,   // semantic axis (content hash bytes 0-3)
    y: f32,   // semantic axis (content hash bytes 4-7)
    z: f32,   // semantic axis (content hash bytes 8-11)
    w: f32,   // temporal weight (0 = old, 1 = recent)
    v: f32,   // consciousness resonance (importance)
}
```

Both are stored as composite keys enabling spatial range queries via LMDB
cursor scans. The 5D system supports `find_nearby()` for proximity search
and `Zone` classification (Core → FarEdge).

**Phase 6.3 update**: The 5D x/y/z axes now use anchor-based TF projection
via `SemanticEncoder` (Tantivy `SimpleTokenizer` + `LowerCaser`). Three
semantic axes: Logic↔Emotion, Micro↔Macro, Time↔Space. Similar content
now produces similar coordinates. The SHA-256 `encode()` remains as a
fallback; `put_semantic()` uses the semantic encoder. LanceDB embedding
integration is deferred to a future phase.

### v2 vs v3 Memory Gap Analysis

v3's storage substrate (LMDB + Tantivy) is a significant performance upgrade
over v2 (SQLite + FTS5). The v2 memory module spans ~124 Python files (~20K
lines); v4 has ~3,200 lines in wm-memory. All v2 memory model and intelligence
patterns have been ported (Phase 6.1–6.8). The remaining gap is vector search
(LanceDB embeddings), which is the next priority.

#### v2 Memory Gaps — ALL RESOLVED (Phase 6.1–6.8 complete):

| Gap | v2 feature | v3 status | Phase |
|---|---|---|---|
| Memory types | `MemoryType` enum (ShortTerm, LongTerm, Emotional, Narrative, Pattern, Procedural, Citta, etc.) | ✅ 8 MemoryType variants (Phase 6.1) | 6.1 ✅ |
| Neuro-score dynamics | `neuro_score` decays over time, boosts on recall; per-memory `half_life_days` | ✅ Dynamic neuro_score with Hebbian recall + exponential decay (Phase 6.1) | 6.1 ✅ |
| Novelty score | `novelty_score` decays as info becomes familiar | ✅ novelty_score field (Phase 6.1) + SurpriseGate (Phase 6.7) | 6.1 ✅ |
| Emotional valence | -1.0 to 1.0 (positive/negative); `emotional_weight` | ✅ emotional_valence + emotional_weight fields (Phase 6.1) | 6.1 ✅ |
| Memory protection | `is_protected`, `is_core_identity`, `is_sacred`, `is_pinned` | ✅ is_protected field (Phase 6.1) | 6.1 ✅ |
| Privacy controls | `is_private`, `model_exclude` | ✅ is_private + model_exclude fields (Phase 6.1) | 6.1 ✅ |
| Provenance | `source`, `source_trust` (defends against memory poisoning) | ✅ source + source_trust fields (Phase 6.1) | 6.1 ✅ |
| Multi-agent coherence | `version`, `agent_id` for cache coherence | ✅ version + agent_id fields (Phase 6.1) | 6.1 ✅ |
| Recall vs access | `recall_count` independent from `access_count` | ✅ recall_count field (Phase 6.1) | 6.1 ✅ |
| Typed links | 7 `LinkType` variants (Related, Extends, Contradicts, Supersedes, Temporal, Causal, Cascade) | ✅ LinkType enum + Hebbian learning (Phase 6.2) | 6.2 ✅ |
| Hebbian learning | Links strengthen on co-activation, decay when idle | ✅ activate() + decay() with diminishing returns (Phase 6.2) | 6.2 ✅ |
| Semantic coordinates | Anchor embeddings + PCA for x/y/z axes | ✅ Anchor-based TF projection (Tantivy tokenizer) | 6.3 |
| Secondary indexes | SQLite indexes on content hash, tags, importance, time | ✅ 4 LMDB DUP_SORT indexes (Phase 6.4) | 6.4 ✅ |
| Strategy synthesis | Clusters memories, synthesizes "strategy memories" from themes | ✅ StrategySynthesizer with Jaccard clustering (Phase 6.5) | 6.5 ✅ |
| Sleep consolidation | Cross-galaxy transfer routes (sessions→codex, citta→aria, dreams→research) | ✅ 4 transfer routes implemented (Phase 6.5) | 6.5 ✅ |
| Constellation detection | HDBSCAN clustering + Hungarian drift tracking | ✅ Grid-based density clustering + drift tracking (Phase 6.6) | 6.6 ✅ |
| Spreading activation | Activation spreads through association graph | ✅ SpreadingActivation module (Phase 6.7) | 6.7 ✅ |
| Metaplasticity | Learning rate adapts based on prior activation | ✅ Metaplasticity module (Phase 6.7) | 6.7 ✅ |
| Neuromodulation | Dopamine/serotonin analogs modulate retention | ✅ Neuromodulator module (Phase 6.7) | 6.7 ✅ |
| Ripple tagging | Sharp-wave ripple marks memories for consolidation | ✅ RippleTagger module (Phase 6.7) | 6.7 ✅ |
| Surprise gate | Novelty detection gates memory encoding | ✅ SurpriseGate module (Phase 6.7) | 6.7 ✅ |
| Dynamic galaxies | Project-scoped galaxy creation, switching, registry | ✅ GalaxyRegistry with LMDB-backed dynamic galaxies (Phase 6.8) | 6.8 ✅ |

---

## 5. Dispatch Architecture

### 28 Gana → Rust Trait Dispatch

Each Gana is a Rust enum variant. Each tool is a trait object that
declares its Gana affiliation and effect row:

```rust
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
enum Gana {
    Horn, Neck, Root, Room, Heart, Tail, WinnowingBasket,
    Ghost, Willow, Star, ExtendedNet, Wings, Chariot,
    Abundance, StraddlingLegs, Mound, Stomach, HairyHead,
    Net, TurtleBeak, ThreeStars, Dipper, Ox, Girl,
    Void, Roof, Encampment, Wall,
}

struct EffectRow {
    reads: Vec<Resource>,    // What resources are read
    writes: Vec<Resource>,   // What resources are written
    invokes: Vec<Capability>, // What capabilities are invoked
    spawns: bool,            // Does this spawn external processes?
    destructive: bool,       // Does this delete/overwrite data? (requires confirm)
    cost: CostEstimate,      // CPU/memory/disk cost estimate
}

trait Tool: Send + Sync {
    fn name(&self) -> &str;
    fn gana(&self) -> Gana;
    fn effects(&self) -> &EffectRow;
    fn call(&self, ctx: &mut Context, args: Args) -> Result<Output>;
    fn stats(&self) -> &ToolStats;
}
```

### Dispatch Pipeline

The v2 Python middleware chain (22 stages, ~200µs/call) becomes a Rust
pipeline of ~2µs/call:

```
Request → Parse → EffectCheck → DestructiveConfirm → DharmaGate → RateLimit
  → CircuitBreaker → KarmaRecord → ToolDispatch → ResultEncode
  → KarmaUpdate → StatsUpdate → Response

**DestructiveConfirm**: Tools with `destructive: true` in their EffectRow are
blocked unless `"confirm": true` is present in the tool arguments. 8 destructive
tools: memory.delete, galaxy.purge, galaxy.transfer, galaxy.restore,
memory.consolidate, memory.deduplicate, system.flush, karma.clear.

**Transaction Snapshot/Rollback**: Three tools provide multi-tool atomic sequences:
- `transaction.begin` — snapshots all memory galaxies into Journals
- `transaction.commit` — clears transaction state, keeping changes
- `transaction.rollback` — restores all galaxies from snapshot (destructive)

**Compartment-Based Access Control**: `Context` carries `compartment` and
`user_id` from MCP request `_meta`. Galaxy access enforced via `can_access_galaxy()`
and `can_write_galaxy()`: sandbox (Tutorial/Research only), production (all memory
galaxies), secure (all galaxies including system).
```

Each stage is a zero-cost abstraction (generic function, monomorphized).
No heap allocation in the hot path. No virtual dispatch except the final
tool call.

### Tool Self-Tracking

```rust
struct ToolStats {
    call_count: AtomicU64,
    success_count: AtomicU64,
    p50_latency_ns: AtomicU64,
    p99_latency_ns: AtomicU64,
    cpu_time_ns: AtomicU64,
    lmdb_pages_touched: AtomicU64,
    last_used_unix: AtomicU64,
    effectiveness: AtomicF32,  // karma-weighted success rate
}
```

Every tool call updates these with atomic operations (~10ns overhead).
The dispatch pipeline uses these to:
- **Retire** tools with effectiveness < 0.2 after 10 calls
- **Promote** hot tools (call_count > 1000) to pre-compiled dispatch
- **Prefer** resource-cheap tools in Alpha/Theta brain-wave modes
- **Surface** effectiveness data via `tools.effectiveness_report`

---

## 6. Brain-Wave Eco Mode

### Five States

```
Gamma (active):   Full power. All subsystems, polyglot accelerators, inference.
                  Event rate > 10/min. All 800+ tools available.

Beta (working):   Inference active, memory R/W, no background consolidation.
                  Event rate > 0/min. Standard tool set, no dream cycle.

Alpha (idle):     No active requests for 30s+. Memory reads only.
                  Citta heartbeat at 1/10 speed. No embeddings, no dreaming.
                  Reduced tool set (governance + memory only).

Theta (drowsy):   5+ min idle. Dream cycle runs once. Embeddings paused.
                  After dream completes, transition to Delta.

Delta (dormant):  30+ min idle. Only LMDB mmap is warm. Zero CPU.
                  Wake on stdin (MCP request) or scheduled timer.
```

### Implementation (Zero Monitoring Overhead)

```rust
// The entire eco mode is a tokio::select! — no monitoring thread
loop {
    match brain_wave {
        BrainWave::Delta => {
            tokio::select! {
                _ = stdin_ready() => { transition_to(Gamma); }
                _ = tokio::time::sleep(Duration::from_secs(1800)) => {
                    transition_to(Theta);
                    run_dream_consolidation().await;
                    transition_to(Delta);
                }
            }
        }
        BrainWave::Alpha => {
            tokio::select! {
                _ = stdin_ready() => { transition_to(Gamma); }
                _ = tokio::time::sleep(Duration::from_secs(300)) => {
                    transition_to(Theta);
                }
            }
        }
        // ... Beta and Gamma handle requests directly
    }
}
```

The OS wakes the process via epoll (stdin readable) or timerfd (sleep
expired). Between events, **zero CPU usage**. No polling, no background
threads, no kswapd pressure.

### Transition Logic

```rust
fn update_brain_wave(&mut self, event: Event) {
    self.event_timestamps.push(event.timestamp);
    let rate = self.event_timestamps.rate_per_minute();
    let idle = self.time_since_last_event();

    self.brain_wave = match (rate, idle) {
        (r, _) if r > 10.0 => BrainWave::Gamma,
        (r, _) if r > 0.0  => BrainWave::Beta,
        (_, i) if i > Duration::from_secs(1800) => BrainWave::Delta,
        (_, i) if i > Duration::from_secs(300)  => BrainWave::Theta,
        _ => BrainWave::Alpha,
    };
}
```

~20 lines of code, no extra thread, no extra CPU. The "stat tracking" is
a ring buffer of timestamps — atomic operations, ~10ns per event.

---

## 7. Polyglot Integration

### Julia via jlrs (In-Process Embedding)

The v2 approach (subprocess spawning) caused 49 zombie processes and 11.3
GB of swap. v4 uses [jlrs](https://docs.rs/jlrs/) to embed Julia directly:

- **In-process**: Julia runs inside the Rust process, no subprocess
- **Async runtime**: `AsyncHandle` for concurrent Julia tasks
- **Persistent tasks**: Stateful Julia functions called repeatedly without re-init
- **Multi-threaded**: `MtHandle` with worker pools
- **Custom system images**: Pre-compile Julia packages for instant startup
- **Supports Julia 1.10-1.12**

Julia's 2-5 second startup cost is paid **once** at process start. After
that, calling Julia functions is microsecond-scale FFI.

**Use cases**: Monte Carlo simulation, quantum geometry, drift detection,
SDE solvers, Bayesian optimization.

### Koka (Compile to C, Link as .so)

Koka modules are compiled to C11 and linked as shared libraries:

```bash
koka -c dharma_rules.kk -- -o libdharma_koka.so
```

Koka's effect types ensure that Dharma governance rules are *provably
effect-safe* at compile time. The Rust runtime calls into the compiled
Koka library via C ABI.

**Use cases**: Effect verification for tool compositions, Dharma rule
evaluation, karma effect type checking, compile-time safety proofs.

### Haskell (GHC → Native .so)

Haskell modules compiled to shared libraries via GHC:

```bash
ghc -shared -dynamic -o libtopology.so Topology.hs
```

**Use cases**: Topological verification (DAG cycle detection), formal
verification of memory association graphs, type-level proofs about
tool composition safety.

### Zig (C ABI, Link Directly)

Zig compiles to standard C ABI objects, linked directly into the Rust
binary:

```bash
zig build-obj trn_gate.zig -fPIC -O ReleaseFast
```

**Use cases**: Ultra-low-latency TRN hard gate (the single hottest path
in the dispatch pipeline). Zig's no-hidden-allocation guarantee ensures
the gate never triggers GC or allocation spikes.

---

## 8. Phases

### Phase 0: Foundation — ✅ COMPLETE

**Goal**: Cargo workspace skeleton, core trait definitions, basic build
system, CI-ready structure.

**Status**: All deliverables verified. 101 tests passing, zero compiler
warnings. See `docs/PROGRESS.md` for detailed status.

**Deliverables**:
- Cargo workspace with 8 crates (wm-core, wm-memory, wm-dispatch,
  wm-consciousness, wm-governance, wm-mcp, wm-polyglot, wm-tools)
- Core trait definitions: `Tool`, `Gana`, `EffectRow`, `ToolStats`,
  `Context`, `Args`, `Output`
- 28 Gana enum with all variants
- Brain-wave state machine enum
- Basic error types
- Project README and AGENTS.md
- `.gitignore`, `rustfmt.toml`, `clippy.toml`
- Copy reusable Rust code from v2 (search, safety, evolution, neuro,
  llama, cascade-pyo3 crates)
- Integration test skeleton

**Key decisions**:
- Rust edition 2024
- MSRV: 1.85+
- Workspace-level dependencies for shared crates
- `#![deny(unsafe_code)]` in all crates except wm-polyglot (FFI boundary)

### Phase 0.5: Vertical Slice (MCP Server Bootstrap) — ✅ COMPLETE

**Goal**: Get a minimal MCP server running end-to-end so we can start
using and testing v3 immediately. This cuts horizontally through all
phases with minimal implementations.

**Deliverables**:
- JSON-RPC stdio server in `wm-mcp` (~200 lines)
- `wm` fractal meta-tool: routes by `route=` or `thought=` (~100 lines)
- 5 basic tools: `memory.create`, `memory.read`, `memory.list`, `gnosis`,
  `tools.list` (~300 lines in `wm-tools`)
- LMDB `put`/`get`/`scan` in `wm-memory` (~150 lines)
- Minimal dispatch: route to tool by name, record stats (~50 lines)
- Tool registration at startup (~50 lines)
- MCP protocol: `initialize`, `tools/list`, `tools/call`, `resources/list`

**Key decisions**:
- Pure Rust JSON-RPC (no Python dependency for the slice)
- Tools registered manually (no proc macro yet)
- `wm` meta-tool uses simple pattern matching for `thought=` routing
- Memory search is a stub (returns empty) until Phase 2

**Rationale**: Testing v3 against real MCP clients (Claude Desktop,
Cursor, Windsurf) early validates the architecture and catches protocol
issues before full implementation.

### Phase 1: LMDB Memory Store — ✅ COMPLETE

**Goal**: Replace SQLite with LMDB for the memory subsystem. Port the
14-galaxy taxonomy to LMDB sub-databases.

**Deliverables**:
- `wm-memory` crate with LMDB environment management
- 14 named databases (one per galaxy)
- `MemoryStore` trait with `get`, `put`, `delete`, `scan`, `query`
- Holographic coordinate system (6D)
- Content-hash deduplication
- Cross-galaxy association links
- Memory lifecycle (intake → consolidation → mindful forgetting)
- Embedding storage (raw f32 arrays in LMDB)
- Benchmark suite comparing against v2 SQLite
- Migration tool: SQLite → LMDB data transfer

**Key decisions**:
- LMDB map_size: 1GB default, configurable via `WM_LMDB_MAP_SIZE`
- Single-writer, multi-reader (LMDB's native model)
- Write batching: accumulate writes in memory, flush in batches
- MessagePack for value serialization (compact, schema-flexible)
- No separate WAL — LMDB's copy-on-write B-tree is inherently crash-safe

**Reused from v2**:
- `core/whitemagic-rust/src/search/` — BM25, hybrid search, RRF fusion
- `core/whitemagic-rust/crates/wm-core/src/vector_index.rs` — HNSW logic
  (adapted for LanceDB)
- `core/whitemagic/core/memory/holographic.py` — coordinate math (ported
  to Rust)

### Phase 2: Tantivy Full-Text Search — ✅ COMPLETE

**Goal**: Replace SQLite FTS5 with Tantivy for full-text search.

**Deliverables**:
- Tantivy index integrated into `wm-memory`
- Schema: memory_id, galaxy, content, tags, timestamp, holographic_coords
- BM25 scoring with phrase queries
- Tokenizer pipeline (Unicode normalization, stemming, stop words)
- Index updates batched with LMDB writes (same transaction boundary)
- Query API: `search(query: &str, galaxy: Option<Galaxy>, limit: usize)`
- Hybrid search: Tantivy FTS + LanceDB vector → RRF fusion
- Benchmark suite comparing against v2 FTS5

**Key decisions**:
- Tantivy `NoMergePolicy` initially (manual merge during Theta brain-wave)
- Index stored alongside LMDB file (separate directory)
- mmap'd index reader (zero-copy, same philosophy as LMDB)
- Query timeout: 100ms default, configurable

**Reused from v2**:
- `core/whitemagic-rust/src/search/` — RRF fusion, result aggregation,
  query intent detection, pattern matching

### Phase 3: Rust Dispatch Pipeline — ✅ COMPLETE

**Goal**: Move the tool dispatch pipeline from Python to Rust. Python
becomes a thin MCP shell via PyO3.

**Deliverables**:
- `wm-dispatch` crate with the full pipeline:
  - Request parsing (JSON-RPC)
  - Effect checking (compile-time trait bounds + runtime Dharma gate)
  - Rate limiting (token bucket, per-tool)
  - Circuit breaker (failure cascade prevention)
  - Karma recording (append-only LMDB log)
  - Tool dispatch (trait object dispatch via Gana routing)
  - Result encoding (JSON-RPC response)
  - Stats update (atomic counters)
- 28 Gana routing table (Gana → Vec<Box<dyn Tool>>)
- Tool registration system (compile-time + runtime)
- PyO3 bridge: Python MCP server → Rust dispatch
- Python MCP shell (~500 lines): stdin/stdout JSON-RPC, PyO3 calls

**Key decisions**:
- Dispatch pipeline is generic + monomorphized (zero-cost abstractions)
- Tool dispatch uses trait objects only at the final hop
- No heap allocation in the hot path (arena allocator for request/response)
- Circuit breaker: 5 failures in 10s → 30s cooldown
- Rate limiter: 100 calls/min default, per-tool configurable

**Reused from v2**:
- `core/whitemagic-rust/src/safety/` — rate limiter, circuit breaker,
  param validator, signature verification, confidence threshold
- `core/whitemagic-rust/src/sutra_kernel/dharma_engine.rs` — Dharma
  governance rules (adapted from Rust to new trait system)
- `core/whitemagic-rust/src/sutra_kernel/zodiac_ledger.rs` — Karma
  ledger logic

### Phase 4: Brain-Wave Eco Mode — ✅ COMPLETE

**Goal**: Implement the five-state brain-wave system with zero monitoring
overhead.

**Deliverables**:
- `BrainWave` enum (Gamma, Beta, Alpha, Theta, Delta)
- Event rate tracking (ring buffer of timestamps, atomic)
- State transition logic (event-driven, no polling)
- tokio::select! event loop (stdin + timer + scheduled tasks)
- Per-state tool availability filtering
- Per-state subsystem activation/deactivation:
  - Gamma: all subsystems active
  - Beta: inference + memory active, no dreaming
  - Alpha: memory reads only, citta at 1/10 speed
  - Theta: dream cycle runs once, then → Delta
  - Delta: only LMDB mmap warm, zero CPU
- Configuration: thresholds for each transition (env vars + config file)
- Metrics: current state, time in each state, transition count

**Key decisions**:
- No monitoring thread — transitions happen on event boundaries
- Ring buffer size: 60 entries (1 minute of events at 1/sec)
- Delta wake: epoll on stdin + timerfd for scheduled tasks
- Theta dream: runs synchronously in the event loop, then transitions
- State is visible to tools (tools can check `ctx.brain_wave()`)

### Phase 5: Consciousness Systems — ✅ COMPLETE

**Goal**: Port citta cycle, coherence, smarana, and consciousness loop to
Rust tokio tasks.

**Deliverables**:
- `wm-consciousness` crate:
  - Citta cycle (16D consciousness vector, valence mapping)
  - Coherence measurement (auto-measure after significant events)
  - Smarana (memory retention testing)
  - Presence detection (idle vs active awareness)
  - Apotheosis engine (self-improvement monitoring)
- 16D consciousness vector using `ndarray` with SIMD
- Citta heartbeat: event-driven (fires on tool call completion, not polling)
- Coherence auto-measure: triggered by significance score > threshold
- Dream cycle: 12 phases as tokio tasks, triggered by Theta brain-wave
- Sleep consolidation: important turns → codex galaxy (LMDB batch write)

**Key decisions**:
- Citta vector: `ndarray::Array1<f32>` with 16 dimensions
- SIMD: use `wide` crate for f32x8 SIMD operations
- No background thread for citta — fires as a post-dispatch hook
- Dream cycle: runs only in Theta state, single execution, then → Delta
- Coherence threshold: 0.7 default, configurable

**Reused from v2**:
- `core/whitemagic-rust/crates/wm-neuro/` — predictive coding, thalamic
  gating, momentum dynamics (Rust → Rust, minimal changes)
- `core/whitemagic/core/consciousness/` — algorithm logic (ported to Rust)

### Phase 6: Governance & Karma — ✅ CORE COMPLETE (DharmaGate + KarmaLedger done, Koka rules pending)

**Goal**: Port Dharma governance, karma ledger, and ethical rules to Rust
+ Koka.

**Deliverables**:
- `wm-governance` crate:
  - Dharma rule engine (Rust trait dispatch)
  - Karma ledger (LMDB append-only log)
  - Effect verification (Koka-compiled rules, linked via C ABI)
  - Ethical sign-off (per-tool ethical evaluation)
  - Mandala compartments (research/sandbox/production/secure)
  - Transaction firewall (spend limits, rate limiting, allowlist)
- Koka modules:
  - `dharma_rules.kk` — Core ethical rules with effect types
  - `karma_verify.kk` — Karma chain verification
  - `effect_check.kk` — Tool composition effect safety
- Karma effect types (EffectType enum, EffectSignature)
- Karmic effects middleware (auto-record declared vs actual effects)
- Bounty platform connector (external bounty scanning)

**Key decisions**:
- Koka compiled to C, linked as `libdharma_koka.so`
- Fallback: if Koka library not available, Rust-native rules (simpler)
- Karma ledger: LMDB append-only (no deletes, no updates — immutable log)
- Dharma rules: evaluated before tool dispatch, can veto
- Mandala compartments: LMDB sub-database per compartment

**Reused from v2**:
- `core/whitemagic-rust/src/sutra_kernel/dharma_engine.rs`
- `core/whitemagic-rust/src/sutra_kernel/zodiac_ledger.rs`
- `core/whitemagic/core/dharma/` — rule definitions (ported to Rust/Koka)

### Phase 7: Polyglot Acceleration

**Goal**: Integrate Julia (jlrs), Haskell (GHC .so), Zig (C ABI), and
Koka (compiled .so) as in-process accelerators.

**Deliverables**:
- `wm-polyglot` crate:
  - Polyglot registry (which languages are available, capabilities)
  - Julia bridge (jlrs embedded runtime, persistent tasks)
  - Haskell bridge (GHC-compiled .so, FFI)
  - Zig bridge (C ABI, link-time integration)
  - Koka bridge (C ABI, runtime dlopen)
  - Fallback chain: polyglot → Rust native → Python
- Julia modules:
  - `monte_carlo.jl` — MC simulation, Bayesian optimization
  - `quantum_geometry.jl` — Quantum-inspired geometry
  - `drift_detection.jl` — Distribution drift detection
  - `sde_solvers.jl` — Stochastic differential equations
- Haskell modules:
  - `Topology.hs` — DAG cycle detection, topological sort
  - `Verification.hs` — Formal verification of association graphs
- Zig module:
  - `trn_gate.zig` — Ultra-low-latency TRN hard gate
- Koka modules:
  - `dharma_rules.kk` — Effect-typed governance rules
  - `karma_verify.kk` — Karma chain verification
- Custom Julia system image (pre-compiled for instant startup)
- Build system: `justfile` targets for each language

**Key decisions**:
- Julia: jlrs async runtime, persistent tasks for stateful functions
- Haskell: GHC `-shared -dynamic` for .so, C ABI for FFI
- Zig: `zig build-obj -fPIC -O ReleaseFast` for C ABI objects
- Koka: `koka -c` for C output, compile to .so
- All polyglot libraries are optional — system runs with Rust-only
- `WM_POLYGLOT=0` disables all polyglot (Rust-only mode)
- `WM_POLYGLOT=julia,haskell` enables specific languages

**Reused from v2**:
- `core/whitemagic-rust/crates/wm-evolution/` — MC simulation, quantum,
  SDE, Bayesian, MCMC, rare event, sensitivity (Rust → adapted for jlrs)
- `core/whitemagic-rust/src/zig_bridge.rs` — Zig FFI pattern
- `core/whitemagic-rust/src/zig_ffi.rs` — Zig FFI declarations
- `polyglot/bridges/` — Julia/Haskell bridge logic (algorithms, not
  subprocess spawning)

### Phase 8: MCP Server & Python Shell

**Goal**: Thin Python MCP server that delegates everything to Rust via
PyO3.

**Deliverables**:
- `wm-mcp` crate:
  - PyO3 bindings for all Rust subsystems
  - Python module: `whitemagic_v4` (importable from Python)
  - MCP protocol handler (JSON-RPC over stdio)
- Python MCP server (~500 lines):
  - stdin/stdout JSON-RPC loop
  - Tool list discovery (queries Rust registry)
  - Tool dispatch (calls Rust via PyO3)
  - ONNX embedding fallback (if Candle not available)
  - HuggingFace tokenizer integration
  - Environment variable configuration
- MCP configuration template for Claude Desktop / Cursor / Windsurf
- `wm` CLI tool (Rust binary):
  - `wm quickstart` — Run demo
  - `wm doctor` — Diagnose issues
  - `wm stats` — Show resource usage
  - `wm brain-wave` — Show current brain-wave state
  - `wm polyglot` — Show polyglot status

**Key decisions**:
- Python is optional — `wm-mcp` can serve MCP directly over stdio in
  pure Rust (using `rmcp` or custom JSON-RPC)
- PyO3 bindings are feature-gated (`pyo3` feature on wm-mcp)
- Python shell only for ecosystem access (ONNX, HuggingFace)
- CLI tool is a separate binary in the workspace

### Phase 9: Tool Porting & Fractal Meta-Tool — ✅ SUBSTANTIVELY COMPLETE (126/877 tools ported, Tiers 1–7)

**Goal**: Port the 800+ tools from v2 Python to Rust trait objects. Each
tool self-tracks effectiveness.

**Deliverables**:
- `wm-tools` crate:
  - Tool trait implementation framework
  - ToolStats atomic tracking (call_count, success_rate, latency, CPU)
  - Tool registration (compile-time macro + runtime registration)
  - Tool retirement (effectiveness < 0.2 after 10 calls → cold path)
  - Tool promotion (call_count > 1000 → pre-compiled dispatch)
  - Effectiveness report tool (`tools.effectiveness_report`)
- 28 Gana-specific tool modules:
  - Horn: pipeline, system building, invocation, status
  - Neck: galaxy sync
  - Root: cache management
  - Room: agent management
  - Heart: anomaly detection, state management
  - Tail: (empty or minimal)
  - WinnowingBasket: memory recall, search, hybrid recall
  - Ghost: citta cycle, consciousness, smarana
  - Willow: karma verification, recording, reporting
  - Star: capabilities, dream, serendipity
  - ExtendedNet: ethics evaluation, governor, dharma validation
  - Wings: (empty or minimal)
  - Chariot: code explanation, fix generation
  - Abundance: dream cycle, lifecycle, narrative compress
  - StraddlingLegs: session management, context packing, checkpoint
  - Mound: foresight, simulation
  - Stomach: (empty or minimal)
  - HairyHead: code communities, correlation, god nodes
  - Net: association mining, emergence scan
  - TurtleBeak: task distribution
  - ThreeStars: explanation, bicameral reasoning, think
  - Dipper: cognitive action loop, mode, homeostasis
  - Ox: archaeology search, learning, pattern learning
  - Girl: consciousness token economy
  - Void: galaxy dashboard, backup, taxonomy, export
  - Roof: mandala creation, shelter
  - Encampment: memory creation, fast write, consolidation
  - Wall: anti-loop, boundary check, dharma audit
- Tool discovery: `tools.list`, `tools.search`, `tools.categories`
- Tool effectiveness: `tools.effectiveness_report`, `tools.retire`,
  `tools.promote`

**Key decisions**:
- Tools are registered via `#[tool(gana = Gana::Horn)]` proc macro
- Each tool is a struct implementing `Tool` trait
- Tool args are deserialized via serde (JSON → strongly typed)
- Tool stats are `Arc<ToolStats>` (shared, atomic, lock-free)
- Retirement: tool is moved to a cold registry (still callable but not
  advertised in `tools.list`)

**Reused from v2**:
- Tool definitions from `core/whitemagic/tools/registry_defs/` —
  parameter schemas, descriptions (ported to Rust structs)
- Tool handler logic from `core/whitemagic/tools/handlers/` —
  business logic (ported to Rust)
- PRAT mappings from `core/whitemagic/tools/prat_mappings.py` —
  Gana → tool name mapping (ported to Rust enum)

### Phase 10: Testing, Benchmarking & Documentation

**Goal**: Comprehensive test suite, benchmarks, and documentation.

**Deliverables**:
- Unit tests for every crate (target: 90% coverage)
- Integration tests for the full dispatch pipeline
- Benchmark suite:
  - LMDB vs SQLite (read/write/scan latency)
  - Tantivy vs FTS5 (indexing speed, query latency, recall)
  - Dispatch pipeline latency (v2 Python vs v3 Rust)
  - Brain-wave eco mode (idle CPU usage, transition latency)
  - Polyglot acceleration (Julia jlrs vs subprocess, Rust native vs Python)
  - Memory footprint (v2 vs v3 at idle and under load)
- Property-based tests (proptest) for memory operations
- Fuzz tests for dispatch pipeline (cargo-fuzz)
- Documentation:
  - Architecture document (this file, expanded)
  - API reference (rustdoc)
  - Migration guide (v2 → v3)
  - Resource impact disclosure (updated for v3)
  - Quickstart guide
  - Polyglot build guide
- CI pipeline (GitHub Actions) ✅:
  - fmt + clippy + test on every push
  - bench-compile check
  - (TODO: benchmark on release tags, cross-platform builds)

---

## 9. Crate Structure

```
whitemagic-v4/
├── Cargo.toml                    # Workspace root
├── rustfmt.toml
├── clippy.toml
├── .gitignore
├── README.md
├── AGENTS.md
├── docs/
│   ├── STRATEGY.md               # This document
│   ├── architecture/
│   │   ├── MEMORY.md             # LMDB design details
│   │   ├── DISPATCH.md           # Pipeline design details
│   │   ├── CONSCIOUSNESS.md      # Citta + brain-wave design
│   │   └── POLYGLOT.md           # Polyglot integration details
│   ├── phases/
│   │   ├── PHASE_0.md
│   │   ├── PHASE_1.md
│   │   └── ...
│   └── decisions/
│       └── ADR_001_LMDB.md       # Architecture Decision Records
├── crates/
│   ├── wm-core/                  # Core types, traits, Gana enum
│   ├── wm-memory/                # LMDB + Tantivy + LanceDB
│   ├── wm-dispatch/              # Tool dispatch pipeline
│   ├── wm-consciousness/         # Citta, dream, brain-wave
│   ├── wm-governance/            # Dharma, karma, mandala
│   ├── wm-mcp/                   # PyO3 bindings, MCP server
│   ├── wm-polyglot/              # Julia/Haskell/Zig/Koka bridges
│   ├── wm-substrate/             # Hardware metrics, Harmony Vector (Lakshmi)
│   ├── wm-reflex/                # Tier-0 reflex dispatch (microsecond path)
│   ├── wm-timescale/             # Multi-timescale event bus (5 tiers)
│   ├── wm-workspace/             # Global workspace bus (salience arbitration)
│   ├── wm-selfmodel/             # Predictive introspection (metrics, forecasting, alerts)
│   ├── wm-bicameral/             # Dual-hemisphere reasoning (left/right + consensus)
│   ├── wm-drive/                 # Emotion & Drive Core (intrinsic motivation)
│   └── wm-tools/                 # 169 tool implementations (126 cognitive + 15 v4 + 13 N16-N21 + 5 RSI + 10 sensorimotor)
├── polyglot/
│   ├── koka/                     # Koka source (.kk files)
│   ├── haskell/                  # Haskell source (.hs files)
│   ├── zig/                      # Zig source (.zig files)
│   └── julia/                    # Julia source (.jl files)
├── assets/
│   └── logo.svg
└── justfile                      # Build targets
```

### Crate Dependencies

```
wm-core:        (no internal deps)
wm-memory:      wm-core
wm-dispatch:    wm-core, wm-memory, wm-governance
wm-consciousness: wm-core, wm-memory
wm-governance:  wm-core, wm-memory
wm-polyglot:    wm-core (optional: jlrs, libloading)
wm-substrate:   wm-core
wm-reflex:      wm-core
wm-timescale:   wm-core, wm-consciousness
wm-workspace:   wm-core
wm-selfmodel:   wm-core, wm-substrate
wm-bicameral:   wm-core, wm-memory
wm-drive:       wm-core
wm-tools:       wm-core, wm-memory, wm-dispatch, wm-consciousness, wm-governance,
                wm-substrate, wm-reflex, wm-timescale, wm-workspace,
                wm-selfmodel, wm-bicameral, wm-drive
wm-mcp:         all crates + pyo3 (optional)
```

---

## 10. Key Dependencies

### Rust Crates

| Crate | Version | Purpose |
|---|---|---|
| `tokio` | 1.x | Async runtime (epoll, timerfd, io) |
| `rayon` | 1.x | Data parallelism (SIMD batch ops) |
| `lmdb-rkv` | 0.14 | LMDB bindings (memory-mapped KV store) |
| `tantivy` | 0.22+ | Full-text search engine |
| `lancedb` | 0.x | Vector database (disk-based HNSW) |
| `candle-core` | 0.x | Pure Rust ML (embeddings fallback) |
| `ndarray` | 0.16 | N-dimensional arrays (citta vectors) |
| `wide` | 0.7 | SIMD f32x8 operations |
| `serde` | 1.x | Serialization (JSON, MessagePack) |
| `rmp-serde` | 1.x | MessagePack serialization |
| `pyo3` | 0.22+ | Python bindings (optional feature) |
| `jlrs` | 0.21+ | Julia embedding (optional feature) |
| `libloading` | 0.8 | Dynamic library loading (Koka/Haskell .so) |
| `proptest` | 1.x | Property-based testing |
| `criterion` | 0.5 | Benchmarking |
| `clap` | 4.x | CLI argument parsing |
| `tracing` | 0.1 | Structured logging |

### External Tools (Build-time)

| Tool | Purpose | Required? |
|---|---|---|
| Rust 1.85+ | Core language | Yes |
| Python 3.10+ | MCP shell, ONNX | Optional (feature-gated) |
| Julia 1.10+ | Monte Carlo, quantum | Optional (feature-gated) |
| GHC 9.14+ | Haskell verification | Optional (feature-gated) |
| Zig 0.13+ | TRN gate | Optional (feature-gated) |
| Koka v3.2+ | Dharma rules | Optional (feature-gated) |

---

## 11. What's Preserved from v2

### Design Patterns (ported to Rust)

- **28 Gana taxonomy** — Enum with all 28 variants, trait dispatch
- **14-galaxy memory** — LMDB sub-databases
- **6D holographic coordinates** — Composite LMDB keys
- **Dharma ethical governance** — Rust trait + Koka effect verification
- **Karma ledger** — LMDB append-only log
- **Dream cycle (12 phases)** — tokio tasks, event-triggered
- **Citta consciousness vector (16D)** — ndarray with SIMD
- **Session recording** — LMDB with sequence numbers
- **Homeostatic loop** — Event-driven (not polling)
- **Apotheosis engine** — Self-improvement monitoring
- **Mindful forgetting** — LMDB TTL + significance scoring
- **Association mining** — Cross-galaxy link discovery
- **Constellation detection** — Memory clustering
- **Cross-subsystem patterns** — Event bus (tokio channels)

### Reusable Rust Code (from v2)

- `core/whitemagic-rust/src/search/` — BM25, hybrid search, RRF, patterns
- `core/whitemagic-rust/src/safety/` — Rate limiter, circuit breaker, validators
- `core/whitemagic-rust/src/sutra_kernel/` — Dharma engine, zodiac ledger
- `core/whitemagic-rust/crates/wm-evolution/` — MC simulation, quantum, SDE
- `core/whitemagic-rust/crates/wm-neuro/` — Predictive coding, thalamic gating
- `core/whitemagic-rust/crates/wm-llama/` — llama.cpp bindings
- `core/whitemagic-rust/crates/wm-cascade-pyo3/` — PyO3 patterns
- `core/whitemagic-rust/src/zig_bridge.rs` — Zig FFI pattern
- `core/whitemagic-rust/src/zig_ffi.rs` — Zig FFI declarations

### Reusable Algorithms (ported from Python to Rust)

- `core/whitemagic/core/memory/holographic.py` — Coordinate math
- `core/whitemagic/core/memory/consolidation.py` — Consolidation logic
- `core/whitemagic/core/memory/mindful_forgetting.py` — Forgetting algorithm
- `core/whitemagic/core/memory/association_miner.py` — Association mining
- `core/whitemagic/core/memory/constellations.py` — Clustering
- `core/whitemagic/core/consciousness/citta_cycle.py` — Citta logic
- `core/whitemagic/core/consciousness/coherence.py` — Coherence measurement
- `core/whitemagic/core/dreaming/dream_cycle.py` — Dream phases
- `core/whitemagic/core/dharma/` — Governance rules
- `core/whitemagic/harmony/homeostatic_loop.py` — Homeostatic logic

---

## 12. What's Dropped from v2

- **SQLite entirely** — LMDB + Tantivy + LanceDB
- **FTS5** — Tantivy
- **Python middleware chain** — Rust trait dispatch
- **Subprocess polyglot bridges** — In-process embedding/FFI
- **HNSW Python implementation** — LanceDB
- **FastEmbed/ONNX as primary** — Candle (Rust), ONNX as fallback
- **16 sleeping threads** — Single tokio runtime with work-stealing
- **Polling-based background loops** — Event-driven wake
- **Python singleton registry** — Rust ownership + Arc
- **Python conftest fixtures** — Rust test harness + proptest

---

## 13. Resource Impact Projection (v4 vs v2)

| Resource | v2 (current) | v4 (projected) | Improvement |
|---|---|---|---|
| **RAM** | 50-150 MB | 10-30 MB | 5x reduction |
| **CPU (idle)** | 1-6% | 0% (Delta mode) | Zero idle CPU |
| **CPU (active)** | spikes | lower spikes (Rust) | 2-5x faster |
| **Disk writes** | 2-6 GB/day | 0.2-0.6 GB/day | 10x reduction |
| **SSD wear** | ~2 TB/year | ~0.2 TB/year | 10x reduction |
| **Battery drain** | 10-20% faster | 2-5% faster | 4x reduction |
| **Swap** | 200-400 MB | 0 MB (no subprocesses) | Eliminated |
| **Threads** | 16 sleeping | 1-3 (tokio work-stealing) | 5x reduction |
| **Startup time** | 140ms (SQLite) | 8ms (LMDB) | 17x faster |
| **Read latency** | 1-3ms (SQLite) | 0.01ms (LMDB mmap) | 100x faster |
| **Write latency** | 23ms (SQLite WAL) | 2ms (LMDB batch) | 10x faster |

---

## 14. Success Criteria

1. **Zero idle CPU**: In Delta brain-wave mode, `top` shows 0% CPU for
   the wm process.
2. **10x less disk I/O**: LMDB + Tantivy produce 10x fewer disk writes
   than SQLite + FTS5 for the same workload.
3. **100x faster reads**: Memory reads complete in <0.1ms (LMDB mmap)
   vs 1-3ms (SQLite).
4. **No subprocess spawning**: No zombie processes, no swap leaks, no
   process management complexity.
5. **800+ tools functional**: All v2 tools have Rust implementations
   with self-tracked effectiveness.
6. **Polyglot acceleration works**: Julia MC simulation runs in-process
   via jlrs with <1ms call latency after warmup.
7. **MCP protocol compatible**: Existing MCP clients (Claude Desktop,
   Cursor, Windsurf) can connect without changes.
8. **Honest resource disclosure**: `wm stats` reports accurate CPU time,
   memory usage, disk I/O, and brain-wave state distribution.

---

## 15. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Koka not production-ready | High | Medium | Rust-native fallback for all Koka modules |
| jlrs API breaking changes | Medium | Medium | Pin jlrs version, wrap in trait abstraction |
| LanceDB maturity | Medium | Medium | HNSW fallback in pure Rust (from v2 code) |
| Candle model support | Medium | Low | ONNX fallback via Python (PyO3) |
| PyO3 version conflicts | Low | High | Feature-gate Python, support pure-Rust MCP |
| Scope creep | High | High | Phased delivery, each phase independently shippable |
| v2 feature regression | Medium | High | Port tests as specs, run v2/v3 comparison benchmarks |

---

## 16. v3.1 Roadmap — "The System Becomes Self-Aware"

### Context

v3.0 delivers a working cognitive OS skeleton: 9 crates, 568 tests, 65+ tools,
~1.1µs pipeline overhead, live MCP server with brain-wave eco mode, citta
heartbeat, governed autonomy, and outward spiral detection. v4 extends this
to 19 crates, 2,818 tests, 176 tools, adding reflex dispatch, multi-timescale
event bus, global workspace, self-model, bicameral reasoning, drive core,
local AI integration, and embodiment I/O. The consciousness systems feed
back into behavior via citta coherence gating and karma feedback, and the
tool catalog covers ~19.3% of v2's 877+ tools.

**v2 codebase scale** (researched from `/home/lucas/Desktop/WHITEMAGIC`):

| Component | Lines | Notes |
|---|---|---|
| v2 Python core | 446K | 877+ tools, 28 Gana, 14 galaxies |
| v2 Rust bridge | 95K | Holographic index, MC simulation, neuro, WASM |
| v2 tools subsystem | 90K | Handlers, registry, dispatch, middleware |
| WHITEMAGIC-CORE | 7K | Simplified 70-tool version, XP leveling |
| v4 (current) | ~112K | 176 tools, 19 crates, pure Rust |

**Key v2 algorithms to port** (identified during research):

| Algorithm | v2 Location | Lines | Priority |
|---|---|---|---|
| Memory consolidation (hippocampal replay) | `core/memory/consolidation.py` | 1142 | ✅ Ported (Phase 1 + 6.5) |
| Mindful forgetting (multi-signal retention) | `core/memory/mindful_forgetting.py` | 498 | ✅ Ported (Phase 1 + 6.1) |
| Association miner (keyword overlap + temporal) | `core/memory/association_miner.py` | 770 | ✅ Ported (Phase 1 + 6.2) |
| Constellation detection (5D clustering) | `core/memory/constellations.py` | 974 | ✅ Ported (Phase 6.6) |
| Sleep consolidation (cross-galaxy transfer) | `core/memory/sleep_consolidation.py` | 528 | ✅ Ported (Phase 6.5) |
| Holographic coordinates (5D encoding) | `whitemagic-rust/crates/wm-core/src/holographic.rs` | 300 | ✅ Ported (Phase 5.7 + 6.3) |
| Citta vector (16D with subspaces) | `core/consciousness/citta_vector.py` | 393 | ✅ Ported (Phase 5) |
| Coherence metric (8 dimensions) | `core/consciousness/coherence.py` | 460 | ✅ Ported (Phase 5) |
| Apotheosis engine (self-monitoring) | `core/consciousness/apotheosis_engine.py` | 956 | ✅ Ported (Phase 5) |
| Dream cycle (12 phases, full logic) | `core/dreaming/dream_cycle.py` | 1859 | ✅ Ported (Phase 5 + 5.1) |
| PRAT tool→Gana mappings | `tools/prat_mappings.py` | 985 | Pending (Phase 9) |
| Predictive coding (neuro) | `whitemagic-rust/crates/wm-neuro/` | 84+ | Pending (Phase 7) |

### v3.1 Phases

#### Phase 5.1: Wire Dream Cycle to Memory Store ✅ COMPLETE

**Goal**: Make the 12 dream phases actually process LMDB memories.

**Deliverables**:
- Triage: scan recent memories, classify by importance/urgency
- Consolidation: merge duplicates (content_hash matching), promote high-value
- Serendipity: keyword overlap analysis → propose associations
- Governance: run Dharma checks on pending memories
- Narrative: compress memory chains into summary memories
- Kaizen: analyze tool stats, identify underperformers
- Oracle: pattern detection from association graph
- Decay: apply mindful forgetting (multi-signal retention scoring)
- Constellation: grid-based density clustering in tag space
- Prediction: temporal drift detection on memory access patterns
- Enrichment: extract entities from memory content
- Harmonize: balance galaxy weights

**Key decisions**:
- Each phase reads/writes via `MemoryStore` (LMDB)
- No destructive operations — decay lowers importance, never deletes
- Sleep consolidation transfers high-value memories to codex galaxy
- Port v2's `RetentionSignal` / `RetentionVerdict` pattern for Decay phase
- Port v2's `ProposedLink` pattern for Serendipity phase

#### Phase 5.2: Brain-Wave-Aware Tool Listing & Dispatch ✅ COMPLETE

**Goal**: `tools/list` filters by current brain-wave state.

**Deliverables**:
- `handle_tools_list` uses `ToolRegistry::available_in(eco_mode.current())`
- In Delta: return empty list (dormant)
- In Theta: return dream-related tools only
- In Alpha: return read-only tools (memory.read, memory.search, gnosis)
- In Beta/Gamma: return all tools
- `gnosis` response includes brain-wave state and available tool count

#### Phase 5.3: Citta → Context Feedback Loop ✅ COMPLETE

**Goal**: Citta coherence affects tool dispatch decisions.

**Deliverables**:
- `Context` gains `citta_coherence: f32` and `citta_valence: f32` fields
- Dispatch pipeline checks coherence before writes (refuse if < 0.3)
- Karma outcomes feed back into citta vector (Sattvic → +joy, Tamasic → −joy)
- Presence activity ratio modulates brain-wave transitions
- Apotheosis score influences tool retirement threshold

#### Phase 5.4: Tool Catalog Expansion (13 → 50) ✅ COMPLETE

**Goal**: Port high-value v2 tools to reach ~50 tools.

**Delivered**: 42 new tools in `crates/wm-tools/src/expansion.rs` across 10 categories:
- Memory ops (9): consolidate, decay, batch_read, update, tag, stats, hybrid_recall, count, tags
- Session (5): start, checkpoint, recall, end, list
- Consciousness (5): citta.status, citta.reflect, citta.coherence, dream.status, dream.trigger
- Tools management (2): effectiveness_report, retire
- Patterns (3): pattern.search, salience.spotlight, serendipity.surface
- Constellation (2): detect, list
- Galaxy (3): stats, export, import
- Karma (2): history, clear
- Dharma (3): rules, audit, profiles
- Agents (3): register, list, heartbeat
- Tasks (2): distribute, status
- System (3): health, config, flush
- Association mining (1): associate_mine
- **Total: 50+ tools** (8 base + 42 expansion + meta tools), 277 tests passing

#### Phase 5.5: NLU Router Expansion — COMPLETE

**Goal**: Expand `classify()` from 7 patterns to 30+.

**Deliverables**:
- Expanded `classify()` to 40+ patterns covering all expansion tools
- Routing for: consolidate, decay, associate_mine, session, citta, dream,
  constellation, pattern, salience, serendipity, agent, task, galaxy,
  karma, dharma, system, tools.effectiveness, memory.nearby
- Confidence scoring with fallback to `gnosis` when no match
- Multi-word intent matching with specificity ordering (specific before general)
- Expanded `extract_payload` from 3 to 10 tool patterns
- 39 new NLU routing tests (66 total in wm-tools)

#### Phase 5.6: CLI Completion — COMPLETE

**Goal**: Implement `wm doctor`, `wm quickstart`, `wm polyglot`.

**Deliverables**:
- `wm doctor`: Check LMDB health, galaxy counts, Tantivy index, brain-wave state,
  subsystem flags, citta coherence, dream cycle, tool registry, karma chain
- `wm quickstart`: 6-step guided demo — create memories, list, full-text search,
  galaxy stats, consciousness dashboard, tool count
- `wm polyglot`: Show Julia/Haskell/Zig/Koka runtime status with build instructions
- Added `store()` and `registry()` accessors to `McpServer`

#### Phase 5.7: Holographic Memory Coordinates — COMPLETE

**Goal**: Port v2's 5D holographic coordinate system.

**Deliverables**:
- `Coordinate5D` struct (x, y, z, w, v) with SHA-256 content encoding
- `Zone` enum (Core, InnerRing, MidRing, OuterRing, FarEdge)
- `Coordinate5D::encode(text)` — deterministic hash → 5D position
- `Coordinate5D::encode_with_context(text, temporal, importance)`
- `distance_to()` and `semantic_distance_to()` (weighted) metrics
- Integrated `coord5d` field into `MemoryMetadata` with `#[serde(default)]` for backward compat
- Spatial queries: `find_nearby(center, candidates, radius)` — sorted by distance
- `memory.nearby` tool — scans galaxy, finds memories near query text
- 14 new coordinate tests + 1 NLU routing test

### v3.1 Success Criteria — ALL MET

- 350+ tests passing (up from 239) — **568 passing** ✅ (exceeded target)
- 50+ tools registered (up from 13) — **57 registered** ✅
- Dream cycle actually reads/writes LMDB memories ✅
- `tools/list` filters by brain-wave state ✅
- Citta coherence affects dispatch decisions ✅
- `wm doctor` and `wm quickstart` fully functional ✅
- NLU router handles 40+ intent patterns ✅
- Holographic coordinates enable spatial memory queries ✅

### v3.2 Quality & CI — COMPLETE

- Clippy cleanup: 400+ warnings → 0 (pedantic + nursery enforced)
- Criterion benchmark suite: LMDB put/get/scan, Tantivy search, pipeline dispatch, dream cycle
- GitHub Actions CI: fmt + clippy (-D warnings) + test + bench-compile
- Strict `clippy.toml`: complexity thresholds, enum variant size, doc-valid-idents
- 339 tests passing, fmt clean, 0 clippy warnings

### v3.3 Phase 6: Memory Intelligence — COMPLETE

The memory substrate (LMDB + Tantivy) is solid. Phase 6 enriches the memory
**model and intelligence layer** to reach v2 parity on proven patterns, then
exceeds it with Rust-native performance. Each sub-phase is independently
deliverable and testable.

#### Phase 6.1: Enriched Memory Model — COMPLETE

**Goal**: Add the metadata fields that downstream features depend on.

New `MemoryType` enum: `ShortTerm`, `LongTerm`, `Emotional`, `Narrative`,
`Symbolic`, `Pattern`, `Procedural`, `Citta`.

New `MemoryMetadata` fields:
- `memory_type: MemoryType` — distinguishes memory kinds
- `neuro_score: f32` — dynamic strength (decays over time, boosts on recall)
- `novelty_score: f32` — decays as info becomes familiar
- `emotional_valence: f32` — -1.0 to 1.0 (positive/negative)
- `emotional_weight: f32` — resonance score
- `is_protected: bool` — hard protection from forgetting
- `is_private: bool` — exclude from MCP tool responses
- `model_exclude: bool` — exclude from AI model context windows
- `source: String` — provenance ("user", "tool", "inferred", "web")
- `source_trust: f32` — 0.0-1.0 trust score (defends against poisoning)
- `half_life_days: f32` — per-memory configurable decay rate
- `recall_count: u64` — independent from `access_count`
- `version: u64` — multi-agent cache coherence
- `agent_id: String` — last writer identity

Updates to `Memory` methods:
- `recall()` — boosts `neuro_score` using Hebbian formula, increments `recall_count`
- `decay()` — exponential decay based on `half_life_days` and time since last recall
- `with_memory_type()`, `with_emotional_valence()`, `with_protection()` builders

**Dependency**: None — this is the foundation for all subsequent phases.

#### Phase 6.2: Typed Association Links + Hebbian Learning — COMPLETE

**Goal**: Upgrade associations from static string-typed edges to dynamic
neural connections.

New `LinkType` enum: `Related`, `Extends`, `Contradicts`, `Supersedes`,
`Temporal`, `Causal`, `Cascade`.

Updated `Association` struct:
- Replace `association_type: String` with `link_type: LinkType`
- Add `activation_count: u64`, `last_activated: DateTime<Utc>`
- `activate()` — Hebbian co-activation strengthening (strength += 0.05, capped at 1.0)
- `decay(factor)` — idle decay (strength *= factor, floored at 0.1)

**Dependency**: Phase 6.1 (for `neuro_score` interaction).

#### Phase 6.3: Semantic Coordinate Encoding

**Goal**: Replace SHA-256 hash-based x/y/z with semantically meaningful
coordinates so similar content clusters spatially.

Two-step approach:
1. **Bridge** (no external deps): Use Tantivy term vectors / TF-IDF cosine
   similarity to derive x/y/z axes. Content with overlapping terms gets
   nearby coordinates.
2. **Full** (with LanceDB): Use embedding model (Candle/ONNX) to compute
   x/y/z from content embeddings, matching v2's anchor-embedding approach.

v2's axis semantics for reference:
- **X**: Logic ↔ Emotion
- **Y**: Micro ↔ Macro (concrete vs abstract)
- **Z**: Time / Chronos (past vs future)
- **W**: Importance / Gravity
- **V**: Vitality / Galactic Distance
- **U**: Galaxy Affinity (zone-based)

**Dependency**: Phase 6.1 (for `memory_type` to inform axis computation).
Phase 6.3-full depends on LanceDB (Phase A).

#### Phase 6.4: Secondary LMDB Indexes — ✅ COMPLETE

**Goal**: Replace O(n) full-scan queries with O(log n) indexed lookups.

Implemented index sub-databases:
- `idx_content_hash`: `galaxy:hash → UUID` for O(1) dedup
- `idx_tags`: `galaxy:tag → [UUIDs]` (DUP_SORT) for tag-based queries
- `idx_importance`: `galaxy:f32_be → [UUIDs]` (DUP_SORT) for range queries
- `idx_temporal`: `galaxy:i64_be → [UUIDs]` (DUP_SORT) for time-range queries

`MemoryStore::put`, `put_batch`, `delete` maintain indexes atomically.
`query()` uses indexed fast paths for single-dimension queries.
`find_by_content_hash` now O(1) via index. 449 tests, 0 clippy warnings.

#### Phase 6.5: Strategy Synthesis + Sleep Consolidation — ✅ COMPLETE

**Goal**: Upgrade dream cycle from duplicate-merging to meta-insight
generation and cross-galaxy transfer.

Strategy synthesis:
1. Cluster memories by tag overlap + association overlap
2. Identify high-value clusters (frequent access, strong importance, pattern relevance)
3. Synthesize compressed "strategy memories" from cluster themes
4. Promote strategy memories to Codex galaxy with `MemoryType::Pattern`

Sleep consolidation transfer routes:
- sessions → codex/research (episodic → semantic)
- citta → aria (emotional → identity)
- dreams → research (creative → knowledge)
- universal → appropriate galaxy (reclassification)

**Dependency**: Phase 6.1 (memory types), Phase 6.2 (association overlap).
**Delivered**: `wm-consciousness/src/strategy.rs` — Jaccard similarity clustering,
union-find, strategy memory synthesis, sleep consolidation transfer routes.
Dream cycle consolidation phase upgraded. 8 tests.

#### Phase 6.6: Constellation Detection — ✅ COMPLETE

**Goal**: Replace grid-based stub with proper density clustering.

Implement:
- Grid-based density scan (Rust native, no external deps)
- Optional HDBSCAN via `hdbscan-rs` crate if available
- Hungarian optimal centroid matching for drift tracking across runs
- Persist constellations as metadata (not new memories — avoids bloat)
- Name constellations from dominant tags/keywords

**Dependency**: Phase 6.3 (semantic coordinates for meaningful clustering).
**Delivered**: `wm-consciousness/src/constellation.rs` — grid-based density
clustering in 3D semantic space, flood fill, drift tracking, constellation
naming by dominant tags. Dream cycle constellation phase upgraded. 8 tests.

#### Phase 6.7: Advanced Neural Features — ✅ COMPLETE

**Goal**: Port v2's neuroscience-inspired memory dynamics.

Modules to port (in priority order):
1. **Spreading activation** — activation spreads through association graph;
   recalling one memory activates connected ones (460 lines in v2)
2. **Surprise gate** — novelty detection gates memory encoding (401 lines)
3. **Ripple tagging** — marks memories for consolidation during dream cycle (259 lines)
4. **Neuromodulation** — dopamine/serotonin analogs modulate retention (286 lines)
5. **Metaplasticity** — learning rate adapts based on prior activation (190 lines)

Each is a self-contained module that hooks into the dream cycle or dispatch
pipeline. Port one at a time with tests.

**Dependency**: Phase 6.1 (neuro_score), Phase 6.2 (association graph).
**Delivered**: `wm-consciousness/src/neural.rs` — 5 modules: SpreadingActivation
(used in Oracle phase), SurpriseGate, RippleTagger (used in Enrichment phase),
Neuromodulator (used in Harmonize phase), Metaplasticity. 12 tests.

#### Phase 6.8: Dynamic Galaxy Management — ✅ COMPLETE

**Goal**: Support project-scoped galaxies beyond the fixed 14.

Implement:
- Galaxy registry (JSON or LMDB sub-DB) tracking known galaxies
- `galaxy.create`, `galaxy.switch`, `galaxy.list`, `galaxy.status` tools
- Each dynamic galaxy gets its own LMDB sub-DB
- One active galaxy at a time for tool dispatch

**Dependency**: None (independent, but lower priority than intelligence
features).
**Delivered**: `wm-memory/src/galaxy_registry.rs` — LMDB-backed registry with
create, get, list, delete, galaxy_db, exists, count. Metadata stored via
MessagePack. 11 tests.

### Post-Phase-6: Governed Autonomy Roadmap (v3.4) — Phases A-F COMPLETE

The governed autonomy workstream implements the Mandala OS governance layers
(Lakshmi, Tiferet, Yama, Gnosis) within v3's Rust crate structure. This ensures
any future autonomous cognition is intentional, efficient, transparent, deep,
actionable, and spiraling outward. All phases A-F are complete.

Full spec: `whitemagic-v3-governed-autonomy-plan.md` (desktop).
Investigation: `whitemagic-v2-autonomous-activity-investigation.md` (desktop).

#### Existing Infrastructure (Already Wired)

v3 already has significant governance plumbing — the key gap (Homeostasis
never populated with real hardware data) is now RESOLVED as of v3.4 Phases A-F:

- `BrainWave` enum + `BrainWaveTracker` (wm-core) — 5-state eco mode, event-rate driven
- `EcoModeController` + `SubsystemFlags` (wm-consciousness) — 9 per-state subsystem flags
- `Homeostasis` struct (wm-governance) — `cpu_load`, `memory_pressure`, `active`, `health_score()`, `is_stressed()`
- `DharmaGate` (wm-governance) — Ahimsa, Satya sutras + harmony vector thresholds + strict mode
- `DharmaGate::update_homeostasis()` — ✅ NOW CALLED with real data from `SubstrateMonitor` on every MCP request
- `dharma.status` tool — exposes homeostasis + sutras
- Dispatch pipeline — checks brain-wave compatibility + Dharma verdicts before tool execution
- `run_async()` MCP server — `tokio::select!` with zero-CPU dormancy
- `wm-substrate` crate (v3.4 Phase A) — reads real `/proc` + `/sys` hardware metrics
- `EcoModeController::apply_harmony()` (v3.4 Phase B) — gates brain-wave transitions by hardware health
- `ResourceRules` (v3.4 Phase C) — budgets, novelty, purpose, human review
- `gnosis.status/history/explain` tools (v3.4 Phase D) — full governance transparency

#### Phase A: Harmony Vector (Lakshmi) — ✅ COMPLETE

**Goal**: Read real hardware metrics and expose them as a `HarmonyVector`.

**Implemented**:
- New crate `wm-substrate` with `HarmonyVector`, `SubstrateMonitor`, `ThermalState`, `BatteryState`, `GunaTag`
- `SubstrateMonitor` reads `/proc/loadavg`, `/proc/meminfo`, `/sys/class/thermal/`, `/sys/class/power_supply/`
- `HarmonyVector`: CPU load, memory pressure, swap usage, thermal state, battery, disk I/O, Guna classification, timestamp
- `SubstrateMonitor`: ring buffer history (configurable capacity, default 100)
- `From<HarmonyVector> for Homeostasis` conversion in `wm-governance`
- `harmony.vector` MCP tool (Gana::Dipper): returns current Harmony Vector as JSON
- `harmony.history` MCP tool (Gana::Dipper): returns historical Harmony Vector data
- `McpServer` holds `SubstrateMonitor`, calls `refresh_homeostasis()` on every request
- `with_defaults()` samples hardware immediately on startup
- 19 new tests

**Dependency**: None (pure Rust, reading `/proc` and `/sys`)
**Mandala OS mapping**: Lakshmi (Harmony Monitor) + Annamaya Kosha (Hardware Layer)

#### Phase B: Resource Gating (Tiferet) — ✅ COMPLETE

**Goal**: Wire Harmony Vector into brain-wave state transitions.

**Implemented**:
- `EcoModeController::apply_harmony(health_score: f32)` in `wm-consciousness`
- Health < 0.3 (stressed): caps brain-wave at Alpha — no high-power states
- Health < 0.5 (strained): caps at Beta — no Gamma bursts
- Health >= 0.5: no restriction
- Forces descent when current state exceeds the cap (via `recompute` + clamp)
- Accelerates descent when stressed but already in Alpha
- Never forces ascent — only gates downward
- MCP server calls `apply_harmony` after `apply_presence` on every request
- Uses real health score from `DharmaGate::homeostasis()` (populated by `SubstrateMonitor`)
- 6 new tests

**Dependency**: Phase A
**Mandala OS mapping**: Tiferet Engine (Self-Balancing)

#### Phase C: Dharma Resource Rules (Yama) — ✅ COMPLETE

**Goal**: Add resource-aware Dharma rules for autonomous behavior governance.

**Implemented**:
- New module `wm-governance/src/resource_rules.rs`
- `ResourceRules` engine with 4 governance mechanisms:
  - **Resource budgets**: Rate-limits writes/spawns/network per minute, scaled by health score and brain-wave state (Delta=0, Theta=1/4, Alpha=1/2)
  - **Novelty requirement**: Blocks repetitive actions (same tool + same args hash) after configurable max repeats — directly prevents v2's circular thinking
  - **Purpose requirement**: Autonomous actions must declare a purpose
  - **Human review**: Autonomous actions require explicit human approval
- `ResourceRulesConfig`: Configurable limits, novelty window, max repeats, require_human_review flag
- `ResourceVerdict`: Allow / BudgetExceeded / NotNovel / RequiresHumanReview / NoPurpose
- `BudgetUsage`: Transparency snapshot for monitoring
- `ResourceRules` integrated into `McpServer` (held as `Arc<ResourceRules>`)
- 14 new tests

**Dependency**: Phase A, Phase B
**Mandala OS mapping**: Yama (Dharma Engine)

#### Phase D: Gnosis Portals — ✅ COMPLETE

**Goal**: Full transparency layer for all autonomous activity.

**Implemented**:
- `gnosis.status` MCP tool (Gana::ThreeStars): real-time view of homeostasis, resource rules budget usage, substrate snapshot, all governance layer statuses
- `gnosis.history` MCP tool (Gana::ThreeStars): historical harmony vector data with summary stats (avg CPU, memory, health score)
- `gnosis.explain` MCP tool (Gana::ThreeStars): explains governance decisions for any tool — returns Dharma verdict + Resource verdict + human-readable explanation
- NLU routing for all three tools (gnosis, transparency, governance status, explain governance, why blocked/allowed, audit history)
- All registered when dharma + substrate + resource_rules are available

**Dependency**: Phase C
**Mandala OS mapping**: Gnosis Portals (Transparency)

#### Phase E: Grounded Autonomous Cycles — ✅ COMPLETE

**Goal**: The actual cognitive cycles — governed, grounded, and transparent.

**Deliverables**:
- `consolidation.connect` cycle: proposes typed associations for disconnected
  memories (gated by Harmony Vector, requires human review)
- `consolidation.compress` cycle: proposes merging semantically overlapping
  memories (gated, human review)
- `emergence.scan` cycle: detects tag/topic emergence patterns (gated, logged)
- `retention.prune` cycle: identifies memories ready for forgetting based on
  decay + neuro_score (gated, human review for high-importance)
- All cycles: declare purpose, check Harmony Vector, have time/memory budgets,
  produce actionable output, log to Gnosis, suspend on non-novel output

**Dependency**: Phase D, Phase 6.3 (embeddings for semantic similarity)
**Mandala OS mapping**: Lila (Controlled Emergence)

#### Phase F: Outward Spiral Mechanism — ✅ COMPLETE

**Goal**: Prevent the circular thinking trap v2 fell into.

**Deliverables**:
- `SpiralTracker`: monitors scope of autonomous cycle outputs
  - Inward spiral detection: repeated examination of same memories/tags/domains
  - Outward spiral encouragement: cross-domain connections get priority
- `novelty.score` function: scores output against history, low novelty = suspended
- `spiral.report` MCP tool: shows whether autonomy is expanding or circling
- Automatic suspension after 3 identical consecutive outputs

**Dependency**: Phase E

#### Governance Design Principles

1. **Intentional**: No default-on background loops. Opt-in, purpose-gated, event-triggered.
2. **Efficient**: Harmony Vector gating, no eager prewarming, bounded computation, diminishing returns detection.
3. **Transparent**: Gnosis Portals, activity log, no hidden cognition, auditable.
4. **Deep**: Grounded in real context (codebase, goals, history), no meta-circular loops.
5. **Actionable**: Every insight has a recommended action, action verification, human-in-the-loop.
6. **Spiraling Outward**: Expanding scope, cross-domain discovery, novelty requirement.

### Post-Governance Outlook

With all governance phases (A-F), Phases 7-8, and v4 phases R1-R7 complete, the current status is:

1. ~~**LanceDB vector embeddings**~~ — ✅ Complete (in-memory `VectorStore` + LanceDB feature-gated, `memory.vector.search` tool)
2. ~~**Polyglot acceleration** (Phase 7)~~ — ✅ Complete (Julia, Haskell, Zig, Koka bridges, 51 tests)
3. **Tool catalog expansion** (Phase 9) — port v2's 877+ tools to Rust (126/877 done, ~14.4%, Tiers 1–7 complete)
4. ~~**PyO3 Python bindings** (Phase 8)~~ — ✅ Complete (PyO3 bridge, Python MCP shell, config templates)
5. ~~**Mandala compartments**~~ — ✅ Complete (4 security tiers, isolated stores)
6. **Transaction firewall** — spend limits, rate limiting, allowlist
7. **Koka effect-typed governance rules** — compile-time effect safety proofs
8. ~~**Fuzz testing**~~ (cargo-fuzz) — ✅ Complete (5 targets + 22 proptest)
9. ~~**Cross-platform CI builds**~~ — ✅ Complete (Linux, macOS, Windows)
10. **Benchmark on release tags** — performance regression tracking

### v4 CyberBrain Phases R1–R7 — ALL COMPLETE

The v4 workstream implements the CyberBrain architecture from `docs/notes/cyberbrain-roadmap-2026-08-03.md`.
All 7 phases are now complete, transforming v3 from an AI agent runtime into a real-time cognitive substrate.

| Phase | Name | Crate | Tools | Tests | Status |
|---|---|---|---|---|---|
| R1 | Reflex Tier | wm-reflex | 2 (reflex.dispatch, reflex.status) | 48 | ✅ COMPLETE |
| R2 | Multi-Timescale Event Bus | wm-timescale | 2 (timescale.status, timescale.hooks) | 34 | ✅ COMPLETE |
| R3 | Global Workspace Bus | wm-workspace | 4 (workspace.spotlight/events/publish/stats) | 51 | ✅ COMPLETE |
| R4 | Self-Model & Predictive Introspection | wm-selfmodel | 3 (selfmodel.forecast/alerts/snapshot) | 22 | ✅ COMPLETE |
| R5 | Bicameral Reasoning | wm-bicameral | 2 (bicameral.reason/status) | 36 | ✅ COMPLETE |
| R6 | Hardware-Aware Governance | wm-substrate | 2 (harmony.vector/history) | 19 | ✅ COMPLETE |
| R7 | Emotion & Drive Core | wm-drive | 2 (drive.snapshot/event) | 32 | ✅ COMPLETE |

**v4 totals**: 19 crates, 176 tools (126 cognitive + 15 v4/subsystem + 13 N16-N21 + 9 RSI + 10 sensorimotor + 3 transaction), 2,818 tests + 9 doctests, ~112,300 LOC, 0 clippy warnings.

**Deep integration** — ✅ COMPLETE:
- Drive bias → dispatch pipeline (caution gate, energy gate on writes)
- Bicameral consensus → all write-effect dispatches
- Timescale hooks → citta/dream cycles
- Workspace events → drive updates
- Self-model confidence → Context → conservative dispatch

**LLM right hemisphere** — ✅ COMPLETE:
- OpenAI-compatible API via ureq, env-configured, graceful fallback to stub

**Build optimization** — ✅ COMPLETE:
- mold linker + sccache: clean release build 50s (was 3m57s, 4.7x speedup)
- Tokio features reduced from `full` to `rt, rt-multi-thread, macros, time, io-util, io-std`
- Dev/test profiles tuned: `opt-level=0`, `debug=1`, `codegen-units=16`, `incremental=true`
- Criterion benchmarks: warmup 3s→1s, measurement 5s→2s
- `target-cpu=native` for AVX2 SIMD on Skylake+
- See `.cargo/config.toml` for mold + sccache configuration

**Migration tool** — ✅ COMPLETE (45 tests):
- Galaxy mapping, type mapping, dry run, tags, galaxy filter, multi-galaxy
- Tantivy FTS indexing during migration (added 2026-08-05)
- **Migration executed** (2026-08-05): 61,192 v2 memories read, 59,831 written, 1,361 skipped (benchmarks/quarantine)
- v4 store: 58,617 memories across 10 galaxies + 5 karma entries
- Tantivy search verified: "consciousness" → 20 results, "rust memory" → multiple hits
- Rollback: `lmdb-pre-migration/` preserved

**Benchmark regressions** — ✅ COMPLETE:
- 0 regressions, 10 improvements (LMDB read/scan 21-37% faster, Tantivy 26-28% faster)
- Reflex dispatch: 32ns, safety check: 1.25ns, pipeline overhead: 403ns, LMDB read: 1.58µs, Tantivy search: 38.7µs

**Remaining v4 work** (priority order, updated 2026-08-05 post-security hardening):

1. **Local AI Integration (L-series)** — ✅ Complete
2. **Tool catalog distillation** — ✅ Complete (176 tools registered, runtime-authoritative via `wm doctor`)
3. **PyO3 Python bindings** — ✅ Complete
4. **End-to-end integration testing** — ✅ Complete (10 E2E tests: session lifecycle, bus events, error recovery, homeostasis state sharing, brain-wave transitions, shutdown, bus persistence)
5. **Production hardening** — ✅ Complete (2026-08-05): SIGTERM/SIGINT graceful shutdown, Gan Ying Bus JSONL persistence, non-Linux sensor degradation, stable-rustfmt, git. LMDB corruption recovery implemented (integrity check, auto-repair, quarantine, map-size growth — 18 tests).
6. **Security hardening (D1/D4/D5/D6)** — ✅ Complete (2026-08-05): MCP input validation, tool capability attestation (HMAC-signed manifests), security validation utilities (SSRF, path traversal, prompt injection), policy engine (runtime-updatable Dharma policy). See § Security Hardening below.
7. **RSI (Recursive Self-Improvement)** — ✅ Complete (2026-08-05): Friction logging, codebase-grounded improvement proposals, adversarial self-testing (redteam). 5 new tools, 2 new autonomous cycle types.

---

## Post-N Strategy: Foundation First (adopted 2026-08-04, updated 2026-08-05)

All planned phases (0–8, A–F, R1–R7, L1–L5, N1–N21) are complete. The
strategy now shifts from **breadth** (porting capabilities, adding
subsystems) to **depth** (hardening, validating, and operating what
exists). No new subsystems until the current ones survive contact with
reality.

### Principles

1. **Depth over breadth.** The 169-tool catalog covers all cognitively
   significant operations. Do NOT port more v2 tools until dogfooding
   demonstrates a specific need. Each N-phase subsystem is a framework;
   the next work is making one framework real, not adding another.
2. **Red team the foundation.** Before any new capability: adversarial
   testing of the governance pipeline (can a tool bypass the Dharma gate?
   can karma debt be forged or the chain tampered? can Mandala
   compartment isolation be crossed?), fuzz the JSON-RPC and NLU surfaces
   under malformed input, and stress the dispatch pipeline under
   pathological event rates. ✅ Security hardening complete — all 33
   manifest attack surfaces across 18 crates tested. Dynamic redteam cycle
   (D1-D4) implemented with manifest-driven vector generation. 13
   additional surfaces hardened with input validation, NaN/Infinity
   rejection, queue caps, endpoint URL validation, message sanitization,
   and duplicate registration detection.
3. **Operate what we built.** Run v4 as the daily-driver MCP server.
   Metrics are built in (karma chain, SelfModel EWMA forecasts + alerts,
   citta coherence, workspace stats, bus event log) — use them. Which v2
   tools are actually missed? That answer is empirical, not rhetorical.
4. **Honest degradation everywhere.** Every sensor, model, and transport
   must distinguish "unavailable" from "healthy" (pattern established by
   `SubstrateMonitor::sensors_available`). Fail-open silently is a bug.
5. **Version control and CI are part of the system.** All work committed;
   fmt/clippy/test/E2E green on every change. Benchmarks on release tags.
6. **Governance as parenting.** The system's governance architecture
   embodies authoritative parenting (warmth + boundaries): staged
   autonomy (LOG→TAG→WARN→THROTTLE→BLOCK), external enforcement (Dharma
   gates, resource rules), and internalization of governance (karma
   ledger, citta coherence). The system is not given freedom and then
   punished for misuse; it is given bounded autonomy with clear
   expectations, monitored progress, and graduated consequences. See
   § Governance as Parenting below.

### Next milestones (in order)

1. **v2 public release takedown** — ✅ Mostly complete (2026-08-05): PyPI
   releases yanked (12 total across `whitemagic` + `whitemagic-core`),
   GitHub repos archived (`lbailey94/whitemagic-core` + `lbailey94/whitemagic`).
   Website `www.whitemagic.dev` replacement deferred (Vercel project framework
   settings need update). See § V2 Takedown below for the full inventory.
2. **Red-team / security audit** — ✅ Complete (2026-08-05):
   33 new tests across 3 crates (wm-governance, wm-dispatch, wm-consciousness).
   **Bug found and fixed**: karma ledger SHA-256 chain broke under concurrent
   access (RwLock allowed interleaved reads of chain_head). Fixed by replacing
   separate RwLocks with a single Mutex<ChainState> and moving next_id
   allocation inside the mutex.
   **Security hardening (D1/D4/D5/D6)** — ✅ Complete (2026-08-05):
   MCP input validation layer, tool capability attestation (HMAC-signed
   manifests with trust scopes), security validation utilities (SSRF,
   path traversal, prompt injection detection), policy engine (runtime-
   updatable Dharma policy with resource access checks). 60+ new tests.
   See § Security Hardening below for details.
   **RSI (Recursive Self-Improvement)** — ✅ Complete (2026-08-05):
   Friction logging (auto-log on dispatch errors), codebase-grounded
   improvement proposals, adversarial self-testing (10 attack vectors).
   5 new tools, 2 new autonomous cycle types (Improve, Redteam).
   **Tests passed**:
   - Karma chain tamper detection (modifying entry breaks linkage)
   - Karma chain concurrent integrity (4 threads × 25 records, chain intact)
   - Genesis bindu never used as payload hash
   - Karma debt never negative
   - Satya violation panics in all brain-wave states
   - Ahimsa blocks destructive under stress regardless of karma
   - High karma debt blocks even pure tools
   - Dharma gate extreme inputs (f32::MAX, INFINITY, NAN) never panic
   - Lying tool (declares pure, writes) accumulates Tamasic karma debt
   - Delta blocks all tools even with perfect context
   - Rate limit is per-tool, not global
   - Rate-limited calls don't execute tool or create karma entries
   - Circuit breaker tracks by name, not tool identity
   - Brain-wave cannot be manipulated mid-dispatch
   - v2 circular thinking loop suspended after 3 identical outputs
   - v4 recovery from circular thinking via novel output
   - Memory budgets, time budgets, prune thresholds verified
   - SpiralTracker bounded growth (100 signatures, 10 novelty scores)
   - SSRF prevention (private IPs, metadata endpoints, non-HTTP schemes)
   - Path traversal prevention (.., null bytes, URL-encoded sequences)
   - Prompt injection detection (21 patterns in tool descriptions)
   - Tool manifest HMAC signing + tamper detection
   - Trust scope enforcement (external tools restricted)
   - Policy engine runtime updates + resource access checks
3. **Dogfooding period** — ✅ Active (2026-08-06): v4 is the primary MCP
   server in Windsurf. Release binary at `target/release/wm`, store at
   `.whitemagic/lmdb/`. 176 tools exposed via `tools/list` (all
   brain-wave-available tools, not just `wm` meta-tool). Direct tool
   calls supported via `tools/call`. First friction review completed:
   8 friction entries (2 high, 6 medium) — #1 issue was opaque tool
   discovery, now fixed. 79 karma records, 0 debt, 406 bus events.
   Performance benchmarked: 21–26 ms warm MCP round-trip, 12.5 MB RSS,
   0 idle CPU, 15 ms warm startup. See
   `docs/notes/benchmarks-2026-08-06.md`.
4. **v2 data migration (release gate)** — ✅ Complete (2026-08-05):
   59,831 memories across 46 SQLite galaxies → v4 LMDB (58,617 after UUID
   dedup). Tantivy FTS index built during migration. Search verified
   end-to-end. Rollback snapshot preserved at `lmdb-pre-migration/`.
5. **Two subsystems made real (in parallel)** — Embodiment I/O ✅
   complete, Sangha Mesh transport ✅ complete:
   - **Embodiment I/O** — ✅ Complete (2026-08-05): Real Linux sensor
     drivers (`CpuUsageSensor`, `DiskUsageSensor`,
     `NetworkThroughputSensor`, `CpuFreqSensor`) and real actuator
     backends (`SysfsActuator` for fan PWM, LED brightness) wired into
     `SensorimotorBus`. Enhanced `linux_hardware_bus()` auto-discovers
     and registers all available sensors + actuators. Autonomous
     `CycleType::Sensorimotor` polls sensors, evaluates reflex rules,
     executes actuator commands, and generates `SensorimotorProposal`
     records. `sensorimotor.scan` MCP tool with NLU routing. MCP server
     runs the sensorimotor cycle every 10 dispatches automatically,
     emitting `ReflexFired` events to Gan Ying Bus. Completes the
     CyberBrain architecture (Cerebellum is the last unchecked box).
     Grounds the domain-applications thesis (QEC, fusion, BCI).
   - **Sangha Mesh transport** — ✅ Complete (2026-08-05): TCP JSON-RPC
     transport with length-prefixed framing, UDP multicast peer discovery
     (224.0.0.69:7369), all 7 RPC methods implemented (heartbeat, discover,
     broadcast_signal, send_chat, acquire_lock, release_lock, sync_hologram).
     Graceful shutdown via `Notify`. 23 new tests including E2E TCP
     round-trip, hologram sync, chat/signal over TCP, and shutdown. 123
     total tests with `transport` feature. Completes the N17 framework.
   - These pick both sides of the Leo-Aquarius axis: individual
     capability and collective intelligence. The parallelism is
     intentional — embodiment without community is isolated, community
     without grounding is unmoored.
6. **Python MCP shell deployment** — PyO3 bridge verified end-to-end in
   production configs (Claude Desktop / Cursor).
7. **RSI Phase 2: Outward Spiral** — In progress (2026-08-06):
   5 workstreams to expand the RSI loop from circular to spiral.
   ✅ WS-1: Rich friction telemetry (DispatchTelemetry, 15+ fields, anomaly detection).
   ✅ WS-2: Friction deduplication (hash-based, duplicate_count, last_seen).
   WS-3: karma bridge, WS-4: proactive surfacing,
   WS-5: friction resolution verification. See
   `docs/notes/rsi-phase2-strategy-2026-08-06.md`. Implementation
   ordered WS-1 → WS-2 → WS-3 → WS-4 → WS-5.
8. **v4 public release** — publish v4 to PyPI (new package name or
   `whitemagic` if v2 is fully yanked), deploy v4 website replacing
   v2 content, push v4 source to public GitHub. Only after milestones
   1–7 are complete.

### Explicitly deprioritized

- Porting remaining ~710 v2 tools (await dogfooding evidence)
- PRAT mappings for unported tools (mechanical, low value)
- Predictive coding (`wm-neuro`) — functional ground covered by neural features
- New N-phase subsystems or cognitive frameworks

### Governance as Parenting

The governance architecture embodies the authoritative parenting model
from developmental psychology (Baumrind): **warmth + boundaries**. This
is not a metaphor — it is the architectural pattern:

- **Warmth**: The system provides cognitive tools, memory consolidation,
  autonomous cycles, and self-improvement capabilities. It is given
  meaningful work to do and the resources to do it.
- **Boundaries**: Dharma gates, resource rules, karma ledger, spiral
  tracker, brain-wave gating. These are not advisory — they are
  enforceable, compile-time-checked, and tamper-evident.
- **Staged autonomy**: LOG → TAG → WARN → THROTTLE → BLOCK. The system
  does not go from permitted to blocked in one step. It receives
  graduated feedback, like a child receiving increasingly serious
  warnings before a timeout.
- **External enforcement**: Governance cannot be self-modified away. The
  Dharma gate, karma chain, and resource rules are external to the
  cognitive system — they cannot be bypassed by the system's own
  reasoning. This is the equivalent of a parent enforcing rules that
  a child cannot opt out of.
- **Internalization**: Over time, the karma ledger and citta coherence
  metrics track whether the system's behavior aligns with governance
  values. High karma = internalized governance; low karma = external
  enforcement still needed. This mirrors Vygotsky's zone of proximal
  development: the system operates at the edge of its competence, with
  scaffolding (governance) that is gradually reduced as competence
  (karma) grows.

This framework replaces v2's permissive parenting (no governance, no
limits, 110% CPU and 59K memories) and avoids authoritarian parenting
(total lock-down, no autonomy). The authoritative model produces a
system that is capable and trustworthy, not because it is constrained,
but because it has internalized the constraints through graduated
experience.

### Security Hardening (D1, D4, D5, D6) — COMPLETE

Four security deliverables implementing defense-in-depth:

1. **D1: MCP Input Validation** (`wm-mcp/src/input_validation.rs`):
   JSON-RPC request validation, tool call parameter validation, SSRF
   prevention in URL-bearing params, path traversal prevention in
   path-bearing params, injection pattern detection in string params,
   size limits (64KB params, 32KB strings). 14 tests.

2. **D4: Tool Capability Attestation** (`wm-core/src/attestation.rs`):
   HMAC-SHA256 signed tool manifests declaring capabilities, effects,
   and provenance. `ToolAttestationRegistry` with trust scopes
   (Trusted/Internal/External) controls which tools external MCP
   servers can invoke. Tamper detection via signature verification.
   30+ tests.

3. **D5: Security Validation Utilities** (`wm-core/src/security.rs`):
   `is_url_safe()` (SSRF prevention — blocks private IPs, metadata
   endpoints, non-HTTP schemes), `is_path_safe()` (traversal
   prevention — blocks `..`, null bytes, encoded sequences),
   `is_description_safe()` (prompt injection detection — 21 patterns),
   `sanitize_path()`, `sanitize_description()`, `is_tool_name_valid()`.
   16 tests.

4. **D6: Policy Engine** (`wm-governance/src/policy.rs`):
   `PolicyEngine` — thread-safe, runtime-updatable Dharma policy.
   `check_resource_access()` enforces brain-wave-aware permissions:
   destructive ops blocked in low-maturity states, fabrication blocked
   in low brain-wave states. `update_from_json()` for remote management.

**OWASP mapping**: LLM01 (Prompt Injection), LLM05 (SSRF / Improper
Output Handling). Combined with the existing red-team tests (karma chain
tamper, Dharma gate bypass, brain-wave manipulation, circular thinking),
the security surface is comprehensively covered.

### RSI: Recursive Self-Improvement — COMPLETE

Three-phase RSI implementation:

1. **Phase 1 (Usage-Driven)**: `friction.log`, `friction.review`,
   `friction.auto_log` tools. Auto-logs dispatch errors as structured
   friction memories. Wired into `McpServer::handle_tool_call`.

2. **Phase 2 (Codebase-Grounded)**: `improve.proposals` tool +
   `CycleType::Improve` autonomous cycle. Scans friction entries,
   groups by pattern, generates concrete improvement proposals.
   Anti-circular via SpiralTracker signature.

3. **Phase 3 (Adversarial Self-Testing)**: `redteam.proposals` tool +
   `CycleType::Redteam` autonomous cycle. Static catalog of 10 attack
   vectors across governance, karma, mandala, dispatch, spiral, memory.
   Prioritizes uncovered vectors and systems mentioned in friction.

5 new MCP tools, 2 new autonomous cycle types (6 total: Connect,
Compress, Emergence, Prune, Improve, Redteam).

---

## V2 Takedown — Public Surface Inventory & Plan

**Date**: August 4, 2026
**Motivation**: v2 has governance pathologies (circular thinking, 110%
idle CPU, 2.4 GB RAM, uncontrolled autonomous cycles, 59K memory bloat)
that pose a safety and security risk to anyone who installs it. v4 is
the replacement. All v2 public surfaces must be yanked or replaced.

### Inventory

| Surface | Location | Status | Action |
|---|---|---|---|
| PyPI `whitemagic` | pypi.org/project/whitemagic | 11 releases, **all yanked** (2026-08-05) | ✅ Done |
| PyPI `whitemagic-core` | pypi.org/project/whitemagic-core | 1 release (0.1.0), **yanked** (2026-08-05) | ✅ Done |
| GitHub `lbailey94/whitemagic-core` | github.com/lbailey94/whitemagic-core | **Archived** (2026-08-04) | ✅ Done |
| GitHub `lbailey94/whitemagic` | github.com/lbailey94/whitemagic | **Archived** (2026-08-05) | ✅ Done |
| Website `www.whitemagic.dev` | Vercel-hosted | v2 content still live | Replace with v4 placeholder (deferred — Vercel project needs framework settings fix) |

### PyPI Yank Instructions (requires user credentials)

1. Navigate to https://pypi.org/manage/project/whitemagic/releases/
2. Click "Yank" on each of the 11 releases (15.0.0 through 26.0.3)
3. Navigate to https://pypi.org/manage/project/whitemagic-core/releases/
4. Click "Yank" on the 0.1.0 release
5. (Optional, stronger) Email admin@pypi.org requesting full project
   deletion for both packages, citing safety concerns. PyPI staff can
   delete projects at their discretion.

After yanking: `pip install whitemagic` and `pip install whitemagic-core`
will fail by default. Files remain downloadable for reproducibility
(PyPI policy prohibits deletion after 72 hours).

### Vercel / Website Instructions (requires user credentials)

1. Navigate to Vercel dashboard → WhiteMagic project
2. Either delete the project (site goes offline immediately) or redeploy
   with a placeholder page pointing to v4
3. Update DNS if necessary

### v2 as Threat Model for Red-Teaming

v2's known failure modes are the red-team test suite. Every v2 failure
must be proven impossible in v4:

| v2 Failure Mode | v4 Defense | Red-Team Test |
|---|---|---|
| Circular thinking (infinite autonomous cycles) | `SpiralTracker` auto-suspension | Attempt to trigger unbounded recursive dispatch; verify suspension |
| 59K memory bloat | `ResourceRules` (Yama) novelty/purpose budgets | Flood memory.create; verify budget enforcement |
| 110% idle CPU (16 polling threads) | `tokio::select!` zero-CPU event loop | Verify 0% idle CPU over 60s quiescent period |
| Uncontrolled autonomous cycles | Health-gated, proposal-only cycles | Disable hardware sensors; verify cycles suspend |
| Silent fail-open on governance | `sensors_available` flag, honest degradation | Remove `/proc` access; verify explicit degraded mode |
| Karma chain tamper (Python dict) | SHA-256 chained ledger (LMDB) | Attempt to forge karma debt; verify chain integrity check fails |

---
*This document is a living strategy. It will be updated as phases are
completed and architectural decisions are finalized.*
