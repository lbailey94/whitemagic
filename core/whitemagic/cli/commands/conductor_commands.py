# ruff: noqa: BLE001
# mypy: disable-error-code=no-untyped-def
"""Conductor CLI Commands
Autonomous task orchestration with iterative deepening.
"""

import asyncio
import json
from importlib import import_module

import click


@click.command()
@click.argument("prompt")
@click.option("--iterations", "-n", default=50, help="Maximum iterations")
@click.option("--clones", "-c", default=1000, help="Clones per iteration")
@click.option("--completion", default="<complete>", help="Completion marker")
@click.option("--garden", default="practice", help="Garden to align with")
def conduct(
    prompt: str, iterations: int, clones: int, completion: str, garden: str
) -> None:
    """Autonomous task orchestration with iterative deepening."""
    click.echo("\n🎼 Conductor - Autonomous Orchestration")
    click.echo("=" * 50)
    click.echo(f"Task: {prompt}")
    click.echo(f"Max iterations: {iterations}")
    click.echo(f"Clones per iteration: {clones}")
    click.echo(f"Garden: {garden}")
    click.echo(f"Completion marker: {completion}")
    click.echo()

    try:
        conductor_mod = import_module("whitemagic.orchestration.conductor")
        ConductorConfig = conductor_mod.ConductorConfig
        ConductorOrchestrator = conductor_mod.ConductorOrchestrator

        config = ConductorConfig(
            max_iterations=iterations,
            clones_per_iteration=clones,
            completion_check=completion,
            garden=garden,
        )
        conductor = ConductorOrchestrator(config)
        result = asyncio.run(conductor.conduct(prompt))

        if result:
            click.echo("\n✅ Orchestration Complete!")
            click.echo(f"Iterations: {result.iteration}")
            click.echo(f"Confidence: {result.thought_path.confidence:.2f}")
            click.echo(f"Strategy: {result.thought_path.strategy}")
            click.echo(f"Tokens used: {result.tokens_used}")
            click.echo(f"Completed: {'Yes' if result.is_complete else 'No'}")
            export_path = conductor.export_session()
            click.echo(f"\n📄 Session exported to: {export_path}")
        else:
            click.echo("❌ No result from orchestration")

    except ImportError as e:
        click.echo(f"❌ Conductor not available: {e}", err=True)
        click.echo("Ensure whitemagic.orchestration.conductor is installed", err=True)
    except (ImportError, ModuleNotFoundError) as e:
        click.echo(f"❌ Orchestration failed: {e}", err=True)


@click.command(name="conduct-ritual")
@click.argument("intention")
@click.option("--cycles", "-n", default=30, help="Maximum ritual cycles")
@click.option("--threshold", "-t", default=0.85, help="Mastery threshold (0-1)")
@click.option("--ritual-name", default="unnamed", help="Name for this ritual")
def conduct_ritual(
    intention: str, cycles: int, threshold: float, ritual_name: str
) -> None:
    """Conduct Practice Garden ritual with autonomous deepening."""
    click.echo("\n🌸 Practice Garden - Ritual Conductor")
    click.echo("=" * 50)
    click.echo(f"Ritual: {ritual_name}")
    click.echo(f"Intention: {intention}")
    click.echo(f"Max cycles: {cycles}")
    click.echo(f"Mastery threshold: {threshold}")
    click.echo()

    try:
        ritual_mod = import_module("whitemagic.gardens.practice.ritual_conductor")
        PracticeRitualConductor = ritual_mod.PracticeRitualConductor
        RitualConfig = ritual_mod.RitualConfig

        config = RitualConfig(
            ritual_name=ritual_name, max_cycles=cycles, deepening_threshold=threshold
        )
        conductor = PracticeRitualConductor(config)
        result = asyncio.run(conductor.conduct_ritual(intention))

        if result:
            report = conductor.get_ritual_report()
            click.echo("\n✨ Ritual Complete!")
            click.echo(f"Cycles: {report.get('total_iterations', 0)}")
            click.echo(
                f"Mastery achieved: {'Yes' if report.get('mastery_achieved') else 'No'}"
            )
            click.echo(f"Final confidence: {report.get('max_confidence', 0):.2f}")
            click.echo(
                f"Practice consistency: {report.get('practice_consistency', 0):.2f}"
            )
            if conductor.conductor:
                export_path = conductor.conductor.export_session()
                click.echo(f"\n📄 Ritual log: {export_path}")
        else:
            click.echo("❌ Ritual did not complete")

    except ImportError as e:
        click.echo(f"❌ Ritual conductor not available: {e}", err=True)
    except (ImportError, ModuleNotFoundError) as e:
        click.echo(f"❌ Ritual failed: {e}", err=True)


@click.command(
    name="fast",
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True},
)
@click.pass_context
def fast_cli(ctx: click.Context) -> None:
    """Run fast-mode CLI for quick commands"""
    try:
        from whitemagic.cli.cli_fast import main_fast

        main_fast(ctx.args)
    except Exception as exc:
        click.echo(f"❌ Fast mode failed: {exc}")


@click.command()
@click.argument("task")
@click.option(
    "--max-iterations",
    "-n",
    default=50,
    type=click.IntRange(min=1),
    help="Maximum iterations",
)
def continuous_start(task: str, max_iterations: int) -> None:
    """Start a continuous execution session (v4.3.0)."""
    click.echo("🔄 Starting continuous execution...")
    click.echo(f"   Task: {task}")
    click.echo(f"   Max iterations: {max_iterations}")
    try:
        conductor_mod = import_module("whitemagic.orchestration.conductor")
        ConductorConfig = conductor_mod.ConductorConfig
        ConductorOrchestrator = conductor_mod.ConductorOrchestrator

        conductor = ConductorOrchestrator(
            ConductorConfig(max_iterations=max_iterations)
        )
        result = asyncio.run(conductor.conduct(task))
        export_path = conductor.export_session()
        report = conductor.get_progress_report()

        click.echo("\n✅ Continuous execution complete!")
        click.echo(f"   Iterations: {report.get('total_iterations', 0)}")
        click.echo(f"   Status: {report.get('status', 'unknown')}")
        click.echo(f"   Final confidence: {result.thought_path.confidence:.2f}")
        click.echo(f"   Tokens used: {report.get('tokens_used', 0)}")
        click.echo(f"   Session exported to: {export_path}")
    except ImportError as exc:
        click.echo(f"❌ Continuous conductor not available: {exc}", err=True)
    except Exception as exc:
        click.echo(f"❌ Continuous execution failed: {exc}", err=True)


@click.command()
def iteration_stats() -> None:
    """Show current iteration and rate limit stats (v4.3.0)."""
    click.echo("\n📊 Iteration Statistics (v4.3.0)")
    click.echo("=" * 50)

    try:
        coherence_mod = import_module(
            "whitemagic.core.intelligence.agentic.coherence_persistence"
        )
        get_coherence = coherence_mod.get_coherence
        coherence = get_coherence()
        stats_data = coherence.get_iteration_stats()
        click.echo("\n🧠 Coherence & Rate Limiting:")
        click.echo(f"   Coherence Level: {stats_data.get('coherence_level', 100)}%")
        click.echo(f"   Iteration Count: {stats_data.get('iteration_count', 0)}")
        click.echo(f"   Calls This Hour: {stats_data.get('calls_this_hour', 0)}/100")
        click.echo(f"   Calls Remaining: {stats_data.get('calls_remaining', 100)}")
        click.echo(f"   Total Iterations: {stats_data.get('total_iterations', 0)}")
    except ImportError:
        click.echo("   ⚠️ Coherence persistence not available")

    try:
        anti_loop_mod = import_module("whitemagic.core.intelligence.agentic.anti_loop")
        get_anti_loop = anti_loop_mod.get_anti_loop
        detector = get_anti_loop()
        cb_stats = detector.get_circuit_status()
        state_emoji = {"closed": "🟢", "open": "🔴", "half_open": "🟡"}
        click.echo("\n⚡ Circuit Breaker:")
        click.echo(
            f"   State: {cb_stats['state']} {state_emoji.get(cb_stats['state'], '')}"
        )
        click.echo(f"   Iteration Count: {cb_stats['iteration_count']}")
        click.echo(f"   No Progress Count: {cb_stats['no_progress_count']}")
        if cb_stats.get("recent_errors"):
            click.echo(f"   Recent Errors: {len(cb_stats['recent_errors'])}")
    except ImportError:
        click.echo("   ⚠️ Circuit breaker not available")

    try:
        token_optimizer_mod = import_module(
            "whitemagic.core.intelligence.agentic.token_optimizer"
        )
        TokenBudget = token_optimizer_mod.TokenBudget
        budget = TokenBudget()
        tier_emoji = {"safe": "🟢", "wrap_up": "🟡", "checkpoint": "🔴"}
        click.echo("\n💰 Token Budget:")
        click.echo(
            f"   Status: {budget.usage_tier.upper()} {tier_emoji.get(budget.usage_tier, '')}"
        )
        click.echo(f"   Remaining: {budget.remaining:,}")
    except ImportError:
        click.echo("   ⚠️ Token optimizer not available")

    click.echo("\n" + "=" * 50)


@click.command()
def continuous_status() -> None:
    """Check continuous execution status (v4.3.0)."""
    try:
        conductor_mod = import_module("whitemagic.orchestration.conductor")
        live_status = conductor_mod.load_live_status()

        if live_status is not None:
            progress = live_status.get("progress", {})
            click.echo("\n📡 Live Conductor Status")
            click.echo("=" * 50)
            click.echo(f"   Active: {'yes' if live_status.get('active') else 'no'}")
            click.echo(f"   Phase: {live_status.get('phase', 'unknown')}")
            click.echo(f"   Status: {live_status.get('status', 'unknown')}")
            click.echo(f"   PID: {live_status.get('pid', 'unknown')}")
            if live_status.get("started_at"):
                click.echo(f"   Started: {live_status['started_at']}")
            if live_status.get("last_update"):
                click.echo(f"   Last update: {live_status['last_update']}")
            click.echo(
                f"   Current iteration: {live_status.get('current_iteration', 0)}"
            )
            click.echo(
                f"   Iterations completed: {progress.get('total_iterations', 0)}"
            )
            click.echo(f"   Tokens used: {progress.get('tokens_used', 0)}")
            if live_status.get("current_confidence") is not None:
                click.echo(
                    f"   Current confidence: {live_status['current_confidence']:.2f}"
                )
            if live_status.get("current_strategy"):
                click.echo(f"   Current strategy: {live_status['current_strategy']}")
            if live_status.get("current_preview"):
                click.echo(f"   Current preview: {live_status['current_preview']}")
            if live_status.get("error"):
                click.echo(f"   Error: {live_status['error']}")
            if live_status.get("session_path"):
                click.echo(f"   Session export: {live_status['session_path']}")
            return

        latest_session = conductor_mod.get_latest_conductor_session_path()
        if latest_session is None:
            click.echo("ℹ️ No saved conductor sessions found.")
            click.echo(
                "   Run `wm conduct <prompt>` or `wm continuous-start <task>` first."
            )
            return

        try:
            data = json.loads(latest_session.read_text(encoding="utf-8"))
        except Exception as exc:
            click.echo(
                f"❌ Failed to read latest session {latest_session.name}: {exc}",
                err=True,
            )
            return

        progress = data.get("progress", {})
        config = data.get("config", {})
        click.echo("\n� Latest Conductor Session")
        click.echo("=" * 50)
        click.echo(f"   Session: {latest_session}")
        click.echo(f"   Status: {progress.get('status', 'unknown')}")
        click.echo(f"   Max iterations: {config.get('max_iterations', 'unknown')}")
        click.echo(f"   Iterations completed: {progress.get('total_iterations', 0)}")
        click.echo(f"   Tokens used: {progress.get('tokens_used', 0)}")
        if "avg_confidence" in progress:
            click.echo(f"   Avg confidence: {progress['avg_confidence']:.2f}")
        if "max_confidence" in progress:
            click.echo(f"   Max confidence: {progress['max_confidence']:.2f}")
        click.echo(f"   Completed: {'yes' if progress.get('completed') else 'no'}")
    except Exception as exc:
        click.echo(f"❌ Continuous status unavailable: {exc}", err=True)


@click.command()
def inject_context() -> None:
    """Show what memory context would be injected (v4.3.0)."""
    try:
        memory_injector_mod = import_module(
            "whitemagic.core.intelligence.agentic.memory_injector"
        )
        get_memory_injector = memory_injector_mod.get_memory_injector
        injector = get_memory_injector()
        context_data = injector.inject()

        click.echo("\n🧠 Memory Injection Preview (v4.3.0)")
        click.echo("=" * 50)

        if context_data.resume_context:
            click.echo("\n📋 Resume Context:")
            click.echo(
                context_data.resume_context[:500] + "..."
                if len(context_data.resume_context) > 500
                else context_data.resume_context
            )

        if context_data.short_term_memories:
            click.echo("\n📝 Recent Short-term Memories:")
            for m in context_data.short_term_memories[:5]:
                click.echo(f"   • {m[:100]}")

        if context_data.session_state:
            click.echo("\n⚙️ Session State:")
            for k, v in context_data.session_state.items():
                click.echo(f"   • {k}: {v}")

        click.echo(f"\n📊 Estimated tokens: ~{context_data.total_tokens}")
        click.echo("=" * 50)

    except ImportError as e:
        click.echo(f"❌ Memory injector not available: {e}", err=True)


def register_conductor_commands(main_group: click.Group) -> None:
    """Register all conductor/orchestration commands onto the main CLI group."""
    main_group.add_command(conduct)
    main_group.add_command(conduct_ritual)
    main_group.add_command(fast_cli)
    main_group.add_command(continuous_start)
    main_group.add_command(iteration_stats)
    main_group.add_command(continuous_status)
    main_group.add_command(inject_context)
