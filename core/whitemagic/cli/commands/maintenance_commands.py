# mypy: disable-error-code=no-untyped-def
"""Maintenance CLI Commands
System maintenance and synchronization.
"""

import os
import subprocess
import sys

import click

try:
    from rich.console import Console
    HAS_RICH = True
    console: Console | None = Console()
except ImportError:
    HAS_RICH = False
    console = None


@click.group(name="maintenance")
def maintenance_group() -> None:
    """🔧 System maintenance and synchronization commands"""


@maintenance_group.command(name="reindex")
def maintenance_reindex() -> None:
    """Run The Great Realignment (Full Holographic Re-Indexing)"""
    if HAS_RICH and console:
        console.print("\n[bold cyan]🌌 Starting The Great Realignment...[/bold cyan]\n")
        console.print("[dim]This will re-calculate spatial coordinates for all memories.[/dim]\n")

        try:
            env = os.environ.copy()
            env["PYTHONPATH"] = env.get("PYTHONPATH", "") + ":" + os.getcwd()

            python_bin = os.path.join(os.getcwd(), ".venv", "bin", "python3")
            if not os.path.exists(python_bin):
                python_bin = "python3"

            script_path = os.path.join(os.getcwd(), "scripts", "reindex_data_sea.py")

            if not os.path.exists(script_path):
                console.print(f"[red]❌ Error: Maintenance script not found at {script_path}[/red]")
                return

            subprocess.run([python_bin, script_path], check=True, env=env)
            console.print("\n[bold green]✨ Realignment Complete![/bold green]")
        except subprocess.CalledProcessError as e:
            console.print(f"\n[red]❌ Realignment failed with exit code {e.returncode}[/red]")
        except Exception as e:
            console.print(f"\n[red]❌ Unexpected error: {e}[/red]")
    else:
        click.echo("🌌 Starting The Great Realignment...")
        env = os.environ.copy()
        env["PYTHONPATH"] = env.get("PYTHONPATH", "") + ":."
        subprocess.run([sys.executable, "scripts/reindex_data_sea.py"], env=env, check=False)
