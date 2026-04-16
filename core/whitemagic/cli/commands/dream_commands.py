# mypy: disable-error-code=no-untyped-def
"""Dream Daemon CLI Commands
Start and check the Dream Daemon (offline processing).
"""

import click

try:
    from rich.console import Console
    HAS_RICH = True
    console: Console | None = Console()
except ImportError:
    HAS_RICH = False
    console = None


@click.group(name="dream")
def dream_group() -> None:
    """💤 Dream Daemon (Offline Processing)"""


@dream_group.command(name="start")
@click.option("--daemon/--no-daemon", default=False, help="Run as background daemon")
@click.option("--interval", default=600, help="Dream cycle interval in seconds")
def dream_start(daemon: bool, interval: int) -> None:
    """Start the Dream Daemon"""
    from whitemagic.core.dreaming.daemon import get_daemon

    if daemon:
        if HAS_RICH and console:
            console.print("[green]Starting Dream Daemon (background mode implied by shell)...[/green]")
        else:
            click.echo("Starting Dream Daemon...")

    d = get_daemon()
    d.interval = interval
    d.start()


@dream_group.command(name="status")
def dream_status() -> None:
    """Check Dream Daemon status"""
    if HAS_RICH and console:
        console.print("[yellow]Dream Daemon status check not fully implemented (v0.1)[/yellow]")
    else:
        click.echo("Dream Daemon status check not fully implemented")
