# ruff: noqa: BLE001
"""Self-improvement CLI commands — recursive improvement loop.

Usage:
    whitemagic self-improve                  # Run one cycle
    whitemagic self-improve --cycles 3       # Run multiple cycles
    whitemagic self-improve --json           # JSON output for AI consumption
    whitemagic self-improve --status         # Show loop status
    whitemagic self-improve --record-outcome HYP_ID --success  # Record outcome
"""
from __future__ import annotations

import json as json_module

import click


@click.group()
def self_improve():
    """Recursive self-improvement commands."""


@self_improve.command()
@click.option("--cycles", default=1, help="Number of improvement cycles to run")
@click.option("--max-hypotheses", default=20, help="Max hypotheses per cycle")
@click.option("--json", "json_flag", is_flag=True, help="Emit JSON for AI consumption")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed phase output")
@click.pass_context
def run(ctx, cycles: int, max_hypotheses: int, json_flag: bool, verbose: bool):
    """Run recursive improvement cycles (observe → imagine → predict → recommend)."""
    from whitemagic.core.evolution.recursive_loop import get_improvement_loop

    loop = get_improvement_loop()

    all_cycles = []
    json_output = json_flag or ((ctx.obj or {}).get("json_output", False) if isinstance(ctx.obj, dict) else False)
    for i in range(cycles):
        if not json_output:
            click.echo(f"\n{'='*60}")
            click.echo(f"  Improvement Cycle {i+1}/{cycles}")
            click.echo(f"{'='*60}")

        cycle = loop.run_cycle(max_hypotheses=max_hypotheses)
        all_cycles.append(cycle)

        if json_output:
            continue

        # Human-readable output
        click.echo(f"\n  Cycle ID: {cycle.cycle_id}")
        click.echo(f"  Duration: {cycle.duration_ms:.0f}ms")

        # Phase summaries
        observe = cycle.phase_results.get("observe", {})
        click.echo("\n  Phase 1 — OBSERVE:")
        click.echo(f"    Proposals gathered: {observe.get('total_proposals', 0)}")
        if observe.get("errors"):
            for err in observe["errors"][:3]:
                click.echo(f"    [error] {err}")

        imagine = cycle.phase_results.get("imagine", {})
        click.echo("\n  Phase 2 — IMAGINE:")
        click.echo(f"    Hypotheses created: {imagine.get('hypotheses_created', 0)}")
        click.echo(f"    MC simulations: {imagine.get('mc_simulations', 0)}")
        click.echo(f"    Distinct improvements seen: {imagine.get('distinct_improvements', 0)}")

        predict = cycle.phase_results.get("predict", {})
        click.echo("\n  Phase 3 — PREDICT:")
        click.echo(f"    Predictions stored: {predict.get('predictions_stored', 0)}")

        recommend = cycle.phase_results.get("recommend", {})
        click.echo("\n  Phase 4 — RECOMMEND:")
        recs = recommend.get("recommendations", [])
        click.echo(f"    Recommendations: {len(recs)}")

        for rec in recs[:5]:
            click.echo(f"\n    #{rec['rank']} [{rec['source']}] {rec['title']}")
            click.echo(f"        Score: {rec['score']:.4f} | Impact: {rec['predicted_impact']:.3f} | Confidence: {rec['confidence']:.3f}")
            click.echo(f"        Novelty: {rec['novelty']:.3f} | Effort: {rec['effort']} | Auto-fixable: {rec['auto_fixable']}")
            if rec.get("fix_action"):
                click.echo(f"        Fix action: {rec['fix_action']}")
            if rec.get("recommended_tools"):
                tools_str = ", ".join(f"{t['tool']}({t['expected_success']:.0%})" for t in rec["recommended_tools"])
                click.echo(f"        Recommended tools: {tools_str}")

        learn = cycle.phase_results.get("learn", {})
        click.echo("\n  Phase 5 — LEARN:")
        click.echo(f"    Applications recorded: {learn.get('applications_recorded', 0)}")
        summary = learn.get("learning_summary", {})
        if summary:
            click.echo(f"    Total applications (all-time): {summary.get('total_applications', 0)}")
            click.echo(f"    Overall success rate: {summary.get('overall_success_rate', 0):.1%}")
            click.echo(f"    Improved patterns: {summary.get('improved_patterns', 0)}")

        if verbose and cycle.analytics.get("errors"):
            click.echo("\n  Errors:")
            for err in cycle.analytics["errors"][:5]:
                click.echo(f"    - {err}")

    if json_output:
        output = {
            "cycles": [c.to_dict() for c in all_cycles],
            "total_cycles": len(all_cycles),
            "status": loop.get_status(),
        }
        click.echo(json_module.dumps(output, indent=2, default=str))
    else:
        click.echo("\n" + "=" * 60)
        click.echo(f"  {cycles} cycle(s) complete")
        click.echo(f"  Total distinct improvements tracked: {loop._hll.estimate()}")
        click.echo(f"{'='*60}")


@self_improve.command()
@click.option("--json", "json_flag", is_flag=True, help="Emit JSON")
@click.pass_context
def status(ctx, json_flag: bool):
    """Show recursive improvement loop status."""
    from whitemagic.core.evolution.recursive_loop import get_improvement_loop

    loop = get_improvement_loop()
    s = loop.get_status()

    json_output = json_flag or ((ctx.obj or {}).get("json_output", False) if isinstance(ctx.obj, dict) else False)
    if json_output:
        click.echo(json_module.dumps(s, indent=2, default=str))
        return

    click.echo("\n  Recursive Improvement Loop Status")
    click.echo("  " + "-" * 40)
    click.echo(f"  Cycles run: {s['cycle_count']}")
    click.echo(f"  Distinct improvements: {s['distinct_improvements']}")

    if s.get("last_cycle"):
        lc = s["last_cycle"]
        click.echo(f"\n  Last cycle: {lc['cycle_id']}")
        click.echo(f"    Hypotheses: {lc['hypothesis_count']}")
        click.echo(f"    Duration: {lc['duration_ms']:.0f}ms")

    if s.get("bandit_summary"):
        bs = s["bandit_summary"]
        click.echo("\n  Tool Bandit:")
        click.echo(f"    Total tools: {bs['total_tools']}")
        click.echo(f"    Tools with data: {bs['tools_with_data']}")
        click.echo(f"    Total calls: {bs['total_calls']}")
        if bs.get("top_tools"):
            click.echo("    Top tools:")
            for t in bs["top_tools"][:3]:
                click.echo(f"      {t['tool']}: {t['expected_value']:.1%} ({t['total_calls']} calls)")


@self_improve.command()
@click.argument("hypothesis_id")
@click.option("--success/--failure", required=True, help="Was the improvement successful?")
@click.option("--performance-gain", type=float, default=None, help="Performance gain (e.g., 13.0 for 13x)")
@click.option("--quality-score", type=float, default=None, help="Quality score 0-1")
def record_outcome(hypothesis_id: str, success: bool, performance_gain: float | None, quality_score: float | None):
    """Record the outcome of an implemented improvement.

    This closes the loop — predictions from previous cycles get validated
    against reality, and all tracking structures update.
    """
    from whitemagic.core.evolution.recursive_loop import get_improvement_loop

    loop = get_improvement_loop()
    loop.record_outcome(
        hypothesis_id=hypothesis_id,
        success=success,
        performance_gain=performance_gain,
        quality_score=quality_score,
    )

    click.echo(f"  Recorded: {hypothesis_id} → {'SUCCESS' if success else 'FAILURE'}")
    if performance_gain is not None:
        click.echo(f"  Performance gain: {performance_gain}x")
    if quality_score is not None:
        click.echo(f"  Quality score: {quality_score:.2f}")
    click.echo("  Bandit and AutodidacticLoop updated.")


@self_improve.command()
@click.option("--limit", default=10, help="Number of patterns to show")
def history(limit: int):
    """Show learning history from the autodidactic loop."""
    from whitemagic.core.evolution.autodidactic_loop import AutodidacticLoop

    loop = AutodidacticLoop()
    summary = loop.get_learning_summary()

    click.echo("\n  Learning Summary")
    click.echo("  " + "-" * 40)
    click.echo(f"  Total applications: {summary.get('total_applications', 0)}")
    click.echo(f"  Total outcomes: {summary.get('total_outcomes', 0)}")
    click.echo(f"  Overall success rate: {summary.get('overall_success_rate', 0):.1%}")
    click.echo(f"  Avg performance gain: {summary.get('avg_performance_gain', 0):.2f}x")
    click.echo(f"  Improved patterns: {summary.get('improved_patterns', 0)}")
    click.echo(f"  Decreased patterns: {summary.get('decreased_patterns', 0)}")

    top = loop.get_top_patterns(limit=limit)
    if top:
        click.echo("\n  Top Patterns (by confidence):")
        for p in top:
            change = p.get("confidence_change", 0)
            arrow = "↑" if change > 0 else "↓" if change < 0 else "→"
            click.echo(
                f"    {p['pattern_id'][:40]:40s} "
                f"conf={p['current_confidence']:.3f} {arrow} "
                f"success={p['success_rate']:.1%} "
                f"({p['application_count']} apps)"
            )
