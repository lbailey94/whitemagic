# ruff: noqa: BLE001
"""WhiteMagic daemon CLI commands.

Commands:
    wm daemon start   — Start the consciousness daemon (foreground)
    wm daemon stop    — Stop a running daemon
    wm daemon status  — Check daemon status
    wm daemon loops   — Show loop metrics
"""

from __future__ import annotations

import json
import logging
import os
import signal
import time

import click

logger = logging.getLogger(__name__)


def _register_daemon_commands(cli: click.Group) -> None:
    """Register daemon commands with the CLI group."""

    @cli.group()
    def daemon() -> None:
        """Continuous consciousness daemon control."""
        pass

    @daemon.command()
    @click.option("--background", "-b", is_flag=True, help="Run in background (fork)")
    @click.option("--mesh", is_flag=True, help="Enable P2P mesh (opt-in)")
    @click.option("--tcp", is_flag=True, help="Also listen on TCP localhost:4730")
    @click.option("--no-gateway", is_flag=True, help="Skip Go gateway (Python loops only)")
    def start(background: bool, mesh: bool, tcp: bool, no_gateway: bool) -> None:
        """Start the consciousness daemon."""

        if background:
            # Fork to background
            pid = os.fork()
            if pid > 0:
                click.echo(f"Daemon started (PID {pid})")
                # Write PID file
                from whitemagic.config.paths import WM_ROOT
                pid_file = WM_ROOT / "daemon.pid"
                pid_file.write_text(str(pid))
                return

        click.echo("🌐 WhiteMagic Consciousness Daemon v24.0.0-dev")
        click.echo(f"   Privacy: local_only (mesh={mesh})")
        click.echo()

        # Start NetworkGuard
        from whitemagic.core.consciousness.network_guard import get_network_guard
        guard = get_network_guard()
        if mesh:
            guard.set_mode("mesh_enabled")
        click.echo(f"   NetworkGuard: {guard.privacy_status}")

        # Start consciousness daemon
        from whitemagic.core.consciousness.daemon import get_daemon
        cd = get_daemon()
        cd.start()
        click.echo(f"   Consciousness loops: {len(cd._loops)} started")
        click.echo()

        # Start Go gateway (if available and not skipped)
        gateway_proc = None
        if not no_gateway:
            try:
                import shutil
                import subprocess
                from pathlib import Path

                # Check PATH first, then known locations
                gateway_bin = shutil.which("wm_gateway")
                if not gateway_bin:
                    # Check relative to mesh_aux
                    repo_root = Path(__file__).resolve().parent.parent.parent.parent
                    local_bin = repo_root / "core" / "mesh_aux" / "wm_gateway"
                    if local_bin.exists():
                        gateway_bin = str(local_bin)

                if gateway_bin:
                    args = [gateway_bin]
                    if mesh:
                        args.append("--mesh")
                    if tcp:
                        args.append("--tcp")
                    gateway_proc = subprocess.Popen(
                        args,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                    )
                    click.echo(f"   Go gateway: started (PID {gateway_proc.pid})")
                else:
                    click.echo("   Go gateway: not found (run 'go build ./cmd/wm_gateway/' in mesh_aux/)")
                    click.echo("              Continuing with Python loops only...")
            except Exception as e:
                click.echo(f"   Go gateway: failed ({e})")
                click.echo("              Continuing with Python loops only...")
        else:
            click.echo("   Go gateway: skipped (--no-gateway)")

        click.echo()
        click.echo("   Press Ctrl+C to stop")
        click.echo()

        # Run until interrupted
        try:
            while cd.is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            click.echo("\n   Shutting down...")

        cd.stop()

        if gateway_proc:
            gateway_proc.terminate()
            gateway_proc.wait(timeout=5)

        # Clean up PID file
        from whitemagic.config.paths import WM_ROOT
        pid_file = WM_ROOT / "daemon.pid"
        if pid_file.exists():
            pid_file.unlink()

        click.echo("   Daemon stopped.")

    @daemon.command()
    def stop() -> None:
        """Stop a running daemon."""
        from whitemagic.config.paths import WM_ROOT
        pid_file = WM_ROOT / "daemon.pid"

        if not pid_file.exists():
            click.echo("No daemon running (no PID file found)")
            return

        try:
            pid = int(pid_file.read_text().strip())
            os.kill(pid, signal.SIGTERM)
            click.echo(f"Sent SIGTERM to daemon (PID {pid})")
            time.sleep(1)
            pid_file.unlink()
        except ProcessLookupError:
            click.echo("Daemon process not found, cleaning up PID file")
            pid_file.unlink()
        except Exception as e:
            click.echo(f"Error stopping daemon: {e}")

    @daemon.command()
    def status() -> None:
        """Check daemon status."""
        from whitemagic.config.paths import WM_ROOT
        pid_file = WM_ROOT / "daemon.pid"

        if pid_file.exists():
            try:
                pid = int(pid_file.read_text().strip())
                os.kill(pid, 0)  # Check if process exists
                click.echo(f"Daemon running (PID {pid})")
            except ProcessLookupError:
                click.echo("Daemon PID file exists but process is dead")
            except Exception:
                click.echo("Daemon status unknown")
        else:
            click.echo("Daemon not running")

        # Also check in-process daemon
        try:
            from whitemagic.core.consciousness.daemon import get_daemon
            cd = get_daemon()
            if cd.is_running:
                status = cd.status()
                click.echo(json.dumps(status, indent=2))
        except Exception:
            pass

    @daemon.command()
    def loops() -> None:
        """Show loop metrics."""
        try:
            from whitemagic.core.consciousness.daemon import get_daemon
            cd = get_daemon()
            status = cd.status()
            click.echo("Loop Metrics:")
            click.echo("-" * 60)
            for name, metrics in status.get("loops", {}).items():
                click.echo(
                    f"  {name:8s}  iter={metrics['iterations']:6d}  "
                    f"dur={metrics['last_duration_ms']:.1f}ms  "
                    f"errors={metrics['errors']}"
                )
        except Exception as e:
            click.echo(f"Error: {e}")
