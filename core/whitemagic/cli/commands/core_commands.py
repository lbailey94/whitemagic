# ruff: noqa: BLE001
import logging
from importlib.util import find_spec
from pathlib import Path

import click

from whitemagic.utils.fast_json import dumps_str as _json_dumps

logger = logging.getLogger(__name__)

try:
    from rich.console import Console
    from rich.tree import Tree

    HAS_RICH = True
    console = Console()
except ImportError:
    HAS_RICH = False
    console = None  # type: ignore[assignment]

try:
    from whitemagic import __version__
except ImportError:
    __version__ = "unknown"

__all__ = [
    "explore_command",
    "init_command",
    "quickstart_command",
    "rules_command",
    "systemmap_command",
    "start_session_cli",
    "tutorial_command",
    "list_tools",
    "setup",
    "tools",
]
HAS_CORE = find_spec("whitemagic.core") is not None
HAS_VOICE = False
HAS_GRAPH = False
HAS_EXEC = False
try:
    from whitemagic.cli.cli_sangha import sangha_cli  # noqa: F401

    HAS_SANGHA = True
except ImportError:
    HAS_SANGHA = False


def get_memory():
    """
    Get the memory.
    """
    from whitemagic.core.memory.unified import get_unified_memory

    return get_unified_memory()


@click.command(name="explore")
def explore_command() -> None:
    """Interactive guide to WhiteMagic features"""
    if HAS_RICH and console:
        console.print("\n[bold cyan]🧭 WhiteMagic Explorer[/bold cyan]\n")

        tree = Tree(f"🪄 WhiteMagic v{__version__}")

        gana_branch = tree.add("[cyan]🌙 28 Lunar Mansion Ganas[/cyan]")
        gana_branch.add("wm gana list - View all Ganas by quadrant")
        gana_branch.add("wm gana invoke <tool> - Invoke tool through Gana")
        gana_branch.add("wm gana status - System status")

        dharma_branch = tree.add("[yellow]☸️  Dharma Ethical System[/yellow]")
        dharma_branch.add("wm dharma evaluate <action> - Check ethics")
        dharma_branch.add("wm dharma principles - List principles")
        dharma_branch.add("wm dharma check-boundaries <action> - Check boundaries")

        ml_branch = tree.add("[green]🤖 Local ML Inference[/green]")
        ml_branch.add("wm infer local-query <prompt> - Run local inference")
        ml_branch.add("wm infer local-status - Engine status")

        wisdom_branch = tree.add("[magenta]🧙 Wisdom Systems[/magenta]")
        wisdom_branch.add("wm wisdom consult <question> - Ask wisdom council")
        wisdom_branch.add("wm wisdom iching <question> - Ask I Ching")

        system_branch = tree.add("[blue]🔧 System Commands[/blue]")
        system_branch.add("wm status - Overall status")
        system_branch.add("wm health - Health check")
        system_branch.add("wm start-session - Start session orchestrator")

        console.print(tree)
        console.print("\n[dim]Use --help on any command for more details[/dim]\n")
    else:
        click.echo(
            "WhiteMagic Explorer - Interactive guide (Rich required for full experience)"
        )


@click.command(name="init")
@click.option("--galaxy", default="default", help="Name for the default galaxy")
@click.option("--skip-seed", is_flag=True, help="Skip seeding quickstart memories")
@click.option("--skip-llama", is_flag=True, help="Skip llama-server detection")
@click.pass_context
def init_command(ctx, galaxy: str, skip_seed: bool, skip_llama: bool) -> None:
    """🧙 First-time setup wizard for WhiteMagic.

    Creates state directory, seeds quickstart memories, detects llama-server,
    and runs a health check.
    """

    from whitemagic.config import paths as cfg_paths

    _echo = click.echo

    def _ok(msg: str) -> None:
        _echo(f"  ✅ {msg}")

    def _skip(msg: str) -> None:
        _echo(f"  ⏭️  {msg}")

    def _fail(msg: str) -> None:
        _echo(f"  ❌ {msg}")

    _echo(f"\n🧙 WhiteMagic Init Wizard (v{__version__})\n")

    _echo("Step 1/5: State directory")
    state_root = cfg_paths.get_state_root()  # type: ignore[attr-defined]
    state_root.mkdir(parents=True, exist_ok=True)
    _ok(f"WM_STATE_ROOT = {state_root}")

    _echo("Step 2/5: Default galaxy")
    try:
        from whitemagic.core.memory.galaxy_manager import get_galaxy_manager

        gm = get_galaxy_manager()
        existing = gm.list_galaxies()
        if any(g.get("name") == galaxy for g in existing):
            _ok(f"Galaxy '{galaxy}' already exists")
        else:
            gm.create_galaxy(galaxy)
            _ok(f"Galaxy '{galaxy}' created")
    except Exception as e:
        _fail(f"Galaxy setup: {e}")

    _echo("Step 3/5: Quickstart memories")
    if skip_seed:
        _skip("Skipped (--skip-seed)")
    else:
        try:
            from whitemagic.core.memory.unified import get_unified_memory

            um = get_unified_memory()
            existing_count = len(um.search(tags={"quickstart"}, limit=1))
            if existing_count > 0:
                _ok("Quickstart memories already present")
            else:
                import subprocess
                import sys

                seed_script = (
                    Path(__file__).resolve().parent.parent.parent
                    / "scripts"
                    / "seed_quickstart_memories.py"
                )
                if seed_script.exists():
                    subprocess.run(
                        [sys.executable, str(seed_script)],
                        check=True,
                        capture_output=True,
                    )
                    _ok("Quickstart memories seeded")
                else:
                    _skip("Seed script not found (run from git checkout)")
        except Exception as e:
            _fail(f"Seed: {e}")

    _echo("Step 4/5: llama-server detection")
    if skip_llama:
        _skip("Skipped (--skip-llama-cpp)")
    else:
        try:
            from whitemagic.inference.llama_cpp import BinaryManager
            llama_bin = BinaryManager.find_binary()
            if llama_bin:
                _ok(f"llama-server found: {llama_bin}")
            else:
                _skip("llama-server not found (optional — build from llama.cpp)")
        except Exception:
            _skip("llama-server not found (optional — build from llama.cpp)")


    _echo("Step 5/5: Health check")
    try:
        from whitemagic.tools.dispatch_table import dispatch

        raw = dispatch("health_report") or {}
        health: dict = raw if isinstance(raw, dict) else {}
        score = health.get("health_score", 0)
        status = health.get("health_status", "unknown")
        tool_count = health.get("tool_count", "?")
        _ok(f"Health: {status} ({score:.0%}) | {tool_count} tools")
    except Exception as e:
        _fail(f"Health check: {e}")

    _echo("\n🎉 WhiteMagic is ready! Try:\n")
    _echo("  wm status          # system overview")
    _echo("  wm doctor          # detailed diagnostics")
    _echo("  wm gana invoke gnosis '{\"compact\": true}'  # introspection")
    _echo("")


@click.command(name="rules")
def rules_command() -> None:
    """☸️  Show active Dharma rules (alias for `wm dharma principles`)"""
    from whitemagic.tools.unified_api import call_tool

    try:
        result = call_tool("dharma_rules")
        rules = result.get("details", {}).get(
            "rules", result.get("rules", result.get("principles", []))
        )
        if isinstance(rules, list):
            for r in rules[:20]:
                if isinstance(r, dict):
                    click.echo(
                        f"  {r.get('name', '?')}: {r.get('level', '?')} (weight: {r.get('weight', '?')})"
                    )
                else:
                    click.echo(f"  {r}")
        else:
            click.echo(_json_dumps(result, indent=2, default=str)[:2000])
    except Exception as e:
        click.echo(f"❌ {e}")


@click.command(name="systemmap")
def systemmap_command() -> None:
    """🗺️  Display the system map overview"""
    try:
        from whitemagic.config.paths import get_project_root

        sm = get_project_root().parent / "docs" / "misc" / "SYSTEM_MAP.md"
        if sm.exists():
            text = sm.read_text()
            click.echo(text[:3000])
        else:
            click.echo("System map not found. Try: wm status")
    except Exception as e:
        click.echo(f"❌ {e}")


@click.command(name="start-session")
@click.option("--quiet", is_flag=True, help="Suppress verbose startup output")
def start_session_cli(quiet: bool):
    """Start a WhiteMagic session orchestrator run"""
    try:
        from whitemagic.core.orchestration.session_startup import start_session

        result = start_session(verbose=not quiet)
        click.echo(f"✅ Session start: {result.get('status', 'unknown')}")
        click.echo(
            f"   Activated: {result.get('activated', 0)} | Failed: {result.get('failed', 0)}"
        )
    except Exception as exc:
        click.echo(f"❌ Session start failed: {exc}")


@click.command()
def list_tools() -> None:
    """Alias for tools - list all available commands"""
    # Forward to tools command
    ctx = click.get_current_context()
    ctx.invoke(tools)


@click.command()
def setup() -> None:
    """Interactive setup wizard"""
    click.echo("\n🚀 WhiteMagic Setup Wizard")
    click.echo("=" * 40)

    from whitemagic.config.paths import WM_ROOT, ensure_paths

    config_dir = WM_ROOT
    if config_dir.exists():
        click.echo(f"✅ WhiteMagic already configured at: {config_dir}")
        if click.confirm("Would you like to reconfigure?"):
            pass
        else:
            return

    # Create directories
    click.echo("\n📁 Creating directories...")
    ensure_paths()
    # Extra legacy/utility dirs (best-effort; keep runtime state together)
    for d in ["backups"]:
        (config_dir / d).mkdir(parents=True, exist_ok=True)
    click.echo(f"   ✅ {config_dir}")

    if HAS_CORE:
        click.echo("\n🧠 Initializing memory system...")
        memory = get_memory()
        click.echo(f"   ✅ {memory.get_stats()['total_memories']} memories found")

    # MCP readiness (stdio)
    click.echo("\n🔌 MCP readiness...")
    if find_spec("fastmcp") is not None:
        click.echo("   ✅ fastmcp installed")
    else:
        click.echo("   ⚠️  fastmcp not installed (MCP server won't run)")
        click.echo("      Install: pip install 'whitemagic[mcp]'")

    mcp_entry = Path(__file__).resolve().parent.parent / "run_mcp.py"
    if mcp_entry.exists():
        rel = str(mcp_entry)
        try:
            rel = str(mcp_entry.relative_to(Path.cwd()))
        except ValueError:
            logger.debug("Swallowed exception", exc_info=True)
        click.echo(f"   ✅ MCP entrypoint present: {rel}")
    else:
        click.echo("   ⚠️  MCP entrypoint missing: whitemagic/run_mcp.py")

    click.echo("\n✨ Setup complete!")
    click.echo("\nNext steps:")
    click.echo("  1. Run: wm status")
    click.echo("  2. Try: wm remember 'my first memory' --title 'Hello'")
    click.echo("  3. Use: wm recall 'first'")
    click.echo("  4. MCP: python -m whitemagic.run_mcp")


@click.command()
@click.option("--json", "json_output", is_flag=True, help="Emit tools list as JSON.")
@click.pass_context
def tools(ctx, json_output: bool) -> None:
    """List all available tools and commands"""
    global_json = (
        bool((ctx.obj or {}).get("json_output")) if isinstance(ctx.obj, dict) else False
    )
    emit_json = json_output or global_json

    commands = [
        ("remember", "Create a new memory"),
        ("recall", "Search memories"),
        ("search", "Alias for recall"),
        ("context", "Generate AI context"),
        ("status", "Show system status"),
        ("setup", "Run setup wizard"),
        ("consolidate", "Archive old memories"),
        ("stats", "Show memory statistics"),
        ("health", "Check system health"),
        ("doctor", "Install + ship hygiene check (AI-first)"),
        ("doctor-deep", "Legacy deep audit (unstable)"),
        ("start-session", "Start session orchestrator"),
        ("explore", "Interactive feature guide"),
        ("fast", "Fast-mode CLI passthrough"),
    ]

    garden_commands = [
        ("voice", "Voice and narrative tools"),
        ("gana", "28 Lunar Mansion Gana system"),
        ("dharma", "Ethical reasoning tools"),
        ("wisdom", "Wisdom council and I Ching"),
        ("infer", "Inference tools (local + unified)"),
    ]
    if HAS_SANGHA:
        garden_commands.append(("sangha", "Multi-agent coordination"))

    optional_commands = []
    if HAS_EXEC:
        optional_commands.append(("exec", "Execute terminal commands"))
    if HAS_GRAPH:
        optional_commands.extend(
            [
                ("graph", "Visualize memory relationships"),
                ("graph-stats", "Show relationship statistics"),
            ]
        )

    if emit_json:
        click.echo(
            _json_dumps(
                {
                    "core_commands": [
                        {"command": c, "description": d} for c, d in commands
                    ],
                    "garden_commands": [
                        {"command": c, "description": d} for c, d in garden_commands
                    ],
                    "optional_commands": [
                        {"command": c, "description": d} for c, d in optional_commands
                    ],
                    "usage": "whitemagic <command> --help",
                },
                indent=2,
                sort_keys=True,
            )
        )
        return

    click.echo("\n🛠️  WhiteMagic Tools")
    click.echo("=" * 40)

    click.echo("\nCore Commands:")
    for cmd, desc in commands:
        click.echo(f"  {cmd:<12} - {desc}")

    click.echo("\nGarden Commands:")
    for cmd, desc in garden_commands:
        click.echo(f"  {cmd:<12} - {desc}")

    for cmd, desc in optional_commands:
        click.echo(f"  {cmd:<12} - {desc}")


@click.command(name="quickstart")
@click.option("--json", "json_output", is_flag=True, help="Output results as JSON")
@click.pass_context
def quickstart_command(ctx, json_output: bool) -> None:
    """Run a full demo loop: health check, tutorial search, gnosis.

    Proves the system works end-to-end in under 30 seconds.
    Searches the pre-seeded tutorial galaxy to show real content.
    """
    from whitemagic.tools.unified_api import call_tool

    steps = []

    # Step 1: Health report
    health = call_tool("health_report")
    steps.append({"step": "health", "status": health.get("status", "error")})
    if not json_output:
        ver = health.get("details", {}).get("runtime", {}).get("version", "?")
        tools = health.get("details", {}).get("runtime", {}).get("surface_counts", {}).get("callable_tools", "?")
        click.echo(f"\n  1. Health: v{ver}, {tools} tools — {health.get('status')}\n")

    # Step 2: Search the tutorial galaxy (proves memory system works + shows useful content)
    from whitemagic.core.memory.tutorial_refresh import (
        auto_seed_if_needed,
        is_tutorial_seeded,
    )

    if not is_tutorial_seeded():
        auto_seed_if_needed()

    search = call_tool("search_memories", query="quickstart", galaxy="tutorial", limit=3)
    steps.append({"step": "search_tutorial", "status": search.get("status", "error")})
    if not json_output:
        hits = search.get("details", {}).get("memories", search.get("details", {}).get("results", []))
        count = search.get("details", {}).get("count", len(hits))
        click.echo(f"  2. Tutorial search: {count} results — {search.get('status')}")
        if hits:
            top = hits[0]
            title = top.get("title", "?")
            click.echo(f"     → '{title}'\n")
        else:
            click.echo("     (Tutorial galaxy empty — run 'wm init' to seed)\n")

    # Step 3: Gnosis (self-awareness snapshot)
    gnosis = call_tool("gnosis", compact=True)
    steps.append({"step": "gnosis", "status": gnosis.get("status", "error")})
    if not json_output:
        click.echo(f"  3. Gnosis: {gnosis.get('status')}\n")

    if json_output:
        click.echo(_json_dumps({"steps": steps, "version": __version__}))
    else:
        all_ok = all(s["status"] == "success" for s in steps)
        if all_ok:
            click.echo("  ✅ Quickstart complete — all systems operational.\n")
            click.echo("  Next steps:")
            click.echo("    • wm tutorial                 # guided tour of WhiteMagic")
            click.echo("    • wm recall \"galaxy\"         # search your memories")
            click.echo("    • wm status                   # system status")
            click.echo("    • wm sleep                    # run dream cycle")
            click.echo("    • python -m whitemagic.run_mcp_lean  # start MCP server\n")
        else:
            failed = [s["step"] for s in steps if s["status"] != "success"]
            click.echo(f"  ❌ Quickstart failed at: {', '.join(failed)}\n")
            click.echo("  Run 'wm doctor' for diagnostics.\n")


@click.command(name="tutorial")
@click.argument("topic", required=False, default="")
@click.pass_context
def tutorial_command(ctx, topic: str) -> None:
    """Guided tour of WhiteMagic from the tutorial galaxy."""
    from whitemagic.core.memory.tutorial_refresh import (
        auto_seed_if_needed,
        is_tutorial_seeded,
    )

    if not is_tutorial_seeded():
        click.echo("\n  Seeding tutorial galaxy...\n")
        auto_seed_if_needed()

    from whitemagic.tools.unified_api import call_tool

    if not topic:
        result = call_tool("search_memories", query="tutorial", galaxy="tutorial", limit=20)
    else:
        result = call_tool("search_memories", query=topic, galaxy="tutorial", limit=5)

    if result.get("status") != "success":
        click.echo(f"  Tutorial search failed: {result.get('message', 'unknown error')}")
        return

    hits = result.get("details", {}).get("memories", result.get("details", {}).get("results", []))
    if not hits:
        click.echo(f"\n  No tutorials found for '{topic}'. Try: memory, governance, dream, modes, cli\n")
        return

    click.echo("\n  WhiteMagic Tutorial\n")
    for hit in hits:
        title = hit.get("title", "?")
        content = hit.get("content", hit.get("preview", ""))
        if isinstance(content, str) and len(content) > 500:
            content = content[:500] + "..."
        click.echo(f"  [{title}]")
        click.echo(f"  {content}\n")
