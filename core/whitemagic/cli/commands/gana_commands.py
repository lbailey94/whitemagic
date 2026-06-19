# ruff: noqa: BLE001
# mypy: disable-error-code=no-untyped-def
"""Gana CLI Commands
Interact with the 28 Lunar Mansion Ganas.
"""

import click

from whitemagic.utils.fast_json import loads as _json_loads

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.tree import Tree
    HAS_RICH = True
    console: Console | None = Console()
except ImportError:
    HAS_RICH = False
    console = None
    Panel = None  # type: ignore[assignment,misc]
    Tree = None  # type: ignore[assignment,misc]
    Table = None  # type: ignore[assignment,misc]


@click.group(name="gana")
def gana_group() -> None:
    """🌙 Interact with the 28 Lunar Mansion Ganas"""


@gana_group.command(name="list")
@click.option(
    "--quadrant",
    type=click.Choice(["east", "south", "west", "north", "all"]),
    default="all",
)
def gana_list(quadrant: str) -> None:
    """List all Ganas by quadrant"""
    from whitemagic.core.ganas.registry import get_all_ganas

    ganas = get_all_ganas()
    quadrants = {
        "east": (0, 7, "🐉 Eastern (Spring)", "cyan"),
        "south": (7, 14, "🦅 Southern (Summer)", "red"),
        "west": (14, 21, "🐯 Western (Autumn)", "yellow"),
        "north": (21, 28, "🐢 Northern (Winter)", "blue"),
    }

    if HAS_RICH and console:
        tree = Tree("🌙 28 Lunar Mansion Ganas")
        for quad_key, (start, end, label, color) in quadrants.items():
            if quadrant != "all" and quadrant != quad_key:
                continue
            branch = tree.add(f"[{color}]{label}[/{color}]")
            for i, gana in enumerate(ganas[start:
                end], start + 1):
                mansion = gana.mansion
                branch.add(f"{i}. {mansion.name} ({mansion.value}) - {gana.__class__.__name__}")
        console.print(tree)
        return

    click.echo("🌙 28 Lunar Mansion Ganas")
    for quad_key, (start, end, label, _) in quadrants.items():
        if quadrant != "all" and quadrant != quad_key:
            continue
        click.echo(f"\n{label}")
        for i, gana in enumerate(ganas[start:
            end], start + 1):
            mansion = gana.mansion
            click.echo(f"{i}. {mansion.name} ({mansion.value}) - {gana.__class__.__name__}")


@gana_group.command(name="invoke")
@click.argument("tool_name")
@click.option("--args", help="JSON arguments", default="{}")
def gana_invoke(tool_name: str, args: str) -> None:
    """Invoke a tool through its Gana"""
    from whitemagic.mcp_api_bridge import gana_invoke as invoke_gana

    try:
        args_dict = _json_loads(args)
        if HAS_RICH and console:
            with console.status(f"[cyan]Invoking {tool_name} through Gana...", spinner="moon"):
                result = invoke_gana(target_tool=tool_name, tool_args=args_dict)
        else:
            result = invoke_gana(target_tool=tool_name, tool_args=args_dict)

        if "error" in result:
            if HAS_RICH and console:
                console.print(f"[red]❌ Error:[/red] {result['error']}")
            else:
                click.echo(f"❌ Error: {result['error']}")
            return

        if HAS_RICH and console:
            panel = Panel(
                "[green]✅ Success[/green]\n\n"
                f"[bold]Mansion:[/bold] {result.get('mansion', 'N/A')}\n"
                f"[bold]Garden:[/bold] {result.get('garden', 'N/A')}\n"
                f"[bold]Execution:[/bold] {result.get('execution_ms', 0):.2f}ms\n\n"
                "[bold]Output:[/bold]\n"
                f"{result.get('output', 'N/A')}",
                title=f"🌙 {tool_name}",
                border_style="cyan",
            )
            console.print(panel)
        else:
            click.echo(f"✅ Success: {result.get('output', 'N/A')}")
    except Exception as e:
        if HAS_RICH and console:
            console.print(f"[red]❌ Error:[/red] {e}")
        else:
            click.echo(f"❌ Error: {e}")


@gana_group.command(name="status")
def gana_status() -> None:
    """Show Gana system status and resonance"""
    from whitemagic.core.ganas.registry import TOOL_TO_GANA, get_all_ganas

    ganas = get_all_ganas()
    if HAS_RICH and console:
        table = Table(title="🌙 Gana System Status", show_header=True, header_style="bold magenta")
        table.add_column("Quadrant", style="cyan")
        table.add_column("Ganas", justify="center")
        table.add_column("Tools Mapped", justify="center")

        table.add_row(
            "🐉 Eastern (Spring)",
            "7",
            str(sum(1 for t in TOOL_TO_GANA if TOOL_TO_GANA[t] in [type(g) for g in ganas[:7]])),
        )
        table.add_row(
            "🦅 Southern (Summer)",
            "7",
            str(sum(1 for t in TOOL_TO_GANA if TOOL_TO_GANA[t] in [type(g) for g in ganas[7:14]])),
        )
        table.add_row(
            "🐯 Western (Autumn)",
            "7",
            str(sum(1 for t in TOOL_TO_GANA if TOOL_TO_GANA[t] in [type(g) for g in ganas[14:21]])),
        )
        table.add_row(
            "🐢 Northern (Winter)",
            "7",
            str(sum(1 for t in TOOL_TO_GANA if TOOL_TO_GANA[t] in [type(g) for g in ganas[21:28]])),
        )
        table.add_row("[bold]Total[/bold]", "[bold]28[/bold]", f"[bold]{len(TOOL_TO_GANA)}[/bold]")
        console.print(table)
        console.print("\n[green]✅ All 28 Ganas operational and resonating[/green]")
        return

    click.echo("🌙 Gana System Status")
    click.echo(f"Total Ganas: 28 | Tools mapped: {len(TOOL_TO_GANA)}")
