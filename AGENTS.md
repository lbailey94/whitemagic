# AGENTS.md — WhiteMagic v5 Developer Guide

WhiteMagic v5.8.0 is the historical release baseline, while v7 product
readiness is now the active release track. Use
[`docs/V7_PRODUCT_READINESS.md`](docs/V7_PRODUCT_READINESS.md) as the source of
truth for website containment, private-alpha gates, and stranger testing. Use
[`docs/RELEASE_READINESS.md`](docs/RELEASE_READINESS.md) for v5 evidence and
[`docs/NEXT_SESSION.md`](docs/NEXT_SESSION.md) for the current execution slice.

## Session Continuity

At the start of a working session, recall where the previous session left off
through the `whitemagic-dev` MCP tool (curated profile, writable store):

- `wm(route="session.continuity", args={"n": 5})` — the tail of the most
  recent prior session.
- `wm(route="session.replay", args={"mode": "progressive", "session_id": "<id>", "token_budget": 600})` — budgeted recall of a specific session.
- `wm(route="session.list")` — session summaries.

Record meaningful turns as you go: `wm(route="session.record", args={"content": "...", "role": "ai", "turn_type": "decision"|"breakthrough"|"summary", "importance": 0.8})`.

## Build

```bash
cargo build                    # Debug build
cargo build --release          # Release build
cargo test                     # Run all tests (3,570 tests)
cargo test -p wm-core          # Test a single crate
cargo bench                    # Run benchmarks (criterion)
cargo clippy --all-targets     # Lint (0 warnings)
cargo fmt --all -- --check     # Format check
```

## Architecture (15 crates, 237 tools, ~131,000 LOC, 3,570 tests)

- **wm-core**: Core types (Gana, EffectRow, Tool trait, BrainWave, Galaxy, HolographicCoords, attestation, security, mutable structures)
- **wm-memory**: LMDB store + Tantivy FTS + LanceDB vectors + Mandala compartments + local embedder (HTTP/llama-server + stub)
- **wm-dispatch**: Async tool dispatch pipeline (effect check → destructive confirm → dharma → resource rules (Yama) → rate limit → tool → karma + write-audit journal → stats)
- **wm-cognitive**: Citta cycle, dream cycle, brain-wave eco mode, 7 autonomous cycles, spiral tracker, reflex, timescale, drive, resonance, autonomic (merged from 6 crates in v5 Phase 1)
- **wm-governance**: Dharma rules, karma ledger (SHA-256 chain), resource rules, mandala compartments, policy engine
- **wm-polyglot**: Julia (jlrs), Haskell (FFI), Zig (C ABI), Koka (C ABI)
- **wm-tools**: 237 tool implementations organized by Gana + `wm` meta-tool with explicit routing and optional NLU (embedding router + TF-IDF fallback + 12 prefix routes)
- **wm-mcp**: Async MCP server (JSON-RPC over stdio, exposes only `wm` meta-tool) + `wm` CLI + PyO3 bridge (feature-gated)
- **wm-substrate**: Hardware metrics, Harmony Vector (Lakshmi), /proc + /sys reading, sensorimotor bus
- **wm-bicameral**: Dual-hemisphere reasoning (left: LlamaLeftHemisphere/heuristic, right: BitNet/LLM/stub) + inference router (5-tier complexity-aware routing) + learned router (embedding k-NN + conformal calibration) + edge rule generator + imagination engine + self-play training loop
- **wm-sangha**: Signed multi-agent mesh — HMAC-SHA256 message + identity signatures, peer authority caps, quarantine with the bad-apple rule (locks revoked, messages purged, rejoin refused), 12-vector containment harness (`docs/SANGHA_SECURITY.md`)

## v5 Implementation Phases

- **Phase 1** ✅: Async + crate merge (19→15 crates, 3,009 tests)
- **Phase 2** ✅: Embedding NLU router (shadow mode, OATS refinement, 31 new tests)
- **Phase 3** ✅: Learned inference router (k-NN + conformal calibration, edge rule generator, 29 new tests)
- **Phase 4** ✅: Imagination engine (world model, scenario planning, dream cycle integration, MCP tools, daemon `--research-interval`)
- **Phase 5** ✅: Self-play training loop (proposer/solver/verifier, training-data export, 3 MCP tools, daemon `--selfplay-interval`, 27 tests; live LoRA training/hot-swap remains experimental)
- **Phase 6** ✅: Mutable structures (GanaRegistry drift, DynamicGalaxyRegistry, LearnedDreamCycle, LearnedCycleStrategy, 31 tests + 4 E2E wiring tests)
- **Phase 7** 🔄: Release stabilization (feature wiring complete including vector search; boundary, storage, smoke-test, packaging, and documentation gates remain)

## RSI Pipeline (Phases 1–3 Complete)

- **Phase 1**: Friction logging (`friction.log`, `friction.review`, `friction.auto_log`)
- **Phase 2 Outward Spiral (WS-1–WS-5)**: Rich telemetry envelope, deduplication, karma-friction bridge, proactive improvement, resolution verification with regression detection
- **Phase 3 Adversarial**: E2E outward spiral test, criterion benchmarks, `redteam.from_friction` (regression test synthesis), `redteam.coverage_report` (per-system coverage gaps)
- **12 RSI tools**: friction.log, friction.review, friction.auto_log, improve.proposals, improve.active_proposals, redteam.proposals, redteam.from_friction, redteam.coverage_report, friction.resolve, transaction.begin, transaction.commit, transaction.rollback
- **8 autonomous cycle types**: Connect, Compress, Emergence, Prune, Improve, Redteam, Sensorimotor, Research

## NLU Routing (v5 Phases 2–3)

The `wm` meta-tool supports explicit routing plus a two-layer natural-language
convenience system:

### Layer 1: Embedding NLU Router (Phase 2)
- `EmbeddingRouter` in `wm-tools/src/embedding_router.rs` — cosine similarity against pre-computed tool embeddings
- OATS (Outcome-Aware Tool Selection): offline embedding refinement from success/failure centroids (α=0.15, min 10 observations)
- OATS persistence: `save_oats()` / `load_oats()` serialize outcome stats to JSON for cross-restart learning
- Shadow mode: embedding and TF-IDF results run alongside for evaluation; explicit routing remains the reliable release path until labeled results support promotion
- `nlu.shadow_report` MCP tool: returns disagreement analytics, top disagreement pairs, recent samples, and promotion readiness assessment
- Shadow stats persisted to `mutable_shadow_stats.json` on daemon shutdown
- Stub embedder detected at init → TF-IDF used directly (no semantic degradation)

### Layer 2: Learned Inference Router (Phase 3)
- `LearnedRouter` in `wm-bicameral/src/learned_router.rs` — experimental embedding k-NN (k=5) + conformal calibration
- Replaces 20 regex complexity patterns for inference tier selection
- Cold-start fallback to `ComplexityClassifier` (regex) when history < 10 records
- `EdgeRuleGenerator`: auto-promotes high-frequency simple responses to edge rules (frequency ≥ 5, confidence > 0.9, response < 200 chars)

## Imagination Engine (v5 Phase 4) — Experimental

The imagination engine implements the "imagine → simulate → evaluate → decide" loop (Sutton's search method). MCP tools (`imagine.*`) are labeled `[Experimental]` in their descriptions — live model-update paths are not yet production-verified.

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

## Self-Play Training Loop (v5 Phase 5) — Experimental

The self-play training loop implements the "propose → solve → verify → collect" cycle for autonomous model improvement. MCP tools (`selfplay.*`) are labeled `[Experimental]` in their descriptions — live LoRA training/hot-swap remains experimental.

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
- **Persistence**: All mutable structures save/load JSON state on graceful startup/shutdown (`save_mutable_state()` / `load_mutable_state()`). The daemon also checkpoints periodically (default every 5 min, configurable via `checkpoint_interval_secs` / `--checkpoint-interval`), so a SIGKILL loses at most one checkpoint interval of learning. Files in the store directory: `mutable_gana_registry.json`, `mutable_dynamic_galaxies.json`, `mutable_learned_dream.json`, `mutable_learned_cycles.json` (daemon-owned), `mutable_shadow_stats.json`, `mutable_oats.json`, `mutable_tool_stats.json`. Files at the store root (read by `wm doctor`): `conformal_store.json`, `calibration_store.json`, `claims_ledger.json`, `self_model.json`, `escalation_queue.json`, `tx_firewall_policy.json`
- **E2E tests**: 5 integration tests in `server.rs` verify GanaRegistry recording, DynamicGalaxyRegistry access, LearnedDreamCycle attachment, full pipeline mutable structures integration, and persistence roundtrip

## Vector Search (Phase 7 — Complete)

`RecallEngine` is shared via `Arc<RecallEngine>` across `ConversationalSearch`,
`MemoryCreateTool`, `MemoryBatchCreateTool`, and `MemoryHybridRecallTool`.

### Activation
- Set `WM_EMBEDDER_ENDPOINT` to a llama-server with `--embeddings`
- Without it, `StubEmbedder` is used and all tools fall back to pure BM25
- `RecallEngine::embedder_is_real()` gates hybrid wiring (checks `backend_name() != "stub"`)

### Config (`RecallConfig::from_env()`)
- `WM_RECALL_BM25_WEIGHT` (default 0.5) — BM25 text score weight
- `WM_RECALL_VECTOR_WEIGHT` (default 0.3) — vector cosine similarity weight
- `WM_RECALL_IMPORTANCE_WEIGHT` (default 0.2) — memory importance weight
- Weights clamped to [0, 1] and normalized to sum to 1.0

### Tool Behavior
- `memory.create`: calls `recall.store_with_embedding()` (auto-embeds + stores + indexes) when embedder is real; falls back to plain LMDB + Tantivy
- `memory.batch_create`: same per-item pattern with fallback
- `memory.hybrid_recall`: runs `recall.hybrid_search()` as Phase 0 (BM25 + vector fusion) when embedder is real; falls back to existing BM25-only phases

### Roadmap
See [`docs/VECTOR_SEARCH_ROADMAP.md`](docs/VECTOR_SEARCH_ROADMAP.md) for quick wins (batch embedding, benchmark integration, weight tuning) and longer-term improvements.

## MCP Server

The MCP server exposes a **single tool** (`wm`) via `tools/list`. The full
archive is accessible through the `wm` meta-tool; the curated profile is the
release surface:
- `wm(thought="remember that X is Y")` — optional NLU routing (TF-IDF fallback)
- `wm(route="memory.create", args={...})` — explicit dispatch
- `wm(thought="list tools")` or `wm(route="tools.list")` — discover all tools

### Serve vs Daemon

- `wm serve` is dispatch-only: request handling, telemetry, brain-wave transitions, and a throttled hardware sample (≤1/s). Autonomous work — dream consolidation, the 8 autonomous cycles, WS-4 improvement proposal surfacing — is scheduled by the daemon (`wm daemon`) on its own intervals, never on the request path, so per-request latency stays deterministic.
- Inner tool failures inside `wm` return `{"status":"error", ...}` at the JSON-RPC level (readable for NLU clients), but the server derives the true outcome from that payload so the self-model, friction log, citta, drive and workspace all record failures as failures.

### Tool Surface Profiles

237 tools is an archive, not a v1 product. Profiles curate which tools the `wm` meta-tool can route to (filtering happens before the meta-tools are layered on, so both NLU routing and direct dispatch respect the profile):

- `full` — every tool
- `curated` — the memory-hierarchy surface: `memory.*`, `session.*`, `claims` + `claims.*` aliases, `transaction.*`, diagnostics, `tools.list`, `tools.usage_report`, `nlu.shadow_report`
- `minimal` — `memory.create/read/list/query/search/chat/associate/associations`, `tools.list`, `gnosis`

Select via `wm serve --profile curated` or `WM_TOOL_ALLOWLIST=memory,session,claims` (comma-separated prefixes). **Omitted `--profile` defaults to curated** (verified 2026-08-21); environment variables override the default. Full-surface internals (karma, friction, governance) keep working regardless — only the boundary shrinks.

### Runtime Env Knobs

| Variable | Default | Purpose |
|---|---|---|
| `WM_DISPATCH_TIMEOUT_MS` | 300000 | Per-tool dispatch timeout (0 disables) |
| `WM_DISPATCH_TOOL_RPM` | 60 | Per-tool rate limit (the `wm` meta-tool bucket) |
| `WM_DISPATCH_GLOBAL_RPM` | 300 | Global dispatch limit (each NLU call counts outer `wm` + inner tool) |
| `WM_DISPATCH_BURST` | 10 | Burst allowance per tool |
| `WM_MESH_KEY` | random/process | Stable Sangha node identity across restarts |
| `WM_EMBEDDER_ENDPOINT` | unset (TF-IDF only) | Embedding router backend (`/v1/embeddings`) |
| `WM_EMBEDDER_BACKEND` | unset | `onnx` — use the local ONNX Runtime embedder instead of HTTP |
| `WM_EMBEDDER_ORT_MODEL` | `BAAI/bge-small-en-v1.5` | ONNX model name; `-q` suffix selects INT8-quantized variants (e.g. `bge-small-q`, ~75% smaller) |
| `WM_EMBEDDER_ORT_THREADS` | min(logical, 4) | ONNX intra-op threads — capped default prevents small-machine OOM |
| `WM_EMBEDDER_CACHE_DIR` | unset | Model cache directory for the ONNX embedder |
| `WM_EPISODIC_RERANK_ONLY` | unset | `1` — stub embedder for ingest, real embedder only for episodic rerank (fast benchmark ingest) |
| `WM_TOOL_PROFILE` | `curated` | Tool surface: `full` \| `curated` \| `minimal` |
| `WM_TOOL_ALLOWLIST` | unset | Comma-separated tool-name prefixes (wins over profile) |

`WM_TOOL_PROFILE` is the server-level configuration path. An explicit
`--profile` flag wins over the environment variable; when the flag is
omitted, curated is the default (verified 2026-08-21).

## Claims Ledger Calibration

The claims ledger grades its own track record. `claims` tool action `calibration` reports the resolved set: Brier, mean confidence vs hit rate, the signed calibration gap (positive = overconfident, negative = underconfident), a Wilson 95% interval for the hit rate, and recalibrated confidences for pending claims via empirical-Bayes shrinkage toward the observed hit rate (w = n/(n + 20)). Raw confidences are never edited — calibrated values are reported alongside. As of 2026-08-12: 20 resolved, Brier 0.078, gap **−0.215 (underconfident)**; see `docs/CLAIMS_LEDGER.md`.

## Safety Features

### Destructive Tool Confirmation

Tools that delete or overwrite data set `destructive: true` in their `EffectRow`. The dispatch pipeline blocks these unless `"confirm": true` is present in the tool arguments.

**9 destructive tools**: `memory.delete`, `galaxy.purge`, `galaxy.transfer`, `galaxy.restore`, `memory.consolidate`, `memory.deduplicate`, `system.flush`, `karma.clear`, `transaction.rollback`

Destructive tools are additionally **structurally unreachable via natural-language routing** (`thought=`): they require an explicit `route=` match plus `confirm: true`. Fuzzy NLU can never reach them, regardless of router quality.

### Transaction Snapshot/Rollback

Three tools provide multi-tool atomic sequences:
- `transaction.begin` — snapshots memory galaxies into Journals, stores backup ID in shared state; exact restore semantics are a release gate
- `transaction.commit` — clears transaction state, keeping all changes
- `transaction.rollback` — restores all galaxies from snapshot (destructive, requires `confirm: true`)

### Compartment-Based Access Control

`Context` carries `compartment` and `user_id` from MCP request `_meta`. Galaxy access is enforced via `can_access_galaxy()` and `can_write_galaxy()`:
- `sandbox` — Tutorial, Research only
- `production` — all memory galaxies
- `secure` — user memory galaxies, with system galaxies still restricted

Unknown compartment values currently fail open and are a release blocker. Do
not treat MCP `_meta.user_id` as authenticated authorization.

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
