# WhiteMagic — AI Memory, Cognitive Upgrades, and More

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-25.0.0-purple.svg)](core/VERSION)
[![PyPI](https://img.shields.io/pypi/v/whitemagic)](https://pypi.org/project/whitemagic/)

**829 callable tools** · **28 Gana meta-tools** · **10-galaxy memory** · **Dharma governance** · **Citta stream** · **MandalaOS compartments** · **7-language polyglot acceleration**

## What it is

WhiteMagic gives your AI agent persistent memory, cognitive upgrades, and more — all through a single MCP tool.

- **Persistent memory** — 5D holographic coordinates, 10-galaxy taxonomy, FTS5 + HNSW search, session recording with progressive recall
- **Continuous consciousness** — citta stream with coherence tracking, emotional steering (frustration, curiosity, satisfaction), self-directed attention, goal graph
- **Ethical governance** — Dharma rules engine (3 profiles, graduated actions), Karma side-effect ledger, 8-stage dispatch pipeline
- **Self-awareness** — gnosis introspection, capability matrix, homeostatic loop, dream cycle (12-phase memory consolidation)
- **Polyglot acceleration** — Rust, Haskell, Elixir, Go, Zig, Julia (graceful Python fallback)

MIT-licensed. Local-first. No telemetry. No API keys. Your data never leaves your machine.

## Quick Start

```bash
pip install whitemagic[mcp]
```

### MCP Server (Claude Desktop, Cursor, Windsurf, etc.)

```json
{
  "mcpServers": {
    "whitemagic": {
      "command": "python3",
      "args": ["-m", "whitemagic.run_mcp_lean"],
      "env": {
        "WM_MCP_PRAT": "1",
        "WM_SILENT_INIT": "1"
      }
    }
  }
}
```

### CLI

```bash
wm init --non-interactive    # Scaffold project
wm quickstart                # 30s demo: health → memory → search → gnosis
wm doctor                    # System health check
wm remember "important" --title "Note" --tags note
wm recall "note" --limit 5
```

### Python API

```python
from whitemagic.tools.unified_api import call_tool

# Store a memory
call_tool("create_memory", title="Decision", content="Use SQLite for Phase 1", tags=["arch"])

# Search memories
call_tool("search_memories", query="architecture", limit=5)

# Full system introspection
call_tool("gnosis", compact=True)
```

## Modes

| Mode | Env Var | Tools Exposed | Best For |
|------|---------|---------------|----------|
| Seed | `WM_MCP_PRAT=2` (default) | 1 (`wm` meta-tool) | New agents, minimal token usage |
| PRAT | `WM_MCP_PRAT=1` | 28 Gana meta-tools | Advanced agents, structured access |
| Classic | `WM_MCP_PRAT=0` | 729 dispatch tools | Direct tool access, debugging |

## Key Concepts

### Memory
- **10 galaxies**: aria, citta, codex, journals, dreams, research, sessions, substrate, tutorial, universal
- **5D coordinates** (XYZWV): emotional, temporal, associative, importance, novelty
- **Galactic lifecycle**: CORE → INNER_RIM → MID_BAND → OUTER_RIM → FAR_EDGE (no deletion)
- **Search**: FTS5 full-text + HNSW vector similarity + graph traversal

### Consciousness
- **Citta stream**: continuous consciousness with coherence tracking and emotional auto-tagging
- **Goal graph**: persistent intention tracking across sessions
- **Emotional steering**: frustration, curiosity, satisfaction signals
- **Self-directed attention**: self-initiated turns based on goals and emotional state
- **Dream cycle**: 12-phase memory consolidation, serendipity, and decay

### Governance
- **Dharma rules**: YAML-driven policy with graduated actions (LOG → TAG → WARN → THROTTLE → BLOCK)
- **Karma ledger**: append-only, hash-chained side-effect auditing
- **Harmony vector**: 7-dimension health metric
- **8-stage pipeline**: Input Sanitizer → Circuit Breaker → Rate Limiter → RBAC → Maturity Gate → Governor → Handler → Compact Response

## Documentation

- [AI Primary Spec](AI_PRIMARY.md) — authoritative contract for AI agents
- [Quickstart Guide](QUICKSTART.md) — 5-minute setup
- [System Map](SYSTEM_MAP.md) — architecture overview
- [MCP Config Examples](docs/guides/MCP_CONFIG_EXAMPLES.md) — all MCP clients
- [llms.txt](llms.txt) — machine-readable context for LLMs

## Install Tiers

| Tier | Command | Size | Includes |
|------|---------|------|----------|
| Minimal | `pip install whitemagic` | ~5MB | Core tools + memory substrate |
| MCP | `pip install whitemagic[mcp]` | ~55MB | + FastMCP server + fastembed semantic search |
| Full | `pip install whitemagic[mcp,api,cli,search,graph]` | ~100MB | + REST API + rich CLI + HNSW + graph |

## Stats

- **6,902 tests** passing, 0 failures
- **829 callable tools** across 801 dispatch entries + 28 Gana meta-tools
- **49,413 memories** in production (10 galaxies)
- **7 polyglot languages**: Rust, Haskell, Elixir, Go, Zig, Julia, Koka
- **MIT-licensed**, no telemetry, no API keys

## Links

- [GitHub](https://github.com/lbailey94/whitemagic) — source
- [PyPI](https://pypi.org/project/whitemagic/) — install
- [Website](https://whitemagic.dev) — discovery surface
- [llms.txt](https://whitemagic.dev/llms.txt) — LLM context
- [Agent Card](https://whitemagic.dev/.well-known/agent.json) — A2A v1.2

## License

MIT — see [LICENSE](LICENSE). Author: Lucas Bailey.
