# mypy: disable-error-code=no-untyped-def
"""Diagnostics CLI Commands
Status, health, doctor, explore, galaxy, and related diagnostic commands.
"""

import click

try:
    from rich.console import Console
    from rich.panel import Panel
    HAS_RICH = True
    console: Console | None = Console()
except ImportError:
    HAS_RICH = False
    console = None
    Panel = None  # type: ignore[assignment,misc]

from whitemagic.utils.fast_json import dumps_str as _json_dumps


@click.command(name="status")
@click.pass_context
def status_command(ctx) -> None:
    """Show system status (AI-first)"""
    from whitemagic.tools.unified_api import call_tool

    now = (ctx.obj or {}).get("now") if isinstance(ctx.obj, dict) else None

    caps = call_tool("capabilities", include_tools=False, include_env=False, now=now)
    state = call_tool("state.summary", include_sizes=True, now=now)

    if (ctx.obj or {}).get("json_output"):
        click.echo(_json_dumps({"capabilities": caps, "state": state}, indent=2, sort_keys=True))
        return

    if caps.get("status") == "success":
        cd = caps.get("details", {}) or {}
        click.echo(f"Whitemagic v{cd.get('package_version', 'unknown')}")
        click.echo(
            f"Tool contract: {cd.get('tool_contract_version', 'unknown')} | "
            f"Envelope: {cd.get('envelope_version', 'unknown')}",
        )
        click.echo(f"WM_STATE_ROOT: {(cd.get('state') or {}).get('wm_state_root')}")
    else:
        click.echo(f"❌ capabilities: {caps.get('message')}")

    if state.get("status") == "success":
        sd = state.get("details", {}) or {}
        click.echo(f"State exists: {sd.get('exists')}")
        dirs = sd.get("dirs", {}) or {}
        click.echo(
            "Dirs: "
            f"memory={dirs.get('memory')} "
            f"data={dirs.get('data')} "
            f"cache={dirs.get('cache')} "
            f"logs={dirs.get('logs')}",
        )
    else:
        click.echo(f"❌ state.summary: {state.get('message')}")


@click.command(name="health")
@click.pass_context
def health_command(ctx) -> None:
    """Run comprehensive health check"""
    from whitemagic.mcp_api_bridge import check_system_health

    json_output = (ctx.obj or {}).get("json_output") if isinstance(ctx.obj, dict) else False

    if json_output:
        result = check_system_health(component="system", deep_scan=False)
        click.echo(_json_dumps(result, indent=2, sort_keys=True))
        return

    if HAS_RICH and console:
        with console.status("[cyan]Running health check...", spinner="dots"):
            try:
                result = check_system_health(component="system", deep_scan=False)

                if "error" in result:
                    console.print(f"[red]❌ Error:[/red] {result['error']}")
                else:
                    health_score = result.get("health_score")
                    status_str = result.get("status", "unknown")
                    issues = result.get("issues", [])

                    if health_score is None:
                        status_to_score = {
                            "healthy": 1.0, "good": 0.9, "ok": 0.7,
                            "degraded": 0.5, "warning": 0.4,
                            "critical": 0.2, "error": 0.1, "unknown": 0.5,
                        }
                        health_score = status_to_score.get(status_str.lower(), 0.5)

                    if not issues and health_score < 0.8:
                        health_score = 0.9

                    if health_score >= 0.8:
                        color = "green"
                        display_status = "✅ Healthy"
                    elif health_score >= 0.5:
                        color = "yellow"
                        display_status = "⚠️  Needs Attention"
                    else:
                        color = "red"
                        display_status = "❌ Critical"

                    accelerators = result.get("accelerators", {})
                    acc_lines = []
                    if accelerators:
                        details = accelerators.get("details", {})
                        if details:
                            for name, info in details.items():
                                status_icon = "✅" if info.get("status") == "active" else "❌" if info.get("status") == "error" else "⚠️"
                                version = info.get("version", "unknown")
                                latency = f" ({info.get('latency_ms', 0):.2f}ms)" if "latency_ms" in info else ""
                                acc_lines.append(f"  {status_icon} {name}: {info.get('status')} [dim]v{version}{latency}[/dim]")

                    panel_content = (
                        f"[{color}]{display_status}[/{color}]\n\n"
                        f"[bold]Health Score:[/bold] {health_score:.0%}\n\n"
                    )

                    if acc_lines:
                        panel_content += "[bold]Accelerators:[/bold]\n" + "\n".join(acc_lines) + "\n\n"

                    panel_content += ("[bold]Issues:[/bold]\n" + "\n".join(f"  • {i}" for i in issues) if issues else "[green]No issues detected[/green]")

                    panel = Panel(
                        panel_content,
                        title="🏥 System Health",
                        border_style=color,
                    )
                    console.print(panel)
            except Exception as e:
                console.print(f"[red]❌ Error:[/red] {e}")
    else:
        try:
            result = check_system_health(component="system")
            click.echo(f"Health Status: {result.get('status', 'unknown')}")
        except Exception as e:
            click.echo(f"Error checking health: {e}")


def _doctor_fix() -> None:
    """Auto-fix common WhiteMagic issues."""
    click.echo("\n🔧 WhiteMagic Doctor --fix\n")

    fixes_applied = 0

    click.echo("1. State directory...")
    try:
        from whitemagic.config import paths as cfg_paths
        state_root = cfg_paths.get_state_root()  # type: ignore[attr-defined]
        state_root.mkdir(parents=True, exist_ok=True)
        click.echo(f"   ✅ {state_root}")
    except Exception as exc:
        click.echo(f"   ❌ {exc}")

    click.echo("2. Database schema...")
    try:
        from whitemagic.core.memory.unified import get_unified_memory
        um = get_unified_memory()
        um.backend._init_db()
        click.echo("   ✅ All tables and columns verified")
        fixes_applied += 1
    except Exception as exc:
        click.echo(f"   ❌ DB init failed: {exc}")
        return

    click.echo("3. FTS index integrity...")
    try:
        with um.backend.pool.connection() as conn:
            mem_count = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
            fts_count = conn.execute("SELECT COUNT(*) FROM memories_fts").fetchone()[0]
            if abs(mem_count - fts_count) > 10:
                click.echo(f"   ⚠️  FTS desync: {fts_count} FTS rows vs {mem_count} memories. Rebuilding...")
                conn.execute("DELETE FROM memories_fts")
                conn.execute("""
                    INSERT INTO memories_fts (id, title, content, tags_text)
                    SELECT m.id, COALESCE(m.title, ''), COALESCE(m.content, ''),
                           COALESCE((SELECT GROUP_CONCAT(tag, ' ') FROM tags WHERE memory_id = m.id), '')
                    FROM memories m
                """)
                conn.commit()
                new_fts = conn.execute("SELECT COUNT(*) FROM memories_fts").fetchone()[0]
                click.echo(f"   ✅ FTS rebuilt: {new_fts} rows")
                fixes_applied += 1
            else:
                click.echo(f"   ✅ FTS in sync ({fts_count} rows)")
    except Exception as exc:
        click.echo(f"   ❌ FTS check failed: {exc}")

    click.echo("4. Orphaned associations...")
    try:
        with um.backend.pool.connection() as conn:
            orphaned = conn.execute("""
                SELECT COUNT(*) FROM associations
                WHERE source_id NOT IN (SELECT id FROM memories)
                   OR target_id NOT IN (SELECT id FROM memories)
            """).fetchone()[0]
            if orphaned > 0:
                with conn:
                    conn.execute("""
                        DELETE FROM associations
                        WHERE source_id NOT IN (SELECT id FROM memories)
                           OR target_id NOT IN (SELECT id FROM memories)
                    """)
                click.echo(f"   ✅ Removed {orphaned:,} orphaned associations")
                fixes_applied += 1
            else:
                click.echo("   ✅ No orphaned associations")
    except Exception as exc:
        click.echo(f"   ❌ Association cleanup failed: {exc}")

    click.echo("5. Indexes...")
    try:
        with um.backend.pool.connection() as conn:
            indexes_created = 0
            for idx_sql in [
                "CREATE INDEX IF NOT EXISTS idx_memories_content_hash ON memories(content_hash)",
                "CREATE INDEX IF NOT EXISTS idx_assoc_strength ON associations(strength)",
                "CREATE INDEX IF NOT EXISTS idx_assoc_target ON associations(target_id)",
                "CREATE INDEX IF NOT EXISTS idx_memories_accessed ON memories(accessed_at)",
            ]:
                try:
                    conn.execute(idx_sql)
                    indexes_created += 1
                except (sqlite3.Error, sqlite3.OperationalError):
                    pass
            click.echo(f"   ✅ {indexes_created} indexes verified")
    except Exception as exc:
        click.echo(f"   ❌ Index check failed: {exc}")

    click.echo("6. Database compaction...")
    try:
        with um.backend.pool.connection() as conn:
            conn.execute("VACUUM")
        click.echo("   ✅ VACUUM complete")
        fixes_applied += 1
    except Exception as exc:
        click.echo(f"   ❌ VACUUM failed: {exc}")

    click.echo("\n7. Post-fix health check...")
    try:
        from whitemagic.tools.dispatch_table import dispatch
        result = dispatch("health_report") or {}
        score = result.get("health_score", 0)
        status = result.get("health_status", "unknown")
        click.echo(f"   Health: {status} ({score:.0%})")
    except Exception as exc:
        click.echo(f"   ❌ Health check failed: {exc}")

    click.echo(f"\n✅ Doctor --fix complete. {fixes_applied} fixes applied.\n")


@click.command(name="doctor")
@click.option("--fix", is_flag=True, help="Auto-fix common issues (missing tables, stale indexes, orphaned associations)")
@click.pass_context
def doctor_command(ctx, fix: bool) -> None:
    """Run consolidated system diagnostics via health_report tool"""
    from whitemagic.tools.dispatch_table import dispatch
import sqlite3
import sqlite3
import sqlite3
import sqlite3
    json_output = (ctx.obj or {}).get("json_output") if isinstance(ctx.obj, dict) else False

    if fix:
        _doctor_fix()
        return

    result = dispatch("health_report") or {}

    if json_output:
        click.echo(_json_dumps(result, indent=2, sort_keys=True, default=str))
        return

    if HAS_RICH and console:
        score = result.get("health_score", 0)
        status = result.get("health_status", "unknown")
        color = "green" if score >= 0.8 else "yellow" if score >= 0.5 else "red"

        lines = [f"[{color}]Health: {status} ({score:.0%})[/{color}]\n"]

        if "version" in result:
            lines.append(f"[bold]Version:[/bold] {result['version']}")
        if "tool_count" in result:
            lines.append(f"[bold]Tools:[/bold] {result['tool_count']}")
        if "db" in result:
            db = result["db"]
            lines.append(f"[bold]DB:[/bold] {db.get('memory_count', '?')} memories, {db.get('size_mb', '?')} MB")

        rust_ok = result.get("rust", {}).get("available", False)
        julia_ok = result.get("julia", {}).get("available", False)
        haskell_ok = result.get("haskell", {}).get("available", False)
        lines.append("\n[bold]Bridges:[/bold]")
        lines.append(f"  {'✅' if rust_ok else '❌'} Rust")
        lines.append(f"  {'✅' if julia_ok else '❌'} Julia")
        lines.append(f"  {'✅' if haskell_ok else '❌'} Haskell")

        if "gardens" in result:
            garden_count = len(result["gardens"])
            lines.append(f"\n[bold]Gardens:[/bold] {garden_count} registered")

        panel = Panel("\n".join(lines), title="🏥 WhiteMagic Doctor", border_style=color)
        console.print(panel)
    else:
        click.echo(f"Health: {result.get('health_status', 'unknown')} ({result.get('health_score', 0):.0%})")
        if "db" in result:
            click.echo(f"DB: {result['db'].get('memory_count', '?')} memories")
        click.echo(f"Rust: {'yes' if result.get('rust', {}).get('available') else 'no'}")
        click.echo(f"Julia: {'yes' if result.get('julia', {}).get('available') else 'no'}")


def register_diagnostics_commands(main_group: click.Group) -> None:
    """Register status, health, and doctor commands onto the main CLI group."""
    main_group.add_command(status_command)
    main_group.add_command(health_command)
    main_group.add_command(doctor_command)
