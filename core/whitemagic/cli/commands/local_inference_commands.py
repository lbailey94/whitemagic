# ruff: noqa: BLE001
import click

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    HAS_RICH = True
    console = Console()
except ImportError:
    HAS_RICH = False
    console = None  # type: ignore[assignment]

__all__ = ['infer_local_query', 'infer_local_status']

@click.command(name="local-query")
@click.argument("prompt")
@click.option("--backend", type=click.Choice(["bitnet", "ollama", "auto"]), default="auto")
def infer_local_query(prompt: str, backend: str) -> None:
    """Run local ML inference query (BitNet/Ollama)"""
    from whitemagic.mcp_api_bridge import local_ml_infer

    try:
        if HAS_RICH and console:
            with console.status(f"[cyan]Running inference with {backend}...", spinner="dots"):
                result = local_ml_infer(prompt=prompt, backend=backend if backend != "auto" else None)
        else:
            result = local_ml_infer(prompt=prompt, backend=backend if backend != "auto" else None)

        if "error" in result:
            click.echo(f"❌ Error: {result['error']}")
            return

        if HAS_RICH and console:
            panel = Panel(
                "[bold]Response:[/bold]\n\n"
                f"{result.get('response', 'N/A')}\n\n"
                f"[dim]Backend: {result.get('backend', 'unknown')} | "
                f"Time: {result.get('time_ms', 0):.0f}ms[/dim]",
                title="🤖 Local ML",
                border_style="cyan",
            )
            console.print(panel)
        else:
            click.echo(result.get("response", "N/A"))
    except Exception as e:
        click.echo(f"❌ Error: {e}")
@click.command(name="local-status")
def infer_local_status() -> None:
    """Show local ML engine status"""
    from whitemagic.mcp_api_bridge import local_ml_status

    try:
        result = local_ml_status()
        if HAS_RICH and console:
            table = Table(title="🤖 Local ML Status", show_header=True)
            table.add_column("Backend", style="cyan")
            table.add_column("Available", justify="center")
            table.add_column("Models", justify="center")
            for backend, info in result.get("backends", {}).items():
                available = "✅" if info.get("available") else "❌"
                models = info.get("models", [])
                table.add_row(
                    backend.title(),
                    available,
                    str(len(models)) if models else "0",
                )
            console.print(table)
            default = result.get("default_backend")
            if default:
                console.print(f"\n[green]Default backend:[/green] {default}")
        else:
            for backend, info in result.get("backends", {}).items():
                available = "yes" if info.get("available") else "no"
                models = info.get("models", [])
                click.echo(f"{backend}: {available} ({len(models)} models)")
    except Exception as e:
        click.echo(f"❌ Error: {e}")
