# Changelog

All notable changes to WhiteMagic are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [5.6.0] — 2026-08-09

### ACS compliance surface (Microsoft Agent Control Specification)

- **`wm-governance::acs`** — the five-checkpoint model (input / llm / state / tool_execution / output) mapped onto Dharma governance: `AcsCheckpoint`, `AcsAction` (allow→block severity ladder), `AcsRule` → `PolicyRule` conversion with sutra + OWASP mapping
- **Policy YAML import/export** (`acs-yaml` feature, `serde_yaml`): `DharmaPolicy::to_acs_yaml()` renders the live policy as portable ACS policy YAML; `import_acs_yaml()` parses ACS policies into dharma rules unchanged. Feature-gated: `--features wm-governance/acs-yaml`
- **`dharma.acs` tool** (202 → **204 tools**, with `claims`) — actions: `report` (per-checkpoint coverage table + percent), `export` (policy as ACS YAML), `import` (ACS YAML → dharma rules)
- **`AcsComplianceReport`** — per-checkpoint coverage with `coverage_percent()`, mirroring the OWASP coverage surface; `docs/ACS_ALIGNMENT.md` published as the positioning asset

### Prescience claims ledger (v26 `temporal_db` port)

- **`wm-simulation::claims`** — `ClaimsLedger` with dated, falsifiable claims: `record` (source date + mandatory falsification criterion), `resolve` (validation event → validated credits lead weeks, 1 week = 1 point; falsified recorded as a miss), `status` (totals + per-domain breakdown), `list` (domain/status filters)
- **`claims` tool** — actions: `add`, `resolve`, `status`, `list`; ledger persists to `<store>/claims_ledger.json` on shutdown, restored on startup
- The falsified count is always reported alongside the score — honesty is part of the store, not an afterthought

### Self-model persistence + doctor drift health

- **`SelfModel::to_json()` / `from_json()`** — full state persistence: per-metric
  histories with timestamps, alert rules, and confidence calibrator state. A
  restarted process resumes forecasting, drift alerts, and confidence exactly
  where it left off. Persisted to `<store>/self_model.json` on shutdown,
  restored on startup
- **`wm doctor` live drift health** — reads the persisted self-model and reports
  latest conformal coverage + Brier score with the same thresholds as the alert
  engine (0.85/0.80 coverage warning/critical, 0.15/0.30 Brier), including
  trend direction and exit code contribution on critical drift. The
  conformal → monitor → doctor loop is now closed
- E2E: mutable-state persistence roundtrip now also verifies self-model
  history restore

### Counts

- 202 → **204 tools** (claims, dharma.acs)
- 3,311 → **3,335 tests passing, 0 failed** (+24)
- 0 clippy warnings, fmt clean, cargo-deny all green

## [5.5.0] — 2026-08-08

### MC suite completion (v26 `mc.*` parity)

- **`mc.rare_event`** — rare-event probability estimation:
  - *Subset simulation* (Au & Beck): Metropolis–Hastings conditional sampling with the correct φ(x')/φ(x) acceptance ratio; verified against the analytic chi-square tail P(χ²₂ > 9) ≈ 0.0111
  - *Importance sampling* with exact likelihood-ratio weights and coefficient-of-variation diagnostics
- **`mc.sde`** — SDE solvers: Euler–Maruyama and Milstein (with the ΔW²−Δt correction for GBM), GBM + Ornstein–Uhlenbeck drift, terminal statistics (mean/std/percentiles/min/max), and two-level MLMC extrapolation (coupled seeds)
- **`mc.superforecaster`** — the full orchestrator:
  - *LHS* (Latin Hypercube Sampling with Fisher–Yates stratum permutations)
  - *PCE* surrogate (Hermite basis, normal-equation least squares) with analytic Sobol' first-order/total-effect indices
  - *Bayesian optimization* refinement on top
  - Verified: recovers linear surfaces (R² > 0.99), ranks dominant variables, finds 2-D optima

### GP hyperparameter fitting

- **`GaussianProcess::log_marginal_likelihood`** — `−½yᵀK⁻¹y − ½log|K|` from the existing Cholesky factor
- **`GaussianProcess::fit_hyperparameters`** — optimizes (ℓ, σ_f², σ_n²) in log space using the crate's own BayesianOptimizer (dogfooding); fixes the fixed-hyperparameter limitation
- `mc.surrogate` gains `fit_hyperparameters: true` + `hp_iterations` — verified to recover the length scale of high-frequency data

### Brier → self-model monitoring (feedback triangle complete)

- **New `BrierScore` self-model metric** (lower is better, warning 0.15 / critical 0.3 — the v26 "good calibration" threshold)
- `simulation.calibrate` scorecard now records the average Brier score into the self-model and surfaces drift alerts — alongside `ConformalCoverage`, the calibration subsystem is now fully monitored: conformal (quantification) → Brier (measurement) → selfmodel (monitoring)

### Counts

- 199 → **202 tools** (mc.rare_event, mc.sde, mc.superforecaster)
- 3,284 → **3,311 tests passing, 0 failed** (+27)
- 0 clippy warnings, fmt clean, cargo-deny all green

## [5.4.0] — 2026-08-08

### Conformal drift monitoring

- **`conformal.monitor` tool** — evaluate empirical coverage on recent observations (classification sets or regression intervals + truths), returns coverage report, `drift` flag, and live drift alerts
- **`ConformalCoverage` self-model metric** — each monitor run records empirical coverage into the self-model; the alert engine fires warning/critical drift alerts when coverage persists below 0.85/0.80 (default rules, per-alpha overridable)
- **Auto-persistence** — conformal calibration state now saves to `<store>/conformal_store.json` on shutdown and restores on startup (`wm doctor` section 10 reads the same file — the persistence loop is closed)
- `CoverageReport::evaluate_sets` — new list-based evaluator in wm-conformal

### Brier scorecard (`simulation.calibrate`)

- **New `wm-simulation::calibration` module** — `CalibrationStore` (record/resolve/scorecard), `CalibrationPrediction`, `BrierScorecard` with the **Murphy decomposition**: Brier score, reliability, resolution, uncertainty, and Brier skill score (BSS) vs. climatology — beyond v26's basic average
- **`simulation.calibrate` tool** with actions `record` / `resolve` / `scorecard`; historical calibration gap feeds a small adjustment into future predictions (v26 parity)
- Calibration state auto-persists to `<store>/calibration_store.json` across restarts

### GP surrogate + Bayesian optimization

- **New `wm-simulation::bayesian` module** (pure Rust, no external linear algebra):
  - `GaussianProcess` — RBF-kernel regression with Cholesky solve, posterior mean/variance, numerical jitter
  - `expected_improvement` — EI acquisition with exploration bias
  - `BayesianOptimizer` — random init → GP fit → EI-guided candidate search
  - `Expr` — tiny safe expression evaluator (`x[0]`, `+ - * / ^`, `sin/cos/tan/exp/log/sqrt/abs`, `pi`, `e`) with structural validation, unary minus, and correct `-x^2 = -(x^2)` precedence
- **`mc.surrogate` tool** — fit a GP response surface, predict with uncertainty at query points
- **`mc.optimize` tool** — Bayesian optimization over `param_ranges` with a `fitness_expr` (e.g. `"-(x[0] - 3)^2 + 5"`), full iteration trace in the response

### Hardening batch

- **Time-windowed rate limiting at the MCP boundary** — `RateWindow` (sliding 60s window, default 600 req/min, `wm serve --rate-limit`); complements the per-connection `RequestBudget`; throttled requests get `-32000` with `retry_after_secs`
- **`wm doctor` exit codes** — real issue counting (missing store, corruption, missing Tantivy index, conformal/calibration problems) with exit code 1 on any issue, 0 when healthy; useful for health-check automation
- **CI fuzz corpus regression** — fuzz workflow now replays the committed seed corpora (`-runs=1000`) before the 30s timed runs

### Counts

- 195 → **199 tools** (conformal.monitor, simulation.calibrate, mc.surrogate, mc.optimize)
- 3,240 → **3,284 tests passing, 0 failed** (+44)
- 0 clippy warnings, fmt clean, cargo-deny all green

## [5.3.0] — 2026-08-08

### Boundary hardening (MCP input limits + request budget)

- **Validation layer now enforced** — `validate_request`/`validate_tools_call` existed but were never wired into the request path; SSRF, path traversal, injection, and the 64KB params cap were dead code. All requests now pass boundary validation in `handle()` before any dispatch: malformed structure → `-32602`, unsafe URL → SSRF rejection, traversal → rejection, oversized params → rejection
- **Per-session request budget**: `RequestBudget` (default 10,000 requests/connection, `0` = unlimited), enforced at the boundary with `-32000` when exhausted. Configurable via `wm serve --max-requests`
- **Bounded stdin reads**: raw request lines capped at 1MB (`MAX_REQUEST_SIZE`) in both sync `run()` and async `run_async()` — prevents unbounded allocation from a malicious client (drains to EOL and responds `-32600`)
- New public API: `RequestBudget`, `MAX_REQUEST_SIZE`, `MAX_PARAMS_SIZE`, `MAX_STRING_LEN`, `DEFAULT_MAX_REQUESTS_PER_SESSION`

### Daemon watchdog

- **Stall detection**: watchdog thread monitors the main-loop heartbeat; if no tick within `watchdog_timeout` (default 60s, `0` = disabled), logs CRITICAL, grants a 10s grace window for state saving, then force-exits (`exit(1)`) so a supervisor (Docker `restart` / systemd `Restart=always`) restarts the daemon
- **Panic resilience**: all five heavy components (cycle sweep, dream, codegen, research, self-play) wrapped in `catch_unwind` — a panic in one component no longer kills the daemon
- Configurable via `wm daemon --watchdog-timeout` / `config.toml [daemon] watchdog_timeout_secs`

### Fuzz corpus seeds (committed)

- **76 curated seeds across all 7 targets** (was: only auto-generated nlu_classify inputs, nothing tracked) — seeds committed as `seed_*` files so CI bootstraps coverage instantly; regenerated sha1 artifacts stay ignored
- **Fuzz build fix**: `serde` was missing from `fuzz/Cargo.toml` deps — `json_rpc_parse` target did not compile
- **`--all-features` fix**: `wm-polyglot` enabled jlrs without selecting a Julia version feature (jlrs-macros hard-error); added `julia-1-10`

### Tooling

- **`wm doctor` conformal calibration health** (section 10): reports classifier/regressor/APS fitted status, sample counts, and alphas from `<store>/conformal_store.json`; guides calibration/persistence when absent
- **Count correction**: tool registry is 195 (docs previously said 192)
- **Doctest fix**: `SplitConformalClassifier` doc example used the pre-`&[f64]` API and failed to compile

### Counts

- 3,212 → **3,240 tests passing, 0 failed** (28 new: budget 5, boundary 5, bounded-line 6, watchdog 3, doctest 1, +8 config/daemon)
- 0 clippy warnings, fmt clean, cargo-deny all green

## [5.2.2] — 2026-08-08

### Conformal Prediction (net-new feature)

- **New crate `wm-conformal`** — distribution-free uncertainty quantification with finite-sample coverage guarantees (present in neither v26 nor v5 before)
- `SplitConformalClassifier`: label prediction sets, nonconformity `1 − score`
- `SplitConformalRegressor`: value intervals, nonconformity absolute residual
- `AdaptivePredictionSets` (Romano et al. 2020): smaller sets for calibrated models, with the required uniform tie-break term
- `CoverageReport`: empirical coverage evaluation for drift monitoring
- 7 new MCP tools: `conformal.fit_classifier`, `conformal.fit_regressor`, `conformal.predict_set`, `conformal.predict_interval`, `conformal.status`, `conformal.export`, `conformal.import`
- Coverage guarantee statistically verified: ≈ 1−α averaged over 40 calibration draws × 80K test points (classifier 0.90, regressor 0.95, APS ≥ 0.89)
- 20 new tests; total 3,212 passing, 0 failed

### Hardening

- **Daemon SIGTERM handling**: graceful shutdown (karma flush + learned-state save) on SIGTERM for Docker/systemd, alongside existing SIGINT
- **Audit of production unwraps**: all 31 remaining sites confirmed logically guarded (length-checked slices, is_empty guards, checked_sub)
- 0 clippy warnings, fmt clean, all cargo-deny checks passing

### Tool surface

- 185 → 192 tools (7 conformal)
- Dependency audit: 2 vulnerabilities → 0 (pyo3 0.22→0.29, tantivy 0.22→0.26)
- 72 lock()/read()/write().unwrap() panic sites → graceful degradation

## [5.2.1] — 2026-08-10


### Karma Ledger Optimization & Phase 7 Benchmarks

#### Karma Write-Behind Batching
- **Batched LMDB writes**: `KarmaLedger` buffers `record()` calls in memory and flushes via single LMDB transaction (`flush_threshold=16` default)
- **Benchmark results** (criterion, release profile):
  - `karma_record_batched`: 97.7 µs/call (batched, threshold=16)
  - `karma_record_synchronous`: 1.07 ms/call (threshold=0, flush every record)
  - **10.9x throughput improvement** (batched vs synchronous)
  - `karma_flush_16_entries`: 314.7 µs per batch flush (16 entries in one LMDB transaction)
  - `dispatch_noop_with_karma`: 168.2 µs (full pipeline + karma record)
  - `dispatch_noop_no_karma`: 1.25 µs (pipeline overhead without karma)

#### Mutable Structure Benchmarks (13 criterion benchmarks)
- **GanaRegistry**: record_usage 228 ns, record_co_usage 1.02 µs, co_usage_count 171 ns, analyze_drift 80 ns, serialize 1.13 µs, deserialize 1.61 µs
- **LearnedDreamCycle**: record_phase 488 ns, phases_to_run 457 ns, update_phase_order 568 ns, serialize 3.71 µs, deserialize 5.45 µs
- **LearnedCycleStrategy**: record_cycle 362 ns, cycles_to_run 29 ns, update_priority_order 390 ns, serialize 3.97 µs, deserialize 3.81 µs

#### Daemon Karma Flush on Shutdown
- **Explicit `flush()` call**: Daemon's graceful shutdown now explicitly flushes the karma ledger before saving mutable state, ensuring no pending batched entries are lost when the process exits
- **Root cause**: `KarmaLedger::Drop` flushes, but the daemon holds `Arc<KarmaLedger>` inside `McpServer` — `Drop` doesn't fire until the server itself is dropped, which is outside `run_daemon`'s scope

#### E2E Integration Test
- **`pipeline_karma_batched_e2e`**: Full dispatch cycle with 20 tool calls (10 honest + 10 wasteful), verifies pending buffer count, total_debt accuracy (2.0), chain integrity after flush, and persistence across ledger instances

### Metrics
- **185 tools** (unchanged)
- **3,168 tests** (up from 3,167: +1 E2E karma batching test)
- **0 clippy warnings**, fmt clean

## [5.2.0] — 2026-08-10

### v5 Strategy Implementation (Phases 5–6)

#### Phase 5: Self-Play Training Loop ✅
- **`SelfPlayLoop`** (`wm-bicameral/src/self_play.rs`, ~1,650 lines): proposer → solver → verifier → training data collection loop
- **`TaskProposer`**: grounded/ungrounded task generation with memory context, 5 task types (CodeGeneration, ToolDispatch, Reasoning, Memory, Creative)
- **`TaskSolver`**: attempts to solve proposed tasks using bicameral handlers
- **3 Verifier implementations**: `SelfVerifier` (LLM self-critique with calibration), `ExactMatchVerifier`, `ToolResultVerifier`
- **`LoRAAdapterManager`**: hot-swap adapter management with versioning and min-sample thresholds
- **`SelfPlayConfig`**: configurable cycle count, task types, consecutive failure limits, adapter update thresholds
- **`SelfPlayStats`**: accuracy tracking, per-task-type success rates, difficulty trends, adapter update history
- **3 MCP tools**: `selfplay.run`, `selfplay.status`, `selfplay.export` (`wm-tools/src/expansion/self_play.rs`)
- **Daemon integration**: `--selfplay-interval` CLI flag, self-play cycle in daemon main loop with memory grounding
- **27 new tests**: task proposer, solver, verifiers, LoRA adapter, full cycle, multi-cycle, training data export, stats
- **1 benchmark**: `self_play_bench` (single cycle ~100µs, 20 cycles ~134µs)

#### Phase 6: Mutable Structures ✅
- **`GanaRegistry`** (`wm-core/src/mutable.rs`): Gana taxonomy drift based on co-usage patterns
  - Co-usage matrix with string keys for JSON serialization
  - Drift threshold triggers suggested merges with confidence scores
  - Per-Gana usage counts and rolling success rates
  - `analyze_drift()` returns top-N reorganization suggestions
- **`DynamicGalaxyRegistry`**: dynamic galaxy creation from memory clustering
  - Configurable min cluster size, max galaxies, prune threshold
  - Auto-pruning of ineffective galaxies
  - Effectiveness tracking per dynamic galaxy
- **`LearnedDreamCycle`**: learned dream cycle phase selection
  - 12-phase effectiveness tracking (runs, useful results, avg improvement, avg duration)
  - Phase reordering by effectiveness score
  - Ineffective phase filtering (configurable threshold + min runs)
- **`LearnedCycleStrategy`**: learned autonomous cycle strategies
  - 4 strategies: FixedOrder, PriorityBased, BestOnly, Adaptive
  - Auto-transitions from FixedOrder to PriorityBased after min_runs
  - Per-cycle-type effectiveness tracking with proposal counts
  - Priority order updates based on effectiveness scores
- **31 new tests**: GanaRegistry (7), DynamicGalaxyRegistry (5), LearnedDreamCycle (6), PhaseEffectiveness (1), LearnedCycleStrategy (7), serialization (4), CycleEffectiveness (1)

### Metrics (v5 Phases 1–6)
- **14 crates** (unchanged)
- **179 tools** (176 + 3 self-play)
- **3,142 tests** (up from 3,080; 31 Phase 6 + 4 E2E wiring)
- **0 clippy warnings**, fmt clean
- **~3,400 lines new code** (Phase 5: ~1,950, Phase 6: ~1,200, Wiring: ~250)

### Phase 7: Polish & Verification (In Progress)
- **Mutable structures wiring**: All 4 mutable structures integrated into the live pipeline
  - `GanaRegistry` → `DispatchPipeline` via `with_gana_registry()`, records usage + co-usage on every tool dispatch
  - `LearnedDreamCycle` → `DreamCycle` via `with_learned()`, reorders phases by effectiveness, records phase results
  - `LearnedCycleStrategy` → `AutonomousCycleRunner` via `with_learned()`, selects cycles adaptively, records cycle effectiveness
  - `GanaRegistry` + `DynamicGalaxyRegistry` → `McpServer` via `Arc<Mutex<>>`, shared instances initialized in `with_defaults()`
  - `LearnedCycleStrategy` + `LearnedDreamCycle` → Daemon main loop
- **4 E2E integration tests**: GanaRegistry recording, DynamicGalaxyRegistry access, LearnedDreamCycle attachment, full pipeline integration
- **All benchmarks passing**: dream, reflex, RSI, self-play, router, pipeline
- **0 clippy warnings**, fmt clean

## [5.1.0] — 2026-08-09

### v5 Strategy Implementation (Phase 4)

#### Phase 4: Imagination Engine ✅
- **`WorldModel`** (`wm-bicameral/src/world_model.rs`, 775 lines): bicameral LLM state prediction with `predict()`, `rollout()`, `generate_actions()`
- **`ScenarioEngine`** (`wm-bicameral/src/scenario.rs`, 602 lines): core imagine→simulate→evaluate loop with `imagine()`, `select_best()`, `reflect()`
- **`ScenarioEvaluator`** (`wm-bicameral/src/evaluator.rs`, 438 lines): multi-criteria scoring (goal progress, risk, novelty, confidence)
- **`SimulationBridge`** (`wm-bicameral/src/simulation_bridge.rs`): connects `wm-simulation` (Monte Carlo, forecasting, counterfactual) to imagination engine
- **`ImaginationConfigurator`** (`wm-bicameral/src/configurator.rs`, 440 lines): `DeliberationMode` (Direct, Shallow, Deep, Research) for depth selection
- **3 MCP tools**: `imagine.scenario`, `imagine.predict`, `imagine.reflect` (`wm-tools/src/expansion/imagination.rs`, 557 lines)
- **Dream cycle integration**: Oracle phase enhanced with `ScenarioEngine::reflect()` for counterfactual replay on hub memories
- **`CycleType::Research`**: 8th autonomous cycle — scans for open problems, generates hypotheses, stores as `MemoryType::Hypothesis`
- **Daemon `--research-interval`**: dedicated Research cycle on separate schedule (0 = run with regular cycle sweep)
- **`McpServer::init_imagination()`**: builds `ScenarioEngine` at startup, wired into dream + cycle contexts
- **2 new tests**: `dream_context_with_imagination`, `dream_cycle_oracle_with_imagination`

### Metrics (v5 Phases 1–4)
- **14 crates** (unchanged)
- **176 tools** (unchanged)
- **3,080 tests** (up from 3,078)
- **0 clippy warnings**, fmt clean

## [5.0.0] — 2026-08-08

### v5 Strategy Implementation (Phases 1–3)

#### Phase 1: Foundation (Async + Crate Merge) ✅
- **Crate merge**: 19 → 14 crates (wm-cognitive absorbs wm-consciousness, wm-reflex, wm-timescale, wm-drive, wm-resonance, wm-autonomic)
- **Async dispatch**: `async fn dispatch`, `#[async_trait]` Tool, `.await` at all call sites
- **Async MCP server**: `handle_request`, `handle`, `handle_tools_call` all async
- **Test conversion**: All tests converted to `#[tokio::test]` + `async fn`
- **3,009 tests pass**, 0 clippy warnings, fmt clean
- ~5,000 lines changed across 60+ files

#### Phase 2: Embedding NLU Router ✅ (shadow mode)
- **`EmbeddingRouter`** (`wm-tools/src/embedding_router.rs`, ~530 lines): cosine similarity against pre-computed tool embeddings
- **OATS** (Outcome-Aware Tool Selection): offline embedding refinement from success/failure centroids (α=0.15, min 10 observations)
- **Shadow mode**: embedding router primary, TF-IDF fallback runs alongside logging disagreements
- **Graceful fallback**: stub embedder detected at init → TF-IDF used directly
- **Integration**: `WmMetaTool::with_embedder()`, `register_meta_tools()` calls `create_embedder()`
- **31 new tests**: cosine sim, OATS refinement, A/B comparison with TF-IDF
- Step 2.8 (remove TF-IDF) deferred until production accuracy validation

#### Phase 3: Learned Inference Router ✅ (shadow mode)
- **`LearnedRouter`** (`wm-bicameral/src/learned_router.rs`, ~1,100 lines): embedding k-NN (k=5) + conformal calibration
- **`RoutingHistory`**: k-NN store with prompt frequency tracking and outcome-based weighting
- **`EdgeRuleGenerator`**: auto-promotes high-frequency simple responses to compiled edge rules (frequency ≥ 5, confidence > 0.9, response < 200 chars)
- **Shadow mode**: learned router primary, regex classifier runs alongside logging disagreements
- **Cold-start fallback**: `ComplexityClassifier` (regex) when history < 10 records
- **Integration**: `InferenceRouter::with_embedder()`, `with_learned_router()`, `record_learned_outcome()`, `observe_for_edge_rules()`, `promote_edge_rules()`
- **29 new tests**: cosine sim, k-NN routing, A/B comparison with regex, edge rule promotion
- Step 3.5 (remove regex) deferred until production accuracy validation

### Metrics (v5 Phases 1–3)
- **14 crates** (down from 19)
- **176 tools** (unchanged)
- **~115,000 LOC** (up from ~112,300)
- **3,078 tests** (up from 2,818: +152 crate merge, +31 embedding router, +29 learned router, +48 other)
- **0 clippy warnings**, fmt clean

## [4.0.0] — 2026-08-07

### Summary

Complete rewrite of WhiteMagic from Python to Rust. A cognitive operating system for agentic AI with 176 tools, 19 crates, ~112,300 lines of Rust, 2,818 tests, and zero clippy warnings. Exposed as an MCP server with a single `wm` meta-tool — all tools accessible via NLU routing or explicit dispatch.

### Architecture

- **19 crates**: wm-core, wm-memory, wm-dispatch, wm-consciousness, wm-governance, wm-polyglot, wm-tools, wm-mcp, wm-substrate, wm-bicameral, wm-drive, wm-autonomic, wm-reflex, wm-timescale, wm-workspace, wm-selfmodel, wm-resonance, wm-sangha, wm-simulation
- **176 tools** organized across 28 Gana (cognitive function categories)
- **14-galaxy memory** architecture backed by LMDB (zero-copy, memory-mapped)
- **Tantivy** full-text search with BM25 scoring and query sanitization
- **LanceDB** optional vector indexing (SIMD-accelerated ANN)
- **Local embedder** via HTTP (llama-server) with stub fallback
- **Shared IndexWriter** — single Tantivy writer behind Mutex, eliminating lock contention

### Cognitive Architecture

- **Citta consciousness**: 16D consciousness vector with coherence measurement
- **Dream cycle**: 12-phase memory consolidation
- **Brain-wave eco mode**: 5 states (Gamma, Beta, Alpha, Theta, Delta) with zero idle CPU
- **7 autonomous cycle types**: Connect, Compress, Emergence, Prune, Improve, Redteam, Sensorimotor
- **Bicameral reasoning**: Dual-hemisphere (left: heuristic, right: LLM/BitNet/stub) with inference router
- **Self-model**: Predictive introspection with forecasting and alerts
- **Global workspace**: Spotlight arbitration, salience scoring, event bus
- **Drive core**: 5 intrinsic motivation drives with decay toward baseline
- **Reflex dispatch**: Safety bitmask, 8 builtin handlers, permissive/strict modes
- **Timescale bus**: 3-tier event bus (Reactive/Planning/Strategic) with brain-wave gating

### Safety Features

- **Destructive tool confirmation**: 8 tools require `"confirm": true` in args
- **Transaction snapshot/rollback**: 3 tools (begin/commit/rollback) with batch restore (>99% performance improvement)
- **Compartment-based access control**: sandbox/production/secure levels with runtime galaxy arg enforcement
- **Karma ledger**: SHA-256 hash chain for all tool actions
- **Dharma governance**: Ethical rules and resource management

### RSI Pipeline (Phases 1–3)

- **Phase 1**: Friction logging (friction.log, friction.review, friction.auto_log)
- **Phase 2**: Outward spiral (WS-1–WS-5) with telemetry, deduplication, karma bridge, resolution verification
- **Phase 3**: Adversarial (redteam.from_friction, redteam.coverage_report, E2E tests, criterion benchmarks)
- **12 RSI tools** total

### NLU Router

- 166 TF-IDF profiles with cosine similarity
- 12 prefix routes for common patterns
- Stopword filtering, English stemmer
- Payload extraction (e.g., "remember that X" → memory.create with content=X)

### Polyglot Integration

- **Julia** (jlrs), **Haskell** (FFI), **Zig** (C ABI), **Koka** (C ABI)
- All in-process via FFI — no subprocess overhead

### MCP Server

- Single `wm` meta-tool exposed via `tools/list`
- JSON-RPC over stdio
- CLI: `wm serve`, `wm quickstart`, `wm doctor`, `wm stats`, `wm brain-wave`, `wm polyglot`
- Optional PyO3 bridge for Python MCP shell

### Embodiment I/O

- Linux /proc + /sys sensor reading
- Sensorimotor bus with hardware abstraction
- Homeostatic loop and anomaly detection
- Harmony Vector (Lakshmi) for hardware-aware governance

### Security Hardening

- 20 catalog attack vectors covered
- 33 manifest attack surfaces tested
- Query sanitization (Tantivy injection prevention)
- Input validation on all MCP endpoints
- `#![forbid(unsafe_code)]` in all crates except FFI boundaries

### Performance

- Sub-6ms dispatch latency
- 14 MB release binary
- Zero-copy LMDB reads
- Atomic stats (no locks in hot path)
- Transaction rollback: ~4.5ms for 100 memories (was ~1.8-2.6s)

### Development Phases (All Complete)

- Phases 0–8: Core runtime, memory, dispatch, consciousness, governance, polyglot, MCP, fuzz, CI
- Phases A–F: Governed autonomy roadmap
- Phases R1–R7: CyberBrain architecture (reflex, timescale, workspace, self-model, bicameral, drive)
- Phases L1–L5: Local AI integration (BitMamba, LlamaLeftHemisphere, BitNet, inference router, OrtEmbedder)
- Phases N1–N21: Neural integration (Gan Ying Bus, Sangha mesh, simulation, resonance, sensorimotor)
- RSI Phases 1–3: Friction logging, outward spiral, adversarial testing

### Bug Fixes (Post-Initial Development)

- **Tantivy writer lock contention**: Moved IndexWriter into SearchEngine behind Mutex, eliminating lock errors when multiple tools try to index simultaneously
- **Dynamic galaxy compartment bypass**: Pipeline now checks runtime galaxy argument in addition to static EffectRow declarations
- **Silent Codex fallback**: BM25 results with unknown galaxies are skipped instead of misattributed
- **Orphaned embeddings**: Vector search skips embeddings whose memory was deleted
- **LMDB nested transaction bug**: Fixed silent failures in vector search caused by opening read txns during cursor txns
- **Transaction rollback performance**: Batch operations reduce 100-memory rollback from ~2s to ~4.5ms

### Removed (vs v2)

- Python runtime (replaced by Rust)
- Subprocess-based polyglot (replaced by FFI)
- ~10,000 tests (replaced by 2,818 focused tests: property, fuzz, E2E, criterion, security, red-team)
- 877-tool catalog (distilled to 176 runtime-authoritative tools)
