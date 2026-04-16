"""
CLI Commands: Thought Galaxy (G003)
===================================

wm thought status/recall/score
"""

import click

from whitemagic.config import paths
from whitemagic.core.memory.thought_galaxy import ThoughtGalaxy


@click.group(name="thought")
def thought_cli() -> None:
    """🧠 Thought Galaxy & Meta-Cognition"""
    pass

def _get_galaxy():
    db_path = paths.get_state_root() / "memory" / "galaxies" / "thought_traces" / "galaxy.db"
    if not db_path.parent.exists():
        db_path.parent.mkdir(parents=True, exist_ok=True)
    return ThoughtGalaxy(str(db_path))

@thought_cli.command(name="status")
def status_cmd() -> None:
    """Show Thought Galaxy statistics."""
    galaxy = _get_galaxy()
    stats = galaxy.stats()

    click.echo("🌌 Thought Galaxy Status")
    click.echo(f"Total Episodes: {stats['total_episodes']}")
    click.echo(f"Average Score:  {stats['average_score']:.2f}")
    click.echo("\n🏆 Top Strategies:")
    for strat in stats['top_strategies']:
        click.echo(f"  - {strat['strategy']}: {strat['avg_score']:.2f} (n={strat['count']})")

@thought_cli.command(name="recall")
@click.argument("task_type")
def recall_cmd(task_type: str) -> None:
    """Recall best strategies for a task type."""
    galaxy = _get_galaxy()
    episodes = galaxy.recall_best_strategies(task_type)

    if not episodes:
        click.echo(f"No strategies found for '{task_type}'")
        return

    click.echo(f"🧠 Best strategies for '{task_type}':")
    for i, ep in enumerate(episodes, 1):
        click.echo(f"\n{i}. Strategy: {ep.strategy} (Score: {ep.outcome_score})")
        click.echo(f"   Context: {ep.context_summary}")
        click.echo(f"   Trace: {ep.thought_trace[:100]}...")

@thought_cli.command(name="score")
@click.option("--manual", type=float, help="Manual score (-1.0 to 1.0)")
def score_cmd(manual: float | None) -> None:
    """Score the most recent episode (placeholder)."""
    # In a real impl, this would connect to the active session state
    click.echo("Scoring functionality requires active session connection (not yet implemented in CLI)")
