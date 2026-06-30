---
description: WhiteMagic polyglot acceleration — Rust, Haskell, Elixir, Go, Zig bridges
---

# WM Polyglot

WhiteMagic has 7 polyglot acceleration cores (Mojo removed in v23.2):

## Languages
- **Rust** — SIMD ops, cascade backend, batch distance/dot/top-k
- **Haskell** — Pure functional analysis
- **Elixir** — Concurrent distributed processing
- **Go** — Fast compilation utilities
- **Zig** — Systems-level optimization
- **Julia** — Scientific computing
- **Python** — Primary language, fallback for all accelerators

## Graceful Degradation
Every optional feature must fail safely:
- Rust extension missing → Python fallback runs transparently
- FastAPI not installed → webhook routes return `missing_dependency` envelope
- Any polyglot compiler absent → Python fallback

## Building
```bash
# Rust
cd polyglot/rust && cargo build --release

# Elixir
cd polyglot/elixir && mix escript.build

# Go
cd polyglot/go && go build ./...
```

## Testing
Polyglot tests are in `tests/archive_polyglot/` — run separately if needed.
Unit tests must mock at class boundary, never spawn subprocesses.
