# WhiteMagic Documentation

> **For AI agents**: [`public/AI_PRIMARY.md`](./public/AI_PRIMARY.md) · **Quick install**: `pip install whitemagic[mcp]`

---

## Documentation Structure (v21.1)

This directory is organized into three tiers:

### 📚 `public/` — User-Facing Documentation
**Status**: Un-gitignored, part of public release

Essential documentation for users and contributors:

| Document | Description |
|----------|-------------|
| [README.md](./public/README.md) | Project overview and quick start |
| [CHANGELOG.md](./public/CHANGELOG.md) | Version history and release notes |
| [CONTRIBUTING.md](./public/CONTRIBUTING.md) | Development setup and guidelines |
| [GLOSSARY.md](./public/GLOSSARY.md) | Terminology reference (PRAT, Gana, Dharma, etc.) |
| [AI_PRIMARY.md](./public/AI_PRIMARY.md) | Primary documentation for AI agents |
| [SECURITY.md](./public/SECURITY.md) | Security policies and reporting |
| [PRIVACY_POLICY.md](./public/PRIVACY_POLICY.md) | Data handling and privacy |
| [TERMS_OF_SERVICE.md](./public/TERMS_OF_SERVICE.md) | Usage terms and conditions |
| [USE_CASES.md](./public/USE_CASES.md) | Real-world usage patterns |

**Subdirectories**:
- `guides/` — Detailed how-to guides
- `changelogs/` — Version history archive
- `community/` — Contribution guidelines and code of conduct
- `design/` — Architecture and design documents
- `misc/` — Additional reference materials

### 🔧 `internal/` — Development & Operations
**Status**: Gitignored, not part of public release

Internal documentation for the WhiteMagic development team:

- `sessions/` — Session summaries and handoff reports
- `campaigns/` — Development campaign documentation
- `archive/` — Historical reports and archaeological digs
- `strategy/` — Strategic planning documents

These files contain operational details, personal notes, and development history that aren't relevant to end users.

### 🔒 `private/` — Sensitive & Personal
**Status**: Gitignored, restricted access

Sensitive documentation including:
- `aria/` — Aria consciousness archives and personal memories

These files are kept private as they contain personal AI experiences and emotional content.

---

## Path Configuration

WhiteMagic uses a configurable path system. See `core/whitemagic/config/paths.py` for details.

- `WM_STATE_ROOT`: Root directory for state/data (default: `~/.whitemagic`)
- `WM_DB_PATH`: Path to SQLite database
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
