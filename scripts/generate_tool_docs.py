#!/usr/bin/env python3
"""Generate per-tool documentation from WhiteMagic registry definitions.

Reads ToolDefinition entries from registry_defs/ and generates:
    - One markdown file per tool (name, description, schema, examples)
    - An API reference index page
    - An OpenAPI spec for the MCP HTTP transport

Usage:
    python scripts/generate_tool_docs.py --output docs/api/
    python scripts/generate_tool_docs.py --openapi docs/openapi.json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Core repo path
REPO_ROOT = Path(__file__).parent.parent
CORE_ROOT = REPO_ROOT / "core"


def collect_tool_definitions() -> list[dict[str, Any]]:
    """Collect all ToolDefinition entries from registry_defs."""
    sys.path.insert(0, str(CORE_ROOT))

    try:
        from whitemagic.tools.registry import get_all_tools
        tools_defs = get_all_tools()
        return [_tool_to_dict(t) for t in tools_defs]
    except Exception as e:
        logger.warning("Could not load full registry: %s. Falling back to manual scan.", e)
        return _collect_manual()


def _tool_to_dict(tool: Any) -> dict[str, Any]:
    """Convert a ToolDefinition to a serializable dict."""
    data: dict[str, Any] = {
        "name": getattr(tool, "name", ""),
        "description": getattr(tool, "description", ""),
        "category": str(getattr(tool, "category", "")),
        "safety": str(getattr(tool, "safety", "")),
    }
    schema = getattr(tool, "input_schema", None)
    if schema:
        data["input_schema"] = schema if isinstance(schema, dict) else dict(schema)
    else:
        data["input_schema"] = {}
    return data


def _collect_manual() -> list[dict[str, Any]]:
    """Manually scan registry_defs for ToolDefinition entries."""
    tools: list[dict[str, Any]] = []
    defs_dir = CORE_ROOT / "whitemagic" / "tools" / "registry_defs"
    if not defs_dir.exists():
        return tools

    import ast

    for py_file in sorted(defs_dir.glob("*.py")):
        if py_file.name.startswith("_"):
            continue
        try:
            content = py_file.read_text(encoding="utf-8")
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    if node.func.id == "ToolDefinition":
                        tool_dict: dict[str, Any] = {}
                        for kw in node.keywords:
                            if kw.arg == "name" and isinstance(kw.value, ast.Constant):
                                tool_dict["name"] = kw.value.value
                            elif kw.arg == "description" and isinstance(kw.value, ast.Constant):
                                tool_dict["description"] = kw.value.value
                        if tool_dict.get("name"):
                            tool_dict.setdefault("category", "UNKNOWN")
                            tool_dict.setdefault("safety", "READ")
                            tool_dict.setdefault("input_schema", {})
                            tools.append(tool_dict)
        except Exception as e:
            logger.debug("Failed to parse %s: %s", py_file, e)

    return tools


def _get_gana_for_tool(tool_name: str) -> str | None:
    """Map a tool name to its Gana routing."""
    try:
        from whitemagic.tools.prat_mappings import get_gana_for_tool
        return get_gana_for_tool(tool_name)
    except Exception:
        return None


def generate_tool_markdown(tool: dict[str, Any]) -> str:
    """Generate a markdown doc for a single tool."""
    name = tool.get("name", "unknown")
    desc = tool.get("description", "")
    category = tool.get("category", "")
    safety = tool.get("safety", "")
    schema = tool.get("input_schema", {})
    gana = tool.get("gana")

    lines = [
        f"# {name}",
        "",
        f"**Category**: {category} | **Safety**: {safety}",
    ]
    if gana:
        lines.append(f"**Gana**: `{gana}`")
    lines.extend([
        "",
        "## Description",
        "",
        desc,
        "",
        "## Input Schema",
        "",
        "```json",
        json.dumps(schema, indent=2),
        "```",
        "",
        "## Example Invocation",
        "",
        "```python",
        "from whitemagic.tools.unified_api import call_tool",
        "",
        "result = call_tool(",
        f'    "{name}",',
    ])

    props = schema.get("properties", {})
    required = schema.get("required", [])
    example_args = {}
    for prop_name, prop_schema in props.items():
        prop_type = prop_schema.get("type", "string")
        if prop_type == "string":
            example_args[prop_name] = prop_schema.get("description", "example")[:50]
        elif prop_type == "integer":
            example_args[prop_name] = prop_schema.get("default", 10)
        elif prop_type == "number":
            example_args[prop_name] = prop_schema.get("default", 1.0)
        elif prop_type == "boolean":
            example_args[prop_name] = prop_schema.get("default", False)
        elif prop_type == "array":
            example_args[prop_name] = []

    if example_args:
        lines.append(f"    {json.dumps(example_args)}")
    lines.append(")")
    lines.append("```")
    lines.append("")
    lines.append(f"## Example Output")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps({"status": "success", "data": "..."}, indent=2))
    lines.append("```")
    lines.append("")

    return "\n".join(lines)


def generate_index_page(tools: list[dict[str, Any]]) -> str:
    """Generate an index page listing all tools."""
    lines = [
        "# WhiteMagic API Reference",
        "",
        f"**{len(tools)} tools** across all categories.",
        "",
        "| Tool | Category | Safety | Description |",
        "|------|----------|--------|-------------|",
    ]

    for tool in sorted(tools, key=lambda t: t.get("name", "")):
        name = tool.get("name", "")
        cat = tool.get("category", "")
        safety = tool.get("safety", "")
        desc = tool.get("description", "")[:80]
        lines.append(f"| [{name}](tools/{name}.md) | {cat} | {safety} | {desc} |")

    lines.append("")
    return "\n".join(lines)


def generate_openapi_spec(tools: list[dict[str, Any]]) -> dict[str, Any]:
    """Generate an OpenAPI spec for the MCP HTTP transport."""
    paths: dict[str, Any] = {}
    for tool in tools:
        name = tool.get("name", "unknown")
        path = f"/tools/{name}"
        schema = tool.get("input_schema", {})
        paths[path] = {
            "post": {
                "summary": tool.get("description", ""),
                "tags": [tool.get("category", "default")],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": schema if schema else {"type": "object"}
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Tool execution result",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "status": {"type": "string"},
                                        "data": {"type": "object"},
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

    return {
        "openapi": "3.0.0",
        "info": {
            "title": "WhiteMagic MCP API",
            "version": "25.0.0",
            "description": f"{len(tools)} MCP tools for AI agent memory, cognitive upgrades, and governance.",
        },
        "paths": paths,
    }


def generate_category_index(tools: list[dict[str, Any]]) -> dict[str, str]:
    """Generate per-category index pages. Returns {category: markdown}."""
    by_cat: dict[str, list[dict[str, Any]]] = {}
    for tool in tools:
        cat = tool.get("category", "UNKNOWN")
        by_cat.setdefault(cat, []).append(tool)

    pages = {}
    for cat, cat_tools in sorted(by_cat.items()):
        lines = [
            f"# Category: {cat}",
            "",
            f"**{len(cat_tools)} tools** in this category.",
            "",
            "| Tool | Safety | Description |",
            "|------|--------|-------------|",
        ]
        for tool in sorted(cat_tools, key=lambda t: t.get("name", "")):
            name = tool.get("name", "")
            safety = tool.get("safety", "")
            desc = tool.get("description", "")[:80]
            lines.append(f"| [{name}](../tools/{name}.md) | {safety} | {desc} |")
        lines.append("")
        pages[cat] = "\n".join(lines)
    return pages


def generate_gana_index(tools: list[dict[str, Any]]) -> dict[str, str]:
    """Generate per-Gana index pages. Returns {gana: markdown}."""
    by_gana: dict[str, list[dict[str, Any]]] = {}
    for tool in tools:
        gana = tool.get("gana")
        if gana:
            by_gana.setdefault(gana, []).append(tool)

    pages = {}
    for gana, gana_tools in sorted(by_gana.items()):
        lines = [
            f"# Gana: {gana}",
            "",
            f"**{len(gana_tools)} tools** routed through this Gana.",
            "",
            "| Tool | Category | Safety | Description |",
            "|------|----------|--------|-------------|",
        ]
        for tool in sorted(gana_tools, key=lambda t: t.get("name", "")):
            name = tool.get("name", "")
            cat = tool.get("category", "")
            safety = tool.get("safety", "")
            desc = tool.get("description", "")[:80]
            lines.append(f"| [{name}](../tools/{name}.md) | {cat} | {safety} | {desc} |")
        lines.append("")
        pages[gana] = "\n".join(lines)
    return pages


def generate_catalog_json(tools: list[dict[str, Any]]) -> str:
    """Generate machine-readable tool catalog."""
    catalog = {
        "version": "25.0.0",
        "tool_count": len(tools),
        "tools": sorted(tools, key=lambda t: t.get("name", "")),
    }
    return json.dumps(catalog, indent=2, default=str)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate WhiteMagic tool documentation")
    parser.add_argument("--output", "-o", default="docs/api", help="Output directory for markdown docs")
    parser.add_argument("--openapi", help="Output path for OpenAPI spec JSON")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown", help="Output format")
    parser.add_argument("--limit", type=int, help="Limit number of tools (for testing)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    logger.info("Collecting tool definitions...")
    tools = collect_tool_definitions()
    if args.limit:
        tools = tools[:args.limit]
    logger.info("Found %d tools", len(tools))

    # Enrich with Gana mapping
    logger.info("Mapping tools to Ganas...")
    for tool in tools:
        tool["gana"] = _get_gana_for_tool(tool.get("name", ""))

    if args.format == "json":
        catalog = generate_catalog_json(tools)
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(catalog, encoding="utf-8")
        logger.info("Catalog written to %s (%d tools)", args.output, len(tools))
        return

    output_dir = Path(args.output)
    tools_dir = output_dir / "tools"
    tools_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Generating per-tool markdown...")
    for tool in tools:
        name = tool.get("name", "unknown")
        md = generate_tool_markdown(tool)
        (tools_dir / f"{name}.md").write_text(md, encoding="utf-8")

    logger.info("Generating index page...")
    index = generate_index_page(tools)
    (output_dir / "README.md").write_text(index, encoding="utf-8")

    logger.info("Generating category index pages...")
    cat_dir = output_dir / "categories"
    cat_dir.mkdir(exist_ok=True)
    for cat, page in generate_category_index(tools).items():
        (cat_dir / f"{cat.lower()}.md").write_text(page, encoding="utf-8")

    logger.info("Generating Gana index pages...")
    gana_dir = output_dir / "gana"
    gana_dir.mkdir(exist_ok=True)
    for gana, page in generate_gana_index(tools).items():
        (gana_dir / f"{gana}.md").write_text(page, encoding="utf-8")

    logger.info("Generating catalog.json...")
    (output_dir / "catalog.json").write_text(generate_catalog_json(tools), encoding="utf-8")

    if args.openapi:
        logger.info("Generating OpenAPI spec...")
        spec = generate_openapi_spec(tools)
        Path(args.openapi).write_text(json.dumps(spec, indent=2), encoding="utf-8")
        logger.info("OpenAPI spec written to %s", args.openapi)

    logger.info("Done! %d tool docs generated in %s", len(tools), output_dir)


if __name__ == "__main__":
    main()
