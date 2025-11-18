"""Memory statistics and analytics dashboard."""

from collections import Counter
from typing import Dict


def generate_stats(manager) -> Dict:
    """Generate comprehensive memory statistics."""
    entries = list(manager._entries(None, include_archived=True))

    stats = {
        "total_memories": len(entries),
        "by_type": Counter(e["type"] for e in entries),
        "by_status": Counter(e["status"] for e in entries),
        "total_tags": 0,
        "unique_tags": set(),
        "avg_tags_per_memory": 0,
        "relationships": 0,
        "most_common_tags": [],
    }

    tag_counts = Counter()
    for e in entries:
        tags = e.get("tags", [])
        stats["total_tags"] += len(tags)
        stats["unique_tags"].update(tags)
        tag_counts.update(tags)

        if e.get("related_to"):
            stats["relationships"] += len(e["related_to"])

    if entries:
        stats["avg_tags_per_memory"] = round(stats["total_tags"] / len(entries), 2)

    stats["unique_tags"] = len(stats["unique_tags"])
    stats["most_common_tags"] = tag_counts.most_common(10)

    return stats


def print_stats_dashboard(stats: Dict):
    """Print formatted stats dashboard."""
    from rich.console import Console
    from rich.table import Table

    console = Console()
    console.print("\n[bold cyan]📊 WhiteMagic Memory Statistics[/bold cyan]\n")

    # Overview
    console.print(f"[green]Total Memories:[/green] {stats['total_memories']}")
    console.print(f"[green]Short-term:[/green] {stats['by_type'].get('short_term', 0)}")
    console.print(f"[green]Long-term:[/green] {stats['by_type'].get('long_term', 0)}")
    console.print(f"[green]Archived:[/green] {stats['by_status'].get('archived', 0)}")
    console.print(f"\n[yellow]Unique Tags:[/yellow] {stats['unique_tags']}")
    console.print(f"[yellow]Avg Tags/Memory:[/yellow] {stats['avg_tags_per_memory']}")
    console.print(f"[yellow]Relationships:[/yellow] {stats['relationships']}\n")

    # Top tags table
    if stats["most_common_tags"]:
        table = Table(title="Top Tags")
        table.add_column("Tag", style="cyan")
        table.add_column("Count", style="magenta", justify="right")

        for tag, count in stats["most_common_tags"][:10]:
            table.add_row(tag, str(count))

        console.print(table)
