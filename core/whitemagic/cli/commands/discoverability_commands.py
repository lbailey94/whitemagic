# ruff: noqa: BLE001
# mypy: disable-error-code=no-untyped-def
"""Discoverability & export commands for AI agents.

Commands:
    wm manifest --format openai|mcp|whitemagic|summary  — Export tool manifest
    wm tools search <query>    — Semantic search over tool descriptions
    wm tools schema <tool_name> — Show JSON schema for a tool
    wm capabilities --deep     — Full capability snapshot
"""

from typing import Any

import click

from whitemagic.utils.fast_json import dumps_str as _json_dumps


# ---------------------------------------------------------------------------
# wm manifest — Tool format export
# ---------------------------------------------------------------------------

@click.command()
@click.option("--format", "fmt", type=click.Choice(["openai", "mcp", "whitemagic", "summary"]),
              default="summary", help="Export format")
@click.option("--include-schemas", is_flag=True, help="Include input schemas in export")
@click.option("--json", "json_flag", is_flag=True, help="Output as JSON (always on for manifest)")
@click.pass_context
def manifest(ctx, fmt: str, include_schemas: bool, json_flag: bool) -> None:
    """Export tool manifest in OpenAI, MCP, or WhiteMagic format.

    Examples:
        wm manifest --format openai
        wm manifest --format mcp --include-schemas
        wm manifest --format summary
    """
    from whitemagic.tools.unified_api import call_tool

    result = call_tool("manifest", format=fmt, include_schemas=include_schemas)
    data = result.get("details", result) if isinstance(result, dict) else result

    if isinstance(data, dict) and "format" in data:
        click.echo(_json_dumps(data, indent=2, default=str))
    else:
        click.echo(_json_dumps(result, indent=2, default=str))


# ---------------------------------------------------------------------------
# wm tools search — Semantic tool discovery
# ---------------------------------------------------------------------------

@click.command(name="search")
@click.argument("query")
@click.option("--limit", "-n", default=10, help="Max results")
@click.option("--json", "json_flag", is_flag=True, help="Output as JSON")
@click.pass_context
def tools_search(ctx, query: str, limit: int, json_flag: bool) -> None:
    """Semantic search over tool names and descriptions.

    Example:
        wm tools search "memory consolidation"
        wm tools search "ethics" --json
    """
    from whitemagic.tools.registry import get_all_tools

    json_output = json_flag or ((ctx.obj or {}).get("json_output", False) if isinstance(ctx.obj, dict) else False)

    query_lower = query.lower()
    tools = get_all_tools()
    scored: list[tuple[int, Any]] = []

    for tool in tools:
        score = 0
        name = tool.name.lower()
        desc = (tool.description or "").lower()
        category = tool.category.value.lower() if hasattr(tool.category, 'value') else str(tool.category).lower()

        if name == query_lower:
            score += 100
        elif name.startswith(query_lower):
            score += 50
        elif query_lower in name:
            score += 30

        if query_lower in desc:
            score += 20
            for word in query_lower.split():
                if word in desc:
                    score += 5

        if query_lower in category:
            score += 15

        if score > 0:
            scored.append((score, tool))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = scored[:limit]

    if json_output:
        output = {
            "query": query,
            "total_matches": len(scored),
            "results": [
                {
                    "name": t.name,
                    "description": t.description,
                    "category": t.category.value if hasattr(t.category, 'value') else str(t.category),
                    "safety": t.safety.value if hasattr(t.safety, 'value') else str(t.safety),
                    "score": score,
                }
                for score, t in results
            ],
        }
        click.echo(_json_dumps(output, indent=2, default=str))
    else:
        if not results:
            click.echo(f"No tools found matching '{query}'")
            return

        click.echo(f"\n🔍 Found {len(scored)} tools matching '{query}' (showing top {len(results)}):")
        click.echo("=" * 60)
        for score, tool in results:
            cat = tool.category.value if hasattr(tool.category, 'value') else str(tool.category)
            click.echo(f"  [{score:>3}] {tool.name:<30} ({cat})")
            if tool.description:
                desc = tool.description[:80] + "..." if len(tool.description) > 80 else tool.description
                click.echo(f"         {desc}")


# ---------------------------------------------------------------------------
# wm tools schema — JSON schema export for a tool
# ---------------------------------------------------------------------------

@click.command(name="schema")
@click.argument("tool_name")
@click.option("--format", "fmt", type=click.Choice(["json", "openai", "mcp"]),
              default="json", help="Schema format")
@click.option("--json", "json_flag", is_flag=True, help="Output as JSON (always on for schema)")
@click.pass_context
def tools_schema(ctx, tool_name: str, fmt: str, json_flag: bool) -> None:
    """Show JSON schema for a specific tool.

    Examples:
        wm tools schema recall
        wm tools schema recall --format openai
        wm tools schema remember --format mcp
    """
    from whitemagic.tools.registry import get_tool

    tool = get_tool(tool_name)
    if tool is None:
        click.echo(f"Tool '{tool_name}' not found", err=True)
        raise click.Abort()

    if fmt == "openai":
        schema = tool.to_openai_function()
    elif fmt == "mcp":
        schema = tool.to_mcp_tool()
    else:
        schema = tool.to_dict()

    click.echo(_json_dumps(schema, indent=2, default=str))


# ---------------------------------------------------------------------------
# wm capabilities --deep — Full capability snapshot
# ---------------------------------------------------------------------------

@click.command()
@click.option("--deep", is_flag=True, help="Include full tool list and schemas")
@click.option("--include-schemas", is_flag=True, help="Include input schemas for each tool")
@click.option("--json", "json_flag", is_flag=True, help="Output as JSON")
@click.pass_context
def capabilities(ctx, deep: bool, include_schemas: bool, json_flag: bool) -> None:
    """Show system capabilities snapshot.

    Examples:
        wm capabilities
        wm capabilities --deep --json
        wm capabilities --deep --include-schemas
    """
    from whitemagic.tools.unified_api import call_tool

    json_output = json_flag or ((ctx.obj or {}).get("json_output", False) if isinstance(ctx.obj, dict) else False)

    result = call_tool("capabilities", include_tools=deep, include_schemas=include_schemas)
    data = result.get("details", result) if isinstance(result, dict) else result

    if json_output:
        click.echo(_json_dumps(result, indent=2, default=str))
    else:
        if isinstance(data, dict):
            click.echo("\n🔮 WhiteMagic Capabilities")
            click.echo("=" * 50)

            if "version" in data:
                click.echo(f"  Version: {data['version']}")

            if "tool_count" in data:
                click.echo(f"  Tools: {data['tool_count']}")

            if "surface_counts" in data:
                counts = data["surface_counts"]
                click.echo(f"  Surface: {counts}")

            if "features" in data:
                features = data["features"]
                click.echo("\n  Features:")
                for name, enabled in sorted(features.items()):
                    status = "✅" if enabled else "❌"
                    click.echo(f"    {status} {name}")

            if "tools" in data and deep:
                tools_list = data["tools"]
                click.echo(f"\n  Tools ({len(tools_list)}):")
                for t in tools_list[:20]:
                    name = t.get("name", "?")
                    cat = t.get("category", "?")
                    click.echo(f"    {name:<30} ({cat})")
                if len(tools_list) > 20:
                    click.echo(f"    ... and {len(tools_list) - 20} more")
        else:
            click.echo(_json_dumps(result, indent=2, default=str))


def register_discoverability_commands(main_group: click.Group) -> None:
    """Register manifest, tools search/schema, and capabilities commands."""
    main_group.add_command(manifest)
    main_group.add_command(capabilities)

    # Create a tools group for search and schema
    @main_group.group(name="tools-discover")
    def tools_discover_group():
        """Tool discovery and schema commands."""
        pass

    tools_discover_group.add_command(tools_search)
    tools_discover_group.add_command(tools_schema)
