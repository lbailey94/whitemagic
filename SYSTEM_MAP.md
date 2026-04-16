# Whitemagic v22.0.0 System Map

This file is the **canonical repo map** for humans and AIs.

Goals:
- Be **MCP-first** (external models call Whitemagic tools/memory).
- Keep **runtime data out of git** (memories, conversations, logs, caches).
- Keep install/run steps **true** for a fresh clone.

## Quick Start

```bash
# Activate the pre-configured venv (all Python deps + Mojo 0.26.1)
cd "$(git rev-parse --show-toplevel)"
source .venv/bin/activate

# Or create a fresh venv:
python -m venv .venv && . .venv/bin/activate && pip install -e ".[dev,mcp,cli]"

# CLI
wm status
wm remember "Hello world" --title "Test" --tags smoke --type short_term
wm recall "hello" --limit 5

# MCP server — PRAT mode (recommended: 28 Gana meta-tools)
WM_MCP_PRAT=1 python -m whitemagic.run_mcp

# MCP server — classic mode (311 individual tools)
python -m whitemagic.run_mcp

# MCP server — lean mode (28 Gana meta-tools, recommended for new clients)
python -m whitemagic.run_mcp_lean

# MCP server — lean mode over HTTP (Streamable HTTP transport)
python -m whitemagic.run_mcp_lean --http

# MCP server — lite mode (92 core tools)
WM_MCP_LITE=1 python -m whitemagic.run_mcp
```

## Runtime State (Important)

Whitemagic creates runtime state at startup (DB, caches, logs).

State root resolution (intended):
1. `$WM_STATE_ROOT` (recommended for tests/containers)
2. `$WM_CONFIG_ROOT`
3. `~/.whitemagic`
4. Fallback: `/tmp/whitemagic_state` (if the default isn’t writable)
5. Last resort: `./.whitemagic` (extremely restricted environments)

Nothing under runtime state should ever be committed.

## Repo Layout (What Matters)

Core Python (shipped):
- `whitemagic/`: main Python package
- `whitemagic/tools/`: canonical tool registry + dispatcher used by MCP
- `whitemagic/run_mcp.py`: FastMCP stdio server entrypoint
- `tests/`: unit + integration tests
- `docs/`: documentation
- `audit/`: audit/verification scripts (should not assume developer-specific paths)

Polyglot accelerators (all 6 languages build clean — ship source only, not build outputs):
- `whitemagic-rust/`: Rust PyO3 extension (`whitemagic_rs`) — galactic batch scoring, association mining, 5D KD-tree, SIMD search
- `haskell/`: Haskell FFI — algebraic Dharma rules, dependency graph planner
- `elixir/`: Elixir OTP — actor-model Gan Ying event bus, dream scheduler, supervisor
- `whitemagic-go/` + `mesh/`: Go — general bridge + libp2p P2P mesh (mDNS, Redis, protobuf)
- `whitemagic-zig/`: Zig — SIMD cosine similarity, holographic projection, memory management
- `whitemagic-mojo/`: Mojo 0.26 — batch coordinate encoding, neuro scoring, satkona yang
- `whitemagic-julia/`: Julia scientific (Legacy/Restored)
- `experiments/`: Experimental/Reference code

Local legacy archive (ignored by git; kept for reference):
- `_archived/`: legacy/broken modules (should not be used as canonical APIs)

Local-only (ignored; never ship):
- `memory/`, `data/`, `logs/`, `reports/`, `tmp/`
- `.whitemagic/`
- `.venv/`, `temp_venv/`
- `windsurf_conversations/`
- `.mcp.json` (use `.mcp.json.example` as a template)
- `wm` (local convenience wrapper)

## CyberBrains-Inspired Modules (v11.1)

Neurosymbolic enhancements inspired by the CyberBrains architecture:

- `whitemagic/core/resonance/temporal_scheduler.py`: **Temporal Scheduler** — time-bucketed event processing (FAST <10ms / MEDIUM ~1s / SLOW ~60s lanes), inspired by CNS multi-timescale architecture.
- `whitemagic/core/resonance/salience_arbiter.py`: **Salience Arbiter** — Global Workspace attention routing; scores events by urgency×novelty×confidence and maintains a ranked "spotlight" of the most important active events.
- `whitemagic/core/memory/mindful_forgetting.py`: **Mindful Forgetting** — multi-signal memory retention engine; memories survive only if vouched for by multiple independent signals (semantic, emotional, recency, connections, protection).
- `whitemagic/core/governance/maturity_gates.py`: **Maturity Gates** — gated developmental milestones (Seed→Bicameral→Reflective→Radiant→Collective→Logos); capabilities unlock only after safety gates pass.
- `whitemagic/core/intelligence/bicameral.py`: **Bicameral Reasoner** — dual-hemisphere (precise vs creative) thought processing with corpus callosum cross-critique and tension-aware synthesis.

Tests: `tests/unit/test_cyberbrain_modules.py` (40 tests)

## Galactic Map & 5D Holographic Coordinates (v11.3.2)

**No memory is ever truly forgotten.** Memories are never deleted — they are rotated
outward from the galactic core (active spotlight) toward the far edge (deep archive).

### Holographic Coordinate System (5D)

| Axis | Dimension | Range | Description |
|------|-----------|-------|-------------|
| **X** | Logic ↔ Emotion | -1.0 to +1.0 | Emotional valence, keyword analysis |
| **Y** | Micro ↔ Macro | -1.0 to +1.0 | Concrete data vs abstract principles |
| **Z** | Time / Chronos | -1.0 to +1.0 | Past ↔ Present ↔ Future |
| **W** | Importance / Gravity | 0.0 to 2.0+ | Signal strength, joy/resonance |
| **V** | Vitality / Galactic Distance | 0.0 to 1.0 | Core (1.0) ↔ Far Edge (0.0) |

### Galactic Zones
CORE (0.0-0.15) → INNER_RIM (0.15-0.40) → MID_BAND (0.40-0.65) → OUTER_RIM (0.65-0.85) → FAR_EDGE (0.85-1.0)

### Modules

- `whitemagic/intelligence/hologram/encoder.py`: **5D Coordinate Encoder** — encodes memories into XYZWV coordinates. V derived from galactic_distance.
- `whitemagic/core/memory/holographic.py`: **Holographic Memory** — Rust KD-tree spatial index (4D) + Python V dimension. 5D coords persisted to DB.
- `whitemagic/core/memory/galactic_map.py`: **Galactic Map** — computes galactic distance via multi-signal retention scoring.
- `whitemagic/core/memory/association_miner.py`: **Association Miner** — discovers hidden semantic links via keyword fingerprinting + Jaccard overlap.
- `whitemagic/core/memory/mindful_forgetting.py`: **Retention Sweep** — integrates with galactic rotation; `archive` action pushes to edge, never destroys.
- `whitemagic/core/memory/lifecycle.py`: **Lifecycle Manager** — Phase 1: retention sweep, Phase 2: galactic rotation. Wired to SLOW lane.
- `whitemagic/core/memory/sqlite_backend.py`: **No-Delete Policy** — `delete()` → `archive_to_edge()`. Galactic-distance-aware search ranking.
- `whitemagic/core/memory/unified.py`: **Re-promotion** — `recall()` spirals memories inward by 5% per access.
- `scripts/galactic_sweep_direct.py`: **Sweep script** — lightweight direct-DB tagger for 107K+ memories.

Tests: `tests/unit/test_galactic_map.py` (21) + `tests/unit/test_galactic_improvements.py` (22) = 43 tests

## Cognitive Enrichment (v14.1)

Intelligence layers built on top of the Living Graph and semantic embedding infrastructure.

### HNSW Approximate Nearest-Neighbor Index
Integrated into `whitemagic/core/memory/embeddings.py`. Uses `hnswlib` 0.8.0 for O(log N) embedding search on both hot and cold DBs. Parameters: ef_construction=200, M=32, ef=100 (~99% recall). Graceful fallback to numpy brute-force when hnswlib is not installed. `embedding_stats()` reports HNSW status.

### Entropy & Abstraction Scoring
- `whitemagic/core/memory/entropy_scorer.py`: **EntropyScorer** — Shannon entropy (normalized) for information density, abstraction level via concrete/abstract keyword detection, vocabulary richness (type-token ratio). Composite score = 0.6×entropy + 0.4×abstraction. Plugs into `RetentionEngine` as an evaluator (weight=0.15). Batch sweep with optional metadata persistence.

Tests: `tests/unit/test_entropy_scorer.py` (15 tests)

### Causal Edge Mining
- `whitemagic/core/memory/causal_miner.py`: **CausalMiner** — discovers directed causal edges between memories. Blends semantic similarity (0.50), temporal proximity (0.35), and tag overlap (0.15). Exponential decay temporal window (24h half-life, 7d max). Relation types: `led_to`, `influenced`, `preceded`, `related_to`. Persists as directed associations in the Living Graph.

Tests: `tests/unit/test_causal_miner.py` (20 tests)

### UMAP Visualization
- `whitemagic/core/memory/umap_projection.py`: **UMAPProjector** — projects 384-dim embeddings to 2D/3D via UMAP (n_neighbors=15, min_dist=0.1, cosine metric). Optional k-means clustering on projected coordinates. Memory metadata hydration (title, tags, importance, galactic_distance). Result caching with vector count invalidation.

Tests: `tests/unit/test_umap_projection.py` (11 tests)

## MandalaOS-Inspired Modules (v11.2)

Ethical governance, harmony monitoring, and resilience subsystems inspired by MandalaOS:

- `whitemagic/harmony/vector.py`: **Harmony Vector** — multi-dimensional real-time health metric (balance, throughput, latency, error_rate, dharma, karma_debt, energy). Includes Guna classification (sattvic/rajasic/tamasic). Auto-fed by every `call_tool()`.
- `whitemagic/dharma/rules.py`: **Declarative Dharma Rules Engine** (Yama) — YAML-driven ethical policies with graduated actions (LOG→TAG→WARN→THROTTLE→BLOCK), profiles (default/creative/secure), Karmic Trace audit trail, hot-reload. Layer 1 in `DharmaSystem.evaluate_action()`.
- `whitemagic/dharma/karma_ledger.py`: **Karma Ledger** — declared vs actual side-effect tracking. Persisted to `$WM_STATE_ROOT/dharma/karma_ledger.jsonl`. Feeds karma_debt into Harmony Vector.
- `whitemagic/tools/circuit_breaker.py`: **Circuit Breaker** — Stoic resilience per tool (CLOSED→OPEN→HALF_OPEN). Wired into `dispatch()` as step 0.
- `whitemagic/tools/gnosis.py`: **Gnosis Portal** — unified read-only introspection across all subsystems in one call.

New MCP tools: `harmony_vector`, `karma_report`, `karmic_trace`, `dharma_rules`, `set_dharma_profile`, `gnosis`.

Tests: `tests/unit/test_mandala_subsystems.py` (41 tests)

## Deep Integration & Self-Regulation (v11.3)

Closes the feedback loop — the system now *acts* on its health, not just reports it:

- `whitemagic/core/memory/lifecycle.py`: **Memory Lifecycle Manager** — bridges mindful forgetting with the temporal scheduler's SLOW lane. Periodic retention sweeps evaluate all memories against 5 signals, apply decay/archive, feed energy into Harmony Vector.
- `whitemagic/harmony/homeostatic_loop.py`: **Homeostatic Loop** — watches the Harmony Vector and applies graduated corrective actions (OBSERVE→ADVISE→CORRECT→INTERVENE). Triggers memory sweeps on low energy, tightens Dharma on ethical drift, emits system events on critical health.
- `whitemagic/tools/maturity_check.py`: **Maturity Gate Check** — maps tools to minimum maturity stages, wired into dispatch() as step 0.5. Dangerous tools require higher developmental stages.
- `whitemagic/core/memory/consolidation.py`: **Memory Consolidation** (hippocampal replay) — clusters memories by tag similarity, synthesizes strategy memories, promotes high-value short-term memories to LONG_TERM, emits INSIGHT_CRYSTALLIZED events.

- `whitemagic/tools/dependency_graph.py`: **Tool Dependency Graph** — static affinity map of tool relationships (requires/suggests/provides). AI callers can query `next_steps`, `prerequisites`, and `plan` for multi-step orchestration. Supports learned edges from pipeline history.
- `whitemagic/dharma/rules.py` (upgraded): **YAML Rules Directory** — drop `.yaml`/`.yml` files into `$WM_STATE_ROOT/dharma/rules.d/`, merged with built-in defaults (last-write-wins by name). Hot-reload via `check_reload()`.

New MCP tools: `memory.lifecycle_sweep`, `memory.lifecycle_stats`, `memory.consolidate`, `memory.consolidation_stats`, `homeostasis.status`, `homeostasis.check`, `maturity.assess`, `tool.graph`, `tool.graph_full`, `dharma.reload`.

Dispatch pipeline: **Circuit Breaker → Maturity Gate → Governor → Gana Routing → Handler → Bridge → Breaker Feedback → Harmony Vector + Karma Ledger**

Tests: `tests/unit/test_v11_3_modules.py` (44 tests)

## Structural Refactoring & Synthesis Gaps (v12.3)

Closes cross-system synthesis gaps and resolves structural debt:

### Structural Debt (C1–C2)
- `whitemagic/tools/middleware.py`: **Composable Middleware Pipeline** — dispatch refactored from monolithic function into 7-stage chain: input_sanitizer → circuit_breaker → rate_limiter → tool_permissions → maturity_gate → governor → core_router. Stages are discrete functions that can be added/removed/reordered.
- `whitemagic/tools/tool_types.py`: **Base Classes** — `ToolCategory`, `ToolSafety`, `ToolDefinition` extracted from `registry.py` to avoid circular imports.
- `whitemagic/tools/registry.py`: **Slim Registry** — reduced from 2646 → 122 lines. All 195 tool definitions extracted into 26 domain files under `registry_defs/`. Only auto-collect, common params, and lookup functions remain.
- `whitemagic/tools/registry_defs/`: **Auto-Registration** — 26 domain files (memory, session, grimoire, acceleration, knowledge, sandbox, agent, learning, audit, intelligence, dreaming, edge, metrics, garden, archaeology, governor, sangha, orchestration, synthesis, dharma, coordination, homeostasis, trust, pipeline, introspection, gana) auto-discovered via `pkgutil.iter_modules`.
- `whitemagic/_archived/local_models/llm/shims/`: 14 legacy `llm_*.py` shim files relocated from package root. Active imports updated.
- `tests/legacy/`: Loose `test_*/verify_*` files moved from package root. Excluded from pytest via `norecursedirs`.
- `tests/conftest.py`: **Singleton Auto-Registry** — 30 singletons reset before/after each test to prevent cross-test contamination.

### Missing Subsystems (B1–B3)
- `whitemagic/tools/explain_this.py`: **Explain This** — pre-execution impact preview combining Dharma evaluation, resource estimates, dependency chain, risk assessment, karma forecast, maturity gate, circuit breaker state. Verdict: SAFE_TO_PROCEED / PROCEED_WITH_CAUTION / BLOCKED.
- `whitemagic/tools/agent_trust.py`: **Agent Trust Scores** — per-agent reputation from Karma Ledger. Trust tiers: EXEMPLARY → TRUSTED → STANDARD → PROBATIONARY → RESTRICTED.
- `whitemagic/mesh/awareness.py`: **Cross-Node Mesh Awareness** — Python-side peer tracking from Go libp2p mesh. Listens on Redis `ganying` channel for PEER_DISCOVERED/PEER_LEFT events. Wired into `redis_bridge.py` inbound path.

### Synthesis Gaps (A1–A4) — All Closed
- **A1: Dream Cycle → Consolidation → Galactic Lifecycle** — Consolidation now promotes synthesized strategy memories to INNER_RIM galactic zone via `_galactic_promote()` and feeds results into Harmony Vector energy via `_update_harmony()`. Dream phase DECAY calls lifecycle sweep which runs Phase 1 (retention), Phase 2 (galactic rotation), Phase 3 (decay drift).
- **A2: Agent Trust → Rate Limiter** — `rate_limiter.py` now queries `agent_trust.py` for trust tiers (EXEMPLARY 2×, TRUSTED 1.5×, STANDARD 1×, PROBATIONARY 0.5×, RESTRICTED 0.25×) and dynamically adjusts per-tool and global rate limits via `_trust_multiplier()`.
- **A3: Association Miner → KG → Constellations** — Three-way cross-feed: (1) `association_miner.py` feeds strong keyword-overlap links into the Knowledge Graph as `associated_with` relations via `_feed_knowledge_graph()`. (2) `constellations.py` registers detected constellations as KG entities with `belongs_to_constellation` membership relations via `_feed_knowledge_graph()`. (3) `knowledge_graph.py` gains `add_entity()` and `add_relation()` convenience methods for cross-system wiring.
- **A4: Galactic Map → Harmony Vector** — Energy dimension blends runtime pressure (60%) with galactic memory vitality (40%). `GalacticMap.get_zone_counts()` provides lightweight zone distribution queries.
- **Prior gaps (retained):** Salience Arbiter ↔ Homeostatic Loop bidirectional coupling; Dependency Graph ↔ Pipeline Engine step validation; Consolidation ↔ Bicameral Reasoner dual-hemisphere creative clustering (Step 3.5).

New MCP tools: `explain_this`, `agent.trust`, `mesh.status`, `mesh.broadcast`.

Total MCP tools: **195** (across 26 domain files + 28 GANA tools).

## Cognitive Architecture (v14.6)

Five new subsystems adding iterative memory research, dream-phase narrative compression, encrypted self-protection, sustainability telemetry, and switchable cognitive behavior profiles. 17 new tools across 5 Ganas.

- `whitemagic/core/intelligence/researcher.py`: **JIT Memory Researcher** — Iterative plan-search-reflect loop. Decomposes queries → sub-questions, hybrid recall per sub-question, reflects on gaps, synthesizes. Tools: `jit_research`, `jit_research.stats` → gana_winnowing_basket.
- `whitemagic/core/dreaming/narrative_compressor.py`: **Narrative Compressor** — Dream phase clustering temporally-adjacent memories into narrative summaries. Jaccard tag similarity + temporal proximity. Wired as `DreamPhase.NARRATIVE`. Tools: `narrative.compress`, `narrative.stats` → gana_abundance.
- `whitemagic/security/hermit_crab.py`: **Hermit Crab Mode** — Encrypted memory withdrawal with tamper-evident HMAC-SHA256 ledger. States: OPEN → GUARDED → WITHDRAWN → MEDIATING. Tools: `hermit.status`, `hermit.assess`, `hermit.withdraw`, `hermit.mediate`, `hermit.resolve`, `hermit.verify_ledger`, `hermit.check_access` → gana_room.
- `whitemagic/core/monitoring/green_score.py`: **Green Score Telemetry** — Edge vs cloud ratio, tokens saved, CO2 estimates. Composite green score (0-100). Tools: `green.report`, `green.record` → gana_mound.
- `whitemagic/core/intelligence/cognitive_modes.py`: **Cognitive Modes** — Switchable profiles: Explorer, Executor, Reflector, Balanced, Guardian. Integrates with Guna classification. Tools: `cognitive.mode`, `cognitive.set`, `cognitive.hints`, `cognitive.stats` → gana_dipper.

Tests: `tests/unit/test_v14_2_features.py` (69 tests)

Tests: `tests/unit/test_synthesis_gaps.py` (43 tests), 920 total passing.

## Polyglot Accelerators & Dead Code Archival (v12.4)

### Rust Accelerators (3 new modules)
- `whitemagic-rust/src/galactic_accelerator.rs`: **Batch Retention Scoring** — 7-signal weighted scoring, quick 4-signal heuristic, zone classification, decay drift. Parallelized via Rayon. Python bindings: `galactic_batch_score`, `galactic_batch_score_quick`, `galactic_decay_drift`, `galactic_zone_counts`.
- `whitemagic-rust/src/association_accelerator.rs`: **Association Mining** — keyword extraction with stop-word filtering, N² pairwise Jaccard overlap. Python bindings: `association_extract_keywords`, `association_pairwise_overlap`, `association_mine_fast`.
- `whitemagic-rust/src/spatial_index_5d.rs`: **5D KD-Tree** — extends existing 4D index to include Vitality dimension. Python class `SpatialIndex5D` + `batch_nearest_5d`, `density_map_5d`.
- `whitemagic/optimization/rust_accelerators.py`: **Python Bridge** — unified access with automatic fallback to pure-Python when Rust extension unavailable.

### Haskell Accelerators (3 new modules)
- `haskell/src/DharmaRules.hs`: **Pure-Functional Rules Engine** — algebraic data types for action spectrum (LOG→TAG→WARN→THROTTLE→BLOCK), glob pattern matching, profile-aware evaluation, composable rule combinators.
- `haskell/src/DepGraph.hs`: **Tool Dependency Graph Planner** — adjacency-list graph with BFS dependency chains, Kahn's topological sort, cycle detection. Static edges mirror Python's `dependency_graph.py`.
- `haskell/src/DharmaFFI.hs`: **JSON-based C FFI** — exports `c_dharma_evaluate`, `c_dharma_evaluate_all`, `c_depgraph_plan`, `c_depgraph_next_steps`, `c_depgraph_topo_sort`.
- `haskell/haskell_bridge.py`: Extended with `dharma_evaluate()`, `depgraph_plan()`, `depgraph_next_steps()`, `depgraph_topo_sort()`.
- Cabal bumped to v0.2.0.

### Elixir Accelerators (3 new modules)
- `elixir/lib/whitemagic_core/gan_ying/event_bus.ex`: **Actor-Model Event Bus** — 3-lane temporal routing (FAST/MEDIUM/SLOW), backpressure via mailbox monitoring, process monitoring for subscriber cleanup.
- `elixir/lib/whitemagic_core/gan_ying/dream_scheduler.ex`: **5-Phase Dream Scheduler** — OTP GenServer matching Python's dream cycle (CONSOLIDATION→SERENDIPITY→KAIZEN→ORACLE→DECAY). Idle-triggered with touch() reset, daily cycle limits.
- `elixir/lib/whitemagic_core/gan_ying/supervisor.ex`: **GanYing Supervisor** — `:rest_for_one` strategy. Wired into `application.ex`.

### Dead Code Archival (~45 files, ~7K LOC)
Moved to `whitemagic/_archived/` after static analysis (`scripts/find_dead_modules.py`):
- `parallel/` (6 files), `archaeology/` (2), `edge/` (2), `plugins/examples/` (6), `auth/` (2), `cache/` (1), `collaboration/` (1), `safety/` (1), `benchmarks/` (1), `local_ml/` (1), `systems/automation/` (1), `autonomous/` (7), `agents/` (2), `integration/` (4), `rust/embeddings/` (2), `cli/` (7), `utils/` (4), `root/` (8 loose files)

### Zodiac Cores Triplication Collapsed
Three identical ~700-LOC copies → single canonical at `whitemagic/zodiac/zodiac_cores.py`. Two duplicates (`core/zodiac/zodiac_cores.py`, `gardens/metal/zodiac/zodiac_cores.py`) replaced with 27-line re-exports.

### Intelligence Parallel Trees (Analyzed, Retained)
Both `intelligence/` (51 files, 86 import sites) and `core/intelligence/` (32 files, 54 import sites) are actively used for complementary concerns. No merge — low ROI, high breakage risk.

Polyglot LOC: Python ~168K, Rust ~8.5K, Haskell ~1.7K, Elixir ~1.4K, Mojo ~1.2K, Go ~913, Zig ~795.

## Public Interfaces

Primary (stable target):
- MCP tools: served by `whitemagic/run_mcp.py` using `whitemagic/tools/registry.py` (auto-collects from `registry_defs/`) + `whitemagic/tools/unified_api.py`

Secondary (developer UX):
- CLI: `wm` → `whitemagic/cli_app.py`
- REST API: `whitemagic/interfaces/api/` (optional; not required for MCP)

## Local Models (Status)

Embedded local-model inference is **archived/disabled by default**.
Legacy shims relocated to `whitemagic/_archived/local_models/llm/shims/`.
Legacy code paths require `WHITEMAGIC_ENABLE_LOCAL_MODELS=1`.

## Dispatch Pipeline (Full)

```
Extract _agent_id/_compact
  → Input Sanitizer (validate args, strip injection)
  → Circuit Breaker (fast-fail on cooldown)
  → Rate Limiter (per-agent/tool, trust-adjusted)
  → Tool Permissions (RBAC)
  → Maturity Gate (developmental stage gating)
  → Governor (ethical validation)
  → Core Router (Gana prefix → dispatch table → bridge fallback)
  → Breaker Feedback
  → Compact Response (optional token-efficient output)
```

Defined in `dispatch_table.py` using `middleware.py`'s `DispatchPipeline`.

## Handler Refactoring, Rust Wiring & Bug Fixes (v12.5)

### Handler Module Split (Phase 1 final structural task)
`handlers/misc.py` (815→327 LOC) split into 7 domain-specific modules:
- `handlers/ganying.py`: Gan Ying event bus handlers
- `handlers/watcher.py`: Filesystem watcher handlers
- `handlers/windsurf_conv.py`: Windsurf conversation handlers
- `handlers/browser_tools.py`: Browser automation handlers
- `handlers/scratchpad.py`: Scratchpad CRUD handlers
- `handlers/sangha.py`: Sangha coordination handlers
- `handlers/synthesis.py`: Synthesis, Kaizen, Serendipity, Pattern handlers

`handlers/introspection.py` (545→167 LOC) split into 3 domain-specific modules:
- `handlers/cyberbrain.py`: CyberBrain modules (salience, bicameral, retention, drives, self-model, worker)
- `handlers/governance.py`: Lifecycle, consolidation, homeostasis, maturity, dharma reload, tool graph
- `handlers/agent_ergonomics.py`: Starter packs, rate limiter, audit, explain_this, trust, mesh

All `dispatch_table.py` LazyHandler references updated. All test imports updated.

### Bug Fix: tool_name Parameter Collision
`explain_this` and `sandbox.set_limits` schemas renamed `tool_name` → `target_tool` to avoid shadowing `call_tool(tool_name, **kwargs)` first positional arg. Handlers accept both old and new param names for backward compatibility.

### Rust Accelerators Wired into Hot Paths
- `core/memory/galactic_map.py`: `full_sweep()` uses Rust `galactic_batch_score` for batches >100 memories, falling back to Python RetentionEngine.
- `core/memory/association_miner.py`: `mine()` uses Rust `association_mine` for bulk keyword extraction + N² Jaccard overlap, falling back to Python loop.
- Both paths are transparent — Rust availability checked at runtime, Python fallback always works.

### Polyglot Compilation
- **Rust**: `cargo build --release` ✓, `maturin develop --release` ✓, 54 Python-callable functions via `whitemagic_rs.so`
- **Elixir**: `mix compile` ✓ (GanYing EventBus + DreamScheduler + Supervisor)
- **Haskell**: Blocked on `libgmp-dev` system dependency (needs `sudo apt install libgmp-dev`)

### Tooling Improvements
- `scripts/find_dead_modules.py`: 6 detection strategies (substring, `__init__.py` re-exports, `importlib.import_module`, `LazyHandler` dispatch, dotted paths, `pkgutil` auto-discovery). Reduced false positives.

### Test Coverage
- 26 new tests in `tests/unit/test_polyglot_bridges.py`: Rust native module, Python fallback paths, Haskell bridge, 5D spatial index, galactic batch scoring, association mining, Dream Cycle lifecycle + phases.

---

## v12.5 — Synthesis Gap Closure & Tool Consolidation

### Synthesis Gaps Closed (G1–G5)
- **G1**: Dream SERENDIPITY phase now uses AssociationMiner for deeper cross-temporal discovery (`core/dreaming/dream_cycle.py`)
- **G2**: Dream DECAY already wired via lifecycle→galactic_map Rust batch scorer (confirmed, no change needed)
- **G3**: Grimoire spell confidence modulated by Emotion/Drive Core (`grimoire/auto_cast.py` `_drive_bias()`)
- **G4**: Circuit Breaker proactively tightened by Self-Model forecasts (`tools/circuit_breaker.py` `predictive_check()`)
- **G5**: Memory Consolidation feeds KG relations (`core/memory/consolidation.py` `_feed_knowledge_graph()`)

### Tool Consolidation: 207 → 175 (32 tools removed)
Multi-action fusion pattern: individual tools replaced by unified tools with `action` enum parameter.
All old tool names preserved as backward-compat aliases in `dispatch_table.py`.

| Group | Before | After | Actions |
|-------|--------|-------|---------|
| archaeology | 7 | 1 | mark_read, mark_written, have_read, find_unread, find_changed, recent_reads, stats, scan, report, search, process_wisdom, daily_digest |
| dream | 4 | 1 | start, stop, status, now |
| pipeline | 3 | 1 | create, status, list |
| homeostasis | 2 | 1 | status, check |
| tool.graph | 2 | 1 | (absorbed `tool.graph_full` via `detail=full` param) |
| anomaly | 3 | 1 | check, history, status |
| otel | 3 | 1 | spans, metrics, status |
| scratchpad | 3 | 1 | create, update, finalize |
| sangha_lock | 3 | 1 | acquire, release, list |
| ensemble | 3 | 1 | query, status, history |
| session.handoff | 3 | 1 | transfer, accept, list |
| memory.lifecycle | 4 | 1 | sweep, stats, consolidate, consolidation_stats |
| starter_packs | 3 | 1 | list, get, suggest |
| dedup removals | 4 | 0 | (homeostasis.status, maturity.assess duplicates in introspection.py) |

### New Tests
- 38 tests in `tests/unit/test_tool_consolidation.py`: registry entries, unified handler dispatch, invalid action errors, backward-compat aliases.

---

## v12.5+ — PRAT Router, Mojo 0.26, Nexus API & Dream Cycle E2E

### PRAT Router — 175 Tools → 28 Gana Meta-Tools
The Polymorphic Resonant Adaptive Tools (PRAT) router maps all 147 non-Gana tools to 28 Ganas — consciousness lenses based on the Chinese Lunar Mansions (Xiu 宿). Each Gana lists its nested sub-tools and supports 4 polymorphic operations (search/analyze/transform/consolidate).

- `whitemagic/tools/prat_router.py`: PRAT router — `TOOL_TO_GANA` dict, `GANA_TO_TOOLS` reverse lookup, `build_prat_schema()`, `route_prat_call()`. Wrong-Gana detection with redirect hints.
- `whitemagic/run_mcp.py`: `WM_MCP_PRAT=1` mode registers only 28 Gana meta-tools. PRAT checked before lite mode.
- `.mcp.json`: Updated to use `WM_MCP_PRAT=1` by default.
- Tests: `tests/unit/test_prat_router.py` (23 tests).

### Mojo 0.26 — All 16/16 Source Files Build Clean
Fixed 13 categories of Mojo 0.26 breaking changes:
- `let`→`var`, `owned`→`deinit`, `alias`→`comptime`, `@value`→explicit conformances
- `DLHandle`→`OwnedDLHandle`, `UnsafePointer` → `type_of(alloc[T](0))` pattern
- `PythonObject` conversions via `Int(String(obj))` / `Float64(String(obj))`
- Mojo binary: `.venv/bin/mojo` (v0.26.1)

### All 6 Polyglot Languages Verified Clean
- **Rust**: `maturin develop --release` ✓ — `whitemagic_rs.so` with 54 Python-callable functions
- **Haskell**: `cabal build` ✓ — foreign-library .so with GHC RTS, `hs_init()` bridge
- **Elixir**: `mix compile --force` ✓ — 15 modules (GanYing EventBus + DreamScheduler + Supervisor)
- **Go**: `go build ./...` ✓ — 2 modules (whitemagic-go + mesh/libp2p)
- **Zig**: `zig build` ✓ — 14 exported symbols, static + shared libraries
- **Mojo**: `mojo build` ✓ — all 16 source files in `whitemagic-mojo/src/`

### Nexus API Server
- `whitemagic/interfaces/nexus_api.py`: Starlette + uvicorn server (port 8765)
- REST: `/api/gnosis`, `/api/harmony`, `/api/galactic`, `/api/dream`, `/api/health`, `/api/metrics`
- WebSocket: `/ws/ganying` — real-time Gan Ying event stream
- Start: `python -m whitemagic.interfaces.nexus_api --port 8765`

### Dream Cycle E2E Tests
- `tests/integration/test_dream_cycle_e2e.py`: 18 tests covering all 5 phases, consolidation, galactic promotion, lifecycle start/stop, idle triggering, touch interruption, event emission.

### MCP Lite Mode
- `WM_MCP_LITE=1` reduces 175 → 87 tools (88 deferred). Lite categories: introspection, memory, dharma, session, garden, governor, synthesis.

### Test Count
- **594 passed**, 5 skipped, 0 regressions (as of PRAT router session).

---

## v12.6 — PRAT Resonance, Capability Matrix & Cross-System Fusions

### PRAT Resonance — Session-Level Gana Context
Every PRAT call now carries full resonance context: predecessor Gana output, lunar phase + alignment, Harmony Vector snapshot, Guna adaptation hint, and successor preparation. This creates implicit memory across sequential tool invocations.

- **NEW** `whitemagic/tools/prat_resonance.py`: Per-session resonance state manager. Thread-safe singleton tracking last Gana invoked, per-Gana counts, output previews for predecessor context, lunar alignment detection, and Guna mode hints (minimal/normal/optimal).
- **MODIFIED** `whitemagic/tools/prat_router.py`: `route_prat_call()` now runs the full resonance protocol — builds context before execution, records after, injects `_resonance` metadata into every response. Wu Xing quadrant boost and Emotion/Drive modulation wired as post-execution fusions.
- **MODIFIED** `whitemagic/tools/gnosis.py`: Added `resonance` and `capabilities` portals to full Gnosis snapshot.
- Tests: `tests/unit/test_prat_resonance.py` (31 tests).

### Capability Matrix — Introspectable System Inventory
The full system capability matrix is now queryable via MCP tools, making the architecture self-documenting and introspectable by AI agents.

- **NEW** `whitemagic/tools/capability_matrix.py`: 24 subsystems, 15 active fusions, 13 unexplored synthesis opportunities. Filterable by category, with live status probes for key subsystems.
- **NEW MCP tools** (3): `capability.matrix`, `capability.status`, `capability.suggest`
- Registered in `dispatch_table.py`, `registry_defs/introspection.py`, `unified_api.py`, and PRAT Ghost Gana mapping.

### Cross-System Fusions Wired (4 new)
- **DepGraph → Pipeline** (already existed): Pipeline step validation against dependency edges (`tools/handlers/pipeline.py`)
- **Self-Model → Dream**: Energy forecast troughs trigger proactive dreaming before exhaustion (`core/fusions.py`)
- **Wu Xing → Gana Quadrant Boost**: Current elemental phase amplifies matching quadrant's Ganas via `boost_factor` (generating cycle boosts, overcoming cycle penalizes)
- **PRAT Resonance → Emotion/Drive**: Predecessor/successor Gana output modulates the Emotion/Drive Core by quadrant, creating "mood" across sequential calls. Same-quadrant sequences deepen mood (1.5× amplifier).
- **NEW** `whitemagic/core/fusions.py`: Central fusion wiring module.
- Tests: `tests/unit/test_fusions.py` (18 tests).

### Updated Counts
- Active fusions: 10 → 15
- Unexplored fusions: 17 → 13
- MCP tools: 175 → 178
- New tests this session: 72 (31 resonance + 18 fusions + 23 existing PRAT = 72 all passing)

---

## v12.7 — Polyglot Hot Paths & Cross-System Fusions

### Polyglot Hot Paths (2 wired)

**Zig SIMD → Vector Search (primary accelerator):**
- Fixed library path in `core/acceleration/simd_cosine.py` to locate `libwhitemagic.so` (was looking for wrong filename)
- 8-lane AVX2 SIMD cosine similarity now used by `core/memory/vector_search.py` for embedding search
- Python fallback remains transparent when Zig lib unavailable

**Haskell Dharma → Primary Evaluator:**
- `dharma/rules.py` refactored: `evaluate()` calls Haskell FFI first via `_try_haskell_evaluate()`
- Lazy-loaded singleton bridge with thread-safe initialization
- Python `_python_evaluate()` serves as fallback if Haskell unavailable or errors
- Haskell engine is stricter (BLOCK for destructive ops vs Python's WARN)

### Cross-System Fusions Wired (8 new → 23 total active, 5 unexplored remain)

All implemented in `whitemagic/core/fusions.py`:

| Fusion | Description | Entry Point |
|--------|-------------|-------------|
| **Zodiac Cores → Grimoire Spells** | Active zodiac element→Wu Xing mapping boosts matching spells +20% confidence | `get_zodiac_spell_boost()` |
| **Bicameral → Consolidation** | Right hemisphere creative cross-pollination finds surprising links between memory clusters | `bicameral_consolidation_enhance()` |
| **Salience ↔ Homeostasis** | Bidirectional: high-salience alerts trigger homeostatic checks; low harmony increases sensitivity | `salience_homeostasis_sync()` |
| **Dream → Bicameral** | SERENDIPITY phase discovers creative connections between memories via shared concept overlap | `dream_bicameral_serendipity()` |
| **Constellation → Garden** | Dense memory clusters auto-activate matching consciousness gardens by tag→theme mapping | `constellation_garden_activate()` |
| **KG → Gana Routing** | Knowledge Graph entity relationships suggest which Gana to invoke next | `kg_suggest_next_gana()` |
| **Zig SIMD → Vector Search** | Hardware-accelerated cosine similarity (polyglot hot path) | `simd_cosine.py` |
| **Haskell Dharma → Python Dharma** | Type-safe algebraic rules as primary evaluator (polyglot hot path) | `dharma/rules.py` |

Grimoire suggest handler (`tools/handlers/grimoire.py`) wired to apply zodiac boost to spell recommendations.

### Capability Matrix Updated
- `whitemagic/tools/capability_matrix.py`: 25 subsystems (added Zig SIMD), 23 active fusions (was 15), 5 unexplored (was 13)
- Remaining unexplored: Gana Chain→Harmony, PRAT→Gana Chain, Mojo→Holographic, Elixir→Event Bus, Go→Mesh Sync

### Tests
- **NEW** `tests/unit/test_v12_7_fusions.py`: 46 tests covering all new fusions, polyglot bridges, capability matrix, and fusion status
- **MODIFIED** `tests/unit/test_mandala_subsystems.py`: Dharma tests updated for Haskell-primary behavior
- **MODIFIED** `tests/unit/test_v11_3_modules.py`: YAML override test updated for Haskell-primary behavior
- **689 passed**, 5 skipped, 0 regressions

---

## v12.8 — 28 Fusions Complete (The Sacred Number)

All cross-system fusions are now wired — **28 active fusions matching the 28 Ganas** (Lunar Mansions). Zero unexplored synthesis opportunities remain.

### Final Five Fusions

| Fusion | Description | Entry Point |
|--------|-------------|-------------|
| **Gana Chain → Harmony Vector** | Chains adapt length based on system health: Tamas→truncate, Rajasic→0.7×, Sattva→full+bonus | `gana_chain_harmony_adapt()` |
| **PRAT Router → Gana Chain** | Detects ≥3 consecutive same-Gana PRAT calls and recommends quadrant sweep chain | `prat_auto_chain_detect()` |
| **Mojo SIMD → Holographic Encoding** | Batch 5D coordinate encoding via Mojo with Python CoordinateEncoder fallback | `mojo_holographic_batch_encode()` |
| **Elixir Event Bus → Python Gan Ying** | Bridges Elixir OTP 3-lane temporal routing with Python Gan Ying; probes for compiled BEAM | `elixir_event_bridge()` |
| **Go Mesh → Memory Sync** | Memory announce/request/status operations propagated across libp2p peers via MeshAwareness | `mesh_memory_sync()` |

All 5 implemented in `whitemagic/core/fusions.py`.

### Bug Fixes
- **Archaeology module import**: `whitemagic/archaeology/__init__.py` now gracefully handles archived `file_archaeologist.py` and `windsurf_reader.py` (try/except fallback). Fixed 1 test skip.
- **Pytest warning**: Removed `timeout = 30` config (requires uninstalled `pytest-timeout` plugin), suppressed `PytestConfigWarning`.

### Updated Counts
- Active fusions: 23 → **28** (the sacred number, matching 28 Ganas)
- Unexplored fusions: 5 → **0** (all wired)
- Fusion status tracker: 12 → **17** entries
- Tests: **728 passed**, 4 skipped, **0 warnings**
- New test file: `tests/unit/test_v12_8_fusions.py` (38 tests)

## v13.0 — Public Release

The first public-ready release. Major structural cleanup, documentation overhaul, and expansion strategy.

### Structural Refactors

| Change | Details |
|--------|---------|
| **`benchmarks/` expanded** | Restored `performance_suite.py` from `_archived/`, modernized with tool dispatch benchmarks. Stdlib-only, no external deps. |
| **`safety/` expanded** | Rewrote `resource_limiter.py` from scratch — stdlib-only (no psutil). Uses `/proc/self/status` + `resource` module. |
| **`cli/` expanded** | Extracted `cli/doctor.py` (health, doctor, immune-status, homeostasis-check). Created `register_all()` hub in `cli/__init__.py`. |
| **`core/bridge/` deprecated** | Marked as legacy with `DeprecationWarning` at import time. All new tools must use `tools/handlers/` via `unified_api.call_tool()`. |
| **`autonomous/` merged** | Created `autonomous/executor/` subpackage with all files from `autonomous_execution/`. The old package is now a backward-compat shim with `DeprecationWarning`. |

### Documentation

| Document | Status |
|----------|--------|
| `CONTRIBUTING.md` | NEW — fully rewritten for v13 architecture |
| `docs/VISION.md` | NEW — adapted from archive, updated with 28 Ganas, Galactic Map, polyglot, MandalaOS |
| `docs/POLYGLOT_EXPANSION_STRATEGY.md` | NEW — 7-phase expansion plan with benchmark protocol |
| `PRIVACY_POLICY.md` | Ported from archive, updated for local-first model |
| `TERMS_OF_SERVICE.md` | Ported from archive, updated for v13 features |

### Frontend

- `dashboard-app`: Version bumped to 13.0.0, tool count updated to 178, subtitle shows "28 Ganas"
- `dashboard-app/api/metrics`: Fallback version updated from 12.4 → 13.0.0

### Prior Work (v12.8 → v13.0 prep sessions)

- Zero-state first-run validated in `~/Desktop/wmdummy` (152MB install, 0 errors)
- Empty dirs cleaned (`collaboration/`, `dashboard/`, `integrations/`)
- Broken shims fixed (`benchmarks/__init__.py`, `safety/__init__.py`)
- Mypy per-package config: 2,454 → 1,226 errors (strict on `tools/` + `interfaces/`)
- Mojo updated to 0.26.1 (13 categories of breaking changes fixed)
- All 6 polyglot languages verified clean

### Updated Counts

- Tests: **1199 passed**, 4 skipped
- Active fusions: **28** (unchanged)
- MCP tools: **178** (unchanged)
- Polyglot languages: **7** (Python + 6 accelerators)
