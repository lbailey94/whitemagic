"""Dream Cycle CLI Commands — interface to the 12-phase dream engine.

The dream cycle is WhiteMagic's background processing system, inspired by
biological sleep. When the system is idle, it runs through phases that
consolidate memories, surface serendipitous connections, analyze patterns,
and integrate new knowledge.

Usage:
    wm dream start          Start the dream cycle
    wm dream stop           Stop dreaming
    wm dream status         Show current phase and stats
    wm dream report         Show what the system dreamed
    wm dream run            Run a single dream cycle now
    wm dream phases         List all 12 dream phases
"""

import click

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    # Markdown import removed — unused, add back if needed
    HAS_RICH = True
    console: Console | None = Console()
except ImportError:
    HAS_RICH = False
    console = None


@click.group(name="dream")
def dream_group() -> None:
    """Dream Cycle — background memory consolidation and insight generation."""


@dream_group.command(name="start")
@click.option("--interval", default=600, help="Dream cycle interval in seconds")
@click.option("--idle-threshold", default=120, help="Seconds of idle before dreaming")
def dream_start(interval: int, idle_threshold: int) -> None:
    """Start the Dream Cycle.

    The system will begin watching for idle periods. When no tool calls
    occur for the idle threshold, it enters the dream cycle: a sequence
    of 12 phases that consolidate memories, find serendipitous connections,
    analyze patterns, and integrate knowledge.
    """
    from whitemagic.core.dreaming.dream_cycle import get_dream_cycle

    dc = get_dream_cycle()
    dc.cycle_interval = interval
    dc.idle_threshold = idle_threshold
    dc.start()

    if HAS_RICH and console:
        console.print(
            Panel(
                f"[green]Dream Cycle started[/green]\n"
                f"  Interval: {interval}s\n"
                f"  Idle threshold: {idle_threshold}s\n"
                f"  Phases: 12 (triage → consolidation → serendipity → governance →\n"
                f"           narrative → kaizen → oracle → decay → constellation →\n"
                f"           prediction → enrichment → harmonize)\n\n"
                f"The system will dream when idle. Use [cyan]wm dream status[/cyan] to check.",
                title="Dream Cycle",
                border_style="green",
            )
        )
    else:
        click.echo(
            f"Dream Cycle started (interval={interval}s, idle={idle_threshold}s)"
        )


@dream_group.command(name="stop")
def dream_stop() -> None:
    """Stop the Dream Cycle."""
    from whitemagic.core.dreaming.dream_cycle import get_dream_cycle

    dc = get_dream_cycle()
    dc.stop()

    if HAS_RICH and console:
        console.print("[yellow]Dream Cycle stopped[/yellow]")
    else:
        click.echo("Dream Cycle stopped")


@dream_group.command(name="status")
def dream_status() -> None:
    """Show current Dream Cycle status.

    Displays whether the system is dreaming, the current phase, how many
    cycles have completed, and recent dream artifacts.
    """
    from whitemagic.core.dreaming.dream_cycle import get_dream_cycle

    dc = get_dream_cycle()
    status = dc.status()

    if HAS_RICH and console:
        table = Table(title="Dream Cycle Status", show_header=True)
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Running", "✅ yes" if status.get("running") else "❌ no")
        table.add_row("Dreaming", "💤 yes" if status.get("dreaming") else "⚪ idle")
        table.add_row("Current Phase", str(status.get("current_phase", "none")))
        table.add_row("Total Cycles", str(status.get("total_cycles", 0)))
        table.add_row("Idle Seconds", f"{status.get('idle_seconds', 0):.0f}s")
        table.add_row("Idle Threshold", f"{status.get('idle_threshold', 120):.0f}s")
        table.add_row("Cycle Interval", f"{status.get('cycle_interval', 600):.0f}s")

        recent = status.get("recent_dreams", [])
        if recent:
            table.add_row("Recent Dreams", f"{len(recent)} artifacts")
        else:
            table.add_row("Recent Dreams", "none yet")

        console.print(table)
    else:
        click.echo(f"Running: {status.get('running')}")
        click.echo(f"Dreaming: {status.get('dreaming')}")
        click.echo(f"Phase: {status.get('current_phase')}")
        click.echo(f"Cycles: {status.get('total_cycles', 0)}")
        click.echo(f"Recent dreams: {len(status.get('recent_dreams', []))}")


@dream_group.command(name="run")
def dream_run() -> None:
    """Run a single dream cycle now.

    Executes all 12 phases immediately, regardless of idle state.
    Useful for manual triggering or testing.
    """
    from whitemagic.core.dreaming.dream_cycle import get_dream_cycle

    dc = get_dream_cycle()

    if HAS_RICH and console:
        console.print("[cyan]Running single dream cycle...[/cyan]")

    dc.touch()  # Reset idle timer

    import asyncio

    try:
        asyncio.run(dc._run_phase())
        if dc._history:
            report = dc._history[-1]
            if HAS_RICH and console:
                console.print(
                    Panel(
                        f"[green]Dream cycle complete[/green]\n"
                        f"  Phase: {report.phase.value}\n"
                        f"  Duration: {report.duration_ms:.0f}ms\n"
                        f"  Success: {report.success}\n"
                        + (f"  Error: {report.error}\n" if report.error else "")
                        + (f"\n  Details: {report.details}" if report.details else ""),
                        title="Dream Report",
                        border_style="green",
                    )
                )
            else:
                click.echo(
                    f"Dream complete: phase={report.phase.value}, success={report.success}, duration={report.duration_ms:.0f}ms"
                )
        else:
            click.echo("Dream cycle ran but produced no report")
    except Exception as e:  # noqa: BLE001
        if HAS_RICH and console:
            console.print(f"[red]Dream cycle error: {e}[/red]")
        else:
            click.echo(f"Error: {e}")


@dream_group.command(name="report")
@click.option("--limit", default=10, help="Maximum dreams to show")
def dream_report(limit: int) -> None:
    """Show recent dream artifacts.

    Dreams are stored as artifacts that capture what the system
    consolidated, what serendipity it found, and what insights
    it promoted during each cycle.
    """
    try:
        from whitemagic.core.dreaming.dream_artifacts import list_dreams

        dreams = list_dreams()
        if limit > 0:
            dreams = dreams[:limit]
    except Exception as e:  # noqa: BLE001
        if HAS_RICH and console:
            console.print(f"[yellow]Could not load dream artifacts: {e}[/yellow]")
        else:
            click.echo(f"Could not load dream artifacts: {e}")
        return

    if not dreams:
        if HAS_RICH and console:
            console.print(
                Panel(
                    "[dim]No dreams yet. The system dreams when idle.[/dim]\n\n"
                    "To trigger a dream manually:\n"
                    "  [cyan]wm dream run[/cyan]\n\n"
                    "Or start automatic dreaming:\n"
                    "  [cyan]wm dream start[/cyan]",
                    title="Dream Journal",
                    border_style="dim",
                )
            )
        else:
            click.echo("No dreams yet. Use 'wm dream run' to dream manually.")
        return

    if HAS_RICH and console:
        table = Table(title="Dream Journal", show_header=True)
        table.add_column("#", style="dim", width=4)
        table.add_column("Phase", style="cyan")
        table.add_column("Status", style="white")
        table.add_column("Created", style="dim")
        table.add_column("Revisits", style="dim", justify="right")

        for i, dream in enumerate(dreams[:limit], 1):
            table.add_row(
                str(i),
                dream.get("phase", "?"),
                dream.get("status", "?"),
                dream.get("created_at", "?")[:19] if dream.get("created_at") else "?",
                str(dream.get("revisit_count", 0)),
            )
        console.print(table)
        console.print(
            f"\n[dim]{len(dreams)} dream artifacts. Use 'wm dream read <id>' for details.[/dim]"
        )
    else:
        for i, dream in enumerate(dreams[:limit], 1):
            click.echo(
                f"  {i}. [{dream.get('phase', '?')}] {dream.get('status', '?')} — {dream.get('created_at', '?')[:19]}"
            )


@dream_group.command(name="read")
@click.argument("dream_id")
def dream_read(dream_id: str) -> None:
    """Read a specific dream artifact by ID."""
    try:
        from whitemagic.core.dreaming.dream_artifacts import read_dream

        dream = read_dream(dream_id)
    except Exception as e:  # noqa: BLE001
        click.echo(f"Error: {e}")
        return

    if dream is None:
        click.echo(f"Dream not found: {dream_id}")
        return

    if HAS_RICH and console:
        content = dream.get("content", {})
        phase = content.get("phase", "unknown")
        details = content.get("details", {})
        success = content.get("success", True)

        panel_content = f"[bold cyan]Phase:[/bold cyan] {phase}\n"
        panel_content += (
            f"[bold]Status:[/bold] {'✅ success' if success else '❌ failed'}\n"
        )
        panel_content += (
            f"[bold]Duration:[/bold] {content.get('duration_ms', 0):.0f}ms\n"
        )
        panel_content += f"[bold]Created:[/bold] {content.get('created_at', '?')}\n"
        panel_content += f"[bold]Revisits:[/bold] {content.get('revisit_count', 0)}\n\n"

        if details:
            panel_content += "[bold]Details:[/bold]\n"
            for key, value in details.items():
                if isinstance(value, (list, dict)):
                    panel_content += f"  {key}: {len(value)} items\n"
                else:
                    panel_content += f"  {key}: {value}\n"

        if content.get("insights"):
            panel_content += "\n[bold green]Insights:[/bold green]\n"
            for insight in content.get("insights", [])[:5]:
                panel_content += f"  • {insight}\n"

        console.print(
            Panel(panel_content, title=f"Dream: {dream_id}", border_style="cyan")
        )
    else:
        click.echo(f"Dream: {dream_id}")
        click.echo(f"  Phase: {dream.get('phase', '?')}")
        click.echo(f"  Status: {dream.get('status', '?')}")
        click.echo(f"  Details: {dream.get('details', {})}")


@dream_group.command(name="phases")
def dream_phases() -> None:
    """List all 12 dream phases with descriptions."""
    phases = [
        ("1. TRIAGE", "Quick scan — identify memories needing attention"),
        ("2. CONSOLIDATION", "Hippampal replay — cluster and promote memories"),
        ("3. SERENDIPITY", "Surface unexpected cross-temporal connections"),
        ("4. GOVERNANCE", "Echo chamber detection — check for circular reasoning"),
        ("5. NARRATIVE", "Narrative compression — condense verbose memories"),
        ("6. KAIZEN", "Analyze tool usage patterns for improvement hints"),
        ("7. ORACLE", "Consult Grimoire for contextual recommendations"),
        ("8. DECAY", "Mindful forgetting — rotate old memories outward"),
        ("9. CONSTELLATION", "Auto-merge related memory constellations"),
        ("10. PREDICTION", "Predictive drift detection — forecast trends"),
        ("11. ENRICHMENT", "Entity extraction & semantic enrichment"),
        ("12. HARMONIZE", "Wu Xing balance & harmony tuning"),
    ]

    if HAS_RICH and console:
        table = Table(title="Dream Phases (12)", show_header=True)
        table.add_column("Phase", style="cyan")
        table.add_column("Description", style="white")
        for name, desc in phases:
            table.add_row(name, desc)
        console.print(table)
    else:
        for name, desc in phases:
            click.echo(f"  {name}: {desc}")


@dream_group.command(name="promote")
@click.argument("dream_id")
def dream_promote(dream_id: str) -> None:
    """Promote a dream artifact to a permanent memory."""
    try:
        from whitemagic.core.dreaming.dream_artifacts import promote_dream

        result = promote_dream(dream_id)
        if result:
            if HAS_RICH and console:
                console.print(
                    f"[green]Dream {dream_id} promoted to memory: {result.get('promoted_to_memory_id', '?')}[/green]"
                )
            else:
                click.echo(f"Promoted: {result.get('promoted_to_memory_id', '?')}")
        else:
            click.echo(f"Dream not found: {dream_id}")
    except Exception as e:  # noqa: BLE001
        click.echo(f"Error: {e}")
