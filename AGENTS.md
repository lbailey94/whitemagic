# AGENTS.md — WhiteMagic v5 Developer Guide

## Build

```bash
cargo build                    # Debug build
cargo build --release          # Release build
cargo test                     # Run all tests (3,438 tests)
cargo test -p wm-core          # Test a single crate
cargo bench                    # Run benchmarks (criterion)
cargo clippy --all-targets     # Lint (0 warnings)
cargo fmt --all -- --check     # Format check
```

## Architecture (15 crates, 229 tools, ~131,000 LOC, 3,438 tests)

- **wm-core**: Core types (Gana, EffectRow, Tool trait, BrainWave, Galaxy, HolographicCoords, attestation, security, mutable structures)
- **wm-memory**: LMDB store + Tantivy FTS + LanceDB vectors + Mandala compartments + local embedder (HTTP/llama-server + stub)
- **wm-dispatch**: Async tool dispatch pipeline (effect check → destructive confirm → dharma → rate limit → tool → stats)
- **wm-cognitive**: Citta cycle, dream cycle, brain-wave eco mode, 7 autonomous cycles, spiral tracker, reflex, timescale, drive, resonance, autonomic (merged from 6 crates in v5 Phase 1)
- **wm-governance**: Dharma rules, karma ledger (SHA-256 chain), resource rules, mandala compartments, policy engine
- **wm-polyglot**: Julia (jlrs), Haskell (FFI), Zig (C ABI), Koka (C ABI)
- **wm-tools**: 229 tool implementations organized by Gana + `wm` meta-tool with NLU routing (embedding router + TF-IDF fallback + 12 prefix routes)
- **wm-mcp**: Async MCP server (JSON-RPC over stdio, exposes only `wm` meta-tool) + `wm` CLI + PyO3 bridge (feature-gated)
- **wm-substrate**: Hardware metrics, Harmony Vector (Lakshmi), /proc + /sys reading, sensorimotor bus
- **wm-bicameral**: Dual-hemisphere reasoning (left: LlamaLeftHemisphere/heuristic, right: BitNet/LLM/stub) + inference router (5-tier complexity-aware routing) + learned router (embedding k-NN + conformal calibration) + edge rule generator + imagination engine + self-play training loop
- **wm-sangha**: Signed multi-agent mesh — HMAC-SHA256 message + identity signatures, peer authority caps, quarantine with the bad-apple rule (locks revoked, messages purged, rejoin refused), 12-vector containment harness (`docs/SANGHA_SECURITY.md`)

## v5 Implementation Phases

- **Phase 1** ✅: Async + crate merge (19→15 crates, 3,009 tests)
- **Phase 2** ✅: Embedding NLU router (shadow mode, OATS refinement, 31 new tests)
- **Phase 3** ✅: Learned inference router (k-NN + conformal calibration, edge rule generator, 29 new tests)
- **Phase 4** ✅: Imagination engine (world model, scenario planning, dream cycle integration, MCP tools, daemon `--research-interval`)
- **Phase 5** ✅: Self-play training loop (proposer/solver/verifier, LoRA hot-swap, 3 MCP tools, daemon `--selfplay-interval`, 27 tests)
- **Phase 6** ✅: Mutable structures (GanaRegistry drift, DynamicGalaxyRegistry, LearnedDreamCycle, LearnedCycleStrategy, 31 tests + 4 E2E wiring tests)
- **Phase 7** 🔄: Polish & verification (wiring complete, benchmarks passing, docs updated)

## RSI Pipeline (Phases 1–3 Complete)

- **Phase 1**: Friction logging (`friction.log`, `friction.review`, `friction.auto_log`)
- **Phase 2 Outward Spiral (WS-1–WS-5)**: Rich telemetry envelope, deduplication, karma-friction bridge, proactive improvement, resolution verification with regression detection
- **Phase 3 Adversarial**: E2E outward spiral test, criterion benchmarks, `redteam.from_friction` (regression test synthesis), `redteam.coverage_report` (per-system coverage gaps)
- **12 RSI tools**: friction.log, friction.review, friction.auto_log, improve.proposals, improve.active_proposals, redteam.proposals, redteam.from_friction, redteam.coverage_report, friction.resolve, transaction.begin, transaction.commit, transaction.rollback
- **8 autonomous cycle types**: Connect, Compress, Emergence, Prune, Improve, Redteam, Sensorimotor, Research

## NLU Routing (v5 Phases 2–3)

The `wm` meta-tool routes natural language to tools via a two-layer system:

### Layer 1: Embedding NLU Router (Phase 2)
- `EmbeddingRouter` in `wm-tools/src/embedding_router.rs` — cosine similarity against pre-computed tool embeddings
- OATS (Outcome-Aware Tool Selection): offline embedding refinement from success/failure centroids (α=0.15, min 10 observations)
- OATS persistence: `save_oats()` / `load_oats()` serialize outcome stats to JSON for cross-restart learning
- Shadow mode: embedding router primary, TF-IDF fallback runs alongside; `ShadowModeStats` tracks disagreements, samples, and promotion readiness (rate < 20%, ≥ 100 queries)
- `nlu.shadow_report` MCP tool: returns disagreement analytics, top disagreement pairs, recent samples, and promotion readiness assessment
- Shadow stats persisted to `mutable_shadow_stats.json` on daemon shutdown
- Stub embedder detected at init → TF-IDF used directly (no semantic degradation)

### Layer 2: Learned Inference Router (Phase 3)
- `LearnedRouter` in `wm-bicameral/src/learned_router.rs` — embedding k-NN (k=5) + conformal calibration
- Replaces 20 regex complexity patterns for inference tier selection
- Cold-start fallback to `ComplexityClassifier` (regex) when history < 10 records
- `EdgeRuleGenerator`: auto-promotes high-frequency simple responses to edge rules (frequency ≥ 5, confidence > 0.9, response < 200 chars)

## Imagination Engine (v5 Phase 4)

The imagination engine implements the "imagine → simulate → evaluate → decide" loop (Sutton's search method):

### Components
- `WorldModel` in `wm-bicameral/src/world_model.rs` — bicameral LLM state prediction with `predict()`, `rollout()`, `generate_actions()`
- `ScenarioEngine` in `wm-bicameral/src/scenario.rs` — core imagine→simulate→evaluate loop with `imagine()`, `select_best()`, `reflect()`
- `ScenarioEvaluator` in `wm-bicameral/src/evaluator.rs` — multi-criteria scoring (goal progress, risk, novelty, confidence)
- `SimulationBridge` in `wm-bicameral/src/simulation_bridge.rs` — connects `wm-simulation` (Monte Carlo, forecasting, counterfactual)
- `ImaginationConfigurator` in `wm-bicameral/src/configurator.rs` — `DeliberationMode` (Direct, Shallow, Deep, Research) for depth selection

### Integration Points
- **MCP tools**: `imagine.scenario`, `imagine.predict`, `imagine.reflect` (in `wm-tools/src/expansion/imagination.rs`)
- **Autonomous cycle**: `CycleType::Research` scans for open problems, generates hypotheses via `ScenarioEngine`, stores as `MemoryType::Hypothesis`
- **Dream cycle**: Oracle phase uses `ScenarioEngine::reflect()` for counterfactual replay on hub memories
- **Daemon**: `--research-interval` flag (0 = run with regular cycle sweep, >0 = dedicated Research cycle)
- **McpServer**: `init_imagination()` builds `ScenarioEngine` at startup, wired into dream + cycle contexts

## Self-Play Training Loop (v5 Phase 5)

The self-play training loop implements the "propose → solve → verify → collect" cycle for autonomous model improvement:

### Components
- `SelfPlayLoop` in `wm-bicameral/src/self_play.rs` — orchestrates the full cycle with `run()`, `run_cycle()`, `stats()`, `export_training_data()`
- `TaskProposer` — generates tasks (grounded in memory or ungrounded), 5 task types: CodeGeneration, ToolDispatch, Reasoning, Memory, Creative
- `TaskSolver` — attempts to solve proposed tasks using bicameral handlers
- `SelfVerifier` — LLM self-critique with historical accuracy calibration
- `ExactMatchVerifier` — checks if solution contains expected answer
- `ToolResultVerifier` — checks if tool dispatch succeeded
- `LoRAAdapterManager` — hot-swap adapter management with versioning and min-sample thresholds
- `SelfPlayConfig` — configurable cycle count, task types, consecutive failure limits, adapter update thresholds

### Integration Points
- **MCP tools**: `selfplay.run`, `selfplay.status`, `selfplay.export` (in `wm-tools/src/expansion/self_play.rs`)
- **Daemon**: `--selfplay-interval` flag (0 = disabled, >0 = dedicated self-play cycle)
- **Training data**: Collected samples exported as JSONL or llama.cpp format for LoRA fine-tuning

## Mutable Structures (v5 Phase 6)

Makes previously fixed structures learnable:

### Components
- `GanaRegistry` in `wm-core/src/mutable.rs` — tracks co-usage patterns between Ganas, suggests taxonomy reorganization when drift threshold exceeded
- `DynamicGalaxyRegistry` — creates virtual galaxies from memory clustering, auto-prunes ineffective ones
- `LearnedDreamCycle` — learns which of the 12 dream phases are most effective, reorders/skips phases based on historical data
- `LearnedCycleStrategy` — learns which autonomous cycle types are most effective, supports 4 strategies (FixedOrder, PriorityBased, BestOnly, Adaptive)
- `PhaseEffectiveness` / `CycleEffectiveness` — per-phase/cycle effectiveness records with rolling averages

### Wiring (Phase 7)
- **DispatchPipeline**: `GanaRegistry` attached via `with_gana_registry()`, records usage + co-usage on every tool dispatch
- **DreamCycle**: `LearnedDreamCycle` attached via `with_learned()`, reorders phases by effectiveness, records phase results
- **AutonomousCycleRunner**: `LearnedCycleStrategy` attached via `with_learned()`, selects cycles adaptively, records cycle effectiveness
- **McpServer**: `GanaRegistry` and `DynamicGalaxyRegistry` shared via `Arc<Mutex<>>`, initialized in `with_defaults()`
- **Daemon**: `LearnedCycleStrategy` wired into `AutonomousCycleRunner`, `LearnedDreamCycle` wired into `DreamCycle`
- **Emergence cycle**: `DynamicGalaxyRegistry` wired via `CycleContext::with_dynamic_galaxies()`, auto-creates dynamic galaxies from detected tag clusters
- **Persistence**: All mutable structures save/load JSON state on daemon startup/shutdown (`save_mutable_state()` / `load_mutable_state()`). Files: `mutable_gana_registry.json`, `mutable_dynamic_galaxies.json`, `mutable_learned_dream.json`, `mutable_learned_cycles.json`, `mutable_shadow_stats.json` in the store directory
- **E2E tests**: 5 integration tests in `server.rs` verify GanaRegistry recording, DynamicGalaxyRegistry access, LearnedDreamCycle attachment, full pipeline mutable structures integration, and persistence roundtrip

## MCP Server

The MCP server exposes a **single tool** (`wm`) via `tools/list`. All 229 tools are accessible through the `wm` meta-tool:
- `wm(thought="remember that X is Y")` — NLU routing (embedding primary, TF-IDF fallback)
- `wm(route="memory.create", args={...})` — explicit dispatch
- `wm(thought="list tools")` or `wm(route="tools.list")` — discover all tools

### Serve vs Daemon

- `wm serve` is dispatch-only: request handling, telemetry, brain-wave transitions, and a throttled hardware sample (≤1/s). Autonomous work — dream consolidation, the 8 autonomous cycles, WS-4 improvement proposal surfacing — is scheduled by the daemon (`wm daemon`) on its own intervals, never on the request path, so per-request latency stays deterministic.
- Inner tool failures inside `wm` return `{"status":"error", ...}` at the JSON-RPC level (readable for NLU clients), but the server derives the true outcome from that payload so the self-model, friction log, citta, drive and workspace all record failures as failures.

### Runtime Env Knobs

| Variable | Default | Purpose |
|---|---|---|
| `WM_DISPATCH_TIMEOUT_MS` | 300000 | Per-tool dispatch timeout (0 disables) |
| `WM_DISPATCH_TOOL_RPM` | 60 | Per-tool rate limit (the `wm` meta-tool bucket) |
| `WM_DISPATCH_GLOBAL_RPM` | 300 | Global dispatch limit (each NLU call counts outer `wm` + inner tool) |
| `WM_DISPATCH_BURST` | 10 | Burst allowance per tool |
| `WM_MESH_KEY` | random/process | Stable Sangha node identity across restarts |
| `WM_EMBEDDER_ENDPOINT` | unset (TF-IDF only) | Embedding router backend (`/v1/embeddings`) |

## Safety Features

### Destructive Tool Confirmation

Tools that delete or overwrite data set `destructive: true` in their `EffectRow`. The dispatch pipeline blocks these unless `"confirm": true` is present in the tool arguments.

**8 destructive tools**: `memory.delete`, `galaxy.purge`, `galaxy.transfer`, `galaxy.restore`, `memory.consolidate`, `memory.deduplicate`, `system.flush`, `karma.clear`

Destructive tools are additionally **structurally unreachable via natural-language routing** (`thought=`): they require an explicit `route=` match plus `confirm: true`. Fuzzy NLU can never reach them, regardless of router quality.

### Transaction Snapshot/Rollback

Three tools provide multi-tool atomic sequences:
- `transaction.begin` — snapshots all memory galaxies into Journals, stores backup ID in shared state
- `transaction.commit` — clears transaction state, keeping all changes
- `transaction.rollback` — restores all galaxies from snapshot (destructive, requires `confirm: true`)

### Compartment-Based Access Control

`Context` carries `compartment` and `user_id` from MCP request `_meta`. Galaxy access is enforced via `can_access_galaxy()` and `can_write_galaxy()`:
- `sandbox` — Tutorial, Research only
- `production` — all memory galaxies
- `secure` — all galaxies including system galaxies

## Conventions

- `#![forbid(unsafe_code)]` in all crates except wm-polyglot and wm-mcp/pyo3_bridge (FFI boundaries)
- wm-mcp uses `#![deny(unsafe_code)]` at crate level, `#![allow(unsafe_code)]` in `pyo3_bridge` module only
- All public types derive `Debug`, `Clone`, `Serialize`, `Deserialize` where applicable
- Tests are in-module (`#[cfg(test)] mod tests`) — no separate test files
- Every tool implements the `Tool` trait and declares its `Gana` and `EffectRow`
- No heap allocation in dispatch hot path (use arena allocators)
- Atomic stats only — no locks in tool stats tracking

## Polyglot Build

```bash
# Rust only (default)
cargo build --release

# With Julia support
cargo build --release --features wm-polyglot/julia

# With Python MCP shell (PyO3)
cargo build --release --features wm-mcp/python

# With LanceDB vector search
cargo build --features wm-memory/lancedb
```

## CLI Commands

```bash
wm serve       # Start MCP server (JSON-RPC over stdio, exposes wm meta-tool)
wm quickstart  # Run demo
wm doctor      # Diagnose issues (--store flag for custom path)
wm stats       # Show resource usage and consciousness dashboard (--store flag)
wm brain-wave  # Show current brain-wave state (--store flag)
wm polyglot    # Show polyglot status
```

## Python MCP Shell

```bash
# Build PyO3 extension
cargo build --release --features python -p wm-mcp
ln -sf libwm_mcp.so target/release/whitemagic_v4.so

# Run Python MCP server
PYTHONPATH=target/release python python/whitemagic_v4_server.py --store ~/.local/share/whitemagic/lmdb
```

## Benchmarks

```bash
# RSI pipeline benchmarks (criterion)
cargo bench -p wm-tools --bench rsi_bench

# Results (--quick):
# friction_hash: ~243 ns
# log_error_new_entry: ~17.2 ms (tempdir-dominated)
# log_error_dedup (100 entries): ~1.2 ms
# friction_log_tool_call: ~1.45 ms
```
