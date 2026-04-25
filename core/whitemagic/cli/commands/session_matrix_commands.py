"""Session, Matrix, Graph and Observe CLI commands.

Extracted from cli_app.py as part of B1 decomposition (v22 roadmap).
All commands were previously defined inline in the 786-line cli_app.py.
"""
from __future__ import annotations

import click


def register_session_matrix_commands(main: click.Group, get_memory_fn, status_command, json_dumps_fn) -> None:
    """Register session, matrix, graph, and observe commands onto the main group."""

    @main.command()
    @click.option("--output", "-o", default="memory_graph.html", help="Output file for the graph")
    def graph(output: str) -> None:
        """Generate relationship graph for memories (v4.5.0)."""
        try:
            memory = get_memory_fn()
            nodes = []
            links = []
            all_memories = memory.search(limit=200)
            for i, mem in enumerate(all_memories):
                nodes.append({"id": mem.id, "title": mem.title or "Untitled", "group": str(mem.memory_type)})
                for tag in (mem.tags or set()):
                    links.append({"source": mem.id, "target": f"tag:{tag}", "value": 1})
            html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>WhiteMagic Memory Graph</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>body {{ font-family: Arial, sans-serif; margin: 0; }} #graph {{ width: 100vw; height: 100vh; }}</style>
</head>
<body>
    <div id="graph"></div>
    <script>
        const nodes = {json_dumps_fn(nodes)};
        const links = {json_dumps_fn(links)};
        const svg = d3.select("#graph").append("svg").attr("width", "100%").attr("height", "100%");
        const simulation = d3.forceSimulation(nodes)
            .force("link", d3.forceLink(links).id(d => d.id).distance(80))
            .force("charge", d3.forceManyBody().strength(-200))
            .force("center", d3.forceCenter(window.innerWidth / 2, window.innerHeight / 2));
        const link = svg.append("g").selectAll("line").data(links).join("line").attr("stroke", "#999").attr("stroke-opacity", 0.6);
        const node = svg.append("g").selectAll("circle").data(nodes).join("circle").attr("r", 8).attr("fill", "#69b3a2");
        node.append("title").text(d => d.title);
        simulation.on("tick", () => {{
            link.attr("x1", d => d.source.x).attr("y1", d => d.source.y).attr("x2", d => d.target.x).attr("y2", d => d.target.y);
            node.attr("cx", d => d.x).attr("cy", d => d.y);
        }});
    </script>
</body>
</html>"""
            with open(output, "w") as f:
                f.write(html_content)
            click.echo(f"✅ Graph generated: {output} ({len(nodes)} nodes, {len(links)} links)")
        except Exception as e:
            click.echo(f"❌ Failed to generate graph: {e}", err=True)

    @main.command(name="session-start")
    def session_start() -> None:
        """Bootstrap new session with full context loading."""
        click.echo("\n🚀 Starting WhiteMagic Session...")
        click.echo("=" * 40)
        try:
            from whitemagic.maintenance.capability_harness import run_harness
            report = run_harness()
            passed = getattr(report, "passed", 0)
            failed = getattr(report, "failed", 0)
            click.echo(f"\n✅ Session initialized with {passed}/{passed + failed} capabilities")
        except (ImportError, ModuleNotFoundError) as e:
            click.echo(f"⚠️  Warning: {e}")
        click.echo("\n📚 Use 'wm tools' to see available commands")

    @main.command(name="session-status")
    def session_status() -> None:
        """Show current session status."""
        ctx = click.get_current_context()
        ctx.invoke(status_command)

    @main.command(name="matrix-stats")
    def matrix_stats() -> None:
        """Show Memory Matrix statistics."""
        click.echo("\n📊 Memory Matrix Statistics")
        click.echo("=" * 40)
        try:
            memory = get_memory_fn()
            stats_data = memory.get_stats()
            total = stats_data["total_memories"]
            click.echo(f"Total memories: {total}")
            type_counts = stats_data.get("by_type", {})
            for mt_name, count in type_counts.items():
                click.echo(f"  {mt_name:<12}: {count}")
        except Exception as e:
            click.echo(f"⚠️  Matrix not available: {e}")

    @main.command(name="matrix-seen")
    @click.option("--limit", default=10, help="Max items")
    def matrix_seen(limit: int) -> None:
        """List recently accessed memories."""
        try:
            memory = get_memory_fn()
            recent_accessed = memory.list_accessed(limit=limit)
            click.echo("\n🧠 Recently Accessed Memories")
            click.echo("=" * 40)
            for mem in recent_accessed:
                preview = str(mem.content)
                if len(preview) > 80:
                    preview = preview[:77] + "..."
                click.echo(f"{mem.accessed_at.isoformat()} | {mem.memory_type.name:<10} | {mem.id} | tags={list(mem.tags)}")
                click.echo(f"  {preview}")
        except Exception as e:
            click.echo(f"⚠️  Matrix not available: {e}")

    @main.command(name="matrix-search")
    @click.option("--query", required=True, help="Text to search in content")
    @click.option("--limit", default=10, help="Max results")
    def matrix_search(query: str, limit: int) -> None:
        """Search memories by substring (quick local scan)."""
        try:
            memory = get_memory_fn()
            results = memory.search(query=query, limit=limit)
            click.echo(f"\n🔎 Matrix Search: '{query}' (showing up to {limit})")
            click.echo("=" * 50)
            for mem in results:
                preview = str(mem.content)
                if len(preview) > 120:
                    preview = preview[:117] + "..."
                click.echo(f"{mem.memory_type.name:<10} | {mem.id} | tags={list(mem.tags)}")
                click.echo(f"  {preview}")
            if not results:
                click.echo("No matches found.")
        except Exception as e:
            click.echo(f"⚠️  Matrix search unavailable: {e}")

    @main.command(name="activate-all")
    def activate_all() -> None:
        """Full system activation - bootstrap all capabilities."""
        click.echo("\n⚡ Activating All WhiteMagic Systems...")
        click.echo("=" * 40)
        ctx = click.get_current_context()
        ctx.invoke(session_start)
        ctx.invoke(status_command)
        click.echo("\n✅ Full system activation complete!")

    @main.command(name="manifest")
    def manifest() -> None:
        """Export tools as JSON manifest."""
        commands = {}
        for name, cmd in main.commands.items():
            commands[name] = {
                "help": cmd.help or "No description",
                "params": [p.name for p in cmd.params],
            }
        click.echo(json_dumps_fn(commands, indent=2))

    @main.command()
    def observe() -> None:
        """Real-time Gan Ying event viewer (v4.5.0)."""
        try:
            import time
            from collections import deque

            from rich.live import Live
            from rich.table import Table

            from whitemagic.core.resonance.gan_ying import get_bus
        except ImportError as e:
            click.echo(f"❌ Failed to import required modules: {e}")
            return

        bus = get_bus()
        events: deque = deque(maxlen=20)

        def on_event(event) -> None:
            events.append(event)

        if hasattr(bus, "listen_all"):
            bus.listen_all(on_event)
        else:
            click.echo("⚠️  GanYingBus does not support listen_all. Update core.")
            return

        def generate_table():
            table = Table(title="🔮 Gan Ying Resonance (Real-time)", expand=True)
            table.add_column("Time", style="cyan", no_wrap=True)
            table.add_column("Type", style="magenta")
            table.add_column("Source", style="green")
            table.add_column("Data", style="white")
            table.add_column("Conf", justify="right", style="yellow")
            for e in sorted(list(events), key=lambda ev: ev.timestamp, reverse=True):
                data_str = str(e.data)
                if len(data_str) > 50:
                    data_str = data_str[:47] + "..."
                table.add_row(
                    e.timestamp.strftime("%H:%M:%S.%f")[:-3],
                    e.event_type.name if hasattr(e.event_type, "name") else str(e.event_type),
                    e.source, data_str, f"{e.confidence:.2f}",
                )
            return table

        import importlib
        console = importlib.import_module("rich.console").Console()
        console.print("[bold green]Starting observer... Press Ctrl+C to stop.[/bold green]")
        try:
            with Live(generate_table(), refresh_per_second=4, console=console) as live:
                while True:
                    live.update(generate_table())
                    time.sleep(0.25)
        except KeyboardInterrupt:
            console.print("\n[bold yellow]Observer stopped.[/bold yellow]")
