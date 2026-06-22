# WhiteMagic — Agentic AI Governance & Metacognition Substrate

[![CI](https://github.com/whitemagic-ai/whitemagic/actions/workflows/ci.yml/badge.svg)](https://github.com/whitemagic-ai/whitemagic/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-22.2.0-purple.svg)](core/VERSION)

A locally runnable, MIT-licensed research/lab artifact and source library for agentic AI governance, metacognition, memory substrate experiments, and distributed orchestration.

**28 PRAT Gana meta-tools** · **Rust SIMD acceleration** · **WASM compilation target** · **Safety governance**

## Quick Start

```bash
# Lite install (MCP server + CLI, minimal dependencies)
pip install -e core/.[lite]

# Start MCP server
python -m whitemagic.run_mcp

# Or use the CLI
wm status
```

See [QUICKSTART.md](QUICKSTART.md) for detailed setup instructions.

## Installation Tiers

| Tier | Command | Includes |
|------|---------|----------|
| **Lite** | `pip install whitemagic[lite]` | MCP server + CLI (~5 deps) |
| **Core** | `pip install whitemagic[core]` | + Database + Networking + Auth + Trust |
| **Heavy** | `pip install whitemagic[heavy-tier]` | + Embeddings + Search + Graph + ML stack |

Individual extras: `mcp`, `cli`, `api`, `embeddings`, `search`, `graph`, `db`, `encrypt`, `trust`, `net`, `openai`, `vision`, `watcher`, `dashboard`

## Architecture

```
whitemagic/                  # Core library (this repo)
├── core/                    # Python package (pip install whitemagic)
│   ├── whitemagic/          # Main source
│   │   ├── tools/           # 28 PRAT Gana tools
│   │   ├── core/            # Memory, resonance, patterns, governance
│   │   ├── hermes/          # Telemetry/context hooks
│   │   ├── interfaces/      # CLI, API, Dashboard
│   │   └── config/          # Path resolution, settings
│   ├── tests/               # current local audit baseline: 2,379 passed, 67 skipped
│   └── docs/                # Package documentation
├── polyglot/                # Language accelerators (minus CODEX)
│   ├── mojo/                # GPU/SIMD kernels
│   ├── whitemagic-koka/     # Effect handler orchestration
│   ├── whitemagic-zig/      # FFI bridge
│   └── whitemagic-go/       # Concurrent services
├── grimoire/                # Canonical 28 Gana chapters
├── docs/                    # Project documentation
└── whitemagic-app/          # Tauri desktop app (local-first UI)

whitemagic-site/             # Public website (sibling repo)
whitemagic-codex/            # Rust document pipeline (sibling repo)
```

See [`ARCHITECTURE_MANIFEST_2026-06-04.md`](ARCHITECTURE_MANIFEST_2026-06-04.md) for the full post-extraction directory map and sibling repo relationships.

## Entry Points

| Entry Point | Purpose |
|-------------|---------|
| `python -m whitemagic.run_mcp` | MCP Server (FastMCP) — Full 28 Gana cycle |
| `python -m whitemagic.run_mcp_lean` | MCP Server (Lean) — stdlib only, <1s handshake |
| `wm` / `whitemagic` | CLI — All whitemagic commands |

## Safety Architecture

WhiteMagic includes built-in safety mechanisms for agentic AI:

- **Governor** — Pre-execution validation for forbidden actions
- **Input Sanitizer** — Validates and sanitizes all tool inputs
- **Rate Limiter** — Prevents resource exhaustion
- **Constitutional Checks** — Ethical governance constraints
- **Tool Permissions** — Fine-grained access control per Gana

## Development

```bash
# Clone and install dev dependencies
git clone https://github.com/whitemagic-ai/whitemagic.git
cd whitemagic
pip install -e core/.[dev]

# Run tests
cd core && pytest tests/ -q

# Lint
cd core && ruff check whitemagic/

# Rust check
cd core/whitemagic-rust && cargo check --features python
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for full development guidelines.

## Verification Baselines

| Baseline | Result |
|----------|--------|
| **v23.0.0 release baseline** | 1,470 passing tests, 2 skipped, 0 failed (as of 2026-06-19) |
| **Current local audit baseline** | 1,470 passing tests, 2 skipped, 0 failed (as of 2026-06-18) |

## Documentation

| Document | Description |
|----------|-------------|
| [QUICKSTART.md](QUICKSTART.md) | Getting started guide |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Development setup and guidelines |
| [CHANGELOG.md](CHANGELOG.md) | Version history |
| [docs/public/GLOSSARY.md](docs/public/GLOSSARY.md) | Terminology reference |
| [docs/public/LITE_VS_HEAVY.md](docs/public/LITE_VS_HEAVY.md) | Installation tier comparison |

## License

[MIT](LICENSE)
