# ruff: noqa: BLE001
# mypy: disable-error-code=no-untyped-def
"""Cognitive workflow commands for AI agents.

High-level commands orchestrating multiple tools for common AI cognitive workflows.

Commands:
    wm think <query>     — Multi-spectral reasoning shortcut
    wm reflect            — Trigger self-reflection, return cognitive state snapshot
    wm dream --auto       — Start dream cycle, stream events, auto-promote artifacts
    wm evolve --cycles N  — Run self-improvement cycles with automatic outcome recording
    wm ground <action>    — Dharma evaluation shortcut for go/no-go decisions
"""

import click

from whitemagic.utils.fast_json import dumps_str as _json_dumps


def _get_json_output(ctx, json_flag: bool) -> bool:
    """Merge local --json flag with global ctx.obj["json_output"]."""
    return json_flag or ((ctx.obj or {}).get("json_output", False) if isinstance(ctx.obj, dict) else False)


# ---------------------------------------------------------------------------
# wm think — Multi-spectral reasoning
# ---------------------------------------------------------------------------

@click.command()
@click.argument("query")
@click.option("--json", "json_flag", is_flag=True, help="Output as JSON")
@click.pass_context
def think(ctx, query: str, json_flag: bool) -> None:
    """Multi-spectral reasoning shortcut.

    Runs the multi-spectral reasoner (6 lenses: I Ching, Wu Xing, Art of War,
    Zodiac, Doctrine, Cognitive) on a query.

    Example:
        wm think "Should I consolidate memories now?"
        wm think "What's the best approach for this refactor?" --json
    """
    from whitemagic.tools.unified_api import call_tool

    json_output = _get_json_output(ctx, json_flag)

    result = call_tool("reasoning.multispectral", query=query)
    data = result.get("details", result) if isinstance(result, dict) else result

    if json_output:
        click.echo(_json_dumps(result, indent=2, default=str))
    else:
        click.echo(f"\n🧠 Multi-Spectral Reasoning: {query}")
        click.echo("=" * 60)

        if isinstance(data, dict):
            lenses = data.get("lenses", data.get("analyses", {}))
            if isinstance(lenses, dict):
                for lens_name, analysis in lenses.items():
                    click.echo(f"\n  [{lens_name}]")
                    if isinstance(analysis, dict):
                        for k, v in analysis.items():
                            click.echo(f"    {k}: {v}")
                    else:
                        click.echo(f"    {analysis}")

            synthesis = data.get("synthesis", data.get("conclusion"))
            if synthesis:
                click.echo(f"\n  Synthesis: {synthesis}")
        else:
            click.echo(_json_dumps(result, indent=2, default=str)[:2000])


# ---------------------------------------------------------------------------
# wm reflect — Self-reflection / cognitive state snapshot
# ---------------------------------------------------------------------------

@click.command()
@click.option("--json", "json_flag", is_flag=True, help="Output as JSON")
@click.pass_context
def reflect(ctx, json_flag: bool) -> None:
    """Trigger self-reflection, returning a cognitive state snapshot.

    Combines self-model forecasts, coherence level, cognitive mode,
    and galactic distribution into a single introspective view.

    Example:
        wm reflect
        wm reflect --json
    """
    from whitemagic.tools.unified_api import call_tool

    json_output = _get_json_output(ctx, json_flag)

    # Gather cognitive state from multiple tools
    snapshot: dict = {"sections": {}}

    # Self-model forecast
    try:
        sm = call_tool("selfmodel.forecast")
        snapshot["sections"]["self_model"] = sm.get("details", sm) if isinstance(sm, dict) else sm
    except Exception:
        pass

    # Coherence
    try:
        coh = call_tool("homeostasis.check")
        snapshot["sections"]["coherence"] = coh.get("details", coh) if isinstance(coh, dict) else coh
    except Exception:
        pass

    # Cognitive mode
    try:
        cm = call_tool("cognitive.mode")
        snapshot["sections"]["cognitive_mode"] = cm.get("details", cm) if isinstance(cm, dict) else cm
    except Exception:
        pass

    # Galactic distribution
    try:
        gal = call_tool("galactic.stats")
        snapshot["sections"]["galactic"] = gal.get("details", gal) if isinstance(gal, dict) else gal
    except Exception:
        pass

    # Gnosis (unified introspection)
    try:
        gn = call_tool("gnosis", compact=True)
        snapshot["sections"]["gnosis"] = gn.get("details", gn) if isinstance(gn, dict) else gn
    except Exception:
        pass

    if json_output:
        click.echo(_json_dumps(snapshot, indent=2, default=str))
    else:
        click.echo("\n🪞 Cognitive Reflection")
        click.echo("=" * 60)

        for section, data in snapshot["sections"].items():
            click.echo(f"\n  [{section}]")
            if isinstance(data, dict):
                for k, v in list(data.items())[:10]:
                    val_str = str(v)[:100] if isinstance(v, (str, int, float, bool)) else _json_dumps(v, default=str)[:100]
                    click.echo(f"    {k}: {val_str}")
            else:
                click.echo(f"    {data}")

        click.echo(f"\n  Sections captured: {list(snapshot['sections'].keys())}")


# ---------------------------------------------------------------------------
# wm dream --auto — Start dream cycle with auto-promotion
# ---------------------------------------------------------------------------

@click.command()
@click.option("--auto", is_flag=True, help="Auto-promote dream artifacts to permanent memories")
@click.option("--cycles", "-n", default=1, help="Number of dream cycles to run")
@click.option("--json", "json_flag", is_flag=True, help="Output as JSON")
@click.pass_context
def dream(ctx, auto: bool, cycles: int, json_flag: bool) -> None:
    """Start dream cycle, optionally auto-promoting artifacts.

    Without --auto, starts the background dream cycle.
    With --auto, runs N cycles immediately and promotes any artifacts.

    Examples:
        wm dream              — Start background dreaming
        wm dream --auto       — Run 1 cycle immediately, auto-promote
        wm dream --auto -n 3  — Run 3 cycles with auto-promotion
    """
    from whitemagic.tools.unified_api import call_tool

    json_output = _get_json_output(ctx, json_flag)

    if not auto:
        # Start background dream cycle
        result = call_tool("dream_start")
        data = result.get("details", result) if isinstance(result, dict) else result

        if json_output:
            click.echo(_json_dumps(result, indent=2, default=str))
        else:
            click.echo("🌙 Dream cycle started")
            if isinstance(data, dict):
                click.echo(f"   Status: {data.get('status', 'started')}")
        return

    # Auto mode: run cycles immediately
    results: list = []
    for i in range(cycles):
        cycle_result = call_tool("dream_now")
        data = cycle_result.get("details", cycle_result) if isinstance(cycle_result, dict) else cycle_result
        results.append(data)

        # Auto-promote artifacts if any
        if isinstance(data, dict) and data.get("artifacts"):
            for artifact in data["artifacts"]:
                if isinstance(artifact, dict) and artifact.get("id"):
                    try:
                        call_tool("dream.promote", artifact_id=artifact["id"])
                    except Exception:
                        pass

    if json_output:
        click.echo(_json_dumps({"cycles": results, "auto_promoted": auto}, indent=2, default=str))
    else:
        click.echo(f"\n🌙 Dream cycle complete: {cycles} cycle(s)")
        for i, r in enumerate(results):
            if isinstance(r, dict):
                phase = r.get("phase", "?")
                artifacts = r.get("artifacts", [])
                click.echo(f"  Cycle {i+1}: phase={phase}, artifacts={len(artifacts)}")
                if auto and artifacts:
                    click.echo(f"    → Auto-promoted {len(artifacts)} artifact(s)")


# ---------------------------------------------------------------------------
# wm evolve — Self-improvement cycles
# ---------------------------------------------------------------------------

@click.command()
@click.option("--cycles", "-n", default=1, help="Number of improvement cycles")
@click.option("--record", is_flag=True, help="Automatically record outcomes")
@click.option("--json", "json_flag", is_flag=True, help="Output as JSON")
@click.pass_context
def evolve(ctx, cycles: int, record: bool, json_flag: bool) -> None:
    """Run self-improvement cycles with automatic outcome recording.

    Example:
        wm evolve -n 3 --record
        wm evolve --json
    """
    from whitemagic.tools.unified_api import call_tool

    json_output = _get_json_output(ctx, json_flag)

    all_cycles: list = []
    for i in range(cycles):
        result = call_tool("kaizen_analyze")
        data = result.get("details", result) if isinstance(result, dict) else result
        all_cycles.append(data)

        if record and isinstance(data, dict):
            try:
                call_tool("karma_record", action="self_improve",
                          outcome="improvement_cycle", details=data)
            except Exception:
                pass

    if json_output:
        click.echo(_json_dumps({"cycles_run": len(all_cycles), "results": all_cycles},
                               indent=2, default=str))
    else:
        click.echo(f"\n🧬 Self-Evolution: {cycles} cycle(s) complete")
        for i, cycle in enumerate(all_cycles):
            if isinstance(cycle, dict):
                improvements = cycle.get("improvements", cycle.get("hints", []))
                click.echo(f"  Cycle {i+1}: {len(improvements) if isinstance(improvements, list) else '?'} improvement(s)")
                if record:
                    click.echo(f"    → Outcome recorded to Karma Ledger")


# ---------------------------------------------------------------------------
# wm ground — Dharma go/no-go evaluation
# ---------------------------------------------------------------------------

@click.command()
@click.argument("action")
@click.option("--params", "-p", help="JSON params for the action")
@click.option("--json", "json_flag", is_flag=True, help="Output as JSON")
@click.pass_context
def ground(ctx, action: str, params: str | None, json_flag: bool) -> None:
    """Dharma evaluation shortcut for go/no-go decisions.

    Evaluates an action against Dharma principles and returns
    a clear GO / CAUTION / NO-GO verdict.

    Examples:
        wm ground "delete_memory"
        wm ground "execute_command" -p '{"command": "rm -rf /"}'
        wm ground "consolidate" --json
    """
    import json as json_lib
    from whitemagic.tools.unified_api import call_tool

    json_output = _get_json_output(ctx, json_flag)

    kwargs: dict = {"action": action}
    if params:
        try:
            kwargs["params"] = json_lib.loads(params)
        except json_lib.JSONDecodeError:
            kwargs["params"] = params

    result = call_tool("evaluate_ethics", **kwargs)
    data = result.get("details", result) if isinstance(result, dict) else result

    # Determine verdict
    verdict = "GO"
    if isinstance(data, dict):
        score = data.get("ethical_score", data.get("score", 1.0))
        if isinstance(score, (int, float)):
            if score < 0.3:
                verdict = "NO-GO"
            elif score < 0.7:
                verdict = "CAUTION"
        blocked = data.get("blocked", data.get("violates", False))
        if blocked:
            verdict = "NO-GO"

    if json_output:
        click.echo(_json_dumps({"verdict": verdict, "result": result}, indent=2, default=str))
    else:
        colors = {"GO": "green", "CAUTION": "yellow", "NO-GO": "red"}
        icons = {"GO": "✅", "CAUTION": "⚠️", "NO-GO": "🛑"}

        click.echo(f"\n{icons.get(verdict, '?')} Dharma Verdict: {verdict}")
        click.echo("=" * 40)
        click.echo(f"  Action: {action}")

        if isinstance(data, dict):
            for k, v in data.items():
                if k not in ("action",):
                    val_str = str(v)[:120] if not isinstance(v, (dict, list)) else _json_dumps(v, default=str)[:120]
                    click.echo(f"  {k}: {val_str}")


def register_cognitive_commands(main_group: click.Group) -> None:
    """Register cognitive workflow commands."""
    main_group.add_command(think)
    main_group.add_command(reflect)
    main_group.add_command(dream)
    main_group.add_command(evolve)
    main_group.add_command(ground)
