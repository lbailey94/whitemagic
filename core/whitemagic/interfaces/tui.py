"""WhiteMagic Cognitive Cockpit — Multi-mode TUI

Upgrades the original GalaxyTUI into a multi-mode observatory for the
cognitive substrate. Not a chat interface — a visual control panel.

Modes:
    1. Galaxy     — 4D holographic memory space (original view)
    2. Telemetry  — System health, coherence, self-model forecasts
    3. Tools      — Tool registry browser with schemas
    4. Dream      — Dream cycle status and artifact viewer

The TUI reuses CLI commands internally — it's a view layer, not a separate API.
"""
from typing import Any

from textual.app import App, ComposeResult  # type: ignore[import-not-found]
from textual.containers import Horizontal, Vertical  # type: ignore[import-not-found]
from textual.reactive import reactive  # type: ignore[import-not-found]
from textual.widgets import (  # type: ignore[import-not-found]
    DataTable,
    Footer,
    Header,
    Label,
    Static,
)

from whitemagic import __version__

try:
    from whitemagic.core.memory.unified import get_unified_memory
    HAS_MEMORY = True
except ImportError:
    HAS_MEMORY = False


class GalaxyStats(Static):
    """Widget to display galaxy statistics."""

    total_stars = reactive(0)
    clusters = reactive(0)

    def compose(self) -> ComposeResult:
        yield Label("🌌 Galaxy Stats", classes="box-title")
        yield Label(f"Stars: {self.total_stars}", id="stat-stars")
        yield Label(f"Clusters: {self.clusters}", id="stat-clusters")

    def watch_total_stars(self, val: int) -> None:
        self.query_one("#stat-stars", Label).update(f"Stars: {val}")

    def watch_clusters(self, val: int) -> None:
        self.query_one("#stat-clusters", Label).update(f"Clusters: {val}")


class GalaxyMap(Static):
    """Widget to display the 4D holographic map."""

    def on_mount(self) -> None:
        self.update_map([])

    def update_map(self, memories: list[Any]) -> None:
        from whitemagic.tools.tui.galaxy import GalaxyExplorer
        explorer = GalaxyExplorer(memories)
        width = self.size.width - 2
        height = self.size.height - 2
        if width <= 0:
            width = 60
        if height <= 0:
            height = 20
        self.update(explorer.generate_map(width, height))


class TelemetryPanel(Static):
    """System telemetry: health, coherence, self-model."""

    def render_telemetry(self) -> None:
        from whitemagic.tools.unified_api import call_tool

        lines: list[str] = []

        try:
            result = call_tool("health_report")
            data = result.get("details", result) if isinstance(result, dict) else result
            if isinstance(data, dict):
                score = data.get("health_score", 0)
                status = data.get("health_status", "?")
                lines.append(f"[bold]Health:[/bold] {status} ({score:.0%})")
                if "db" in data:
                    db = data["db"]
                    lines.append(f"[bold]DB:[/bold] {db.get('memory_count', '?')} memories, {db.get('size_mb', '?')} MB")
                rust = data.get("rust", {}).get("available", False)
                lines.append(f"[bold]Rust:[/bold] {'yes' if rust else 'no'}")
        except Exception as e:
            lines.append(f"[red]Health error: {e}[/]")

        try:
            from whitemagic.core.intelligence.agentic.coherence_persistence import (
                get_coherence,
            )
            coh = get_coherence()
            stats = coh.get_iteration_stats()
            level = stats.get("coherence_level", 100)
            color = "green" if level >= 50 else "red"
            lines.append(f"\n[bold]Coherence:[/bold] [{color}]{level}%[/]")
            lines.append(f"  Iterations: {stats.get('iteration_count', 0)}")
            lines.append(f"  Calls/hr: {stats.get('calls_this_hour', 0)}/100")
        except ImportError:
            lines.append("\n[dim]Coherence: not available[/]")

        try:
            result = call_tool("selfmodel.forecast")
            data = result.get("details", result) if isinstance(result, dict) else result
            if isinstance(data, dict):
                lines.append("\n[bold]Self-Model Forecast:[/bold]")
                alerts = data.get("alerts", [])
                for alert in alerts[:5]:
                    lines.append(f"  ! {alert}")
                if not alerts:
                    lines.append("  [green]No alerts - all systems nominal[/]")
        except Exception:
            lines.append("\n[dim]Self-Model: not available[/]")

        try:
            result = call_tool("galactic.stats")
            data = result.get("details", result) if isinstance(result, dict) else result
            if isinstance(data, dict):
                lines.append("\n[bold]Galactic Distribution:[/bold]")
                for zone, count in data.get("zone_counts", {}).items():
                    lines.append(f"  {zone}: {count}")
        except Exception:
            pass

        self.update("\n".join(lines))


class ToolsPanel(Static):
    """Tool registry browser."""

    def render_tools(self) -> None:
        from whitemagic.tools.registry import get_all_tools

        try:
            tools = get_all_tools()
            lines: list[str] = [f"[bold]Callable Tools: {len(tools)}[/]\n"]

            by_cat: dict[str, list] = {}
            for t in tools:
                cat = t.category.value if hasattr(t.category, 'value') else str(t.category)
                by_cat.setdefault(cat, []).append(t)

            for cat in sorted(by_cat.keys()):
                lines.append(f"[bold cyan]{cat}[/] ({len(by_cat[cat])})")
                for t in by_cat[cat][:5]:
                    desc = (t.description or "")[:60]
                    lines.append(f"  {t.name:<30} {desc}")
                if len(by_cat[cat]) > 5:
                    lines.append(f"  ... and {len(by_cat[cat]) - 5} more")
                lines.append("")

            self.update("\n".join(lines))
        except Exception as e:
            self.update(f"[red]Error loading tools: {e}[/]")


class DreamPanel(Static):
    """Dream cycle status and artifacts."""

    def render_dream(self) -> None:
        from whitemagic.tools.unified_api import call_tool

        lines: list[str] = []

        try:
            result = call_tool("dream_status")
            data = result.get("details", result) if isinstance(result, dict) else result
            if isinstance(data, dict):
                lines.append("[bold]Dream Cycle Status[/]\n")
                lines.append(f"  Active: {data.get('dreaming', data.get('active', False))}")
                lines.append(f"  Current phase: {data.get('current_phase', '?')}")
                lines.append(f"  Total cycles: {data.get('total_cycles', 0)}")
                lines.append(f"  Idle threshold: {data.get('idle_threshold', '?')}s")

                recent = data.get("recent_dreams", [])
                if recent:
                    lines.append(f"\n[bold]Recent Dreams ({len(recent)}):[/]")
                    for dream in recent[:5]:
                        if isinstance(dream, dict):
                            lines.append(f"  - {dream.get('phase', '?')}: {str(dream.get('summary', ''))[:60]}")
        except Exception as e:
            lines.append(f"[red]Dream status error: {e}[/]")

        try:
            result = call_tool("dream.report")
            data = result.get("details", result) if isinstance(result, dict) else result
            if isinstance(data, dict):
                artifacts = data.get("artifacts", [])
                lines.append(f"\n[bold]Artifacts: {len(artifacts)}[/]")
                for a in artifacts[:5]:
                    if isinstance(a, dict):
                        lines.append(f"  - [{a.get('type', '?')}] {str(a.get('title', ''))[:50]}")
        except Exception:
            pass

        self.update("\n".join(lines) if lines else "[dim]Dream cycle not available[/]")


class CognitiveCockpit(App):
    """Multi-mode Cognitive Cockpit for WhiteMagic.

    Modes:
        1. galaxy    - 4D holographic memory space
        2. telemetry - System health and self-model
        3. tools     - Tool registry browser
        4. dream     - Dream cycle status
    """

    CSS = """
    Screen {
        layout: vertical;
    }

    #main-container {
        height: 100%;
    }

    #sidebar {
        width: 20%;
        height: 100%;
        border: solid green;
    }

    #view-area {
        width: 80%;
        height: 100%;
    }

    .box {
        border: solid green;
    }

    .box-title {
        text-align: center;
        background: $accent;
        color: $text;
        padding: 1;
    }

    GalaxyMap {
        height: 100%;
        border: double cyan;
        content-align: center middle;
    }

    TelemetryPanel {
        height: 100%;
        padding: 1 2;
        border: solid yellow;
    }

    ToolsPanel {
        height: 100%;
        padding: 1 2;
        border: solid blue;
    }

    DreamPanel {
        height: 100%;
        padding: 1 2;
        border: solid magenta;
    }

    DataTable {
        height: 100%;
        border: solid blue;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("1", "switch_mode('galaxy')", "Galaxy"),
        ("2", "switch_mode('telemetry')", "Telemetry"),
        ("3", "switch_mode('tools')", "Tools"),
        ("4", "switch_mode('dream')", "Dream"),
    ]

    current_mode = reactive("galaxy")

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Horizontal(
            Vertical(
                GalaxyStats(classes="box"),
                Static(
                    "Controls\n\n"
                    "[1] Galaxy\n"
                    "[2] Telemetry\n"
                    "[3] Tools\n"
                    "[4] Dream\n"
                    "[r] Refresh\n"
                    "[q] Quit",
                    classes="box",
                ),
                id="sidebar",
            ),
            Vertical(
                GalaxyMap(id="galaxy_view"),
                DataTable(id="memory_table"),
                id="view-area",
            ),
            id="main-container",
        )
        yield Footer()

    def on_mount(self) -> None:
        self.title = f"WhiteMagic Cockpit v{__version__}"
        self.sub_title = "Galaxy Mode"
        self.set_timer(0.2, self.action_refresh)

    def action_switch_mode(self, mode: str) -> None:
        """Switch between cockpit modes."""
        self.current_mode = mode
        self.sub_title = f"{mode.title()} Mode"

        view_area = self.query_one("#view-area")
        for widget_id in ["galaxy_view", "telemetry_view", "tools_view", "dream_view", "memory_table"]:
            try:
                w = self.query_one(f"#{widget_id}")
                w.remove()
            except Exception:
                pass

        if mode == "galaxy":
            galaxy = GalaxyMap(id="galaxy_view")
            table = DataTable(id="memory_table")
            view_area.mount(galaxy)
            view_area.mount(table)
        elif mode == "telemetry":
            panel = TelemetryPanel(id="telemetry_view")
            view_area.mount(panel)
            panel.render_telemetry()
        elif mode == "tools":
            panel = ToolsPanel(id="tools_view")
            view_area.mount(panel)
            panel.render_tools()
        elif mode == "dream":
            panel = DreamPanel(id="dream_view")
            view_area.mount(panel)
            panel.render_dream()

        self.notify(f"Switched to {mode.title()} mode")

    def action_refresh(self) -> None:
        """Refresh data for the current mode."""
        mode = self.current_mode

        if mode == "galaxy":
            self._refresh_galaxy()
        elif mode == "telemetry":
            try:
                panel = self.query_one("#telemetry_view", TelemetryPanel)
                panel.render_telemetry()
            except Exception:
                pass
        elif mode == "tools":
            try:
                panel = self.query_one("#tools_view", ToolsPanel)
                panel.render_tools()
            except Exception:
                pass
        elif mode == "dream":
            try:
                panel = self.query_one("#dream_view", DreamPanel)
                panel.render_dream()
            except Exception:
                pass

    def _refresh_galaxy(self) -> None:
        """Refresh galaxy mode data."""
        if not HAS_MEMORY:
            self.notify("Error: WhiteMagic Core not available", severity="error")
            return

        memory = get_unified_memory()
        stats = memory.get_stats()
        galaxy_stats = self.query_one(GalaxyStats)
        galaxy_stats.total_stars = stats.get("total_memories", 0)
        galaxy_stats.clusters = stats.get("total_topics", 0)

        try:
            from whitemagic.core.intelligence.vector_lake import get_vector_lake
            lake = get_vector_lake()
            raw_results = lake.get_holographic_sample(limit=100)

            try:
                self.query_one(GalaxyMap).update_map(raw_results)
            except Exception:
                pass

            try:
                table = self.query_one(DataTable)
                table.clear(columns=True)
                table.add_columns("ID", "Title", "X", "Y", "W")
                for m in raw_results:
                    mid = str(m.get("id", ""))[:8]
                    title = str(m.get("title", "Untitled"))[:30]
                    x = f"{m.get('x', 0):.2f}"
                    y = f"{m.get('y', 0):.2f}"
                    w = f"{m.get('w', 0):.2f}"
                    table.add_row(mid, title, x, y, w)
            except Exception:
                pass

            self.notify(f"Synchronized {len(raw_results)} stars")
        except Exception as e:
            self.notify(f"Refresh error: {e}", severity="warning")


GalaxyTUI = CognitiveCockpit


if __name__ == "__main__":
    CognitiveCockpit().run()
