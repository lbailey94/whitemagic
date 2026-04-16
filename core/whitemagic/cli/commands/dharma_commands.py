"""Dharma CLI commands — extracted from cli_app.py (PSR-028 decomposition)."""
from __future__ import annotations

import click

from whitemagic.utils.fast_json import loads as _json_loads

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.tree import Tree
    HAS_RICH = True
    console = Console()
except ImportError:
    HAS_RICH = False
    console = None  # type: ignore[assignment]


@click.group(name="dharma")
def dharma_group() -> None:
    """☸️  Ethical reasoning and boundary detection"""


@dharma_group.command(name="evaluate")
@click.argument("action")
@click.option("--context", help="Additional context (JSON)", default="{}")
def dharma_evaluate(action: str, context: str) -> None:
    """Evaluate an action against ethical principles"""
    from whitemagic.mcp_api_bridge import dharma_evaluate_ethics

    try:
        context_dict = _json_loads(context)
        if HAS_RICH and console:
            with console.status("[yellow]Consulting ethical principles...", spinner="dots"):
                result = dharma_evaluate_ethics(action={"description": action}, context=context_dict)
        else:
            result = dharma_evaluate_ethics(action={"description": action}, context=context_dict)

        score = result.get("score", 0)
        concerns = result.get("concerns", [])

        if HAS_RICH and console:
            if score >= 0.8:
                color = "green"
                status = "✅ Aligned"
            elif score >= 0.5:
                color = "yellow"
                status = "⚠️  Concerning"
            else:
                color = "red"
                status = "❌ Violation"

            panel = Panel(
                f"[{color}]{status}[/{color}]\n\n"
                f"[bold]Action:[/bold] {action}\n"
                f"[bold]Ethical Score:[/bold] {score:.2%}\n\n"
                "[bold]Concerns:[/bold]\n"
                + ("\n".join(f"  • {c}" for c in concerns) if concerns else "  None"),
                title="☸️  Dharma Evaluation",
                border_style=color,
            )
            console.print(panel)
        else:
            click.echo(f"Ethical Score: {score:.2%}")
            if concerns:
                click.echo("Concerns:")
                for c in concerns:
                    click.echo(f"  - {c}")
            else:
                click.echo("No concerns.")
    except Exception as e:
        click.echo(f"❌ Error: {e}")


@dharma_group.command(name="principles")
@click.option("--level", help="Filter by level (universal, compassion, integrity, etc.)")
def dharma_principles(level: str | None) -> None:
    """List all ethical principles"""
    from whitemagic.mcp_api_bridge import dharma_list_principles

    try:
        result = dharma_list_principles(level=level)
        principles = result.get("principles", [])

        if HAS_RICH and console:
            table = Table(title="☸️  Dharma Principles", show_header=True, header_style="bold yellow")
            table.add_column("Principle", style="cyan")
            table.add_column("Level", style="magenta")
            table.add_column("Weight", justify="center")
            for p in principles:
                table.add_row(
                    p.get("name", "Unknown"),
                    p.get("level", "Unknown"),
                    f"{p.get('weight', 0):.1f}",
                )
            console.print(table)
        else:
            for p in principles:
                click.echo(f"{p.get('name', 'Unknown')} ({p.get('level', 'Unknown')})")
    except Exception as e:
        click.echo(f"❌ Error: {e}")


@dharma_group.command(name="check-boundaries")
@click.argument("action")
def dharma_check_boundaries(action: str) -> None:
    """Check for boundary violations"""
    from whitemagic.mcp_api_bridge import dharma_check_boundaries

    try:
        if HAS_RICH and console:
            with console.status("[yellow]Checking boundaries...", spinner="dots"):
                result = dharma_check_boundaries(action={"description": action}, context={})
        else:
            result = dharma_check_boundaries(action={"description": action}, context={})

        violations = result.get("violations", [])
        if HAS_RICH and console:
            if not violations:
                console.print(Panel("[green]✅ No boundary violations detected[/green]", border_style="green"))
            else:
                tree = Tree("⚠️  Boundary Violations")
                for v in violations:
                    branch = tree.add(
                        f"[red]{v.get('type', 'Unknown')}[/red] (severity: {v.get('severity', 0):.1f})",
                    )
                    branch.add(f"[dim]{v.get('reason', 'No reason provided')}[/dim]")
                console.print(tree)
        elif not violations:
            click.echo("✅ No boundary violations detected")
        else:
            click.echo("⚠️  Boundary Violations:")
            for v in violations:
                click.echo(f"- {v.get('type', 'Unknown')}: {v.get('reason', 'No reason provided')}")
    except Exception as e:
        click.echo(f"❌ Error: {e}")
