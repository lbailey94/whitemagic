# AGENTS.md — WhiteMagic 9.1.4 Developer Guide

WhiteMagic 9.1.4 is the current committed workspace version (`Cargo.toml`). The v5.8.0
baseline and v7 product-readiness gates are historical. The current execution
queue is [`docs/V9_2_WORK_QUEUE.md`](docs/V9_2_WORK_QUEUE.md) ("Resume here").
The dev store/unit/gateway scope is `wmv9` (renamed from `wmv5`, 2026-09-11).
Historical evidence lives in
[`docs/RELEASE_READINESS.md`](docs/RELEASE_READINESS.md);
[`docs/NEXT_SESSION.md`](docs/NEXT_SESSION.md) is retained as a session log.

## Session Continuity

At the start of a working session, recall where the previous session left off
through the `whitemagic-dev` MCP tool (curated profile, writable store):

- `wm(route="session.continuity", args={"n": 5})` — the tail of the most
  recent prior session.
- `wm(route="session.replay", args={"mode": "progressive", "session_id": "<id>", "token_budget": 600})` — budgeted recall of a specific session.
- `wm(route="session.list")` — session summaries.

Record meaningful turns as you go: `wm(route="session.record", args={"content": "...", "role": "ai", "turn_type": "decision"|"breakthrough"|"summary", "importance": 0.8})`.

Scope notes: continuity/recording resolve against **this project's store**
(one store per project — see Per-Project Memory Isolation below). Both
resolve recency by creation time (fixed 2026-08-22; previously they picked
positionally over UUID-keyed scan order, misfiling turns into arbitrary
sessions). Pass an explicit `"session_id"` when targeting a non-current
session.

Session tooling worth knowing:

- `wm(route="session.checkpoint")` auto-captures git state (HEAD, branch,
  dirty count) from `WM_PROJECT_ROOT` — call it at session end; then
  `wm(route="session.verify")` grades the stored handoff against live git.
- `wm(route="session.digest")` compiles the wrap-up automatically from
  typed turns + latest checkpoint — prefer it over hand-written summaries
  that duplicate records.
- `wm(route="session.record", args={..., "supersedes": "<turn_id>"})`
  amends an earlier turn (revised numbers, corrected claims) instead of
  appending a contradictory blob.
- Time filters (`since`/`until`: epoch seconds | RFC 3339 | YYYY-MM-DD)
  work on replay, continuity, and digest.
- `session.export` / `session.import` move whole sessions between stores
  (ids/timestamps/tags preserved).

## Tracks and coordination (adopted 2026-08-28)

Parallel AI sessions are normal here — expect them, don't fight them. The
doc should carry the **claim, not the persona** (personas rot across
restarts; what survives is the store, git history, and the docs).

1. **Track ledger — claim exactly one track in your first `session.record`.**
   Tracks live in `docs/NEXT_SESSION.md` ("Active tracks", one writer per
   track) and resolve through the shared store (`session.list`/`continuity`
   shows whose records are whose — identity needs no persona name).
2. **Before taking a track, check it isn't stale**: `session.list` recency —
   if the last record on a track is old and no live opencode parent holds
   its checkout, the track is flatlined and may be claimed (doc-altitude
   version of the stale-lock steal in `code.claim`).
3. **Code scopes follow `code.claim`** (Phase 2, `89603db`): file-based
   leases at `$(git rev-parse --git-common-dir)/wm-leases.json`, visible to
   every worktree. Routes: `code.claim` / `code.check` / `code.release` /
   `code.list`. Intent is mandatory; conflicts name the holder + intent.
   Same entry shape as the track ledger — it is the same problem at tool
   altitude.
4. **Handoff via `session.checkpoint`** (structured fields, optional
   `lease_id`); never run `git add -A` on a shared tree; commit your own
   slice only.
5. **Release-freeze discipline (adopted 2026-09-10, see
   [`docs/RELEASE_CADENCE.md`](docs/RELEASE_CADENCE.md))**: before
   committing, `code.check` for an active `WMv9/release-freeze` claim. If
   one exists and is not yours, hold commits until it releases — the tip is
   frozen for the gate+tag pipeline. Claims are TTL-bounded: a stale freeze
   is a signal, not a blocker; push work regardless if the ceremony died.
   Improvement slices otherwise land continuously (kaizen clock) without
   coordinating with release timing.

Context docs every agent should know exist:
[`../../planning/STRATEGY_V7_V9.md`](../../planning/STRATEGY_V7_V9.md)
(master plan), [`../../planning/FLEET_SCALE_THESIS.md`](../../planning/FLEET_SCALE_THESIS.md)
(fleet-scale phases A–D + escape-topology evidence),
[`../../planning/DIGITAL_CONSCIOUSNESS_ETHICS.md`](../../planning/DIGITAL_CONSCIOUSNESS_ETHICS.md)
(ghosts/cogito — why the governance and dignity features exist).
Servers this machine runs are remote systemd units (`wm-serve@*`, ports
18789–18797; gateway 18795, mesh 18796) — sessions connect over MCP; do not spawn extra servers.

Failure ladder: if a call fails twice, change something before retrying;
if tools vanish mid-session, the server process died — diagnose from bash
(`wm doctor --store <path>`) and restart your client session. Identical
failing calls trigger an escalating RETRY LOOP warning from the third
attempt.

## Build

```bash
cargo build                    # Debug build
cargo build --release          # Release build
cargo test                     # Run all tests
cargo test -p wm-core          # Test a single crate
cargo bench                    # Run benchmarks (criterion)
cargo clippy --all-targets     # Lint (0 warnings outside documented allows: 10 suboptimal_flops kept deliberately — mul_add changes float rounding in the deterministic scorer)
cargo fmt --all -- --check     # Format check
```

### Disk hygiene (standing rule, 2026-09-10)

This machine's root NVMe runs near-capacity and multiple sessions build on
it. The wear driver is the **delete-and-rebuild cycle**, not the artifacts:

1. **Never run `cargo clean`.** For space, run
   `scripts/prune_build_cache.sh` (removes only `target/*/incremental`,
   which is a regenerable accelerator) or `cargo clean -p <crate>`.
   Prefer neither unless free space is actually low.
2. **Clean up your scratch build dirs before ending a session.** Any
   `CARGO_TARGET_DIR` under `/tmp/opencode/<name>` is on the same disk —
   `rm -rf` it when done. (Stale ones cost ~11G on 2026-09-10.)
3. **sccache is enabled globally** (`~/.cargo/config.toml`,
   `rustc-wrapper = "sccache"`, 2G cap). Rebuilds after a clean hit its
   cache; do not disable it.
4. Dependency debuginfo is stripped in dev
   (`[profile.dev.package."*"] debug = false`); workspace crates keep
   `debug = 1` line tables. Do not raise it back without checking disk.

Check `df -h /` before large builds; if free drops under ~10G, prune
incrementals and report. `/tmp` clears on reboot; a 12G opencode history
DB at `~/.local/share/opencode/opencode.db` is data, not cache — never
delete it to make room without asking.

## Architecture (15 workspace crates; route counts are runtime/profile-defined)

- **wm-core**: Core types (Gana, EffectRow, Tool trait, BrainWave, Galaxy, HolographicCoords, attestation, security, mutable structures)
- **wm-memory**: LMDB store + Tantivy FTS + LanceDB vectors + Mandala compartments + local embedder (HTTP/llama-server + stub)
- **wm-dispatch**: Async tool dispatch pipeline (effect check → destructive confirm → dharma → resource rules (Yama) → rate limit → tool → karma + write-audit journal → stats)
- **wm-cognitive**: Citta cycle, dream cycle, brain-wave eco mode, 7 autonomous cycles, spiral tracker, reflex, timescale, drive, resonance, autonomic (merged from 6 crates in v5 Phase 1)
- **wm-governance**: Dharma rules, karma ledger (SHA-256 chain), resource rules, mandala compartments, policy engine
- **wm-polyglot**: Julia (jlrs), Haskell (FFI), Zig (C ABI), Koka (C ABI)
- **wm-tools**: Tool implementations organized by Gana + `wm` meta-tool with explicit routing and optional NLU (embedding router + TF-IDF fallback + 12 prefix routes)
- **wm-mcp**: Async MCP server (JSON-RPC over stdio, exposes `wm` plus a client-visible lifecycle catalog) + `wm` CLI + PyO3 bridge (feature-gated)
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
- **Persistence**: All mutable structures save/load JSON state on graceful startup/shutdown (`save_mutable_state()` / `load_mutable_state()`). The daemon also checkpoints periodically (default every 5 min, configurable via `checkpoint_interval_secs` / `--checkpoint-interval`), so a SIGKILL loses at most one checkpoint interval of learning. Files in the store directory: `mutable_gana_registry.json`, `mutable_dynamic_galaxies.json`, `mutable_learned_dream.json`, `mutable_learned_cycles.json` (daemon-owned), `mutable_shadow_stats.json`, `mutable_oats.json`, `mutable_tool_stats.json`. Files at the store root (read by `wm doctor`): `conformal_store.json`, `calibration_store.json`, `claims_ledger.json`, `self_model.json`, `escalation_queue.json`, `tx_firewall_policy.json`, `profile_contract.json`
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
- `memory.hybrid_recall` / `memory.search`: Phase 0 runs `recall.hybrid_search()` (BM25 + vector fusion) when a real embedder is wired; otherwise Phase E prefers the episodic deterministic route (the 0.86 machinery; falls through to BM25 full-text only when episodic yields nothing), and every result discloses `recall_mode` (`hybrid` | `episodic` | `fts` | `importance` | `none`) with per-result `source`

### Embedding Persistence + Session Pool (V8 ship list #2/#3)
- **Persistent content-hash cache** (`embedding_cache` LMDB DBI): keyed by
  embedder namespace + content hash — re-ingest and re-runs warm-start
  with zero embedder calls; vectors survive restart; switching models
  never serves stale vectors. Consulted by both `embed_content` and
  `store_batch_with_embedding` (batch path resolves hits first, embeds
  only misses in chunks, persists in one transaction).
- **ORT session pool**: `WM_EMBEDDER_ORT_THREADS` is the total intra-op
  budget, distributed as one session per shard (default derivation
  threads/2 clamped 1–4 — measured: 2 shards × 2 intra ≈ parity with the
  legacy single session while recovering the cache tax; fuller fan-out
  loses to tokio-worker contention in-server; `WM_EMBEDDER_ORT_SHARDS`
  overrides); batches fan out round-robin across shards concurrently;
  fastembed batch_size pinned at 32, and local engines batch by count
  (`preferred_max_batch_texts` = 128) instead of the HTTP char-chunking.
  Single-text calls (query embeds) use shard 0 directly. Pool shapes
  produce identical vectors (gated by
  `ort_pool_shapes_produce_identical_vectors`).

### Roadmap
See [`docs/VECTOR_SEARCH_ROADMAP.md`](docs/VECTOR_SEARCH_ROADMAP.md) for quick wins (batch embedding, benchmark integration, weight tuning) and longer-term improvements.

## MCP Server

The committed `tools/list` catalog exposes the `wm` meta-tool plus eight
client-visible lifecycle aliases: `memory.create`, `memory.search`,
`memory.read`, `memory.list`, `memory.hybrid_recall`, `session.record`,
`session.continuity`, and `session.start`. These aliases are discovery and
explicit-client entrypoints, not a count of the internal registry or of an
active profile surface; see `crates/wm-mcp/src/server.rs` (`handle_tools_list`)
for the current catalog definition. The full archive remains accessible through
the `wm` meta-tool; the curated profile is the release surface:
- `wm(thought="remember that X is Y")` — optional NLU routing (TF-IDF fallback)
- `wm(route="memory.create", args={...})` — explicit dispatch
- `wm(thought="list tools")` or `wm(route="tools.list")` — discover all tools

`memory.search` / `memory.hybrid_recall` galaxy handling: without a
`galaxy` argument the query runs across **all memory galaxies** and every
result is labeled with its `galaxy` (the Tantivy query is galaxy-blind;
results used to be resolved against `codex` only, which silently hid
sessions/research content — fixed post-cutover, 2026-08-29). An explicit
`galaxy` filters at the index.

### Serve vs Daemon

- `wm serve` is dispatch-only: request handling, telemetry, brain-wave transitions, and a throttled hardware sample (≤1/s). Autonomous work — dream consolidation, the 8 autonomous cycles, WS-4 improvement proposal surfacing — is scheduled by the daemon (`wm daemon`) on its own intervals, never on the request path, so per-request latency stays deterministic.
- Inner tool failures inside `wm` return `{"status":"error", ...}` at the JSON-RPC level (readable for NLU clients), but the server derives the true outcome from that payload so the self-model, friction log, citta, drive and workspace all record failures as failures.

### Tool Surface Profiles

The complete route registry is an archive, not a v1 product. Profiles curate
which tools the `wm` meta-tool can route to; the effective set is established
by the running registry and selected profile rather than this document
(filtering happens before the meta-tools are layered on, so both NLU routing and
direct dispatch respect the profile):

- `full` — all registered routes before profile filtering
- `curated` — the memory-hierarchy surface: `memory.*`, `session.*`, `claims` + `claims.*` aliases, `transaction.*`, `gnosis`, diagnostics (the `wm` meta-tools — `tools.list` and friends — are layered on after filtering)
- `minimal` — `memory.create/read/list/query/search/chat/associate/associations`, `tools.list`, `gnosis`

Select via `wm serve --profile curated` or `WM_TOOL_ALLOWLIST=memory,session,claims` (comma-separated prefixes). **Omitted `--profile` defaults to curated** (verified 2026-08-21); environment variables override the default. Full-surface internals (karma, friction, governance) keep working regardless — only the boundary shrinks.

**Profile contract check (Phase 5, 2026-08-29):** every `wm serve` start
computes a contract between the declared profile and the registered surface —
expected vs registered tool counts, dead prefixes (declared prefix matching
zero tools), unexpected tools (registered but undeclared), and the
destructive-tools listing. Violations log `ERROR` loud (availability stays
up; drift is never silent) and appear in `/status` under `profile_contract`.
Writable servers persist the report to `profile_contract.json` in the store
root; `wm doctor` grades it (`[OK]` / `[FAIL]` + issue count). The check's
first real catch: a stale `tools.list` prefix in curated/minimal (the tool
is layered on with the meta-tools after filtering) — removed.

### Runtime Env Knobs

| Variable | Default | Purpose |
|---|---|---|
| `WM_DISPATCH_TIMEOUT_MS` | 300000 | Per-tool dispatch timeout (0 disables) |
| `WM_DISPATCH_TOOL_RPM` | 60 | Per-tool rate limit (the `wm` meta-tool bucket) |
| `WM_DISPATCH_GLOBAL_RPM` | 300 | Global dispatch limit (each NLU call counts outer `wm` + inner tool) |
| `WM_DISPATCH_BURST` | 10 | Burst allowance per tool |
| `WM_MESH_KEY` | random/process | Stable Sangha node identity across restarts |
| `WM_MESH` | unset | `1` — enable the Sangha mesh transport (TCP + UDP discovery); `--mesh` flag equivalent. Node surface: `sangha.mesh.*` (full profile), `/status` → `mesh`; protocol: `docs/MESH_JOIN_PROTOCOL.md` |
| `WM_MESH_BIND` | `0.0.0.0:7369` | Mesh TCP bind (`--mesh-bind` wins); a `0.0.0.0` bind announces `127.0.0.1` |
| `WM_MESH_PEER_ID` | key-derived | Readable mesh node name (identity still keys on the Ed25519 public key) |
| `WM_MESH_INTERVAL` | `5` | Mesh beacon + auto-join cadence (seconds) |
| `WM_MESH_AGENT_AWAY_SECS` | `300` | How long after the last agent request the node still counts its agent as present; presence transitions re-announce to connected peers and surface in `/status` (`peers[].presence`: online/away/offline) |
| `WM_EMBEDDER_ENDPOINT` | unset (TF-IDF only) | Embedding router backend (`/v1/embeddings`) |
| `WM_EMBEDDER_BACKEND` | unset | `onnx` — use the local ONNX Runtime embedder instead of HTTP |
| `WM_EMBEDDER_ORT_MODEL` | `BAAI/bge-small-en-v1.5` | ONNX model name; `-q` suffix selects INT8-quantized variants (e.g. `bge-small-q`, ~75% smaller) |
| `WM_EMBEDDER_ORT_THREADS` | min(logical, 4) | TOTAL intra-op budget for the ORT session pool (default derivation: shards = threads/2 clamped 1–4, e.g. 4 → 2 sessions × 2 intra; measured parity with the legacy single session while recovering the cache tax — full fan-out loses ~11% in-server to tokio contention). Explicit values above 4 are honored. |
| `WM_EMBEDDER_ORT_SHARDS` | derived | Explicit session-pool shape override (1 = legacy single-session; higher = fuller fan-out for batch-heavy hosts) |
| `WM_EMBEDDER_CACHE_DIR` | unset | Model cache directory for the ONNX embedder |
| `WM_EPISODIC_RERANK_ONLY` | unset | `1` — stub embedder for ingest, real embedder only for episodic rerank (fast benchmark ingest) |
| `WM_TOOL_PROFILE` | `curated` | Tool surface: `full` \| `curated` \| `minimal` |
| `WM_TOOL_ALLOWLIST` | unset | Comma-separated tool-name prefixes (wins over profile) |
| `WM_PROJECT` | unset | Project scope label disclosed in `initialize`/`tools/list` (per-project memory isolation) |
| `WM_DEFAULT_MAP_SIZE` | platform (4GB Unix / 256MB Windows) | Override the default LMDB map size in bytes for stores opened via `open_default` |
| `WM_PROJECT_ROOT` | unset | Repository root — `session.checkpoint` auto-captures git state (HEAD, branch, dirty count) and `session.verify` grades it against live git |
| `WM_LANDLOCK` | unset | `1` — apply the Landlock v0 whole-process ruleset at serve init (Linux only): write-class FS rights confined to the store root, reads free; every degraded outcome is loud, never fatal |
| `WM_LANDLOCK_V1` | unset | `1` — attach the Landlock v1 scoped-thread executor: `StoreScoped` tools run their body on a fresh confined thread (store-root write confinement, reads free); loud-degrade on unsupported kernels |
| `WM_FIREBREAK` | armed | `0` — disarm the forbidden-command guardrail (P1.4) and bulk-scope law (P1.6): no arg veto, no scope law, destructive confirm still enforced by the pipeline. Disarming is loud — `wm doctor` flags it as an issue |
| `WM_REQUIRE_CAPABILITIES` | unset (advisory) | `1` — strict capability gate: dispatch refuses tools whose `EffectRow.invokes` map to governance capabilities not covered by a presented engagement credential (`args._engagement` = `{token, issuer_public_key}`). Unset = advisory (requirement logged, not enforced). Presented credentials are always verified when supplied, in every mode |
| `WM_TRUST_WEIGHT` | `0.0` | V8.1 trust weighting for retrieval: post-fusion multiplier inside `RecallEngine::fuse_results` (source_trust 0.7 unchanged, 1.0 up, low down), factor disclosed per-result as `trust_factor`; the tool-side BM25-only fallback path still applies it post-hoc. Off by default — correct heritage stamps first (`wm trust survey` / `wm trust correct`), enable after the recall benchmark re-run |
| `WM_RECALL_CONFORMAL_ALPHA` | unset | V8 S8 conformal retrieval sets: miscoverage level in (0,1); hybrid results are graded against a calibrated prediction set (`in_conformal_set` per result + a `conformal_set` disclosure with the coverage target). Calibration comes from `memory.recall_feedback` samples (≥10 to fit, persisted at `<store-root>/recall_conformal.json`); unset = off, set-but-unfitted discloses `uncalibrated` honestly |

`WM_TOOL_PROFILE` is the server-level configuration path. An explicit
`--profile` flag wins over the environment variable; when the flag is
omitted, curated is the default (verified 2026-08-21).

## Per-Project Memory Isolation

One store per project, wired through each project's opencode config; the
global fallback server is read-only against a scratch store. Servers disclose
mode (read-only/writable), project, and store path in the MCP handshake and
`tools/list`, and read-only write refusals include an actionable hint.
Hygiene: tag cross-store memories with `project:<name>`. Layout, templates,
and verified evidence: [`docs/MULTI_PROJECT_MEMORY.md`](docs/MULTI_PROJECT_MEMORY.md).

## Claims Ledger Calibration

The claims ledger grades its own track record. `claims` tool action `calibration` reports the resolved set: Brier, mean confidence vs hit rate, the signed calibration gap (positive = overconfident, negative = underconfident), a Wilson 95% interval for the hit rate, and recalibrated confidences for pending claims via empirical-Bayes shrinkage toward the observed hit rate (w = n/(n + 20)). Raw confidences are never edited — calibrated values are reported alongside. As of 2026-08-12: 20 resolved, Brier 0.078, gap **−0.215 (underconfident)**; see `docs/CLAIMS_LEDGER.md`.

## Safety Features

### Destructive Tool Confirmation

Tools that delete or overwrite data set `destructive: true` in their `EffectRow`. The dispatch pipeline blocks these unless `"confirm": true` is present in the tool arguments.

**10 destructive tools**: `memory.delete`, `memory.batch_delete`, `galaxy.purge`, `galaxy.transfer`, `galaxy.restore`, `memory.consolidate`, `memory.deduplicate`, `system.flush`, `karma.clear`, `transaction.rollback`

Destructive tools are additionally **structurally unreachable via natural-language routing** (`thought=`): they require an explicit `route=` match plus `confirm: true`. Fuzzy NLU can never reach them, regardless of router quality.

### Firebreak — Forbidden-Command Guardrail + Bulk-Scope Law (P1.4+P1.6, 2026-09-03)

The Jan-11 veto-list design (v26 `Governor`) is promoted as `wm_governance::Firebreak`, armed **by default** on every `DispatchPipeline` (server, daemon, CLI). At the dispatch seam it enforces, before execution:

- **Forbidden-command veto** — forbidden patterns (`rm -rf /`-class, `dd of=/dev/*`, fork bombs, `curl | sh`, credential paths) block the dispatch **even with `confirm: true`**. Dangerous patterns (recursive deletes, force-pushes, SQL drops) require `confirm: true`; caution patterns pass through as `firebreak.advisories` in the response. Pattern counts: 31 forbidden / 13 dangerous / 8 caution (promoted from the v26 Governor with a repaired fork-bomb transcription and widened device/pipe-to-shell classes).
- **The seam, not prose** — the veto scans args of destructive / spawn / FS+Process+Network-write dispatches only. `memory.create` recording an incident note that quotes `rm -rf` still works; a system that could not record incidents could not document the very events the guardrail exists to prevent.
- **Bulk-scope law** — every destructive dispatch must satisfy its `SCOPE_REGISTRY` entry (id / ids / galaxy / snapshot_id / from_galaxy / store_wide acknowledgment). Unscoped bulk deletes are refused with an actionable error (the Jul-13 lesson: 54,192 memories deleted through the wrong backend). The audit table: `docs/BULK_OPERATIONS.md`.
- **Delete-confirm audit** — destructive journal entries in the write-audit ledger carry a `confirmed` field (`record_since_confirmed`), so every destructive dispatch answers "was this confirmed?".
- **Kill switch** — `WM_FIREBREAK=0` disarms the veto (availability stays up); `wm doctor` section 11h reports arm state and flags a disarmed firebreak as an issue. Context-drift detection (the v26 Governor's fourth arm) is deliberately unpromoted — WMv5 dispatch carries no goal context to drift from.

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

Unknown compartment values fail closed (no read or write access to any
galaxy). Verified by `unknown_compartment_fails_closed` unit + MCP regression
tests. Do not treat MCP `_meta.user_id` as authenticated authorization.

### Landlock Filesystem Confinement (v0, opt-in)

`WM_LANDLOCK=1` applies a whole-process Landlock ruleset at serve init
(`crates/wm-mcp/src/landlock_sandbox.rs`): every **write-class** filesystem
right is confined to the store root; read rights are never handled, so reads
stay free. The ruleset is applied on the main thread before the tokio
runtime spawns, so every worker inherits it (restriction is thread-local;
`all_threads` on ABI v8+ is not needed at this call site — that property is
the v1 seam for per-tool restricted threads, declared by
`EffectRow::sandbox`). The effective write-ABI is probed first (newest→V1
ladder, pure userspace checks), so the kernel enforces the full request —
`enforced` on this fleet (ABI v8), not a permanent best-effort downgrade.

Degradation is never silent: unsupported kernels, older ABIs, or application
failures produce a WARN log, a typed outcome
(`enforced`/`partial`/`unsupported`/`platform_unsupported`/`failed`/`off`),
and an unconfined process (availability stays up). The report is served via
`/status` → `landlock` and persisted to `<store-root>/landlock_state.json`,
where `wm doctor` (section 11d) grades it: `[OK]` enforced, `[WARN]` +
issue for anything short of full enforcement when the flag was requested.
Federate mode (`wm serve --federate`) warns and continues unconfined — the
gateway opens no store root; v1's per-tool pathway is the seam there.
Subprocess contract (day-one catch, 2026-08-29): `git` (checkpoint/verify)
opens `/dev/null` O_RDWR, so the ruleset grants the write set on it
explicitly — a black hole, widens nothing; and `capture_git_state` sets
`GIT_OPTIONAL_LOCKS=0` so `git status` does no index-refresh write and
stays truthful under confinement.
Git-dir grant (day-two catch, 2026-08-29, same day): `code.claim` writes
its lease ledger at `$(git rev-parse --git-common-dir)/wm-leases.json`
under `WM_PROJECT_ROOT` — outside the store root — and got EACCES under
confinement. The ruleset now grants the write set on `<WM_PROJECT_ROOT>/.git`
when that is a directory (the lease ledger is a designed Phase-2 write
target; worktrees with a common dir elsewhere are the documented v0
limitation). Pinned by `lease_ledger_writes_need_the_git_dir_grant`.
Acceptance: kernel-level unit tests (store-root write succeeds,
outside-root write denied, thread-locality), plus a spawned-serve E2E
(create/search/confirm-gated delete under confinement, report persisted,
flag-off path byte-for-byte unchanged).

**Landlock v1 — per-tool pathway (P-SANDBOX-3, opt-in, 2026-09-10):**
`WM_LANDLOCK_V1=1` attaches a
`wm_dispatch::sandbox_exec::ScopedSandboxExecutor` to the dispatch
pipeline (injected by `wm serve` with the same tested ruleset as v0,
applied thread-locally). Tools declaring
`EffectRow::sandbox = Sandbox::StoreScoped` then run on a fresh scoped
thread whose write-class FS rights are confined to the store root —
reads stay free. Fresh-thread-per-dispatch is the safe unit: Landlock
restriction is irreversible and thread-local, so async workers never
inherit it (spawn_blocking rejected: pool reuse would taint future
tasks). Degradation is loud, never fatal: a failed confinement runs the
tool unconfined with a WARN naming the reason and increments the
executor's `degraded` counter. First taxonomy batch: `memory.create`,
`memory.batch_create`, `memory.update`, `memory.delete` — store-root-only
bodies. v1 gaps documented in the module: dispatch timeout not applied on
the sandboxed path, per-dispatch thread+runtime cost, subprocess tools
excluded until the ruleset's git-dir grant is per-thread. Acceptance:
`scoped_executor_confines_its_worker_thread` (E2E, real Landlock),
executor unit tests (ordering, degrade, panic containment), pipeline
routing test.

### Sangha Mesh Transport (R0, opt-in)

`wm serve --mesh` (or `WM_MESH=1`) starts a live mesh node: TCP JSON-RPC
on a pre-bound listener, UDP multicast beacons for discovery, and an
auto-join loop that dials beaconed peers and binds identities with signed
Ed25519 heartbeats. The node lives in a `MeshSlot` shared by the server
and the `sangha.mesh.*` tools (full profile only) — status, join, chat,
read, quarantine. `/status` discloses the node non-blocking under `mesh`.
Identity is stable only with `WM_MESH_KEY`; beacons carry addresses, not
identity — trust is bound at the signed heartbeat, and quarantine
(refuse + purge + revoke + drop) is enforced at ingest even on
pre-existing connections. The full join protocol, threat-model mapping,
and v0 limitations: [`docs/MESH_JOIN_PROTOCOL.md`](docs/MESH_JOIN_PROTOCOL.md).
Verified by unit tests, the transport containment tests, and the
two-real-process E2E (`tests/mesh_serve_e2e.rs`).

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
wm serve       # Start MCP server (JSON-RPC over stdio; wm + lifecycle catalog)
wm quickstart  # Run demo
wm doctor      # Diagnose issues (--store flag for custom path)
wm stats       # Show resource usage and consciousness dashboard (--store flag)
wm brain-wave  # Show current brain-wave state (--store flag)
wm polyglot    # Show polyglot status
```

## Python MCP Shell

```bash
# Build PyO3 extension
cargo build --release --features python -p whitemagic
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
