# WhiteMagic v5

A cognitive operating system for agentic AI — rebuilt from the ground up in Rust.

## Current Status

**v5.7.7 — Feature phases complete; release stabilization in progress. 15 crates, 229 registered tool implementations, 3,447 tests, ~131,000 LOC, 0 clippy warnings, and 0 dependency vulnerabilities. The release target is the curated local memory/session MCP workflow; explicit routing is the reliable contract, while semantic NLU and the broader cognitive surface remain optional or experimental.**

The product promise is local-first memory and session continuity for coding
agents: remember project context, find it after restart, and carry work across
sessions without sending the memory store to a hosted service.

### v5 Subsystems

- **Embedding NLU Router** (Phase 2): Cosine similarity against pre-computed tool embeddings with OATS offline refinement. Shadow mode with TF-IDF fallback. `nlu.shadow_report` tool for disagreement analytics and promotion readiness. OATS persistence across restarts.
- **Learned Inference Router** (Phase 3, experimental): k-NN (k=5) + conformal calibration for complexity-aware inference tier selection. Edge rule generation is available for research evaluation.
- **Imagination Engine** (Phase 4, optional): World model predictions, scenario planning (imagine → simulate → evaluate → decide), dream cycle counterfactual replay, Research autonomous cycle.
- **Self-Play Training Loop** (Phase 5, experimental): Propose → solve → verify → collect training-data cycle. 3 MCP tools, daemon `--selfplay-interval`; live LoRA training and hot-swap are not part of the release contract.
- **Mutable Structures** (Phase 6): GanaRegistry (taxonomy drift), DynamicGalaxyRegistry (auto-created from emergence clusters), LearnedDreamCycle (adaptive phase selection), LearnedCycleStrategy (adaptive cycle ordering). All persist to disk across restarts.
- **Persistence** (Phase 7): All mutable structures save/load JSON state on daemon startup/shutdown. Learned state accumulates across sessions.
- **Karma Ledger Optimization** (v5.2.1): Write-behind batching (flush_threshold=16) delivers **10.9x throughput improvement** over synchronous LMDB writes (97.7 µs vs 1.07 ms per record). Explicit flush on daemon graceful shutdown ensures no pending entries are lost. E2E integration test verifies batching, chain integrity, and persistence across ledger instances.

| Category | Tools |
|---|---|
| Memory (CRUD + advanced) | create, read, list, delete, query, search, vector.search, associate, associations, consolidate, decay, batch_read, update, tag, stats, hybrid_recall, count, tags, associate_mine, nearby |
| Session | start, checkpoint, recall, end, list |
| Consciousness | citta.status, citta.reflect, citta.coherence, dream.status, dream.trigger, smarana.status, smarana.trace, apotheosis.check, citta.history, dream.analyze, consciousness.depth |
| Governance | karma.report, karma.history, karma.clear, dharma.status, dharma.rules, dharma.audit, dharma.profiles, harmony.vector, harmony.history, gnosis.status, gnosis.history, gnosis.explain |
| Tools management | tools.list, tools.effectiveness_report, tools.retire |
| Patterns | pattern.search, salience.spotlight, serendipity.surface |
| Constellation | detect, list |
| Autonomous Cycles | consolidation.connect, consolidation.compress, emergence.scan, retention.prune |
| Spiral | spiral.report |
| Galaxy | stats, export, import, transfer, merge, snapshot, restore |
| Network | association.mine, pattern.detect, emergence.report, network.stats, network.centrality, network.clusters |
| Agents & Tasks | agent.register, agent.list, agent.heartbeat, task.distribute, task.status |
| System | health, config, flush |
| Knowledge Graph | kg.extract, kg.query, kg.top |
| Graph | graph.walk, graph.community, graph.propagate |
| Archaeology | archaeology.search, learning.pattern, learning.suggest |
| Reasoning | reasoning.bicameral, think, explain |
| Pipeline | pipeline.create, pipeline.list, pipeline.status, skill.invoke, skill.list |
| Anomaly | anomaly.detect, state.snapshot, state.revert |
| Correlation | correlation.analyze, god.nodes |
| Boundary | anti_loop.check, boundary.enforce |
| Meta | wm (explicit routing plus optional NLU, 12 prefix routes), gnosis, tools.list |
| v4: Reflex | reflex.dispatch, reflex.status |
| v4: Workspace | workspace.spotlight, workspace.events, workspace.publish, workspace.stats |
| v4: Timescale | timescale.status, timescale.hooks |
| v4: Self-Model | selfmodel.forecast, selfmodel.alerts, selfmodel.snapshot |
| v4: Bicameral | bicameral.reason, bicameral.status |
| v4: Drive | drive.snapshot, drive.event |
| v4: Resonance | bus.stats, bus.emit, bus.recent |
| v4: Sangha | sangha.peers, sangha.discover, sangha.signal, sangha.chat, sangha.locks, sangha.quarantine |
| v4: Simulation | sim.mc, sim.forecast, sim.counterfactual |
| v4: Sensorimotor | sensorimotor.scan, sensor.list, sensor.read, sensor.poll, sensor.history, actuator.list, actuator.command, actuator.estop, reflex.list, reflex.add, reflex.evaluate |
| v4: Homeostasis | homeostasis.check, homeostasis.adjust, homeostasis.history, homeostasis.alerts |
| RSI | friction.log, friction.review, friction.auto_log, improve.proposals, improve.active_proposals, friction.resolve, redteam.proposals, redteam.from_friction, redteam.coverage_report |
| Transaction | transaction.begin, transaction.commit, transaction.rollback |
| v5: Imagination | imagine.scenario, imagine.predict, imagine.reflect |
| v5: Self-Play | selfplay.run, selfplay.status, selfplay.export |
| v5: NLU Observability | nlu.shadow_report |

### CLI Commands

```bash
wm serve       # Start MCP server (async, tokio, brain-wave eco mode)
wm serve --profile curated   # Memory-hierarchy surface only (memory/session/claims/transactions)
wm daemon      # Persistent daemon — autonomous cycles, dream, self-play (--cycle-interval, --dream-interval, --research-interval, --selfplay-interval)
wm doctor      # Health check — LMDB, Tantivy, citta, dream, tools (--store flag)
wm quickstart  # 6-step guided setup
wm stats       # Consciousness dashboard (--store flag)
wm brain-wave  # Brain-wave state shorthand (--store flag)
wm polyglot    # Polyglot runtime status
wm migrate     # Migrate legacy v26 SQLite memories into the v5 store
```

### Tool Surface Profiles

`wm serve` exposes a curated subset of the 229-tool surface via profiles (see AGENTS.md):

- `--profile full` (default) — everything
- `--profile curated` — the memory-hierarchy product surface: memory, session, claims, transactions, diagnostics, and tools.list
- `--profile minimal` — core memory CRUD + search/chat
- `WM_TOOL_ALLOWLIST=memory,session` — arbitrary prefix allowlist via env

Use the explicit `--profile` flag with v5.7.7. CLI/environment profile
precedence is being hardened before release; see
[docs/RELEASE_READINESS.md](docs/RELEASE_READINESS.md).

### Migrating from v26

If you have a legacy v26 (Python) install with SQLite galaxy databases, migrate
them in one command (dry-run first to preview):

```bash
wm migrate --v2-dir ~/.whitemagic/users/local/galaxies --dry-run   # preview
wm migrate --v2-dir ~/.whitemagic/users/local/galaxies              # migrate
wm migrate --v2-db path/to/codex/whitemagic.db --galaxy codex       # single galaxy
```

Galaxy mapping is automatic: `main`/`archive`→Universal, `meta`→Substrate,
`knowledge`/`openai_archives`→Codex, bench/test/quarantine galaxies are skipped.
All migrated memories land in the store at `--store` (default `~/.local/share/whitemagic`).

### Python MCP Shell (optional)

```bash
cargo build --release --features python -p wm-mcp  # Build PyO3 extension
python python/whitemagic_v5_server.py --store ~/.local/share/whitemagic/lmdb
```

See `python/README.md` for MCP client configuration (Claude Desktop, Cursor, Windsurf).

See [docs/RELEASE_READINESS.md](docs/RELEASE_READINESS.md) for the release plan and acceptance gates, [docs/ARCHIVE_CAPABILITY_MAP.md](docs/ARCHIVE_CAPABILITY_MAP.md) for vetted capabilities from previous versions and the v6+ direction, [docs/GAP_ANALYSIS.md](docs/GAP_ANALYSIS.md) for the v26 comparison and porting roadmap, [docs/CONFORMAL_PREDICTION.md](docs/CONFORMAL_PREDICTION.md) for the conformal prediction feature, and [docs/PROGRESS.md](docs/PROGRESS.md) for phase status.

## What's Different

- **Rust-first**: Core runtime, memory, dispatch, and consciousness in Rust. Python is a thin MCP shell.
- **LMDB memory**: Zero-copy mmap'd reads (100x faster than SQLite). 10x less disk write amplification.
- **Tantivy search**: Lucene-class full-text search in pure Rust (2x faster than FTS5).
- **Brain-wave eco mode**: Five states (Gamma→Delta). Zero CPU when idle. No polling threads.
- **Hardware-aware governance (v4)**: `wm-substrate` reads real `/proc` + `/sys` metrics. Brain-wave transitions gated by hardware health (Tiferet). Resource budgets, novelty detection, purpose requirements, human review (Yama). Full transparency via Gnosis Portals.
- **5D holographic coordinates**: SHA-256 content encoding → spatial memory queries with `find_nearby()`.
- **CyberBrain architecture (v4→v5)**: Consolidated to 15 crates. wm-cognitive merges 6 former crates (citta, dream, autonomous cycles, reflex, timescale, drive). wm-bicameral adds imagination engine, self-play, learned inference router. wm-conformal adds distribution-free prediction with coverage guarantees.
- **Bicameral reasoning**: Dual-hemisphere (left: heuristic, right: LLM/stub) with 5-tier complexity-aware routing. Imagination engine for scenario planning. Self-play training-data collection; live LoRA training and hot-swap remain experimental.
- **NLU router**: Optional two-layer system — embedding router (cosine similarity, OATS refinement) and TF-IDF fallback. Explicit routing remains the reliable path until the labeled shadow set supports promotion.
- **Mutable structures**: Gana taxonomy drift tracking, dynamic galaxy creation from memory clustering, learned dream cycle phase selection, learned autonomous cycle strategy. All persist to disk.
- **Polyglot without subprocesses**: Julia embedded via jlrs, Haskell/Koka/Zig compiled to native libraries.
- **Fractal meta-tool**: 229 registered tools with atomic self-tracked effectiveness stats. MCP server exposes only `wm`; the curated profile is the intended product boundary and the full surface is an archive/research mode.
- **Mandala compartments**: 4 security tiers (Research/Sandbox/Production/Secure) with isolated LMDB+Tantivy+associations per compartment.
- **RSI pipeline**: 3-phase recursive self-improvement — friction logging, deduplication, karma-friction bridge, proactive improvement, resolution verification with regression detection, adversarial test synthesis from friction history, coverage reporting. 12 RSI tools, 8 autonomous cycle types.
- **Fuzz testing**: 8 cargo-fuzz targets + 22 proptest tests across 4 crates.
- **Self-grading claims ledger**: 32 dated falsifiable predictions with Brier scorecard, signed calibration gap, Wilson hit-rate interval, and empirical-Bayes recalibration of pending confidences (`claims` tool `calibration` action — the record is never edited, only re-read through its own track record).
- **Cross-platform CI**: Linux, macOS, Windows test jobs + benchmark-on-release-tag.

## Quick Start

```bash
cargo build --release
./target/release/wm serve --profile curated
```

## Architecture

See [docs/RELEASE_READINESS.md](docs/RELEASE_READINESS.md) for the release plan and [docs/STRATEGY.md](docs/STRATEGY.md) for the full architecture document.

## Build

```bash
cargo build                    # Debug build
cargo build --release          # Release build
cargo test                     # Run all 3,447 tests
cargo clippy --all-targets     # Lint (0 warnings)
cargo build --release --features python -p wm-mcp  # Build with PyO3 bindings
cargo build --features wm-memory/lancedb  # Build with LanceDB vector search
cargo bench -p wm-tools --bench rsi_bench           # RSI pipeline benchmarks
cargo +nightly fuzz run nlu_classify  # Run fuzz target
PROPTEST_CASES=4096 cargo test --all-targets proptest  # Run proptest with high iterations
```

## License

MIT
