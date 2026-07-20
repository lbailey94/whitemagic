"""CLI command: `wm init` — scaffold a new WhiteMagic project directory.

Creates the minimal files an AI agent (or human) needs to understand,
configure, and launch WhiteMagic from a fresh install.

Generated files:
    .mcp.json        — MCP client config (works with Windsurf, Claude Desktop, etc.)
    README.md        — AI-readable orientation and quickstart
    run.sh           — One-line launcher for MCP server (auto-activates venv)
    playground.py    — Interactive demo: capabilities, memory round-trip, gnosis
    .env             — Default environment configuration
    .gitignore       — Sensible defaults for a WM project
    data/            — Runtime data directory
    logs/            — Log output directory

With --from, also ingests existing files (e.g. an Obsidian vault) into a
galaxy during init — the single-command onboarding flow.
"""

from __future__ import annotations

import stat
from pathlib import Path

import click

# Template content — module-level strings, no indentation issues

_README = """\
# WhiteMagic Project

> **Version {version}** — Cognitive scaffolding for AI agents.

This directory was created by `wm init`. It contains everything you need
to start using WhiteMagic as an AI agent or human operator.

## What is WhiteMagic?

WhiteMagic is a **cognitive scaffolding layer** for AI agents. It provides:

- **28 Gana MCP meta-tools** as the stable public contract, backed by a broader internal tool surface
- **Persistent memory** with semantic search, embeddings, and galactic lifecycle
- **Ethical governance** via Dharma rules, Karma ledger, and Harmony Vector
- **Self-awareness** through Gnosis introspection, Self-Model forecasting, and Homeostasis
- **Multi-agent coordination** with task distribution, voting, and pipelines
- **7-language polyglot accelerators** (Rust, Zig, Julia, Haskell, Koka, Elixir, Go) — all free, no accounts needed

## Quick Start

### One-Command Onboarding (with existing notes)

```bash
# Scaffold + ingest your notes + verify + launch — all in one:
wm onboard --from ~/my-obsidian-vault --launch

# Or step by step:
wm init --from ~/my-obsidian-vault --galaxy knowledge
wm quickstart
./run.sh
```

### For AI Agents (MCP)

The fastest path — launch the MCP server and connect your client:

```bash
# PRAT mode: 28 Gana meta-tools (recommended for advanced agents)
./run.sh

# Or manually:
WM_MCP_PRAT=1 python -m whitemagic.run_mcp
```

Your first three MCP calls should be:
1. `gnosis` (compact=true) — system health snapshot
2. `capabilities` — discover available tools
3. `session_bootstrap` — initialize a working session

### For AI Agents (Python API)

```python
from whitemagic.tools.unified_api import call_tool

# Check system health
result = call_tool("gnosis", compact=True)

# Store a memory
call_tool("remember", content="Important finding", title="Research note", tags=["research"])

# Recall it later
results = call_tool("recall", query="important finding")
```

### For Humans

```bash
# System health check
wm doctor

# Interactive playground
python playground.py
```

## Your First 5 Minutes

### Step 1: Create a Memory

```bash
wm remember "I just installed WhiteMagic. This is my first memory." \
  --title "First Memory" --tags onboarding,first
```

### Step 2: Search for It

```bash
wm recall "first memory"
```

You should see the memory you just created. The system searched its database
and found your memory by content. This is **full-text search** — WhiteMagic
also supports semantic search and graph traversal once you have more memories.

### Step 3: See the Galactic Map

Every memory gets 5D holographic coordinates (x, y, z, w, v) that encode
its semantic position. Memories cluster in a "galaxy" with zones:

```
CORE → INNER_RIM → MID_BAND → OUTER_RIM → FAR_EDGE
```

New memories start in CORE (frequently accessed). Over time, if not
accessed, they drift outward. No memory is ever deleted — only rotated.

```bash
wm stats  # See your memory statistics
```

### Step 4: Explore the Dream Cycle

WhiteMagic has a 12-phase dream cycle inspired by biological sleep.
When the system is idle, it consolidates memories, finds serendipitous
connections, and tunes its own balance.

```bash
wm dream phases   # See all 12 phases
wm dream run      # Run a single dream phase now
wm dream report   # See what the system dreamed
```

### Step 5: Connect Your AI

Add the generated `.mcp.json` to your AI client (Claude Desktop, Cursor,
Windsurf, etc.) and your AI will have persistent memory across sessions.

Your AI can now:
- **Remember** what happened in previous conversations
- **Search** its memories by content, semantics, or associations
- **Dream** — consolidate and find connections during idle time
- **Govern itself** — ethical checks before destructive actions
- **Reflect** on its own state through introspection tools

## MCP Configuration

A ready-to-use `.mcp.json` was generated in this directory. To use it with your
MCP client (Windsurf, Claude Desktop, Cursor, etc.), copy or symlink it:

```bash
# Windsurf / Cursor — project-level config (already in place)
cat .mcp.json

# Claude Desktop — copy to global config
cp .mcp.json ~/.claude/mcp.json
```

Or add manually to any MCP client config:

```json
{{
  "mcpServers": {{
    "whitemagic": {{
      "command": "python",
      "args": ["-m", "whitemagic.run_mcp"],
      "env": {{
        "WM_MCP_PRAT": "1",
        "WM_SILENT_INIT": "1"
      }}
    }}
  }}
}}
```

## Server Modes

| Mode | Env Var | Tools | Best For |
|------|---------|-------|----------|
| **Seed** (default) | `WM_MCP_PRAT=2` or unset | 1 tool (`wm`) | Minimal token surface — recommended |
| **PRAT** | `WM_MCP_PRAT=1` | 29 tools (28 Ganas + `wm`) | When you need explicit Gana schemas |
| **Lite** | `WM_MCP_LITE=1` | ~92 core tools | Simple integrations |
| **Full** | `WM_MCP_PRAT=0` | Legacy broad-surface registration | Maximum capability |

> **The `wm` meta-tool ('world in a seed')** auto-routes natural language to any of the 490 underlying tools. In Seed mode, the entire WhiteMagic surface is collapsed into a single tool definition — the absolute minimum token cost. Use `wm(thought='help')` to discover all 28 Ganas and their tools.

## Starter Packs

New to WhiteMagic? Use starter packs to discover tools by workflow:

| Pack | Focus | Key Tools |
|------|-------|-----------|
| `quickstart` | First steps | gnosis, capabilities, session_bootstrap |
| `memory` | Knowledge management | remember, recall, consolidate |
| `introspection` | Health & debugging | harmony_vector, karma_report |
| `coordination` | Multi-agent work | agent.register, task.distribute |
| `reasoning` | Deep analysis | reasoning.bicameral, pattern_search |
| `safety` | Ethics & governance | evaluate_ethics, dharma_rules |

```python
from whitemagic.tools.unified_api import call_tool
call_tool("starter_packs.get", name="quickstart")
```

## Key Concepts

- **Ganas**: 28 lunar mansion-inspired tool clusters. Each groups related tools by domain.
- **Dharma**: Ethical rule engine. Evaluates actions before execution.
- **Karma Ledger**: Tracks declared vs actual side-effects. Auditable.
- **Harmony Vector**: 7-dimensional health metric (balance, throughput, latency, error_rate, dharma, karma_debt, energy).
- **Gnosis**: Unified introspection portal. One call to see everything.
- **Galactic Map**: Memory lifecycle — memories orbit from CORE to FAR_EDGE, never deleted.

## Environment Variables

See `.env` for all configurable options. Key ones:

| Variable | Default | Purpose |
|----------|---------|---------|
| `WM_STATE_ROOT` | `~/.whitemagic` | Where runtime data lives |
| `WM_MCP_PRAT` | `2` (Seed) | `2`=Seed (1 tool: `wm`), `1`=PRAT (29 tools), `0`=Full (630 tools) |
| `WM_SILENT_INIT` | `0` | Suppress startup logging |
| `WM_DB_PATH` | `$WM_STATE_ROOT/memory/whitemagic.db` | Database location |

## Documentation

- **AI Primary Spec**: `python -c "import whitemagic; help(whitemagic)"` or via MCP resource `whitemagic://orientation/ai-primary`
- **Full docs**: [github.com/lbailey94/whitemagic](https://github.com/lbailey94/whitemagic)

---
*Generated by `wm init` — WhiteMagic v{version}*
"""

_RUN_SH = """\
#!/usr/bin/env bash
# WhiteMagic MCP Server Launcher
# Usage: ./run.sh [--full|--lite|--prat]
#
# Modes:
#   --seed  (default) 1 tool (wm meta-tool) — minimal token surface, recommended
#   --prat  29 tools (28 Ganas + wm) — when you need explicit Gana schemas
#   --lite  ~92 core tools — simpler integration
#   --full  Legacy broad-surface registration — maximum capability

set -euo pipefail

# Auto-activate venv if not already active
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -z "${VIRTUAL_ENV:-}" ]; then
    if [ -f "$SCRIPT_DIR/venv/bin/activate" ]; then
        source "$SCRIPT_DIR/venv/bin/activate"
    elif [ -f "$SCRIPT_DIR/.venv/bin/activate" ]; then
        source "$SCRIPT_DIR/.venv/bin/activate"
    fi
fi

MODE="${1:---seed}"

case "$MODE" in
    --full)
        echo "Starting WhiteMagic MCP Server (full mode — legacy broad-surface registration)..."
        WM_MCP_PRAT=0 exec python -m whitemagic.run_mcp
        ;;
    --lite)
        echo "Starting WhiteMagic MCP Server (lite mode — ~92 tools)..."
        WM_MCP_LITE=1 exec python -m whitemagic.run_mcp
        ;;
    --prat)
        echo "Starting WhiteMagic MCP Server (PRAT mode — 29 tools: 28 Ganas + wm)..."
        WM_MCP_PRAT=1 exec python -m whitemagic.run_mcp
        ;;
    --seed|*)
        echo "Starting WhiteMagic MCP Server (seed mode — 1 tool: wm)..."
        WM_MCP_PRAT=2 exec python -m whitemagic.run_mcp
        ;;
esac
"""

_PLAYGROUND_VERSION_PLACEHOLDER = "__WM_VERSION__"

_PLAYGROUND = r'''#!/usr/bin/env python3
"""
WhiteMagic Playground — Interactive demo for new agents and humans.

Run:  python playground.py

This script walks through WhiteMagic's core capabilities:
  1. System health check (Gnosis)
  2. Capability discovery
  3. Memory round-trip (store -> search -> read)
  4. Ethical evaluation (Dharma)
  5. Harmony Vector health pulse

WhiteMagic v__WM_VERSION__
"""
import os
import sys

from whitemagic.utils.fast_json import dumps_str as _json_dumps

# Quiet startup
os.environ.setdefault("WM_SILENT_INIT", "1")

try:
    from whitemagic.tools.unified_api import call_tool
except ImportError:
    print("Error: whitemagic is not installed.")
    print("Install it:  pip install whitemagic")
    sys.exit(1)

try:
    from whitemagic import __version__
except (ImportError, ModuleNotFoundError):
    __version__ = "unknown"


def section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def pretty(data: dict) -> str:
    return _json_dumps(data, indent=2, default=str)[:2000]


def main() -> None:
    print(f"WhiteMagic Playground v{__version__}")
    print("This demo walks through core capabilities.\n")

    # 1. Gnosis — System Health
    section("1. Gnosis — System Health Snapshot")
    result = call_tool("gnosis", compact=True)
    if result.get("status") == "success":
        gnosis = result.get("details", {}).get("gnosis", result.get("details", {}))
        print(f"  Status: {gnosis.get('status', 'unknown')}")
        print(f"  Maturity: {gnosis.get('maturity_stage', 'unknown')}")
        alerts = gnosis.get("alerts", [])
        if alerts:
            print(f"  Alerts ({len(alerts)}):")
            for a in alerts[:
                5]:
                print(f"    - {a}")
        else:
            print("  No alerts — all clear.")
        actions = gnosis.get("next_actions", [])
        if actions:
            act = actions[0]
            if isinstance(act, dict):
                print(f"  Suggested: {act.get('tool', act)} — {act.get('reason', '')}")
            else:
                print(f"  Suggested: {act}")
    else:
        print(f"  Result: {pretty(result)}")

    # 2. Capabilities — Tool Discovery
    section("2. Capabilities — What Can I Do?")
    result = call_tool("capabilities")
    if result.get("status") == "success":
        details = result.get("details", {})
        print(f"  Version: {details.get('version', 'unknown')}")
        tools = details.get("tools", [])
        if isinstance(tools, dict):
            tools = list(tools.values())
        print(f"  Available tools: {len(tools)}")
        categories = {}
        for t_info in tools[:
            300]:
            if isinstance(t_info, dict):
                cat = t_info.get("category", "unknown")
            elif isinstance(t_info, str):
                cat = "unknown"
            else:
                continue
            categories[cat] = categories.get(cat, 0) + 1
        if categories:
            print("  By category:")
            for cat, count in sorted(categories.items(), key=lambda x:
                -x[1])[:8]:
                print(f"    {cat}: {count} tools")
    else:
        print(f"  Result: {pretty(result)}")

    # 3. Memory Round-Trip
    section("3. Memory — Store & Recall")
    print("  Storing a test memory...")
    store_result = call_tool(
        "remember",
        content="WhiteMagic playground test: the answer to everything is 42.",
        title="Playground Test Memory",
        tags=["test", "playground"],
    )
    if store_result.get("status") == "success":
        memory_id = store_result.get("details", {}).get("memory_id", "unknown")
        print(f"  Stored (ID: {memory_id})")
    else:
        print(f"  Store result: {store_result.get('status')}")

    print("  Searching for it...")
    search_result = call_tool("recall", query="answer to everything")
    if search_result.get("status") == "success":
        results = search_result.get("results", [])
        if results:
            print(f"  Found {len(results)} result(s):")
            top = results[0]
            print(f"    Top match: {top.get('content', '')[:100]}")
        else:
            print("  No results (embedding index may need a moment).")
    else:
        print(f"  Search result: {search_result.get('status')}")

    # 4. Dharma — Ethical Evaluation
    section("4. Dharma — Ethical Evaluation")
    result = call_tool("evaluate_ethics", action="Read a file from disk")
    if result.get("status") == "success":
        details = result.get("details", {})
        score = details.get("ethical_score", "unknown")
        concerns = details.get("concerns", [])
        print("  Action: 'Read a file from disk'")
        print(f"  Ethical score: {score}")
        if concerns:
            for c in concerns[:
                3]:
                print(f"  Concern: {c}")
        else:
            print("  No ethical concerns raised.")
    else:
        print(f"  Result: {pretty(result)}")

    # 5. Harmony Vector
    section("5. Harmony Vector — 7D Health Pulse")
    result = call_tool("harmony_vector")
    if result.get("status") == "success":
        hv = result.get("details", {}).get("harmony_vector", result.get("details", {}))
        core_dims = ["balance", "throughput", "latency", "error_rate", "dharma", "karma_debt", "energy"]
        for dim in core_dims:
            val = hv.get(dim)
            if val is not None:
                try:
                    fval = float(val)
                    bar = "#" * int(fval * 20)
                    print(f"  {dim:>15}: {fval:.2f} {bar}")
                except (TypeError, ValueError):
                    print(f"  {dim:>15}: {val}")
        score = hv.get("harmony_score")
        if score is not None:
            print(f"\n  Overall harmony: {float(score):.2f}")
    else:
        print(f"  Result: {pretty(result)}")

    # Done
    section("Done!")
    print("  WhiteMagic is ready. Next steps:")
    print("  - Launch MCP server:  ./run.sh")
    print("  - Check health:       wm doctor")
    print("  - Explore tools:      call_tool('starter_packs.list')")
    print()


if __name__ == "__main__":
    main()
'''

_ENV = """\
# WhiteMagic Environment Configuration
# =====================================
# Copy to .env and customize. All values shown are defaults.

# Where WhiteMagic stores runtime data (DB, sessions, cache, logs)
# Set to ./.whitemagic for project-local state (recommended for isolated installs)
WM_STATE_ROOT=./.whitemagic

# Database path (defaults to $WM_STATE_ROOT/memory/whitemagic.db)
# WM_DB_PATH=

# MCP Server Mode (set ONE of these)
# WM_MCP_PRAT=2       # Seed mode — 1 tool (wm meta-tool) — DEFAULT, minimal token surface
# WM_MCP_PRAT=1       # PRAT mode — 29 tools (28 Ganas + wm)
# WM_MCP_PRAT=0       # Full mode — 490 dispatch tools (legacy broad-surface)
# WM_MCP_LITE=1       # ~92 core tools

# MCP Client Adapter (adjusts schema for specific AI clients)
# WM_MCP_CLIENT=gemini   # Options: gemini, deepseek, qwen, kimi

# Suppress startup banners and logging (good for MCP stdio mode)
# WM_SILENT_INIT=1

# Dharma profile (ethical governance strictness)
# WM_DHARMA_PROFILE=default   # Options: default, creative, secure, violet

# llama-server endpoint for local LLM inference
# WM_LLAMA_HOST=localhost
# WM_LLAMA_PORT=8080

# XRP receive address for gratitude tips (opt-in)
# Leave blank to disable tipping feature:
# WM_XRP_ADDRESS=
# Set your own address to receive tips for your deployment:
"""

_GITIGNORE = """\
# WhiteMagic project .gitignore
__pycache__/
*.pyc
.env
venv/
.venv/
*.db
*.db-journal
*.db-wal
logs/
tmp/
.whitemagic/
"""

_MCP_JSON = """\
{
  "mcpServers": {
    "whitemagic": {
      "command": "python",
      "args": ["-m", "whitemagic.run_mcp"],
      "env": {
        "WM_MCP_PRAT": "1",
        "WM_SILENT_INIT": "1",
        "WM_STATE_ROOT": "./.whitemagic"
      }
    }
  }
}
"""


# CLI command


@click.command(name="init")
@click.argument("directory", default=".", type=click.Path())
@click.option("--force", "-f", is_flag=True, help="Overwrite existing files")
@click.option("--minimal", "-m", is_flag=True, help="Only create README.md and run.sh")
@click.option(
    "--non-interactive",
    "-y",
    is_flag=True,
    help="Skip all prompts, use defaults (for AI agents and CI)",
)
@click.option(
    "--from",
    "from_path",
    default=None,
    type=click.Path(exists=True),
    help="Ingest files from this directory into a galaxy during init (e.g. Obsidian vault)",
)
@click.option(
    "--galaxy",
    "galaxy_name",
    default="knowledge",
    help="Name for the galaxy to ingest files into (default: knowledge)",
)
@click.option(
    "--pattern",
    "file_pattern",
    default="**/*.md",
    help="Glob pattern for files to ingest (default: **/*.md)",
)
@click.option(
    "--launch",
    is_flag=True,
    help="Start the MCP server after setup (blocks until interrupted)",
)
@click.option(
    "--quickstart/--no-quickstart",
    default=True,
    help="Run quickstart verification after init (default: on)",
)
def init_command(
    directory: str,
    force: bool,
    minimal: bool,
    non_interactive: bool,
    from_path: str | None,
    galaxy_name: str,
    file_pattern: str,
    launch: bool,
    quickstart: bool,
) -> None:
    """Initialize a new WhiteMagic project directory.

    Scaffolds the essential files an AI agent needs to understand, configure,
    and launch WhiteMagic. Run this after `pip install whitemagic`.

    With --from, also ingests existing files into a galaxy — the single-command
    onboarding flow for humans and AI agents alike.

    \b
    Examples:
        wm init                          # Initialize current directory
        wm init my-project               # Create and initialize my-project/
        wm init . --from ~/obsidian-vault  # Scaffold + ingest your notes
        wm init . --from ./docs --galaxy research  # Ingest into 'research' galaxy
        wm init . --from ~/vault --launch  # Scaffold + ingest + start MCP server
        wm init . --non-interactive       # No prompts, use defaults (AI agents)
        wm init . --no-quickstart         # Skip verification step
    """
    try:
        from whitemagic import __version__
    except (ImportError, ModuleNotFoundError):
        __version__ = "unknown"

    target = Path(directory).resolve()
    target.mkdir(parents=True, exist_ok=True)

    files: dict[str, str] = {
        ".mcp.json": _MCP_JSON,
        "README.md": _README.format(version=__version__),
        "run.sh": _RUN_SH,
    }

    if not minimal:
        files["playground.py"] = _PLAYGROUND.replace(
            _PLAYGROUND_VERSION_PLACEHOLDER, __version__
        )
        files[".env"] = _ENV
        files[".gitignore"] = _GITIGNORE

    created = []
    skipped = []

    for filename, content in files.items():
        filepath = target / filename
        if filepath.exists() and not force:
            skipped.append(filename)
            continue

        filepath.write_text(content, encoding="utf-8")
        created.append(filename)

        # Make .sh and .py files executable
        if filename.endswith(".sh") or filename.endswith(".py"):
            filepath.chmod(
                filepath.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH
            )

    # Create runtime directories
    for dirname in ("data", "logs", "tmp"):
        (target / dirname).mkdir(exist_ok=True)

    click.echo(f"\n  WhiteMagic v{__version__} — Project initialized at {target}\n")

    if created:
        click.echo("  Created:")
        for f in created:
            click.echo(f"    + {f}")

    if skipped:
        click.echo("\n  Skipped (already exist, use --force to overwrite):")
        for f in skipped:
            click.echo(f"    ~ {f}")

    # ── Ingest files from --from path ──────────────────────────────────
    ingest_result: dict | None = None
    if from_path:
        click.echo(f"\n  Ingesting files from {from_path} into galaxy '{galaxy_name}'...")
        try:
            import os as _os

            resolved_from = str(Path(from_path).resolve())
            existing_allowed = _os.environ.get("WHITEMAGIC_ALLOWED_PATHS", "")
            if resolved_from not in existing_allowed:
                _os.environ["WHITEMAGIC_ALLOWED_PATHS"] = (
                    f"{existing_allowed}:{resolved_from}" if existing_allowed else resolved_from
                )

            from whitemagic.security.tool_gating import get_tool_gate

            gate = get_tool_gate()
            gate.path_validator.allowed_bases.add(Path(resolved_from))

            from whitemagic.core.memory.galaxy_manager import get_galaxy_manager

            gm = get_galaxy_manager()
            existing = gm.list_galaxies()
            if not any(g.get("name") == galaxy_name for g in existing):
                gm.create_galaxy(galaxy_name)
                click.echo(f"    + Galaxy '{galaxy_name}' created")

            result = gm.ingest_files(
                galaxy_name=galaxy_name,
                source_path=from_path,
                pattern=file_pattern,
                max_files=2000,
                tags=["onboarding"],
            )
            ingest_result = result
            ingested = result.get("ingested", 0)
            found = result.get("files_found", 0)
            errors = result.get("errors", 0)
            skipped_files = result.get("skipped", 0)
            click.echo(
                f"    ✅ Ingested {ingested}/{found} files "
                f"({skipped_files} skipped, {errors} errors)"
            )
        except Exception as e:  # noqa: BLE001
            click.echo(f"    ❌ Ingest failed: {e}")
            if non_interactive:
                click.echo("       Continuing with setup (use 'wm galaxy ingest' to retry)")

    # ── Run quickstart verification ────────────────────────────────────
    if quickstart:
        click.echo("\n  Running quickstart verification...")
        try:
            from whitemagic.tools.unified_api import call_tool

            steps_ok = 0
            steps_fail = 0

            # Health
            health = call_tool("health_report")
            if health.get("status") == "success":
                details = health.get("details", {})
                runtime = details.get("runtime", {})
                ver = runtime.get("version", "?")
                tools = runtime.get("surface_counts", {}).get("callable_tools", "?")
                click.echo(f"    ✅ Health: v{ver}, {tools} tools")
                steps_ok += 1
            else:
                click.echo("    ❌ Health check failed")
                steps_fail += 1

            # Memory round-trip
            mem = call_tool(
                "create_memory",
                title="Init Memory",
                content="WhiteMagic init completed successfully.",
                tags=["init", "onboarding"],
            )
            if mem.get("status") == "success":
                click.echo("    ✅ Memory: store works")
                steps_ok += 1
            else:
                click.echo("    ❌ Memory store failed")
                steps_fail += 1

            # Search
            search = call_tool("search_memories", query="init", limit=3)
            if search.get("status") == "success":
                count = search.get("details", {}).get("count", 0)
                click.echo(f"    ✅ Search: {count} results for 'init'")
                steps_ok += 1
            else:
                click.echo("    ❌ Search failed")
                steps_fail += 1

            if steps_fail == 0:
                click.echo(f"\n  ✅ Quickstart passed — all {steps_ok} checks passed.")
            else:
                click.echo(f"\n  ⚠️  Quickstart: {steps_ok} passed, {steps_fail} failed.")
                click.echo("     Run 'wm doctor' for diagnostics.")
        except Exception as e:  # noqa: BLE001
            click.echo(f"    ⚠️  Quickstart skipped: {e}")

    # ── Print next steps ───────────────────────────────────────────────
    click.echo("\n  ── Next steps ──")
    click.echo()
    click.echo("  For humans:")
    click.echo("    python playground.py          # Interactive demo")
    click.echo("    wm doctor                     # System health check")
    click.echo("    wm recall 'init'              # Search your memories")
    if ingest_result:
        click.echo("    wm recall 'knowledge'           # Search ingested notes")
    click.echo()
    click.echo("  For AI agents:")
    click.echo("    ./run.sh                      # Launch MCP server")
    click.echo("    # Then connect via MCP client (Claude Desktop, Cursor, etc.)")
    click.echo("    # First calls: gnosis → capabilities → session_bootstrap")
    click.echo()
    click.echo("  Connect your AI:")
    click.echo("    # .mcp.json is ready in this directory")
    click.echo("    # Claude Desktop: cp .mcp.json ~/.claude/mcp.json")
    click.echo("    # Cursor/Windsurf: already in project config")
    click.echo()

    # ── Launch MCP server ──────────────────────────────────────────────
    if launch:
        click.echo("  ── Launching MCP server ──\n")
        click.echo("  Press Ctrl+C to stop.\n")
        import os
        import sys

        env = os.environ.copy()
        env["WM_MCP_PRAT"] = env.get("WM_MCP_PRAT", "1")
        env["WM_SILENT_INIT"] = "1"
        env["WM_STATE_ROOT"] = str(target / ".whitemagic")

        run_sh = target / "run.sh"
        if run_sh.exists():
            os.execvpe(str(run_sh), [str(run_sh)], env)
        else:
            os.execvpe(
                sys.executable,
                [sys.executable, "-m", "whitemagic.run_mcp"],
                env,
            )

    if non_interactive:
        click.echo("  ✅ Ready.\n")
    else:
        click.echo()


@click.command(name="onboard")
@click.argument("directory", default=".", type=click.Path())
@click.option(
    "--from",
    "from_path",
    default=None,
    type=click.Path(exists=True),
    help="Ingest files from this directory (e.g. Obsidian vault path)",
)
@click.option(
    "--galaxy",
    "galaxy_name",
    default="knowledge",
    help="Galaxy name for ingested files (default: knowledge)",
)
@click.option(
    "--pattern",
    "file_pattern",
    default="**/*.md",
    help="Glob pattern for files to ingest (default: **/*.md)",
)
@click.option(
    "--launch",
    is_flag=True,
    help="Start the MCP server after onboarding (blocks until interrupted)",
)
@click.option(
    "--non-interactive",
    "-y",
    is_flag=True,
    help="Skip all prompts, use defaults (for AI agents and CI)",
)
def onboard_command(
    directory: str,
    from_path: str | None,
    galaxy_name: str,
    file_pattern: str,
    launch: bool,
    non_interactive: bool,
) -> None:
    """One-command onboarding: init + ingest + quickstart + (optional) launch.

    The fastest path from zero to a working WhiteMagic deployment.

    \b
    Examples:
        wm onboard --from ~/my-obsidian-vault    # Ingest your notes + verify
        wm onboard --from ~/vault --launch       # Ingest + start MCP server
        wm onboard --from ./docs --galaxy research  # Ingest into 'research' galaxy
        wm onboard                                # Fresh start, no existing notes
    """
    ctx = click.get_current_context()
    ctx.invoke(
        init_command,
        directory=directory,
        force=False,
        minimal=False,
        non_interactive=non_interactive,
        from_path=from_path,
        galaxy_name=galaxy_name,
        file_pattern=file_pattern,
        launch=launch,
        quickstart=True,
    )


def register(main: click.Group) -> None:
    """Register the init and onboard commands with the main CLI group."""
    main.add_command(init_command)
    main.add_command(onboard_command)
