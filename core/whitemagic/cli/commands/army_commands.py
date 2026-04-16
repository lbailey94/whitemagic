# mypy: disable-error-code=no-untyped-def
"""Army CLI Commands
Shadow clone army deployment and management.
"""

import subprocess
import sys
from pathlib import Path

import click


def _get_army_script() -> Path:
    return Path(__file__).resolve().parent.parent.parent.parent / "scripts" / "deploy_grand_army.py"


@click.group()
def army() -> None:
    """Shadow clone army deployment and management."""


@army.command()
def status() -> None:
    """Show campaign victory status dashboard."""
    script = _get_army_script()
    if script.exists():
        subprocess.run([sys.executable, str(script), "--status"])
    else:
        click.echo("deploy_grand_army.py not found")


@army.command(name="list")
def army_list() -> None:
    """List all available campaigns and objectives."""
    script = _get_army_script()
    if script.exists():
        subprocess.run([sys.executable, str(script), "--list"])
    else:
        click.echo("deploy_grand_army.py not found")


@army.command()
@click.option("--time-limit", "-t", default=300, help="Time limit in seconds (default: 300)")
@click.option("--columns", "-c", default=1, help="Parallel columns for Sun Bin mode")
@click.option("--phase", type=click.Choice(["immediate", "foundation", "infrastructure", "intelligence"]))
@click.option("--yin-yang", is_flag=True, help="Autonomous recon/action/verify cycle")
def deploy(time_limit: int, columns: int, phase: str | None, yin_yang: bool) -> None:
    """Deploy campaigns from doctrine files."""
    script = _get_army_script()
    if not script.exists():
        click.echo("deploy_grand_army.py not found")
        return

    cmd = [sys.executable, str(script), "--campaigns", "--time-limit", str(time_limit)]
    if columns > 1:
        cmd.extend(["--columns", str(columns)])
    if phase:
        cmd.extend(["--phase", phase])
    if yin_yang:
        cmd.append("--yin-yang")

    click.echo(f"\nDeploying shadow clone armies (time limit: {time_limit}s)...")
    subprocess.run(cmd)


@army.command()
@click.argument("name", type=click.Choice(["alpha", "beta", "gamma"]))
def run(name: str) -> None:
    """Run a built-in army (alpha/beta/gamma)."""
    script = _get_army_script()
    if script.exists():
        subprocess.run([sys.executable, str(script), "--army", name])
    else:
        click.echo("deploy_grand_army.py not found")
