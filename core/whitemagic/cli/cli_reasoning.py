"""CLI commands for Multi-Spectral Reasoning

Adds 'wm reason' command for unified reasoning system.
"""

from typing import Any, List, Optional, Tuple

import click


@click.group()
def reasoning() -> None:
    """Multi-spectral reasoning commands"""
    pass


@reasoning.command()
@click.argument('question')
@click.option('--task-type', '-t', default='analysis',
              help='Type of task (implementation, debugging, planning, etc.)')
@click.option('--urgency', '-u', default='normal',
              type=click.Choice(['low', 'normal', 'high']),
              help='Urgency level')
@click.option('--complexity', '-c', default='medium',
              type=click.Choice(['low', 'medium', 'high']),
              help='Complexity level')
@click.option('--lenses', '-l', multiple=True,
              type=click.Choice(['i_ching', 'wu_xing', 'art_of_war', 'zodiac', 'all']),
              help='Specific lenses to use (default: all)')
@click.option('--sequential/--no-sequential', default=True,
              help='Use sequential thinking (default: yes)')
@click.option('--save/--no-save', default=True,
              help='Save reasoning to memory (default: yes)')
def ask(question: str, task_type: str, urgency: str, complexity: str,
        lenses: Tuple[str, ...], sequential: bool, save: bool) -> None:
    """Ask a question using multi-spectral reasoning
    
    Examples:
        wm reason ask "Should I refactor or rewrite?"
        wm reason ask "Best approach for scaling?" -t architecture -u high
        wm reason ask "How to debug this?" -l i_ching -l wu_xing
    """
    from whitemagic.core.intelligence.multi_spectral_reasoning import (
        get_reasoner,
        ReasoningContext,
        ReasoningLens
    )
    
    # Create context
    context = ReasoningContext(
        question=question,
        task_type=task_type,
        urgency=urgency,
        complexity=complexity
    )
    
    # Parse lenses
    lens_mapping = {
        'i_ching': ReasoningLens.I_CHING,
        'wu_xing': ReasoningLens.WU_XING,
        'art_of_war': ReasoningLens.ART_OF_WAR,
        'zodiac': ReasoningLens.ZODIAC,
        'all': ReasoningLens.ALL
    }
    
    selected_lenses: Optional[List[ReasoningLens]] = None
    if lenses:
        selected_lenses = [lens_mapping[l] for l in lenses if l in lens_mapping]
    
    # Reason
    reasoner = get_reasoner()
    result = reasoner.reason(
        question=question,
        lenses=selected_lenses,
        context=context,
        use_sequential_thinking=sequential
    )
    
    # Result is already displayed by the reasoner
    # Just add final summary
    click.echo(f"\n✅ Reasoning complete! Confidence: {result.confidence:.0%}")
    
    if not save:
        click.echo("⚠️  Result not saved to memory (--no-save)")


@reasoning.command()
@click.option('--limit', '-n', default=10,
              help='Number of past reasonings to show')
def history(limit: int) -> None:
    """Show reasoning history (pattern memory)"""
    from whitemagic.core.intelligence.multi_spectral_reasoning import get_reasoner

    reasoner = get_reasoner()
    
    if not reasoner.reasoning_history:
        click.echo("No reasoning history yet.")
        return
    
    click.echo(f"\n🧠 Reasoning History (last {limit}):")
    click.echo("=" * 60)
    
    for i, result in enumerate(reasoner.reasoning_history[-limit:], 1):
        click.echo(f"\n{i}. {result.question}")
        click.echo(f"   Confidence: {result.confidence:.0%}")
        click.echo(f"   Timestamp: {result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        click.echo(f"   Lenses used: {[p.lens.value for p in result.perspectives]}")


@reasoning.command()
def status() -> None:
    """Show reasoning system status"""
    from whitemagic.core.intelligence.multi_spectral_reasoning import get_reasoner

    reasoner = get_reasoner()

    click.echo("\n🌈 Multi-Spectral Reasoning System Status")
    click.echo("=" * 60)
    
    # Check which systems are available
    systems = {
        "I Ching": reasoner.i_ching is not None,
        "Wu Xing": reasoner.wu_xing is not None,
        "Art of War": reasoner.art_of_war is not None,
        "Zodiac": reasoner.zodiac_cores is not None,
        "Gan Ying Bus": reasoner.bus is not None
    }
    
    click.echo("\n📊 Available Systems:")
    for name, available in systems.items():
        status_icon = "✅" if available else "❌"
        click.echo(f"  {status_icon} {name}")
    
    click.echo(f"\n🧠 Reasoning History: {len(reasoner.reasoning_history)} entries")
    click.echo(f"💾 Memory location: {reasoner.memory_dir}")
    
    if reasoner.reasoning_history:
        latest = reasoner.reasoning_history[-1]
        click.echo(f"\n🕐 Latest reasoning:")
        click.echo(f"  Question: {latest.question}")
        click.echo(f"  Confidence: {latest.confidence:.0%}")
        click.echo(f"  Timestamp: {latest.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")


@reasoning.command()
@click.argument('question')
@click.option('--threshold', '-t', default=0.6, type=float,
              help='Similarity threshold (0.0-1.0)')
def similar(question: str, threshold: float) -> None:
    """Find similar past reasonings (pattern matching)"""
    from whitemagic.core.intelligence.multi_spectral_reasoning import get_reasoner

    reasoner = get_reasoner()

    if not reasoner.reasoning_history:
        click.echo("No reasoning history to search.")
        return
    
    click.echo(f"\n🔍 Searching for similar reasonings...")
    click.echo(f"Question: {question}")
    click.echo(f"Threshold: {threshold:.0%}")
    click.echo("=" * 60)
    
    matches: List[Tuple[float, Any]] = []
    for past in reasoner.reasoning_history:
        similarity = reasoner._calculate_similarity(question, past.question)
        if similarity >= threshold:
            matches.append((similarity, past))
    
    if not matches:
        click.echo("\nNo similar reasonings found.")
        return
    
    # Sort by similarity
    matches.sort(key=lambda x: x[0], reverse=True)
    
    click.echo(f"\n✅ Found {len(matches)} similar reasoning(s):\n")
    
    for i, (similarity, past) in enumerate(matches[:5], 1):  # Top 5
        click.echo(f"{i}. Similarity: {similarity:.0%}")
        click.echo(f"   Question: {past.question}")
        click.echo(f"   Recommendation: {past.recommendation[:100]}...")
        click.echo(f"   Confidence: {past.confidence:.0%}")
        click.echo()


if __name__ == "__main__":
    reasoning()
