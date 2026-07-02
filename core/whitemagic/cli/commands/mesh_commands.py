# ruff: noqa: BLE001
"""WhiteMagic mesh CLI commands.

Commands:
    wm mesh status     — Show mesh network status
    wm mesh enable     — Enable P2P mesh networking (opt-in)
    wm mesh disable    — Disable mesh networking (return to local_only)
    wm mesh peers      — List known peers
    wm mesh discover   — Actively discover peers on local network
"""

from __future__ import annotations

import json
import logging

import click

logger = logging.getLogger(__name__)


def _register_mesh_commands(cli: click.Group) -> None:
    """Register mesh commands with the CLI group."""

    @cli.group()
    def mesh() -> None:
        """P2P mesh network control (opt-in, local-first)."""
        pass

    @mesh.command()
    def status() -> None:
        """Show mesh network status."""
        from whitemagic.core.consciousness.network_guard import get_network_guard
        guard = get_network_guard()

        click.echo("WhiteMagic Mesh Status")
        click.echo("=" * 40)
        click.echo(f"Privacy mode: {guard.privacy_status}")
        click.echo(f"Bytes egress:  {guard.total_bytes_egress}")
        click.echo(f"Audit entries: {len(guard._audit_log)}")

        # Check if Go mesh node is running
        try:
            from whitemagic.core.acceleration.go_mesh_bridge import get_go_mesh_status
            status = get_go_mesh_status()
            if status:
                click.echo(f"Go mesh node:  {'running' if status.get('running') else 'stopped'}")
                peers = status.get("peers", [])
                click.echo(f"Known peers:   {len(peers)}")
            else:
                click.echo("Go mesh node:  not started")
        except Exception:
            click.echo("Go mesh node:  unavailable")

    @mesh.command()
    def enable() -> None:
        """Enable P2P mesh networking (opt-in)."""
        from whitemagic.core.consciousness.network_guard import get_network_guard
        guard = get_network_guard()

        old_mode = guard.privacy_status
        guard.set_mode("mesh_enabled")

        click.echo(f"Mesh networking enabled (was: {old_mode})")
        click.echo(f"Privacy mode: {guard.privacy_status}")
        click.echo()
        click.echo("Note: Start the Go mesh node with: wm daemon start --mesh")

    @mesh.command()
    def disable() -> None:
        """Disable mesh networking (return to local_only)."""
        from whitemagic.core.consciousness.network_guard import get_network_guard
        guard = get_network_guard()

        old_mode = guard.privacy_status
        guard.set_mode("local_only")

        click.echo(f"Mesh networking disabled (was: {old_mode})")
        click.echo(f"Privacy mode: {guard.privacy_status}")

    @mesh.command()
    def peers() -> None:
        """List known peers."""
        try:
            from whitemagic.mesh.client import get_mesh_client
            client = get_mesh_client()
            peers = client.known_peers
            if not peers:
                click.echo("No known peers. Run 'wm mesh discover' or start the Go mesh node.")
                return
            click.echo(f"Known peers ({len(peers)}):")
            for peer_id, info in peers.items():
                click.echo(f"  {peer_id}: {info}")
        except Exception as e:
            click.echo(f"Error: {e}")

    @mesh.command()
    def discover() -> None:
        """Actively discover peers on local network."""
        click.echo("Discovering peers...")
        try:
            from whitemagic.mesh.awareness import get_mesh_awareness
            awareness = get_mesh_awareness()
            events = awareness.get_recent_events(limit=10)
            if events:
                click.echo(f"Recent discovery events ({len(events)}):")
                for event in events:
                    click.echo(f"  {event}")
            else:
                click.echo("No peers discovered. Ensure Go mesh node is running.")
        except Exception as e:
            click.echo(f"Error: {e}")
