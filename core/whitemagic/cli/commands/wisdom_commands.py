# mypy: disable-error-code=no-untyped-def
"""Wisdom CLI Commands
Consult wisdom systems: I Ching, Wu Xing, Art of War.
"""

import click

try:
    from rich.console import Console
    from rich.panel import Panel
    HAS_RICH = True
    console = Console()
except ImportError:
    HAS_RICH = False
    console = None


@click.group(name="wisdom")
def wisdom_group() -> None:
    """🧙 Consult wisdom systems (I Ching, Wu Xing, Art of War)"""


@wisdom_group.command(name="consult")
@click.argument("question")
@click.option(
    "--source",
    type=click.Choice(["full_council", "art_of_war", "iching", "synthesize"]),
    default="full_council",
)
@click.option("--urgency", type=click.Choice(["low", "normal", "high", "critical"]), default="normal")
def wisdom_consult(question: str, source: str, urgency: str) -> None:
    """Consult the wisdom council"""
    from whitemagic.mcp_api_bridge import consult_full_council

    try:
        if HAS_RICH and console:
            with console.status(f"[yellow]Consulting {source}...", spinner="moon"):
                result = consult_full_council(question=question, source=source, urgency=urgency)
        else:
            result = consult_full_council(question=question, source=source, urgency=urgency)

        if "error" in result:
            click.echo(f"❌ Error: {result['error']}")
            return

        guidance = result.get("guidance", "No guidance provided")
        confidence = result.get("confidence", 0)
        if HAS_RICH and console:
            panel = Panel(
                f"[bold]Question:[/bold] {question}\n\n"
                f"[bold]Guidance:[/bold]\n{guidance}\n\n"
                f"[dim]Source: {source} | Urgency: {urgency} | Confidence: {confidence:.0%}[/dim]",
                title="🧙 Wisdom Council",
                border_style="yellow",
            )
            console.print(panel)
        else:
            click.echo(guidance)
    except Exception as e:
        click.echo(f"❌ Error: {e}")


@wisdom_group.command(name="iching")
@click.argument("question")
def wisdom_iching(question: str) -> None:
    """Cast I Ching hexagram for guidance"""
    from whitemagic.mcp_api_bridge import consult_iching

    try:
        if HAS_RICH and console:
            with console.status("[yellow]Casting I Ching...", spinner="dots"):
                result = consult_iching(operation="cast", question=question, method="coin")
        else:
            result = consult_iching(operation="cast", question=question, method="coin")

        if "error" in result:
            click.echo(f"❌ Error: {result['error']}")
            return

        hexagram = result.get("hexagram_number", "N/A")
        interpretation = result.get("interpretation", "No interpretation")
        if HAS_RICH and console:
            panel = Panel(
                f"[bold]Hexagram {hexagram}[/bold]\n\n{interpretation}",
                title="☯️  I Ching",
                border_style="cyan",
            )
            console.print(panel)
        else:
            click.echo(f"Hexagram {hexagram}\n{interpretation}")
    except Exception as e:
        click.echo(f"❌ Error: {e}")
