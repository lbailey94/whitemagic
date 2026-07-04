# Contributing to WhiteMagic

> **Version**: 22.0.0 — updated 2026-04-16
>
> For conceptual overview, see `AI_PRIMARY.md` and `SYSTEM_MAP.md`.

Thank you for your interest in contributing to WhiteMagic! This document provides practical guidelines for the v22 codebase.

---

## Prerequisites

- **Python**: 3.11+ (3.12 recommended)
- **Git**: For version control
- **Optional polyglot toolchains**: Rust (maturin), Haskell (GHC), Mojo, Elixir, Zig, Go — only needed if touching accelerator code

## Quick Start

```bash
git clone https://github.com/lbailey94/whitemagic.git
cd whitemagic
python3 -m venv .venv && source .venv/bin/activate

# Core + CLI (minimal)
pip install -e core/.[cli]

# With MCP server
pip install -e core/.[mcp,cli]

# Full dev (all optional deps + linting + testing)
pip install -e core/.[dev,mcp,cli,db,net]
```

### Verify Installation

```bash
wm doctor                    # System diagnostics
wm status                    # Quick health check
python -m pytest core/tests/ -q   # Run test suite (~80% pass rate expected)
```

---

## Development Setup

### Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `WM_STATE_ROOT` | State/data directory | `~/.whitemagic` |
| `WM_DB_PATH` | SQLite database path | `$WM_STATE_ROOT/memory/whitemagic.db` |
| `WM_MCP_PRAT` | Enable PRAT mode (28 Gana meta-tools) | `0` |
| `WM_SILENT_INIT` | Suppress init logs | `0` |

### Polyglot Build (optional)

```bash
# Rust bridge (production-ready)
cd core/whitemagic-rust && maturin develop --release --features python,arrow && cd ../..

# Go bridge (production-ready)
cd polyglot/go && go build -buildmode=c-shared -o libwhitemagic.so && cd ../..

# Other bridges (experimental): Haskell, Mojo, Elixir, Zig — see polyglot/STATUS.md
```

---

## Making Changes

### Branch Naming

- `feature/` — New features
- `fix/` — Bug fixes
- `docs/` — Documentation
- `refactor/` — Code refactoring
- `polyglot/` — Accelerator language changes

### Architecture Guidelines

1. **New tools** go in `whitemagic/tools/handlers/<domain>.py`
2. **Register** the handler in `whitemagic/tools/dispatch_<domain>.py`
3. **Declare schema** in `whitemagic/tools/registry_defs/<domain>.py`
4. **Regenerate registry** after changes: `python core/scripts/generate_mcp_registry.py`
5. **All tool calls** route through `unified_api.call_tool()` → envelope → dispatch → handler
6. **Add regression tests** in `core/tests/unit/regression/` for release-critical fixes

### Code Style

- **Formatter**: Black (100 char line length)
- **Linter**: Ruff
- **Type checking**: mypy — strict on `tools/` and `interfaces/`, relaxed elsewhere
- **Docstrings**: Google style
- **Naming**: PascalCase classes, snake_case functions, UPPER_CASE constants

```bash
cd core
ruff format whitemagic/ tests/
ruff check whitemagic/ tests/
mypy whitemagic/tools whitemagic/interfaces  # strict on public surface
cd ..
```

---

## Testing

```bash
# Full suite (expect ~80% pass rate — some failures are Labs-tier experimental code)
PYTHONPATH=core pytest core/tests/ -q

# With coverage
PYTHONPATH=core pytest core/tests/ --cov=whitemagic --cov-report=term

# Specific test
PYTHONPATH=core pytest core/tests/unit/tools/test_contract.py -v

# Verify install
PYTHONPATH=core python -c "from whitemagic.tools.dispatch_table import DISPATCH_TABLE; print(f'{len(DISPATCH_TABLE)} tools registered')"
```

### Test Structure

```
tests/
├── unit/              # Fast, isolated unit tests
├── integration/       # Cross-subsystem tests
└── conftest.py        # Shared fixtures
```

**Current baseline**: ~750+ passed, ~190 failed (mostly Labs/experimental), 260 skipped

---

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add constellation detection to galactic map
fix: graceful fallback when Rust bridge unavailable
docs: update POLYGLOT_STATUS for Mojo 0.26
refactor: merge autonomous_execution into autonomous/executor
test: add 38 tests for v12.8 fusions
```

---

## Pull Request Guidelines

- One feature/fix per PR
- All tests must pass
- Update relevant docs (AI_PRIMARY.md, SYSTEM_MAP.md if architecture changes)
- Add tests for new functionality
- Reference related issues

---

## Project Structure (v22)

```
core/
├── whitemagic/
│   ├── tools/           # MCP tool system (canonical)
│   │   ├── dispatch_table.py      # Router merging 5 domain slices
│   │   ├── handlers/              # Tool handler implementations
│   │   ├── registry_defs/         # ToolDefinition declarations
│   │   └── unified_api.py         # Central call_tool() entry
│   ├── core/            # Memory, resonance, fusions
│   ├── memory/          # 5D holographic memory, galactic lifecycle
│   ├── dharma/          # Ethical governance, Karma ledger
│   ├── harmony/         # Harmony Vector, homeostatic loop
│   ├── security/        # 8-stage pipeline, governor
│   ├── cli/             # CLI commands
│   └── run_mcp.py       # MCP server entrypoint (canonical)
├── tests/
│   ├── unit/            # Fast unit tests
│   ├── integration/     # Cross-subsystem tests
│   ├── verify/          # P0 contract tests (must always pass)
│   └── conftest.py      # Temp state root, singleton reset
└── scripts/             # CI/verification scripts
polyglot/              # Accelerator bridges (Rust, Go, etc.)
docs/                  # Architecture, glossary, strategy
```

---

## Recognition

Contributors are recognized in release notes and the README.

## Code of Conduct

This project adheres to the [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

Thank you for contributing to WhiteMagic!
