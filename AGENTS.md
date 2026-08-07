# AGENTS.md — WhiteMagic v4 Developer Guide

## Build

```bash
cargo build                    # Debug build
cargo build --release          # Release build
cargo test                     # Run all tests
cargo test -p wm-core          # Test a single crate
cargo bench                    # Run benchmarks (criterion)
cargo clippy --all-targets     # Lint
cargo fmt --all -- --check     # Format check
```

## Architecture (19 crates, 176 tools, ~112,300 LOC, 2,818 tests)

- **wm-core**: Core types (Gana, EffectRow, Tool trait, BrainWave, Galaxy, HolographicCoords, attestation, security)
- **wm-memory**: LMDB store + Tantivy FTS + LanceDB vectors + Mandala compartments + local embedder (HTTP/llama-server + stub)
- **wm-dispatch**: Tool dispatch pipeline (effect check → destructive confirm → dharma → rate limit → tool → stats)
- **wm-consciousness**: Citta cycle, dream cycle, brain-wave eco mode, 7 autonomous cycles, spiral tracker
- **wm-governance**: Dharma rules, karma ledger (SHA-256 chain), resource rules, mandala compartments, policy engine
- **wm-polyglot**: Julia (jlrs), Haskell (FFI), Zig (C ABI), Koka (C ABI)
- **wm-tools**: 176 tool implementations organized by Gana + `wm` meta-tool with NLU routing (166 TF-IDF profiles + 12 prefix routes)
- **wm-mcp**: MCP server (JSON-RPC over stdio, exposes only `wm` meta-tool) + `wm` CLI + PyO3 bridge (feature-gated)
- **wm-substrate**: Hardware metrics, Harmony Vector (Lakshmi), /proc + /sys reading, sensorimotor bus
- **wm-bicameral**: Dual-hemisphere reasoning (left: LlamaLeftHemisphere/heuristic, right: BitNet/LLM/stub) + inference router (5-tier complexity-aware routing)
- **wm-drive**: Intrinsic motivation (5 drives, 9 event kinds, drive bias)
- **wm-autonomic**: BitMamba daemon subprocess, salience processing, telemetry buffering
- **wm-reflex**: Reflex dispatch table, builtins, permissive/strict modes
- **wm-timescale**: 3-tier timescale bus (Reactive/Planning/Strategic), hook registration
- **wm-workspace**: Global workspace theory of consciousness, spotlight, publish, events
- **wm-selfmodel**: Self-model for predictive introspection, forecasting, alerts
- **wm-resonance**: Gan Ying Bus (inter-system resonance), event persistence
- **wm-sangha**: Sangha mesh (peer discovery, signal broadcast, chat, resource locks)
- **wm-simulation**: Monte Carlo, forecasting, counterfactual estimation

## RSI Pipeline (Phases 1–3 Complete)

- **Phase 1**: Friction logging (`friction.log`, `friction.review`, `friction.auto_log`)
- **Phase 2 Outward Spiral (WS-1–WS-5)**: Rich telemetry envelope, deduplication, karma-friction bridge, proactive improvement, resolution verification with regression detection
- **Phase 3 Adversarial**: E2E outward spiral test, criterion benchmarks, `redteam.from_friction` (regression test synthesis), `redteam.coverage_report` (per-system coverage gaps)
- **12 RSI tools**: friction.log, friction.review, friction.auto_log, improve.proposals, improve.active_proposals, redteam.proposals, redteam.from_friction, redteam.coverage_report, friction.resolve, transaction.begin, transaction.commit, transaction.rollback
- **7 autonomous cycle types**: Connect, Compress, Emergence, Prune, Improve, Redteam, Sensorimotor

## MCP Server

The MCP server exposes a **single tool** (`wm`) via `tools/list`. All 176 tools are accessible through the `wm` meta-tool:
- `wm(thought="remember that X is Y")` — NLU routing via TF-IDF cosine similarity
- `wm(route="memory.create", args={...})` — explicit dispatch
- `wm(thought="list tools")` or `wm(route="tools.list")` — discover all tools

## Safety Features

### Destructive Tool Confirmation

Tools that delete or overwrite data set `destructive: true` in their `EffectRow`. The dispatch pipeline blocks these unless `"confirm": true` is present in the tool arguments.

**8 destructive tools**: `memory.delete`, `galaxy.purge`, `galaxy.transfer`, `galaxy.restore`, `memory.consolidate`, `memory.deduplicate`, `system.flush`, `karma.clear`

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
