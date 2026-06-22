# ADR-002: Polyglot Strategy — Right Tool for the Job

**Status**: Accepted  
**Date**: 2026-04-15  
**Deciders**: WhiteMagic core team  
**Tags**: architecture, polyglot, performance

---

## Context

WhiteMagic's core is Python, but several workloads (SIMD similarity, parallel search,
distributed networking) hit hard Python performance limits. The question was how to integrate
high-performance native code.

## Decision

Adopt a **tiered polyglot strategy** rather than rewriting WhiteMagic in a single alternative language:

| Tier | Languages | Integration | Use Case |
|------|-----------|-------------|----------|
| **Production** | Rust, Go | PyO3/maturin (Rust), gRPC binary (Go) | Hot paths: SIMD similarity, parallel search, mesh networking |
| **Advanced** | Julia, Zig | JSON-RPC / FFI | Scientific computing, low-level ops |
| **Experimental** | Koka, Elixir | IPC / effect stubs | Research: effect handlers, actor model |
| **Archival** | Haskell, Erlang, Gleam, Nim | Logic only | Reference implementations |

**Key rules**:
1. All polyglot bridges **must have Python fallbacks**. If the native runtime is unavailable, WhiteMagic degrades gracefully.
2. **Production bridges** must pass CI (`cargo clippy`, `go test ./...`) on every commit.
3. **Experimental bridges** use `fallback_used=True` in `SpecialistResult` and log `logger.debug()` when falling back.
4. **`polyglot/STATUS.md` is the single canonical source** of bridge status (see ADR-004).

## Consequences

**Positive**:
- 100x speedup on memory consolidation (Python → Rust SIMD)
- Go mesh achieves high concurrency without GIL interference
- Language tiers set clear contributor expectations: Production bridges must be maintained, Experimental may break

**Negative**:
- Build matrix complexity: Rust (maturin), Go (go build), Zig (zig build) + Python CI
- Binary distribution: wheels must bundle Rust extension (solved by maturin wheel build)
- Fallback divergence risk: Python fallbacks must stay semantically equivalent to native

## Alternatives Considered

- **Cython/Numba for hot paths**: Rejected — limited to Python ecosystem, no mesh networking
- **Full Rust rewrite**: Rejected — would abandon 182K lines of well-tested Python
- **Julia for all scientific work**: Superseded by Rust SIMD; Julia retained for RRF/K-Means only
