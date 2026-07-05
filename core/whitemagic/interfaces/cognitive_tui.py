# ruff: noqa: BLE001
"""WhiteMagic Cognitive TUI — unified terminal interface.

Three panes in a single screen:
1. **Cockpit** (left) — real-time consciousness loop telemetry, privacy status
2. **Galaxy** (center) — scatter-plot visualizer of 5D holographic memory space
3. **Chat** (right) — interactive conversation + slash commands

Merges the v17 GalaxyExplorer (Rich-based memory scatter plot) with the
Phase 3 cognitive cockpit (gRPC telemetry + chat). Uses Textual for a
full-screen reactive TUI.

Usage::

    wm tui                # full unified interface
    wm tui --cockpit      # cockpit only (telemetry + loops)
    wm tui --chat         # chat only (interactive)
    wm tui --galaxy       # galaxy map only
"""

from __future__ import annotations

import json
import logging
import math
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)

try:
    from textual.app import App, ComposeResult
    from textual.containers import Horizontal, Vertical, VerticalScroll
    from textual.reactive import reactive
    from textual.widgets import Footer, Header, Input, Label, RichLog, Static
    HAS_TEXTUAL = True
except ImportError:
    HAS_TEXTUAL = False

try:
    from whitemagic.mesh.cognitive_client import get_cognitive_client
    HAS_CLIENT = True
except ImportError:
    HAS_CLIENT = False


# ── Widgets ──────────────────────────────────────────────────────────


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
            iters = metrics.get("iterations", 0)
            dur = metrics.get("last_duration_ms", 0)
            lines.append(f"  {status} {name:8s} iter={iters:6d} dur={dur:.1f}ms")
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


class AgentRegistryWidget(Static if HAS_TEXTUAL else object):
    """Show registered agents from the interop registry."""

    def __init__(self) -> None:
        super().__init__("")
        self._agents: list[dict[str, Any]] = []

    def update_agents(self, agents: list[dict[str, Any]]) -> None:
        self._agents = agents
        lines = ["[bold]Connected Agents[/bold]", ""]
        if not agents:
            lines.append("  [dim]none registered[/dim]")
        for a in agents:
            name = a.get("name", "unknown")
            active = a.get("active", False)
            icon = "🟢" if active else "🔴"
            lines.append(f"  {icon} {name}")
        self.update("\n".join(lines))


class GalaxyWidget(Static if HAS_TEXTUAL else object):
    """5D holographic memory scatter plot — ported from v17 GalaxyExplorer."""

    def __init__(self) -> None:
        super().__init__("")
        self._memories: list[dict[str, Any]] = []

    def update_memories(self, memories: list[dict[str, Any]]) -> None:
        self._memories = memories
        self._render()

    def _render(self) -> None:
        if not self._memories:
            self.update("[dim]No memories loaded — press 'r' to refresh[/dim]")
            return

        width = 50
        height = 18
        chart = [[" " for _ in range(width)] for _ in range(height)]
        cx, cy = width // 2, height // 2

        for i, m in enumerate(self._memories):
            x = int(m.get("x", 0) * (width // 2.5)) + cx
            y = int(-m.get("y", 0) * (height // 2.5)) + cy

            if 0 <= x < width and 0 <= y < height:
                if m.get("w", 0) > 0.8:
                    chart[y][x] = "★"
                elif m.get("w", 0) > 0.5:
                    chart[y][x] = "●"
                else:
                    chart[y][x] = "·"

        lines = ["[bold cyan]5D Holographic Galaxy[/bold cyan]", ""]
        for row in chart:
            lines.append("".join(row))
        lines.append("")
        lines.append(f"  [dim]{len(self._memories)} memories shown[/dim]")
        self.update("\n".join(lines))


# ── Main TUI App ─────────────────────────────────────────────────────


if HAS_TEXTUAL:

    class CognitiveTUI(App):
        """The unified cognitive TUI — cockpit + galaxy + chat."""

        CSS = """
        Screen {
            layout: vertical;
        }
        #main-container {
            height: 1fr;
        }
        #left-panel {
            width: 28%;
            border: solid $primary;
            padding: 0 1;
        }
        #center-panel {
            width: 40%;
            border: solid $accent;
            padding: 0 1;
        }
        #right-panel {
            width: 32%;
            border: solid $success;
            padding: 0 1;
        }
        #galaxy-widget {
            height: 1fr;
        }
        #chat-log {
            height: 1fr;
        }
        #chat-input {
            height: 3;
            dock: bottom;
        }
        .hidden {
            display: none;
        }
        """

        mode = reactive("full")

        BINDINGS = [
            ("q", "quit", "Quit"),
            ("r", "refresh", "Refresh"),
            ("t", "toggle", "Toggle Mode"),
        ]

        def __init__(self, mode: str = "full") -> None:
            super().__init__()
            self.mode = mode
            self._client = get_cognitive_client() if HAS_CLIENT else None
            self._telemetry_widget = TelemetryWidget()
            self._loop_widget = LoopStatusWidget()
            self._privacy_widget = PrivacyWidget()
            self._agent_widget = AgentRegistryWidget()
            self._galaxy_widget = GalaxyWidget()
            self._chat_log: RichLog | None = None
            self._input: Input | None = None
            self._update_thread: threading.Thread | None = None
            self._galaxy_thread: threading.Thread | None = None

        def compose(self) -> ComposeResult:
            yield Header(show_clock=True)
            with Horizontal(id="main-container"):
                with VerticalScroll(id="left-panel"):
                    yield self._privacy_widget
                    yield self._telemetry_widget
                    yield self._loop_widget
                    yield self._agent_widget
                with Vertical(id="center-panel"):
                    yield self._galaxy_widget
                with Vertical(id="right-panel"):
                    yield RichLog(id="chat-log", markup=True)
                    yield Input(id="chat-input", placeholder="Type or /help...")
            yield Footer()

        def on_mount(self) -> None:
            self._chat_log = self.query_one("#chat-log", RichLog)
            self._input = self.query_one("#chat-input", Input)

            self._chat_log.write("[bold]WhiteMagic Cognitive TUI[/bold]")
            self._chat_log.write("[dim]Press 'r' to refresh, 't' to toggle, 'q' to quit[/dim]")
            self._chat_log.write("")

            # Connect to gateway if available
            if self._client:
                try:
                    connected = self._client.connect()
                    if connected:
                        self._chat_log.write("[green]✅ Connected to cognitive gateway[/green]")
                        status = self._client.daemon_status()
                        if "active_loops" in status:
                            self._loop_widget.update_loops({
                                name: {"iterations": 0, "errors": 0, "last_duration_ms": 0}
                                for name in status["active_loops"]
                            })
                        self._privacy_widget.update_privacy(
                            status.get("privacy_status", "local_only")
                        )
                    else:
                        self._chat_log.write("[yellow]Gateway not running — local mode[/yellow]")
                except Exception:
                    self._chat_log.write("[yellow]Gateway unavailable — local mode[/yellow]")
            else:
                self._chat_log.write("[yellow]gRPC client not available — local mode[/yellow]")

            # Initial data load
            self._load_galaxy()
            self._load_agents()

            # Start background update thread
            self._update_thread = threading.Thread(target=self._update_loop, daemon=True)
            self._update_thread.start()

        def _update_loop(self) -> None:
            """Background thread to poll daemon telemetry."""
            while True:
                try:
                    from whitemagic.core.consciousness.daemon import get_daemon
                    daemon = get_daemon()
                    if daemon.is_running:
                        status = daemon.status()
                        self.call_from_thread(
                            self._telemetry_widget.update_data,
                            {
                                "uptime": f"{status['uptime_s']:.0f}s",
                                "iterations": status["total_iterations"],
                                "rss_mb": f"{status['rss_mb']:.1f}",
                                "gc_count": status["gc_count"],
                            },
                        )
                        self.call_from_thread(
                            self._loop_widget.update_loops, status.get("loops", {})
                        )
                except Exception:
                    pass
                time.sleep(2)

        def _load_galaxy(self) -> None:
            """Load memory coordinates for the galaxy map."""
            try:
                from whitemagic.core.memory.unified import get_unified_memory
                mem = get_unified_memory()
                stats = mem.get_stats()
                total = stats.get("total_memories", 0)

                # Get a sample of memories with coordinates
                from whitemagic.core.intelligence.vector_lake import get_vector_lake
                lake = get_vector_lake()
                try:
                    sample = lake.get_holographic_sample(limit=200)
                except Exception:
                    sample = []

                if not sample:
                    # Generate placeholder positions from memory IDs
                    import random
                    random.seed(42)
                    sample = [
                        {
                            "id": f"mem_{i}",
                            "x": math.cos(i * 0.5) * (0.3 + random.random() * 0.5),
                            "y": math.sin(i * 0.5) * (0.3 + random.random() * 0.5),
                            "w": random.random(),
                        }
                        for i in range(min(80, total))
                    ]

                self._galaxy_widget.update_memories(sample)
                self._telemetry_widget.update_data({"memories": total})
            except Exception as e:
                self._chat_log.write(f"[red]Galaxy load error: {e}[/red]")

        def _load_agents(self) -> None:
            """Load registered agents from the interop registry."""
            try:
                from whitemagic.tools.handlers.agent_registry import (
                    _all_agents,
                    _is_active,
                )
                agents = _all_agents()
                summaries = [
                    {"name": a.get("name", "?"), "active": _is_active(a)}
                    for a in agents
                ]
                self._agent_widget.update_agents(summaries)
            except Exception:
                pass

        def action_refresh(self) -> None:
            """Refresh all data."""
            self._load_galaxy()
            self._load_agents()
            if self._chat_log:
                self._chat_log.write("[dim]Refreshed[/dim]")

        def action_toggle(self) -> None:
            """Toggle panel visibility."""
            if self.mode == "full":
                self.mode = "cockpit"
                self.query_one("#center-panel").add_class("hidden")
                self.query_one("#right-panel").add_class("hidden")
            elif self.mode == "cockpit":
                self.mode = "chat"
                self.query_one("#center-panel").add_class("hidden")
                self.query_one("#left-panel").add_class("hidden")
                self.query_one("#right-panel").remove_class("hidden")
            else:
                self.mode = "full"
                self.query_one("#left-panel").remove_class("hidden")
                self.query_one("#center-panel").remove_class("hidden")
                self.query_one("#right-panel").remove_class("hidden")
            if self._chat_log:
                self._chat_log.write(f"[dim]Mode: {self.mode}[/dim]")

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
            parts[1] if len(parts) > 1 else ""

            if command == "/quit":
                self.exit()
            elif command == "/status":
                try:
                    from whitemagic.core.consciousness.daemon import get_daemon
                    daemon = get_daemon()
                    status = daemon.status()
                    self._chat_log.write(json.dumps(status, indent=2))
                except Exception:
                    self._chat_log.write("[yellow]Daemon not running[/yellow]")
            elif command == "/agents":
                self._load_agents()
                self._chat_log.write("[dim]Agents refreshed[/dim]")
            elif command == "/galaxy":
                self._load_galaxy()
                self._chat_log.write("[dim]Galaxy refreshed[/dim]")
            elif command == "/interop":
                self._chat_log.write("[bold]Interop Commands:[/bold]")
                self._chat_log.write("  /agents  — List registered agents")
                self._chat_log.write("  /galaxy  — Refresh galaxy map")
                self._chat_log.write("  /status  — Daemon status")
                self._chat_log.write("  /help    — Show commands")
                self._chat_log.write("  /clear   — Clear chat")
                self._chat_log.write("  /quit    — Exit TUI")
            elif command == "/help":
                self._chat_log.write("[bold]Commands:[/bold]")
                self._chat_log.write("  /status   — Daemon telemetry")
                self._chat_log.write("  /agents   — List agents")
                self._chat_log.write("  /galaxy   — Refresh galaxy")
                self._chat_log.write("  /interop  — Interop commands")
                self._chat_log.write("  /clear    — Clear chat")
                self._chat_log.write("  /quit     — Exit")
                self._chat_log.write("")
                self._chat_log.write("[dim]Keys: r=refresh, t=toggle, q=quit[/dim]")
            elif command == "/clear":
                self._chat_log.clear()
            else:
                self._chat_log.write(f"[red]Unknown: {command}[/red]  [dim](try /help)[/dim]")

        def _handle_message(self, text: str) -> None:
            """Handle a chat message — route to daemon or echo."""
            if self._client and self._client.is_connected:
                try:
                    result = self._client.call_tool(
                        gana="horn",
                        tool="dispatch",
                        operation="chat",
                        args={"message": text},
                    )
                    self._chat_log.write(f"[bold green]WM:[/bold green] {json.dumps(result)}")
                except Exception as e:
                    self._chat_log.write(f"[red]Error: {e}[/red]")
            else:
                self._chat_log.write(
                    "[dim](local mode — start daemon for full interaction)[/dim]"
                )

else:
    # Fallback when textual is not available
    class CognitiveTUI:
        """Fallback TUI when textual is not installed."""

        def __init__(self, mode: str = "full") -> None:
            self.mode = mode

        def run(self) -> None:
            print("🌐 WhiteMagic Cognitive TUI")
            print("(textual not installed — using basic mode)")
            print("Install: pip install textual")
            print()

            # Show galaxy (Rich-based, works without textual)
            try:
                from rich.console import Console
                from rich.panel import Panel
                from rich.table import Table
                console = Console()

                # Galaxy map
                try:
                    from whitemagic.core.memory.unified import get_unified_memory
                    mem = get_unified_memory()
                    stats = mem.get_stats()
                    console.print(Panel(
                        f"Memories: {stats.get('total_memories', 0)}\n"
                        f"Galaxies: {stats.get('total_galaxies', 0)}",
                        title="[bold cyan]WhiteMagic Galaxy[/bold cyan]",
                        border_style="cyan",
                    ))
                except Exception:
                    console.print("[yellow]Memory system unavailable[/yellow]")

                # Agents
                try:
                    from whitemagic.tools.handlers.agent_registry import (
                        _all_agents,
                        _is_active,
                    )
                    agents = _all_agents()
                    if agents:
                        table = Table(title="Registered Agents")
                        table.add_column("Name")
                        table.add_column("Status")
                        for a in agents:
                            status = "🟢 active" if _is_active(a) else "🔴 stale"
                            table.add_row(a.get("name", "?"), status)
                        console.print(table)
                except Exception:
                    pass

                # Daemon status
                try:
                    from whitemagic.core.consciousness.daemon import get_daemon
                    daemon = get_daemon()
                    if daemon.is_running:
                        status = daemon.status()
                        console.print(Panel(
                            json.dumps(status, indent=2),
                            title="[bold]Daemon Status[/bold]",
                            border_style="green",
                        ))
                    else:
                        console.print("[yellow]Daemon not running — 'wm daemon start'[/yellow]")
                except Exception:
                    console.print("[yellow]Daemon unavailable[/yellow]")

                # Chat loop
                print("\nChat mode — type /quit to exit, /help for commands")
                while True:
                    try:
                        text = input("> ")
                        if text.strip() == "/quit":
                            break
                        if text.strip() == "/help":
                            print("Commands: /quit, /status, /agents, /help")
                        elif text.strip():
                            print("WM: (local mode — start daemon for full interaction)")
                    except (EOFError, KeyboardInterrupt):
                        break
            except ImportError:
                print("Install rich for better output: pip install rich")


def run_tui(mode: str = "full") -> None:
    """Run the cognitive TUI."""
    if HAS_TEXTUAL:
        app = CognitiveTUI(mode=mode)
        app.run()
    else:
        fallback = CognitiveTUI(mode=mode)
        fallback.run()
