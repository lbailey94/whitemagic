# WhiteMagic Documentation

> **For AI agents**: [`misc/AI_PRIMARY.md`](./misc/AI_PRIMARY.md) · **Quick install**: `pip install whitemagic[mcp]`

---

## Guides

| Document | Description |
|----------|-------------|
| [Quickstart](./guides/QUICKSTART.md) | Getting started in under 5 minutes |
| [MCP Config Examples](./guides/MCP_CONFIG_EXAMPLES.md) | Ready-to-use MCP config templates (PRAT/classic/lite) |
| [Galaxy Per-Client Guide](./guides/GALAXY_PER_CLIENT_GUIDE.md) | Multi-galaxy project-scoped databases |
| [Lite vs Heavy](./guides/LITE_VS_HEAVY.md) | Choosing the right deployment tier |
| [Encryption at Rest](./guides/ENCRYPTION_AT_REST.md) | SQLCipher setup and key management |
| [Venv Migration](./VENV_MIGRATION.md) | Plan for migrating `lib/` to `.venv/` |

## Audit & Status

| Document | Description |
|----------|-------------|
| [Project Audit 2026-04-14](./PROJECT_AUDIT_2026-04-14.md) | Full project audit — directory-by-directory findings, technical debt, improvement roadmap |
| [Consolidation Report](../CONSOLIDATION_REPORT.md) | 6-phase SD card consolidation (66 GB recovered) |
| [Session Handoff 2026-04-13](./SESSION_HANDOFF_2026-04-13.md) | Previous session — completed tasks and remaining work |
| [Glossary](./GLOSSARY.md) | Terminology reference (PRAT, Gana, Dharma, etc.) |

## Design & Vision

| Document | Description |
|----------|-------------|
| [Benchmarks](./design/BENCHMARK_COMPARISON.md) | Performance vs comparable tools |
| [Use Cases](./design/USE_CASES.md) | Real-world usage patterns |
| [TypeScript SDK Design](./design/TYPESCRIPT_SDK_DESIGN.md) | `@whitemagic/sdk` architecture |
| [WASM Strategy](./design/WASM_STRATEGY.md) | WebAssembly deployment path |
| [Triangular Architecture](./plans/triangular-architecture.md) | Laptop/VPS/Railway/Vercel deployment architecture |
| [Rust Reorganization](./plans/rust-reorganization.md) | Plan for Rust src/ module restructure |

## Strategy & Analysis

| Document | Description |
|----------|-------------|
| [Strategy Book](./strategy_manifestos/strategy_book.md) | Comprehensive strategic analysis |
| [Satkona Strategy](./strategy_manifestos/satkona_strategy_book.md) | Six-directional strategic framework |
| [Phase Analyses](./strategy_manifestos/) | 8-phase analysis (core Python, acceleration, ML, frontend, infrastructure, legacy, docs, polyglot) |

## Community

| Document | Description |
|----------|-------------|
| [Contributing](./community/CONTRIBUTING.md) | Contribution guidelines |
| [Changelog](./community/CHANGELOG.md) | Detailed version history |

---

## Path Configuration

WhiteMagic uses a configurable path system. See `core/whitemagic/config/paths.py` for details.

- `WM_STATE_ROOT`: Root directory for state/data (default: `~/.whitemagic`, auto-detects `data/runtime/` on SD card)
- `WM_DB_PATH`: Path to SQLite database
- `WM_MCP_PRAT`: Set to `1` to enable PRAT mode (28 Gana meta-tools)
- `WM_MCP_LITE`: Set to `1` for lite mode (core tools only)
- `WM_MCP_CLIENT`: Set client name for schema adaptation (e.g. `windsurf`, `claude`)
- `WM_SILENT_INIT`: Set to `1` for quiet initialization

## Building Components

- **Python**: `pip install -e core/.[dev]` (or `.[lite]`, `.[core]`, `.[heavy-tier]`)
- **Rust**: `cd core/whitemagic-rust && maturin develop --release --features python`
- **Go**: `cd polyglot/whitemagic-go && go build`
- **Zig**: `cd polyglot/whitemagic-zig && zig build`
- **Mojo**: `cd polyglot/mojo && pixi run mojo build -I src hot_paths.mojo`

## Quick Commands (justfile)

```bash
just setup          # Create venv + install core deps
just setup-heavy    # Full ML stack install
just mcp            # Start MCP server (full)
just mcp-lean       # Start lean MCP server
just test           # Run Python test suite
just test-rust      # Run Rust tests
just lint           # Lint Python code
just db-check       # Database integrity check
just db-stats       # Show database statistics
just doctor         # System health check
just clean          # Clean build artifacts
```
