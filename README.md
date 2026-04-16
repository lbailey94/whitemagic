# WhiteMagic — Agentic AI Platform

[![CI](https://github.com/whitemagic-ai/whitemagic/actions/workflows/ci.yml/badge.svg)](https://github.com/whitemagic-ai/whitemagic/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-22.0.0-purple.svg)](core/VERSION)

A polyglot agentic AI platform with Python core, Rust performance bridges, and multi-language support for AI agents, memory systems, and distributed orchestration.

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
whitemagic/
├── core/                    # Python package (pip install whitemagic)
│   ├── whitemagic/          # Main source
│   │   ├── tools/           # 28 PRAT Gana tools
│   │   ├── core/            # Memory, resonance, patterns, governance
│   │   ├── rust/            # Rust bridge (SIMD, parallel search)
│   │   ├── interfaces/      # CLI, API, Dashboard
│   │   └── config/          # Path resolution, settings
│   ├── whitemagic-rust/     # Rust crate (PyO3 + WASM)
│   ├── whitemagic-math/     # Shared math crate
│   ├── haskell/             # Haskell divination module
│   └── tests/               # 2259 tests
├── polyglot/                # Language bridges
│   ├── mojo/                # GPU/SIMD acceleration
│   ├── whitemagic-koka/     # Effect handler orchestration
│   ├── whitemagic-zig/      # FFI bridge
│   └── whitemagic-go/       # Concurrent services
├── grimoire/                # 28 Gana chapter reference
└── docs/                    # Documentation
```

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

## Documentation

| Document | Description |
|----------|-------------|
| [QUICKSTART.md](QUICKSTART.md) | Getting started guide |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Development setup and guidelines |
| [CHANGELOG.md](CHANGELOG.md) | Version history |
| [docs/GLOSSARY.md](docs/GLOSSARY.md) | Terminology reference |
| [docs/STRATEGY_2026-04-14.md](docs/STRATEGY_2026-04-14.md) | Project roadmap |
| [docs/WAVE4_STRATEGY.md](docs/WAVE4_STRATEGY.md) | Long-term release strategy |
| [docs/LITE_VS_HEAVY.md](docs/LITE_VS_HEAVY.md) | Installation tier comparison |

## License

[MIT](LICENSE)
