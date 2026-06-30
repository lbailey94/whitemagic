---
name: wm-polyglot
description: "Polyglot acceleration — 7 languages, graceful degradation, building, testing"
version: 1.0.0
author: WhiteMagic Labs
license: MIT
platforms: [linux, macos, windows]
metadata:
  whitemagic:
    tags: [polyglot, rust, haskell, elixir, go, zig, julia, koka, acceleration]
---

# Polyglot Acceleration

WhiteMagic has 7 polyglot acceleration cores (Mojo removed in v23.2).

## Languages

| Language | Role | Location |
|----------|------|----------|
| **Rust** | SIMD ops, cascade backend, batch distance/dot/top-k | `polyglot/whitemagic-rs/` |
| **Haskell** | Pure functional analysis, type safety | `polyglot/haskell/` |
| **Elixir** | Concurrent distributed processing | `polyglot/elixir/` |
| **Go** | Fast compilation utilities, gRPC | `polyglot/go/` |
| **Zig** | Systems-level optimization, storage | `polyglot/zig/` |
| **Julia** | Scientific computing, statistics | `polyglot/julia/` |
| **Koka** | Effect tracking, semantics | `polyglot/koka/` |

## Graceful Degradation

Every optional feature must fail safely:
- Rust extension missing → Python fallback runs transparently
- FastAPI not installed → webhook routes return `missing_dependency` envelope
- Any polyglot compiler absent → Python fallback

## Building
```bash
cd polyglot/rust && cargo build --release
cd polyglot/elixir && mix escript.build
cd polyglot/go && go build ./...
```

## Testing
Polyglot tests are in `tests/archive_polyglot/` — run separately if needed.
Unit tests must mock at class boundary, never spawn subprocesses.
