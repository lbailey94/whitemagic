# WhiteMagic Documentation

> **For AI agents**: [`AI_PRIMARY.md`](../AI_PRIMARY.md) · **For developers**: [`README.md`](../README.md) · **Quick install**: `pip install whitemagic[mcp]`

---

## Documentation Structure (v24.1.0)

### 📚 Public Documentation (`docs/public/`)

User-facing and contributor documentation:

| Document | Description |
|----------|-------------|
| [README.md](./public/README.md) | Project overview and quick start |
| [CHANGELOG.md](./public/CHANGELOG.md) | Version history and release notes |
| [CONTRIBUTING.md](./public/CONTRIBUTING.md) | Development setup and guidelines |
| [GLOSSARY.md](./public/GLOSSARY.md) | Terminology reference (PRAT, Gana, Dharma, etc.) |
| [SECURITY.md](./public/SECURITY.md) | Security policies and reporting |
| [TERMS_OF_SERVICE.md](./public/TERMS_OF_SERVICE.md) | Usage terms and conditions |
| [LITE_VS_HEAVY.md](./public/LITE_VS_HEAVY.md) | Deployment tier comparison |
| [ENCRYPTION_AT_REST.md](./public/ENCRYPTION_AT_REST.md) | SQLCipher setup and key management |
| [MCP_CONFIG_EXAMPLES.md](./public/MCP_CONFIG_EXAMPLES.md) | Ready-to-use MCP config templates |

### 🗂️ Active Workspace (`docs/message_board/`)

Current-cycle plans, session handoffs, and active triage documents. See [INDEX.md](../INDEX.md) for the full inventory.

### 🏗️ Architecture Manifest

For the post-extraction repo map — what this repo is, what the sibling repos are, and how they relate — see [`ARCHITECTURE_MANIFEST_2026-06-04.md`](../ARCHITECTURE_MANIFEST_2026-06-04.md).

### 📦 Archive (`docs/archive/`)

Superseded plans, completed audits, and historical reports. Preserved for provenance.

### 🏛️ Architecture & ADRs (`docs/adr/`, `docs/architecture/`)

Formal Architecture Decision Records and durable design documents.

### 🔮 Grimoire (`grimoire/`)

The canonical 28-chapter Gana/garden source. Start at [grimoire/00_PROLOGUE.md](../grimoire/00_PROLOGUE.md).

---

## Path Configuration

See [`core/whitemagic/config/paths.py`](../core/whitemagic/config/paths.py) for details.

- `WM_STATE_ROOT`: Root directory for state/data (default: `~/.whitemagic`)
- `WM_DB_PATH`: Path to SQLite database (default: `$WM_STATE_ROOT/memory/whitemagic.db`)
- `WM_MCP_PRAT`: Set to `1` to enable PRAT mode (28 Gana meta-tools)
- `WM_MCP_LITE`: Set to `1` for lite mode (core tools only)
- `WM_MCP_CLIENT`: Set client name for schema adaptation (e.g. `windsurf`, `claude`)

---

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

---

## License

See [LICENSE](../LICENSE) for full terms.
