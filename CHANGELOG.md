# Changelog

All notable changes to WhiteMagic v4 are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
