# ruff: noqa: BLE001
"""WhiteMagic Cognitive TUI — gRPC-connected terminal interface.

Two modes:
1. Chat mode — interactive conversation with the cognitive daemon
2. Cockpit mode — real-time monitoring of consciousness loops

This replaces the old TUI which was display-only. The new TUI connects
to the Go cognitive gateway via gRPC and provides both interaction
and monitoring.

Usage::

    wm tui           # cockpit mode (default)
    wm tui --chat    # chat mode
"""

from __future__ import annotations

import json
import logging
import os
import sys
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)

try:
    from textual.app import App, ComposeResult
    from textual.containers import Container, Horizontal, Vertical
    from textual.widgets import Footer, Header, Input, Label, RichLog, Static
    from textual.reactive import reactive
    HAS_TEXTUAL = True
except ImportError:
    HAS_TEXTUAL = False

try:
    from whitemagic.mesh.cognitive_client import get_cognitive_client
    HAS_CLIENT = True
except ImportError:
    HAS_CLIENT = False


class TelemetryWidget(Static if HAS_TEXTUAL else object):
    """Real-time telemetry display."""

    def __init__(self) -> None:
        super().__init__("")
        self._data: dict[str, Any] = {}

    def update_data(self, data: dict[str, Any]) -> None:
        self._data = data
        lines = ["[bold]Telemetry[/bold]", ""]
        for key, val in data.items():
            lines.append(f"  {key}: {val}")
        self.update("\n".join(lines))


class LoopStatusWidget(Static if HAS_TEXTUAL else object):
    """Consciousness loop status display."""

    def __init__(self) -> None:
        super().__init__("")
        self._loops: dict[str, Any] = {}

    def update_loops(self, loops: dict[str, Any]) -> None:
        self._loops = loops
        lines = ["[bold]Consciousness Loops[/bold]", ""]
        for name, metrics in loops.items():
            status = "🟢" if metrics.get("errors", 0) == 0 else "🔴"
            lines.append(
                f"  {status} {name:8s} iter={metrics.get('iterations', 0):6d} "
                f"dur={metrics.get('last_duration_ms', 0):.1f}ms"
            )
        self.update("\n".join(lines))


class PrivacyWidget(Static if HAS_TEXTUAL else object):
    """Privacy status indicator."""

    def __init__(self) -> None:
        super().__init__("[bold green]🔒 local_only | 0 bytes sent[/bold green]")

    def update_privacy(self, mode: str, bytes_egress: int = 0) -> None:
        if mode == "local_only":
            self.update(f"[bold green]🔒 local_only | {bytes_egress} bytes sent[/bold green]")
        elif mode == "mesh_enabled":
            self.update(f"[bold yellow]📡 mesh_enabled | {bytes_egress} bytes sent[/bold yellow]")
        elif mode == "cloud_enabled":
            self.update(f"[bold red]☁️ cloud_enabled | {bytes_egress} bytes sent[/bold red]")


if HAS_TEXTUAL:

    class CognitiveTUI(App):
        """The cognitive TUI application."""

        CSS = """
        Screen {
            layout: vertical;
        }
        #main-container {
            height: 1fr;
        }
        #telemetry-panel {
            width: 40%;
            border: solid $primary;
            padding: 1;
        }
        #chat-panel {
            width: 60%;
            border: solid $accent;
            padding: 1;
        }
        #status-bar {
            height: 3;
            dock: bottom;
        }
        .hidden {
            display: none;
        }
        """

        mode = reactive("cockpit")

        def __init__(self, mode: str = "cockpit") -> None:
            super().__init__()
            self.mode = mode
            self._client = get_cognitive_client() if HAS_CLIENT else None
            self._telemetry_widget = TelemetryWidget()
            self._loop_widget = LoopStatusWidget()
            self._privacy_widget = PrivacyWidget()
            self._chat_log: RichLog | None = None
            self._input: Input | None = None
            self._update_timer: threading.Thread | None = None

        def compose(self) -> ComposeResult:
            yield Header()
            with Horizontal(id="main-container"):
                with Vertical(id="telemetry-panel"):
                    yield self._privacy_widget
                    yield self._telemetry_widget
                    yield self._loop_widget
                with Vertical(id="chat-panel"):
                    yield RichLog(id="chat-log", markup=True)
                    yield Input(id="chat-input", placeholder="Type a message or /command...")
            yield Footer()

        def on_mount(self) -> None:
            """Called when the TUI is ready."""
            self._chat_log = self.query_one("#chat-log", RichLog)
            self._input = self.query_one("#chat-input", Input)

            # Connect to gateway
            if self._client:
                connected = self._client.connect()
                if connected:
                    self._chat_log.write("[green]Connected to cognitive gateway[/green]")
                    status = self._client.daemon_status()
                    if "active_loops" in status:
                        self._loop_widget.update_loops({
                            name: {"iterations": 0, "errors": 0, "last_duration_ms": 0}
                            for name in status["active_loops"]
                        })
                    self._privacy_widget.update_privacy(status.get("privacy_status", "local_only"))
                else:
                    self._chat_log.write("[yellow]Gateway not running — using local mode[/yellow]")
            else:
                self._chat_log.write("[yellow]gRPC client not available — using local mode[/yellow]")

            # Start update thread
            self._update_timer = threading.Thread(target=self._update_loop, daemon=True)
            self._update_timer.start()

        def _update_loop(self) -> None:
            """Background thread to update telemetry."""
            while True:
                try:
                    from whitemagic.core.consciousness.daemon import get_daemon
                    daemon = get_daemon()
                    status = daemon.status()
                    self.call_from_thread(self._telemetry_widget.update_data, {
                        "uptime": f"{status['uptime_s']:.0f}s",
                        "iterations": status["total_iterations"],
                        "rss_mb": f"{status['rss_mb']:.1f}",
                        "gc_count": status["gc_count"],
                    })
                    self.call_from_thread(self._loop_widget.update_loops, status.get("loops", {}))
                except Exception:
                    pass
                time.sleep(2)

        def on_input_submitted(self, event: Input.Submitted) -> None:
            """Handle chat input."""
            text = event.value.strip()
            if not text:
                return

            self._chat_log.write(f"[bold cyan]You:[/bold cyan] {text}")
            self._input.value = ""

            if text.startswith("/"):
                self._handle_command(text)
            else:
                self._handle_message(text)

        def _handle_command(self, cmd: str) -> None:
            """Handle slash commands."""
            parts = cmd.split(maxsplit=1)
            command = parts[0]
            args = parts[1] if len(parts) > 1 else ""

            if command == "/quit":
                self.exit()
            elif command == "/status":
                if self._client and self._client.is_connected:
                    status = self._client.daemon_status()
                    self._chat_log.write(json.dumps(status, indent=2))
                else:
                    self._chat_log.write("[yellow]Not connected to gateway[/yellow]")
            elif command == "/help":
                self._chat_log.write("Commands: /quit, /status, /help, /clear")
            elif command == "/clear":
                self._chat_log.clear()
            else:
                self._chat_log.write(f"[red]Unknown command: {command}[/red]")

        def _handle_message(self, text: str) -> None:
            """Handle a chat message."""
            if self._client and self._client.is_connected:
                result = self._client.call_tool(
                    gana="horn",
                    tool="dispatch",
                    operation="chat",
                    args={"message": text},
                )
                self._chat_log.write(f"[bold green]WM:[/bold green] {json.dumps(result)}")
            else:
                # Local mode — just echo
                self._chat_log.write(
                    f"[dim](local mode — connect to gateway for full interaction)[/dim]"
                )

        def action_toggle_mode(self) -> None:
            """Toggle between chat and cockpit modes."""
            self.mode = "chat" if self.mode == "cockpit" else "cockpit"

else:
    # Fallback when textual is not available
    class CognitiveTUI:
        """Fallback TUI when textual is not installed."""

        def __init__(self, mode: str = "cockpit") -> None:
            self.mode = mode

        def run(self) -> None:
            print("WhiteMagic Cognitive TUI")
            print("(textual not installed — using basic mode)")
            print()

            if HAS_CLIENT:
                client = get_cognitive_client()
                if client.connect():
                    status = client.daemon_status()
                    print(f"Gateway: {status.get('version', 'unknown')}")
                    print(f"Privacy: {status.get('privacy_status', 'unknown')}")
                    print(f"Loops: {', '.join(status.get('active_loops', []))}")
                    print()

                    if self.mode == "chat":
                        print("Chat mode — type /quit to exit")
                        while True:
                            try:
                                text = input("> ")
                                if text.strip() == "/quit":
                                    break
                                if text.strip():
                                    result = client.call_tool(
                                        gana="horn", tool="dispatch", args={"message": text}
                                    )
                                    print(f"WM: {json.dumps(result)}")
                            except (EOFError, KeyboardInterrupt):
                                break
                    else:
                        print("Cockpit mode — monitoring (Ctrl+C to exit)")
                        try:
                            for snap in client.telemetry_stream(interval_ms=2000):
                                print(f"  clients={snap['connected_clients']} "
                                      f"privacy={snap['privacy_status']}")
                        except KeyboardInterrupt:
                            pass

                    client.close()
                else:
                    print("Could not connect to gateway. Is 'wm daemon start' running?")
            else:
                print("gRPC client not available.")


def run_tui(mode: str = "cockpit") -> None:
    """Run the cognitive TUI."""
    if HAS_TEXTUAL:
        app = CognitiveTUI(mode=mode)
        app.run()
    else:
        fallback = CognitiveTUI(mode=mode)
        fallback.run()
