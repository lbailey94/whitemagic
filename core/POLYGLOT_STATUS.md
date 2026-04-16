# WhiteMagic Polyglot Status Matrix

> [!IMPORTANT]
> **This file is a SUMMARY REDIRECT.**
> The canonical, authoritative polyglot status document is
> **[polyglot/STATUS.md](../polyglot/STATUS.md)**.
> Always update that file — **never this one** — to avoid contradictions.
> If the tables below diverge from `polyglot/STATUS.md`, `polyglot/STATUS.md` wins.

---

## Quick Summary (as of v21.0.0)

| Language | Status | Notes |
|----------|--------|-------|
| **Rust** | ✅ Production | PyO3 + maturin; SIMD search, consolidation |
| **Go** | ✅ Production | Mesh networking, gRPC; 4,300+ LOC |
| **Koka** | 🧪 Experimental | Effect handlers (PSR-008 complete, not production-hardened) |
| **Mojo** | ❌ Deferred | Await SDK maturity (v22.0+) |
| **Julia** | 🟡 Advanced | JSON-RPC; vectorized decay, clustering |
| **Zig** | 🟡 Advanced | Low-level FFI; SIMD intrinsics (AVX2/SSE) |
| **Haskell** | 📦 Archival | Reference patterns only |
| **Elixir** | 🧪 Stubs | OTP structures; no Python bridge yet |
| **Erlang** | 🔴 Experimental | Actor model prototypes |
| **Gleam** | 🔴 Experimental | Logic verification |
| **Nim** | 🔴 Experimental | Native utils |

For build commands, test commands, integration architecture, and roadmap
see **[polyglot/STATUS.md](../polyglot/STATUS.md)**.

## Maintenance Policy
- **Core (Rust/Go)**: Must pass CI with 100% feature parity with Python fallbacks.
- **Advanced (Julia/Zig)**: Specialised workloads; fallbacks recommended.
- **Experimental**: No stability guarantees; used for research and verification.


## Summary

WhiteMagic follows a "Right Tool for the Job" philosophy, offloading performance-critical or domain-specific tasks to specialized runtimes.

| Language | Maturity | Primary Focus | Integration Level |
|----------|----------|---------------|-------------------|
| **Rust** | 🟢 Production | Similarity, Search, Consolidation | Native (maturin/FFI) |
| **Go** | 🟢 Production | Distributed Mesh, Networking | RPC/Binary |
| **Koka** | 🟢 Production | Effect Orchestration, Deployment | Binary/IPC |
| **Mojo** | 🟡 Advanced | GPU Acceleration, HRR | FFI/Native |
| **Julia** | 🟡 Advanced | Linear Algebra, Forecasts | JSON-RPC/FFI |
| **Zig** | 🟠 Developing | Low-level Graph Ops | FFI |
| **Haskell**| 🔴 Experimental| Hot Path Prototypes | Logic Only |
| **Elixir** | 🔴 Experimental| Hot Path Prototypes | Logic Only |
| **Erlang** | 🔴 Experimental| Memory Core Prototypes | Logic Only |
| **Gleam**  | 🔴 Experimental| Logic Verification | Logic Only |
| **Nim**    | 🔴 Experimental| Native Utils | Logic Only |

---

## 🦀 Rust (`whitemagic-rust`)
- **Status**: ✅ Core Stable
- **Capabilities**: 
    - Parallel memory consolidation (100x faster than Python)
    - Tantivy-based full-text search
    - Vector similarity (SIMD optimized)
    - LZ4 compression
- **Build**: `maturin develop --release`

## 🐹 Go (`whitemagic-go`)
- **Status**: ✅ Core Stable
- **Capabilities**:
    - High-concurrency mesh network coordinator
    - Distributed task execution
    - Lean MCP server implementation
- **LOC**: 4,300+
- **Build**: `go build`

## 🧪 Koka (`whitemagic-koka`)
- **Status**: ✅ Production (PSR-008 Complete)
- **Capabilities**:
    - Algebraic effect handling for system orchestration
    - Safe concurrency for army deployment
    - Formalized logic for memory effects
    - **NEW**: PSR-008 type-safe coordination (locks, barriers, leader election, CAS)
    - **NEW**: Unified effect handlers (circuit breaker + backpressure + transactions + coordination)
- **Build**: `build_native.sh`

## 📦 Mojo (`whitemagic-mojo`)
- **Status**: 🟡 Advanced (Performance Focused)
- **Capabilities**:
    - GPU-accelerated graph operations
    - Holographic Reduced Representations (HRR)
    - Vector indexing
- **Build**: `mojo build`

## 🍕 Julia (`whitemagic-julia`)
- **Status**: 🟡 Advanced (Science Focused)
- **Capabilities**:
    - Vectorized decay analysis
    - K-Means clustering
    - RRF (Reciprocal Rank Fusion)
    - Forecasting metrics
- **Integration**: Persistent server mode

## ⚡ Zig (`whitemagic-zig`)
- **Status**: � Advanced (SIMD Upgraded)
- **Capabilities**:
    - Low-level graph primitive optimization
    - Manual memory management for hot paths
    - **NEW**: True SIMD intrinsics (AVX2/SSE) with @Vector operations
    - **NEW**: Runtime CPU feature detection and optimization
    - SIMD-accelerated keyword extraction (16-byte vectors)
- **Build**: `zig build` (via pixi)

## 🧪 Experimental Tier (Haskell, Elixir, Erlang, Gleam, Nim)
These modules contain specific "hot path" logic or architectural experiments that are not yet fully integrated into the main runtime. They serve as reference implementations for specific logic blocks.

---

## Current Generator Snapshot

Generated from `whitemagic.tools.capability_matrix.get_capability_matrix()` on the current checkout.

- **Total subsystems**: 25
- **Active fusions**: 28
- **Unexplored fusions**: 0
- **Polyglot-accelerated subsystems**: 9
- **Categories**: architecture, governance, intelligence, memory, resonance

## Maintenance Policy
- **Core (Rust/Go/Koka)**: Must pass CI and have 100% feature parity with Python fallbacks.
- **Advanced (Mojo/Julia/Zig)**: Used for specialized workloads; fallbacks optional but recommended.
- **Experimental**: No stability guarantees; used for research and verification.
