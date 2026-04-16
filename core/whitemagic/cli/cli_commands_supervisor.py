"""
CLI Commands: Supervisor (G004)
===============================

wm supervisor status/enable/disable
"""

import click

from whitemagic.autonomous.supervisor import Supervisor
from whitemagic.config import paths


@click.group(name="supervisor")
def supervisor_cli() -> None:
    """🤖 Auto-Prompting Supervisor"""
    pass

def _get_supervisor():
    sop_dir = paths.get_state_root() / "config" / "sops"
    return Supervisor(sop_dir)

@supervisor_cli.command(name="status")
def status_cmd() -> None:
    """Show Supervisor status and loaded SOPs."""
    sup = _get_supervisor()
    st = sup.status()

    click.echo("🤖 Supervisor Status")
    click.echo(f"SOPs Loaded: {st['sops_loaded']}")
    click.echo(f"SOPs Enabled: {st['sops_enabled']}")
    click.echo("\n📋 SOP List:")
    for sop in st['sop_list']:
        icon = "✅" if sop['enabled'] else "❌"
        click.echo(f"  {icon} {sop['name']}")

@supervisor_cli.command(name="enable")
@click.argument("sop_name")
def enable_cmd(sop_name: str) -> None:
    """Enable a specific SOP."""
    sup = _get_supervisor()
    sup.toggle_sop(sop_name, True)
    # Note: In a real system we'd need to persist this change to disk
    click.echo(f"Enabled SOP: {sop_name} (runtime only)")

@supervisor_cli.command(name="disable")
@click.argument("sop_name")
def disable_cmd(sop_name: str) -> None:
    """Disable a specific SOP."""
    sup = _get_supervisor()
    sup.toggle_sop(sop_name, False)
    click.echo(f"Disabled SOP: {sop_name} (runtime only)")
