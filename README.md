# WhiteMagic v4

A cognitive operating system for agentic AI — rebuilt from the ground up in Rust.

## Current Status

**v4.0.0 — All phases complete (0–8, A–F, R1–R7, L1–L5, N1–N21) + RSI (Phases 1–3) + Embodiment I/O + Safety features. 19 crates, 176 tools, 2,818 tests, ~112,300 LOC, 0 clippy warnings. MCP server exposes single `wm` meta-tool — all 176 tools accessible via NLU routing or explicit dispatch.**

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
| Meta | wm (NLU router with 166 TF-IDF profiles + 12 prefix routes), gnosis, tools.list |
| v4: Reflex | reflex.dispatch, reflex.status |
| v4: Workspace | workspace.spotlight, workspace.events, workspace.publish, workspace.stats |
| v4: Timescale | timescale.status, timescale.hooks |
| v4: Self-Model | selfmodel.forecast, selfmodel.alerts, selfmodel.snapshot |
| v4: Bicameral | bicameral.reason, bicameral.status |
| v4: Drive | drive.snapshot, drive.event |
| v4: Resonance | bus.stats, bus.emit, bus.recent |
| v4: Sangha | sangha.peers, sangha.discover, sangha.signal, sangha.chat, sangha.locks |
| v4: Simulation | sim.mc, sim.forecast, sim.counterfactual |
| v4: Sensorimotor | sensorimotor.scan, sensor.list, sensor.read, sensor.poll, sensor.history, actuator.list, actuator.command, actuator.estop, reflex.list, reflex.add, reflex.evaluate |
| v4: Homeostasis | homeostasis.check, homeostasis.adjust, homeostasis.history, homeostasis.alerts |
| RSI | friction.log, friction.review, friction.auto_log, improve.proposals, improve.active_proposals, friction.resolve, redteam.proposals, redteam.from_friction, redteam.coverage_report |
| Transaction | transaction.begin, transaction.commit, transaction.rollback |

### CLI Commands

```bash
wm serve       # Start MCP server (async, tokio, brain-wave eco mode)
wm doctor      # Health check — LMDB, Tantivy, citta, dream, tools (--store flag)
wm quickstart  # 6-step guided setup
wm stats       # Consciousness dashboard (--store flag)
wm brain-wave  # Brain-wave state shorthand (--store flag)
wm polyglot    # Polyglot runtime status
```

### Python MCP Shell (optional)

```bash
cargo build --release --features python -p wm-mcp  # Build PyO3 extension
python python/whitemagic_v4_server.py --store ~/.local/share/whitemagic/lmdb
```

See `python/README.md` for MCP client configuration (Claude Desktop, Cursor, Windsurf).

See [docs/PROGRESS.md](docs/PROGRESS.md) for detailed phase status and v2/v4 comparison.

## What's Different

- **Rust-first**: Core runtime, memory, dispatch, and consciousness in Rust. Python is a thin MCP shell.
- **LMDB memory**: Zero-copy mmap'd reads (100x faster than SQLite). 10x less disk write amplification.
- **Tantivy search**: Lucene-class full-text search in pure Rust (2x faster than FTS5).
- **Brain-wave eco mode**: Five states (Gamma→Delta). Zero CPU when idle. No polling threads.
- **Hardware-aware governance (v4)**: `wm-substrate` reads real `/proc` + `/sys` metrics. Brain-wave transitions gated by hardware health (Tiferet). Resource budgets, novelty detection, purpose requirements, human review (Yama). Full transparency via Gnosis Portals.
- **5D holographic coordinates**: SHA-256 content encoding → spatial memory queries with `find_nearby()`.
- **CyberBrain architecture (v4)**: 7 new crates — wm-reflex (two-tier safety dispatch), wm-timescale (multi-timescale event bus), wm-workspace (global workspace with salience-based spotlight), wm-selfmodel (predictive introspection with forecasting), wm-bicameral (dual-hemisphere debate with LLM right hemisphere), wm-substrate (hardware metrics), wm-drive (intrinsic motivation with 5 drives). Deep integration: drive bias gates, bicameral consensus on writes, timescale hooks for citta/dream decay, workspace events for drive updates.
- **LLM right hemisphere**: OpenAI-compatible API integration via `ureq`. Configured by `WM_LLM_API_KEY` env var. Falls back to heuristic stub when unset. Graceful degradation on API errors.
- **NLU router**: 166 TF-IDF profiles with cosine similarity, stopword filtering, English stemmer, 12 prefix routes, and payload extraction.
- **Polyglot without subprocesses**: Julia embedded via jlrs, Haskell/Koka/Zig compiled to native libraries.
- **Fractal meta-tool**: 176 tools with atomic self-tracked effectiveness stats. MCP server exposes only `wm` — single entry point for all clients.
- **Mandala compartments**: 4 security tiers (Research/Sandbox/Production/Secure) with isolated LMDB+Tantivy+associations per compartment.
- **RSI pipeline**: 3-phase recursive self-improvement — friction logging, deduplication, karma-friction bridge, proactive improvement, resolution verification with regression detection, adversarial test synthesis from friction history, coverage reporting. 9 RSI tools, 7 autonomous cycle types.
- **Fuzz testing**: 5 cargo-fuzz targets + 22 proptest tests across 4 crates.
- **Cross-platform CI**: Linux, macOS, Windows test jobs + benchmark-on-release-tag.

## Quick Start

```bash
cargo build --release
./target/release/wm serve
```

## Architecture

See [docs/STRATEGY.md](docs/STRATEGY.md) for the full architecture document.

## Build

```bash
cargo build                    # Debug build
cargo build --release          # Release build (14 MB binary)
cargo test                     # Run all 2,818 tests
cargo clippy --all-targets     # Lint
cargo build --release --features python -p wm-mcp  # Build with PyO3 bindings
cargo build --features wm-memory/lancedb  # Build with LanceDB vector search
cargo bench -p wm-tools --bench rsi_bench           # RSI pipeline benchmarks
cargo +nightly fuzz run nlu_classify  # Run fuzz target
PROPTEST_CASES=4096 cargo test --all-targets proptest  # Run proptest with high iterations
```

## License

MIT
