"""
CLI Commands: Wu Xing Phase (G007)
==================================

wm phase status/set
"""

import click

from whitemagic.core.wuxing_scheduler import WuXingScheduler

# In a real app, the scheduler would be a singleton or attached to the session service.
# For CLI demo purposes, we instantiate a fresh one or try to connect to a daemon.
# Here we'll just demo the logic.

@click.group(name="phase")
def phase_cli():
    """☯️ Wu Xing Waking Scheduler"""
    pass

@phase_cli.command(name="status")
def status_cmd():
    """Show current Wu Xing phase."""
    # Mock connection to active scheduler
    scheduler = WuXingScheduler()
    st = scheduler.status()

    # Rich formatting if available
    try:
        from rich.console import Console
        from rich.panel import Panel
        console = Console()

        color_map = {
            "wood": "green",
            "fire": "red",
            "earth": "yellow",
            "metal": "white",
            "water": "blue"
        }
        p = st['phase']
        color = color_map.get(p, "white")

        console.print(Panel(
            f"[bold {color}]Current Phase: {p.upper()}[/]\n"
            f"Duration: {st['duration_min']} min / {st['target_duration']} min\n\n"
            f"[bold]Allowed Actions:[/]\n" + "\n".join(f"- {a}" for a in st['allowed_actions']),
            title="☯️ Wu Xing Scheduler",
            border_style=color
        ))
    except ImportError:
        click.echo(f"Phase: {st['phase']}")
        click.echo(f"Allowed: {st['allowed_actions']}")

@phase_cli.command(name="set")
@click.argument("element", type=click.Choice(["wood", "fire", "earth", "metal", "water"], case_sensitive=False))
def set_cmd(element):
    """Manually override the current phase."""
    # In reality, this would send a command to the running agent/scheduler
    click.echo(f"Manual override: Phase set to {element.upper()}")
    click.echo("(Note: This only affects the active session, requires IPC to running agent)")
