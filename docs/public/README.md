# WhiteMagic — Public Documentation

> **For AI agents**: [`AI_PRIMARY.md`](../../AI_PRIMARY.md) · **Quick install**: `pip install whitemagic[mcp]`

---

## Getting Started

| Document | Description |
|----------|-------------|
| [MCP Config Examples](./MCP_CONFIG_EXAMPLES.md) | Ready-to-use MCP config templates (PRAT/classic/lite) |
| [Galaxy Per-Client Guide](./GALAXY_PER_CLIENT_GUIDE.md) | Multi-galaxy project-scoped databases |
| [Lite vs Heavy](./LITE_VS_HEAVY.md) | Choosing the right deployment tier |
| [Encryption at Rest](./ENCRYPTION_AT_REST.md) | SQLCipher setup and key management |

## Reference

| Document | Description |
|----------|-------------|
| [Glossary](./GLOSSARY.md) | Terminology reference (PRAT, Gana, Dharma, etc.) |
| [Use Cases](./USE_CASES.md) | Real-world usage patterns |
| [Terms of Service](./TERMS_OF_SERVICE.md) | Usage terms and conditions |
| [Privacy Policy](./PRIVACY_POLICY.md) | Data handling and privacy |
| [Security](./SECURITY.md) | Security policies and reporting |
| [Contributing](./CONTRIBUTING.md) | Contribution guidelines |
| [Changelog](./CHANGELOG.md) | Version history and release notes |

## Project Documentation

See [`docs/README.md`](../README.md) for the full documentation structure including architecture, ADRs, the grimoire, and the active workspace. See [`INDEX.md`](../../INDEX.md) for the master file index.

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
