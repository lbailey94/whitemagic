"""CLI command for relationship graph visualization."""
import sys
from typing import Dict, List, Set, Optional
from pathlib import Path
from rich.console import Console
from rich.tree import Tree
from rich.panel import Panel

from whitemagic.relationships import get_relationships
from whitemagic.utils import split_frontmatter


def command_graph(manager, args):
    """Show relationship graph for a memory."""
    console = Console()
    
    # Find the memory
    entry = next((e for e in manager._entries(None, True) if e["filename"] == args.filename), None)
    if not entry:
        console.print(f"[red]Not found: {args.filename}[/red]", file=sys.stderr)
        return 1
    
    # Build graph
    max_depth = args.depth if hasattr(args, 'depth') else 2
    visited = set()
    
    tree = Tree(
        f"[bold cyan]{entry['title']}[/bold cyan] [dim]({entry['filename']})[/dim]",
        guide_style="dim"
    )
    
    _build_graph_tree(
        manager, 
        entry['filename'], 
        tree, 
        visited, 
        max_depth, 
        current_depth=0,
        filter_type=getattr(args, 'type', None)
    )
    
    # Display
    if visited:
        panel = Panel(
            tree,
            title=f"[bold]Relationship Graph[/bold]",
            subtitle=f"[dim]Depth: {max_depth} | Nodes: {len(visited)}[/dim]",
            border_style="cyan"
        )
        console.print(panel)
    else:
        console.print("[yellow]No relationships found[/yellow]")
    
    return 0


def _build_graph_tree(
    manager,
    filename: str,
    tree: Tree,
    visited: Set[str],
    max_depth: int,
    current_depth: int,
    filter_type: Optional[str] = None
):
    """Recursively build relationship tree (BFS)."""
    if current_depth >= max_depth:
        return
    
    if filename in visited:
        return
    
    visited.add(filename)
    
    # Get memory
    entry = next((e for e in manager._entries(None, True) if e["filename"] == filename), None)
    if not entry:
        return
    
    # Read relationships from frontmatter
    path = manager.base_dir / entry["path"]
    if not path.exists():
        return
    
    try:
        raw = path.read_text()
        front, _ = split_frontmatter(raw)
        relationships = front.get("related_to", [])
    except Exception:
        return
    
    # Filter by type if specified
    if filter_type:
        relationships = [r for r in relationships if r.get("type") == filter_type]
    
    # Add child nodes
    for rel in relationships:
        rel_filename = rel.get("filename")
        rel_type = rel.get("type", "relates_to")
        rel_desc = rel.get("description", "")
        
        if not rel_filename:
            continue
        
        # Get target memory for title
        target_entry = next(
            (e for e in manager._entries(None, True) if e["filename"] == rel_filename), 
            None
        )
        
        if target_entry:
            # Format node label
            label_parts = [
                f"[bold]{rel_type}[/bold]:",
                f"[cyan]{target_entry['title']}[/cyan]",
                f"[dim]({rel_filename})[/dim]"
            ]
            if rel_desc:
                label_parts.append(f"[dim italic]- {rel_desc}[/dim italic]")
            
            label = " ".join(label_parts)
            
            # Add branch
            if rel_filename in visited:
                # Already visited, show but don't recurse
                tree.add(f"{label} [dim](seen)[/dim]")
            else:
                # New node, recurse
                branch = tree.add(label)
                _build_graph_tree(
                    manager,
                    rel_filename,
                    branch,
                    visited,
                    max_depth,
                    current_depth + 1,
                    filter_type
                )
        else:
            # Target not found
            tree.add(
                f"[bold]{rel_type}[/bold]: [red]{rel_filename} (not found)[/red]"
            )


def command_graph_stats(manager, args):
    """Show graph statistics for all memories."""
    console = Console()
    
    total_memories = 0
    total_relationships = 0
    relationship_types = {}
    memories_with_rels = 0
    orphaned = []
    
    # Scan all memories
    for entry in manager._entries(None, True):
        total_memories += 1
        path = manager.base_dir / entry["path"]
        
        try:
            raw = path.read_text()
            front, _ = split_frontmatter(raw)
            rels = front.get("related_to", [])
            
            if rels:
                memories_with_rels += 1
                total_relationships += len(rels)
                
                for rel in rels:
                    rel_type = rel.get("type", "unknown")
                    relationship_types[rel_type] = relationship_types.get(rel_type, 0) + 1
            else:
                orphaned.append(entry["filename"])
        except Exception:
            continue
    
    # Display stats
    console.print(Panel(
        f"""[bold cyan]Graph Statistics[/bold cyan]

📊 Overview:
  • Total Memories: {total_memories}
  • With Relationships: {memories_with_rels} ({memories_with_rels/total_memories*100:.1f}%)
  • Total Relationships: {total_relationships}
  • Orphaned Memories: {len(orphaned)}

🔗 Relationship Types:
{chr(10).join(f'  • {rtype}: {count}' for rtype, count in sorted(relationship_types.items(), key=lambda x: -x[1]))}

📈 Density: {total_relationships/total_memories:.2f} relationships per memory
""",
        title="Relationship Graph Overview",
        border_style="cyan"
    ))
    
    if orphaned and getattr(args, 'show_orphaned', False):
        console.print("\n[yellow]Orphaned memories (no relationships):[/yellow]")
        for filename in orphaned[:10]:
            console.print(f"  • {filename}")
        if len(orphaned) > 10:
            console.print(f"  ... and {len(orphaned)-10} more")
    
    return 0
