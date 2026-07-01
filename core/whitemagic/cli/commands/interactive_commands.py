# ruff: noqa: BLE001
# mypy: disable-error-code=no-untyped-def
"""Interactive CLI commands for AI agents.

Commands:
    wm repl       — Interactive REPL with tab-completion, /help, /tools, /dharma
    wm stream     — NDJSON event stream for long-running operations
    wm pipeline   — Chain tool calls, passing details from one stage to the next
"""

import asyncio
import json as json_lib
from typing import Any

import click

from whitemagic.utils.fast_json import dumps_str as _json_dumps

# wm repl — Interactive REPL


@click.command()
@click.option("--json", "json_mode", is_flag=True, help="Start in JSON output mode")
@click.option(
    "--dharma", is_flag=True, help="Auto-evaluate Dharma before each tool call"
)
@click.pass_context
def repl(ctx, json_mode: bool, dharma: bool) -> None:
    """Interactive REPL for AI agents with tab-completion and slash commands.

    Slash commands:
        /help [command]    Show help for a command or all commands
        /tools             List all callable tools
        /dharma on|off     Toggle Dharma pre-evaluation
        /json on|off       Toggle JSON output mode
        /history           Show command history
        /quit              Exit REPL
    """
    import shlex

    from whitemagic.tools.unified_api import call_tool

    json_output = json_mode or (
        (ctx.obj or {}).get("json_output", False)
        if isinstance(ctx.obj, dict)
        else False
    )
    dharma_on = dharma

    try:
        import readline  # noqa: F401 — enables history/arrow keys

        _has_readline = True
    except ImportError:
        _has_readline = False

    # Build command list for completion
    try:
        from whitemagic.tools.dispatch_table import DISPATCH_TABLE

        tool_names = sorted(DISPATCH_TABLE.keys())
    except ImportError:
        tool_names = []

    slash_commands = ["/help", "/tools", "/dharma", "/json", "/history", "/quit"]

    click.echo("WhiteMagic REPL — type /help for commands, /quit to exit")
    click.echo(f"  JSON mode: {'on' if json_output else 'off'}")
    click.echo(f"  Dharma guard: {'on' if dharma_on else 'off'}")
    click.echo()

    history: list[str] = []

    while True:
        try:
            prompt = "wm> " if not json_output else "wm[json]> "
            line = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            click.echo("\nGoodbye!")
            break

        if not line:
            continue

        history.append(line)

        # Slash commands
        if line.startswith("/"):
            parts = line.split(None, 1)
            cmd = parts[0]
            arg = parts[1] if len(parts) > 1 else ""

            if cmd == "/quit":
                click.echo("Goodbye!")
                break
            elif cmd == "/help":
                if arg:
                    # Show help for specific tool
                    try:
                        result = call_tool(arg, _dry_run=True)
                        click.echo(
                            _json_dumps(result, indent=2)
                            if json_output
                            else str(result)
                        )
                    except Exception as e:
                        click.echo(f"Error getting help for '{arg}': {e}", err=True)
                else:
                    click.echo("Available slash commands:")
                    for sc in slash_commands:
                        click.echo(f"  {sc}")
                    click.echo()
                    click.echo(f"Callable tools ({len(tool_names)}):")
                    for name in tool_names[::20]:
                        click.echo(f"  {name}")
                    if len(tool_names) > 20:
                        click.echo(
                            f"  ... and {len(tool_names) - 20} more (use /tools for full list)"
                        )
            elif cmd == "/tools":
                if json_output:
                    click.echo(_json_dumps({"tools": tool_names}, indent=2))
                else:
                    click.echo(f"\nCallable tools ({len(tool_names)}):")
                    for name in tool_names:
                        click.echo(f"  {name}")
                    click.echo()
            elif cmd == "/dharma":
                if arg == "on":
                    dharma_on = True
                    click.echo("Dharma guard: ON — will evaluate before each tool call")
                elif arg == "off":
                    dharma_on = False
                    click.echo("Dharma guard: OFF")
                else:
                    click.echo(f"Dharma guard: {'on' if dharma_on else 'off'}")
            elif cmd == "/json":
                if arg == "on":
                    json_output = True
                    click.echo("JSON mode: ON")
                elif arg == "off":
                    json_output = False
                    click.echo("JSON mode: OFF")
                else:
                    click.echo(f"JSON mode: {'on' if json_output else 'off'}")
            elif cmd == "/history":
                for i, h in enumerate(history[-20:], 1):
                    click.echo(f"  {i:3d}  {h}")
            else:
                click.echo(f"Unknown slash command: {cmd}. Try /help")
            continue

        # Tool call: parse as "tool_name key=value key=value ..."
        try:
            tokens = shlex.split(line)
        except ValueError as e:
            click.echo(f"Parse error: {e}", err=True)
            continue

        if not tokens:
            continue

        tool_name = tokens[0]
        kwargs: dict[str, Any] = {}

        for token in tokens[1:]:
            if "=" in token:
                key, val = token.split("=", 1)
                try:
                    kwargs[key] = json_lib.loads(val)
                except json_lib.JSONDecodeError:
                    kwargs[key] = val
            else:
                # Positional arg — pass as "query" if not already set
                if "query" not in kwargs:
                    kwargs["query"] = token
                else:
                    kwargs.setdefault("args", []).append(token)

        # Dharma pre-evaluation
        if dharma_on:
            try:
                dharma_result = call_tool(
                    "evaluate_ethics", action=tool_name, params=kwargs
                )
                if (
                    isinstance(dharma_result, dict)
                    and dharma_result.get("status") == "error"
                ):
                    click.echo(
                        f"⚠️  Dharma blocked: {dharma_result.get('details', {}).get('reason', 'unknown')}"
                    )
                    if json_output:
                        click.echo(_json_dumps(dharma_result, indent=2))
                    continue
            except Exception as e:
                click.echo(f"(Dharma check skipped: {e})")

        try:
            result = call_tool(tool_name, **kwargs)
            if json_output:
                click.echo(_json_dumps(result, indent=2))
            else:
                status = result.get("status", "?") if isinstance(result, dict) else "?"
                if status == "success":
                    details = (
                        result.get("details", result)
                        if isinstance(result, dict)
                        else result
                    )
                    click.echo(_json_dumps(details, indent=2, default=str)[:2000])
                else:
                    click.echo(_json_dumps(result, indent=2, default=str)[:2000])
        except Exception as e:
            click.echo(f"Error: {e}", err=True)


# wm stream — NDJSON Event Streaming


@click.command()
@click.argument(
    "source",
    type=click.Choice(
        [
            "dream",
            "observe",
            "self-improve",
            "coherence",
            "events",
        ]
    ),
)
@click.option("--interval", "-i", default=2.0, help="Polling interval in seconds")
@click.option("--max-events", "-n", default=0, help="Max events (0 = unlimited)")
@click.option("--filter", "-f", help="Filter events by type prefix")
@click.pass_context
def stream(
    ctx, source: str, interval: float, max_events: int, filter: str | None
) -> None:
    """Stream events as NDJSON (newline-delimited JSON).

    Sources:
        dream        — Dream cycle phase events
        observe      — Gan Ying resonance events
        self-improve — Self-improvement cycle events
        coherence    — Coherence/burnout alerts
        events       — Raw event bus (all events)
    """
    count = 0

    def emit(event: dict[str, Any]) -> None:
        """Emit one NDJSON line."""
        nonlocal count
        if filter and not str(
            event.get("type", event.get("event_type", ""))
        ).startswith(filter):
            return
        click.echo(_json_dumps(event, default=str))
        count += 1

    if source == "dream":
        from whitemagic.core.dreaming import get_dream_cycle

        cycle = get_dream_cycle()
        click.echo(
            _json_dumps(
                {
                    "type": "stream_start",
                    "source": "dream",
                    "phase": cycle.get_status().get("current_phase", "?"),
                }
            )
        )

        prev_phase = None
        try:
            while max_events == 0 or count < max_events:
                status = cycle.get_status()
                current_phase = status.get("current_phase", "?")
                if current_phase != prev_phase:
                    emit(
                        {
                            "type": "dream_phase",
                            "phase": current_phase,
                            "status": status,
                        }
                    )
                    prev_phase = current_phase
                asyncio.run(asyncio.sleep(interval))
        except KeyboardInterrupt:
            pass

    elif source == "observe":
        try:
            from whitemagic.core.resonance.gan_ying_async import get_async_bus

            bus = get_async_bus()

            async def stream_events():
                nonlocal count
                click.echo(_json_dumps({"type": "stream_start", "source": "observe"}))
                queue = asyncio.Queue()

                async def handler(event):
                    await queue.put(event)

                bus.on("*", handler)
                try:
                    while max_events == 0 or count < max_events:
                        try:
                            event = await asyncio.wait_for(
                                queue.get(), timeout=interval
                            )
                            emit(
                                {
                                    "type": event.event_type,
                                    "data": event.data,
                                    "source": event.source,
                                }
                            )
                        except TimeoutError:
                            emit({"type": "heartbeat", "ts": _json_dumps(None)})
                finally:
                    pass

            asyncio.run(stream_events())
        except KeyboardInterrupt:
            pass
        except ImportError as e:
            click.echo(
                _json_dumps(
                    {"type": "error", "error": f"Gan Ying bus not available: {e}"}
                )
            )

    elif source == "self-improve":
        from whitemagic.core.evolution.recursive_loop import get_improvement_loop

        loop = get_improvement_loop()
        click.echo(_json_dumps({"type": "stream_start", "source": "self-improve"}))

        try:
            while max_events == 0 or count < max_events:
                status = loop.get_status()
                emit(
                    {
                        "type": "improve_status",
                        "cycles": status.get("cycle_count", 0),
                        "distinct": status.get("distinct_improvements", 0),
                    }
                )
                import time

                time.sleep(interval)
        except KeyboardInterrupt:
            pass

    elif source == "coherence":
        try:
            from whitemagic.core.intelligence.agentic.coherence_persistence import (
                get_coherence,
            )

            coherence = get_coherence()
            click.echo(_json_dumps({"type": "stream_start", "source": "coherence"}))

            try:
                while max_events == 0 or count < max_events:
                    stats = coherence.get_iteration_stats()
                    level = stats.get("coherence_level", 100)
                    event_type = "coherence_ok" if level >= 50 else "coherence_low"
                    emit({"type": event_type, "level": level, "stats": stats})
                    import time

                    time.sleep(interval)
            except KeyboardInterrupt:
                pass
        except ImportError as e:
            click.echo(
                _json_dumps(
                    {
                        "type": "error",
                        "error": f"Coherence persistence not available: {e}",
                    }
                )
            )

    elif source == "events":
        try:
            from whitemagic.core.resonance.gan_ying_async import get_async_bus

            bus = get_async_bus()

            async def stream_all():
                nonlocal count
                click.echo(_json_dumps({"type": "stream_start", "source": "events"}))
                queue = asyncio.Queue()

                async def handler(event):
                    await queue.put(event)

                bus.on("*", handler)
                try:
                    while max_events == 0 or count < max_events:
                        try:
                            event = await asyncio.wait_for(
                                queue.get(), timeout=interval
                            )
                            emit(
                                {
                                    "type": event.event_type,
                                    "data": event.data,
                                    "source": event.source,
                                    "ts": str(getattr(event, "timestamp", "")),
                                }
                            )
                        except TimeoutError:
                            emit({"type": "heartbeat"})
                finally:
                    pass

            asyncio.run(stream_all())
        except KeyboardInterrupt:
            pass
        except ImportError as e:
            click.echo(
                _json_dumps({"type": "error", "error": f"Event bus not available: {e}"})
            )

    click.echo(_json_dumps({"type": "stream_end", "events_emitted": count}))


# wm pipeline — Tool Call Chaining


@click.command()
@click.argument("stages", nargs=-1, required=True)
@click.option("--dry-run", is_flag=True, help="Show resolved chain without executing")
@click.option(
    "--json", "json_flag", is_flag=True, help="Emit full chain result as JSON"
)
@click.pass_context
def pipeline(ctx, stages: tuple[str, ...], dry_run: bool, json_flag: bool) -> None:
    """Chain tool calls, passing details from one stage to the next.

    Each stage is "tool_name:key=value,key=value".
    Use $_ to reference the previous stage's details.

    Examples:
        wm pipeline "recall:query=auth" "remember:content=$_,title=Auth findings"
        wm pipeline "search:query=security" "consolidate:target=$_"
    """
    from whitemagic.tools.unified_api import call_tool

    json_output = json_flag or (
        (ctx.obj or {}).get("json_output", False)
        if isinstance(ctx.obj, dict)
        else False
    )

    parsed_stages: list[dict[str, Any]] = []
    for i, stage in enumerate(stages):
        if ":" not in stage:
            click.echo(
                f"Stage {i + 1} error: expected 'tool_name:key=value,...' but got '{stage}'",
                err=True,
            )
            raise click.Abort()

        tool_name, params_str = stage.split(":", 1)
        kwargs: dict[str, Any] = {}

        if params_str:
            for pair in params_str.split(","):
                if "=" in pair:
                    key, val = pair.split("=", 1)
                    kwargs[key] = val
                else:
                    kwargs.setdefault("query", pair)

        parsed_stages.append({"tool": tool_name.strip(), "kwargs": kwargs})

    if dry_run:
        preview = {"stages": parsed_stages, "dry_run": True}
        click.echo(
            _json_dumps(preview, indent=2)
            if json_output
            else "\n".join(
                f"  {i + 1}. {s['tool']}({_json_dumps(s['kwargs'])})"
                for i, s in enumerate(parsed_stages)
            )
        )
        return

    results: list[dict[str, Any]] = []
    prev_details: Any = None

    for i, stage in enumerate(parsed_stages):
        tool_name = stage["tool"]
        kwargs = dict(stage["kwargs"])

        # Substitute $_ references with previous stage's details
        for key, val in kwargs.items():
            if isinstance(val, str) and "$_" in val:
                if prev_details is None:
                    click.echo(
                        f"Stage {i + 1} error: $_ reference but no previous stage output",
                        err=True,
                    )
                    raise click.Abort()
                # Replace $_ with JSON representation of prev_details
                kwargs[key] = val.replace(
                    "$_",
                    _json_dumps(prev_details)
                    if not isinstance(prev_details, str)
                    else prev_details,
                )
                if val == "$_" and isinstance(prev_details, (dict, list)):
                    kwargs[key] = prev_details

        if not json_output:
            click.echo(f"  [{i + 1}/{len(parsed_stages)}] {tool_name}...")

        try:
            result = call_tool(tool_name, **kwargs)
            results.append({"tool": tool_name, "result": result})

            # Extract details for next stage
            if isinstance(result, dict):
                prev_details = result.get("details", result)
            else:
                prev_details = result

            if not json_output:
                status = result.get("status", "?") if isinstance(result, dict) else "?"
                if status != "success":
                    click.echo(f"  ⚠️  Stage {i + 1} returned status: {status}")
                    click.echo(f"     {str(result)[:200]}")
                    break

        except Exception as e:
            results.append({"tool": tool_name, "error": str(e)})
            if json_output:
                click.echo(
                    _json_dumps(
                        {"stages": results, "error": str(e), "failed_at": i + 1},
                        indent=2,
                        default=str,
                    )
                )
            else:
                click.echo(f"  ❌ Stage {i + 1} failed: {e}", err=True)
            raise click.Abort()

    if json_output:
        click.echo(
            _json_dumps(
                {"stages": results, "completed": len(results)}, indent=2, default=str
            )
        )
    else:
        click.echo(f"\n✅ Pipeline complete: {len(results)} stages executed")
        if prev_details is not None:
            click.echo("\nFinal output:")
            click.echo(_json_dumps(prev_details, indent=2, default=str)[:2000])


def register_interactive_commands(main_group: click.Group) -> None:
    """Register repl, stream, and pipeline commands."""
    main_group.add_command(repl)
    main_group.add_command(stream)
    main_group.add_command(pipeline)
