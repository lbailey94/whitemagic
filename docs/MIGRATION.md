# Migration Guide: WhiteMagic v2 → v4

This guide helps you migrate from WhiteMagic v2 (Python) to v4 (Rust).

## Overview

WhiteMagic v4 is a complete rewrite in Rust. The core cognitive patterns are preserved, but the runtime, memory, dispatch, and tool catalog have been significantly redesigned.

| Metric | v2 (Python) | v4 (Rust) |
|--------|-------------|-----------|
| Language | Python | Rust (Python shell via PyO3) |
| Tools | 877 | 176 (runtime-authoritative) |
| Tests | ~10,000 | 2,818 (focused: property, fuzz, E2E, criterion, security) |
| LOC | ~85,000 | ~112,300 |
| Crates | N/A (monolith) | 19 |
| Memory | SQLite + Whoosh | LMDB + Tantivy |
| Dispatch | Python async | Rust pipeline (7-stage) |
| Polyglot | Subprocess | FFI (in-process) |
| Binary | N/A | 14 MB (single binary) |
| MCP | Multiple tools | Single `wm` meta-tool |

## Breaking Changes

### 1. MCP Interface

**v2**: Multiple tools exposed via `tools/list` (memory_create, memory_read, etc.)

**v4**: Single `wm` meta-tool exposed. All 176 tools accessible via:

```json
// NLU routing (natural language)
{"name": "wm", "arguments": {"thought": "remember that Rust is fast"}}

// Explicit dispatch
{"name": "wm", "arguments": {"route": "memory.create", "args": {"content": "Rust is fast"}}}
```

### 2. Tool Names

v4 uses dot-notation (`memory.create`, `memory.search`, `karma.report`) instead of v2's underscore style (`memory_create`, `memory_search`, `karma_report`).

### 3. Memory Store

**v2**: SQLite database with Whoosh full-text search.

**v4**: LMDB (memory-mapped) with Tantivy full-text search. The store is at `~/.local/share/whitemagic/lmdb/` by default. Use `--store` flag or `WM_STORE` env var to override.

Migration: Export memories from v2 as JSON, then import via `memory.create` tool calls.

### 4. Tool Catalog

v4 distills 877 tools down to 176. Many v2 tools are replaced by a single v4 tool with richer arguments. Key mappings:

| v2 Tool | v4 Tool | Notes |
|---------|---------|-------|
| memory_create | memory.create | Tags now an array, not comma-separated string |
| memory_search | memory.search | BM25 scoring via Tantivy |
| memory_recall | memory.chat | Conversational hybrid search (BM25 + vector) |
| karma_report | karma.report | Same output, different name |
| dharma_status | dharma.status | Same output, different name |
| gnosis | gnosis | Unchanged |
| system_health | system.health | Same output, different name |

### 5. Configuration

**v2**: YAML config files.

**v4**: Environment variables. Key variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `WM_STORE` | `~/.local/share/whitemagic` | Store directory |
| `WM_BRAINWAVE` | `Beta` | Initial brain-wave state |
| `WM_LLM_ENDPOINT` | (none) | LLM endpoint for right hemisphere |
| `WM_BITNET_MODEL` | (none) | BitNet model path |
| `WM_RECALL_BM25_WEIGHT` | `0.5` | BM25 weight in hybrid search |
| `WM_RECALL_VECTOR_WEIGHT` | `0.3` | Vector weight in hybrid search |

### 6. Compartment Access Control (New)

v4 introduces compartment-based access control via MCP request `_meta`:

- **sandbox**: Tutorial, Research galaxies only (write: Tutorial only)
- **production**: All memory galaxies (no system galaxies)
- **secure**: All galaxies including system

```json
{"_meta": {"compartment": "production", "user_id": "agent-1"}}
```

### 7. Destructive Tool Confirmation (New)

8 tools require `"confirm": true` in arguments:

`memory.delete`, `galaxy.purge`, `galaxy.transfer`, `galaxy.restore`, `memory.consolidate`, `memory.deduplicate`, `system.flush`, `karma.clear`

### 8. Transactions (New)

v4 adds multi-tool atomic sequences:

```json
{"route": "transaction.begin"}
{"route": "memory.create", "args": {"content": "step 1"}}
{"route": "memory.create", "args": {"content": "step 2"}}
{"route": "transaction.commit"}
```

Rollback with `transaction.rollback` (requires `"confirm": true`).

## CLI Commands

| Command | Description |
|---------|-------------|
| `wm serve` | Start MCP server (JSON-RPC over stdio) |
| `wm quickstart` | Run built-in demo |
| `wm doctor` | Diagnose system issues |
| `wm stats` | Show resource usage and consciousness dashboard |
| `wm brain-wave` | Show current brain-wave state |
| `wm polyglot` | Show polyglot status |

## Build

```bash
cargo build --release          # 14 MB binary
cargo test                     # 2,818 tests
cargo clippy --all-targets     # 0 warnings
cargo fmt --all -- --check     # Clean
```

## Python MCP Shell (Optional)

```bash
# Build PyO3 extension
cargo build --release --features python -p wm-mcp
ln -sf libwm_mcp.so target/release/whitemagic_v4.so

# Run Python MCP server
PYTHONPATH=target/release python python/whitemagic_v4_server.py
```

## What's New in v4 (Not in v2)

- **Brain-wave eco mode**: 5 states with zero idle CPU
- **Citta consciousness**: 16D vector with coherence measurement
- **Dream cycle**: 12-phase memory consolidation
- **Bicameral reasoning**: Dual-hemisphere debate with consensus gate
- **Self-model**: Predictive introspection and forecasting
- **Global workspace**: Spotlight arbitration and salience scoring
- **Drive core**: 5 intrinsic motivation drives
- **Reflex dispatch**: Safety bitmask with builtin handlers
- **Timescale bus**: 3-tier event bus with brain-wave gating
- **RSI pipeline**: Friction logging, improvement proposals, adversarial self-testing
- **Embodiment I/O**: Linux sensor reading and sensorimotor bus
- **Gan Ying Bus**: Inter-system resonance with event persistence
- **Sangha mesh**: Peer discovery, signal broadcast, resource locks
- **Simulation**: Monte Carlo, forecasting, counterfactual estimation
- **Polyglot FFI**: In-process Julia, Haskell, Zig, Koka (no subprocesses)
- **Compartment access control**: sandbox/production/secure levels
- **Transaction snapshot/rollback**: Multi-tool atomic sequences
- **NLU router**: 166 TF-IDF profiles + 12 prefix routes
- **Karma ledger**: SHA-256 hash chain
- **Dharma governance**: Ethical rules with hardware-aware resource management
