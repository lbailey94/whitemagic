"""Memory-related CLI commands."""
# ruff: noqa: BLE001
from typing import Any

import click

from whitemagic.utils.fast_json import dumps_str as _json_dumps

# Import Rich for beautiful CLI output
try:
    from rich.console import Console
    from rich.table import Table
    HAS_RICH = True
    console = Console()
except ImportError:
    HAS_RICH = False
    console = None  # type: ignore[assignment]

# Import WhiteMagic modules
try:
    from whitemagic.core.memory.unified import get_unified_memory
    HAS_CORE = True
except ImportError:
    HAS_CORE = False

from whitemagic.tools.unified_api import call_tool

_memory = None

def get_memory():  # type: ignore[return]
    """Get or create memory instance (respects WM_STATE_ROOT)."""
    global _memory
    if _memory is None and HAS_CORE:
        _memory = get_unified_memory()
    return _memory


@click.command()
@click.argument("content")
@click.option("--title", help="Memory title")
@click.option("--tags", help="Comma-separated tags")
@click.option("--type", "memory_type", default="short_term",
              type=click.Choice(["short_term", "long_term"]))
@click.pass_context
def remember(ctx, content: str, title: str | None, tags: str | None, memory_type: str) -> None:
    """Create a new memory entry"""
    now = (ctx.obj or {}).get("now") if isinstance(ctx.obj, dict) else None
    json_output = (ctx.obj or {}).get("json_output") if isinstance(ctx.obj, dict) else False

    kwargs: dict[str, Any] = {"content": content}
    if title:
        kwargs["title"] = title
    if tags:
        kwargs["tags"] = tags.split(",")
    if memory_type:
        kwargs["type"] = memory_type

    result = call_tool("create_memory", **kwargs, now_override=now)

    if json_output:
        click.echo(_json_dumps(result))
    else:
        if result.get("status") == "success":
            click.echo(f"✅ Memory created: {result.get('memory_id', 'unknown')}")
        else:
            click.echo(f"❌ Failed: {result.get('error', 'unknown error')}")


@click.command()
@click.argument("query")
@click.option("--limit", default=10, help="Max results")
@click.option("--type", "search_type", help="Filter by memory type")
@click.option("--fast", is_flag=True, help="Use Rust fast_search (v4.9.0)")
@click.pass_context
def recall(ctx, query: str, limit: int, search_type: str | None, fast: bool) -> None:
    """Search memories"""
    from whitemagic.tools.unified_api import call_tool

    now = (ctx.obj or {}).get("now") if isinstance(ctx.obj, dict) else None
    json_output = (ctx.obj or {}).get("json_output") if isinstance(ctx.obj, dict) else False

    kwargs: dict[str, Any] = {"query": query, "limit": limit}
    if search_type:
        kwargs["type"] = search_type
    if fast:
        kwargs["use_rust"] = True

    result = call_tool("search_memories", **kwargs, now_override=now)

    if json_output:
        click.echo(_json_dumps(result))
    else:
        memories = result.get("memories", result.get("results", []))
        if memories:
            if HAS_RICH and console:
                table = Table(title=f"🔍 Search Results: '{query}'", show_header=True, header_style="bold magenta")
                table.add_column("ID", style="cyan", no_wrap=True)
                table.add_column("Content", style="white")
                table.add_column("Type", style="green")
                for mem in memories[:limit]:
                    mem_id = mem.get("id", mem.get("memory_id", "?"))[:8]
                    content = mem.get("content", "")[:60]
                    mem_type = mem.get("type", mem.get("memory_type", "?"))
                    table.add_row(mem_id, content, mem_type)
                console.print(table)
            else:
                for mem in memories[:limit]:
                    mem_id = mem.get("id", mem.get("memory_id", "?"))
                    content = mem.get("content", "")
                    click.echo(f"{mem_id}: {content[:80]}")
        else:
            click.echo("No memories found")


@click.command()
@click.argument("query")
@click.option("--limit", default=10, help="Max results")
@click.option("--type", "search_type", help="Filter by memory type")
@click.option("--fast", is_flag=True, help="Use Rust fast_search (v4.9.0)")
def search(query: str, limit: int, search_type: str | None, fast: bool) -> None:
    """Alias for recall - search memories"""
    # Forward to recall command
    ctx = click.get_current_context()
    ctx.invoke(recall, query=query, limit=limit, search_type=search_type, fast=fast)


@click.command()
@click.option("--tier", default=1, type=click.IntRange(0, 2),
              help="Context tier (0=quick, 1=balanced, 2=deep)")
def context(tier: int) -> None:
    """Generate context summary for AI prompts"""
    if not HAS_CORE:
        click.echo("Error: WhiteMagic core not available", err=True)
        return

    memory = get_memory()
    if not memory:
        click.echo("Error: Memory not initialized", err=True)
        return

    from whitemagic.ai.context_optimizer import get_context_optimizer
    opt = get_context_optimizer()

    if tier == 0:
        result = opt.pack_memories("recent activity", limit=10, token_budget=2000)
    elif tier == 1:
        result = opt.pack_memories("recent activity", limit=20, token_budget=4000)
    else:
        result = opt.pack_full_context("recent activity", token_budget=8000, memory_limit=50)

    click.echo(result.get("context", "No context generated"))


@click.command()
def consolidate() -> None:
    """Archive old short-term memories"""
    if not HAS_CORE:
        click.echo("Error: WhiteMagic core not available", err=True)
        return

    memory = get_memory()
    if not memory:
        click.echo("Error: Memory not initialized", err=True)
        return

    try:
        memory.consolidate()
        click.echo("✅ Memory consolidation complete")
    except Exception as e:
        click.echo(f"❌ Consolidation failed: {e}")


@click.command()
def stats() -> None:
    """Show memory statistics dashboard"""
    if not HAS_CORE:
        click.echo("Error: WhiteMagic core not available", err=True)
        return

    memory = get_memory()
    if not memory:
        click.echo("Error: Memory not initialized", err=True)
        return

    try:
        stats = memory.get_stats()
        if HAS_RICH and console:
            table = Table(title="📊 Memory Statistics", show_header=True, header_style="bold magenta")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")
            for key, value in stats.items():
                table.add_row(str(key), str(value))
            console.print(table)
        else:
            for key, value in stats.items():
                click.echo(f"{key}: {value}")
    except Exception as e:
        click.echo(f"❌ Failed to get stats: {e}")


@click.command(name="memory-list")
@click.option("--limit", default=10, help="Max memories to show")
def memory_list(limit: int) -> None:
    """List recent memories"""
    if not HAS_CORE:
        click.echo("Error: WhiteMagic core not available", err=True)
        return

    memory = get_memory()
    if not memory:
        click.echo("Error: Memory not initialized", err=True)
        return

    try:
        memories = memory.list_recent(limit=limit)
        if HAS_RICH and console:
            table = Table(title=f"📝 Recent Memories (last {limit})", show_header=True, header_style="bold magenta")
            table.add_column("ID", style="cyan", no_wrap=True)
            table.add_column("Content", style="white")
            table.add_column("Created", style="green")
            for mem in memories:
                mem_id = mem.get("id", mem.get("memory_id", "?"))[:8]
                content = mem.get("content", "")[:60]
                created = mem.get("created_at", "?")
                table.add_row(mem_id, content, str(created))
            console.print(table)
        else:
            for mem in memories:
                mem_id = mem.get("id", mem.get("memory_id", "?"))
                content = mem.get("content", "")
                click.echo(f"{mem_id}: {content[:80]}")
    except Exception as e:
        click.echo(f"❌ Failed to list memories: {e}")


@click.command()
@click.option("--from", "from_tag", required=True, help="Starting tag for the journey")
@click.option("--depth", default=3, help="How many hops to traverse")
@click.option("--limit", default=5, help="Max memories per hop")
@click.pass_context
def journey(ctx, from_tag: str, depth: int, limit: int) -> None:
    """Explore memory space via tag-connected hops."""
    now = (ctx.obj or {}).get("now") if isinstance(ctx.obj, dict) else None
    json_output = (ctx.obj or {}).get("json_output") if isinstance(ctx.obj, dict) else False

    results: list[dict[str, Any]] = []
    current_tags = {from_tag}
    visited_ids: set[str] = set()

    for hop in range(depth):
        hop_memories: list[dict[str, Any]] = []
        for tag in list(current_tags):
            search_result = call_tool("search_memories", query=tag, limit=limit, now_override=now)
            for mem in search_result.get("memories", search_result.get("results", [])):
                mem_id = mem.get("id", mem.get("memory_id", ""))
                if mem_id and mem_id not in visited_ids:
                    visited_ids.add(mem_id)
                    hop_memories.append(mem)
                    # Collect new tags for next hop
                    for t in mem.get("tags", []):
                        current_tags.add(t)
        if not hop_memories:
            break
        results.append({"hop": hop + 1, "tag_seeds": list(current_tags), "memories": hop_memories[:limit]})

    if json_output:
        click.echo(_json_dumps({"status": "success", "journey": results}))
    else:
        if HAS_RICH and console:
            from rich.panel import Panel
            for hop_data in results:
                hop_num = hop_data["hop"]
                mems = hop_data["memories"]
                lines = [f"  • {m.get('content', '')[:60]} ({m.get('id', '?')[:8]})" for m in mems]
                console.print(Panel("\n".join(lines), title=f"Hop {hop_num} — {len(mems)} memories", border_style="blue"))
        else:
            for hop_data in results:
                hop_num = hop_data["hop"]
                click.echo(f"\n--- Hop {hop_num} ---")
                for m in hop_data["memories"]:
                    click.echo(f"  [{m.get('id', '?')[:8]}] {m.get('content', '')[:80]}")
