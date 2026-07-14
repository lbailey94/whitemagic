# WhiteMagic — Agentic AI Platform (v25.0.0)

A polyglot agentic AI platform with Python core, Rust performance bridges, and multi-language support for AI agents, memory systems, and distributed orchestration.

## Installation

### Lite (MCP + CLI only)
```bash
pip install -e ".[dev,mcp,cli]"
```

### Core (standard installation with database + networking)
```bash
pip install -e ".[dev,mcp,cli,core]"
```

### Heavy-tier (full ML stack with embeddings + search)
```bash
pip install -e ".[dev,mcp,cli,heavy]"
```

## Quick Start

### MCP Server (FastMCP)
```bash
python -m whitemagic.run_mcp
```

### MCP Server (Lean — stdlib only)
```bash
python -m whitemagic.run_mcp_lean
```

### CLI
```bash
wm status
wm doctor
```

## Project Structure

```
whitemagic/
├── core/           # Core systems (memory, intelligence, governance)
├── tools/          # Tool handlers and dispatch
├── security/       # Security, sanitization, tool gating
├── config/         # Configuration and paths
├── cli/            # Command-line interface
├── rust/           # Rust bridge implementations
└── polyglot/       # Multi-language bridges (Koka, Zig, Mojo, etc.)
```

## Development

### Run Tests

```bash
make test              # Full test suite
make test-core         # Release-critical contract tests only (fast)
pytest tests/          # Direct pytest invocation
```

### Release Validation

```bash
make check-ship        # Validate ship surface hygiene
```

### Lint & Typecheck
```bash
make lint
make typecheck
```

### Build Rust Extensions
```bash
cd whitemagic-rust
maturin develop
```

## Architecture

- **Dispatch Pipeline**: 9 composable middlewares (sanitizer, circuit breaker, rate limiter, security monitor, tool permissions, maturity gate, governor, observability)
- **Memory System**: Unified SQLite backend with holographic spatial index, galactic distance tracking, and consolidation
- **PRAT Ganas**: 28 meta-tools organized into 4 quadrants (Horn, Dipper, Willow, Room)
- **Polyglot Bridges**: Rust, Koka, Zig, Mojo, Go, Elixir, Julia, Haskell, Erlang, Nim

## Documentation

See the workspace root `../README.md` for monorepo structure and project overview.
See `docs/` for detailed documentation.

## License

[MIT License](../LICENSE) — see LICENSE file at repository root.
