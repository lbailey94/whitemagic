from __future__ import annotations

from functools import lru_cache

from whitemagic.tools.registry import AUTHORED_TOOL_REGISTRY, TOOL_REGISTRY, get_tool
from whitemagic.tools.tool_catalog import (
    GANA_NAMES,
    GANA_SHORT_DESC,
    get_dispatch_tool_names,
    get_gana_nested_tools,
)
from whitemagic.tools.tool_types import ToolDefinition, ToolStability


def get_gana_names() -> list[str]:
    return list(GANA_NAMES)



def get_gana_descriptions() -> dict[str, str]:
    return dict(GANA_SHORT_DESC)



@lru_cache(maxsize=1)
def _cached_surface_counts() -> tuple[int, int, int, int, int]:
    nested_tools = get_gana_nested_tools()
    nested_unique = {tool for tools in nested_tools.values() for tool in tools}
    dispatch_tools = set(get_dispatch_tool_names())
    return (
        len(AUTHORED_TOOL_REGISTRY),
        len(TOOL_REGISTRY),
        len(GANA_NAMES),
        len(nested_unique),
        len(dispatch_tools),
    )


def get_surface_counts() -> dict[str, int | dict[str, int]]:
    authored_tools, callable_tools, gana_tools, nested_unique_tools, dispatch_tools = _cached_surface_counts()
    by_stability: dict[str, int] = {tier.value: 0 for tier in ToolStability}
    for tool in TOOL_REGISTRY:
        by_stability[tool.stability.value] = by_stability.get(tool.stability.value, 0) + 1
    return {
        "authored_tools": authored_tools,
        "callable_tools": callable_tools,
        "gana_tools": gana_tools,
        "nested_unique_tools": nested_unique_tools,
        "dispatch_tools": dispatch_tools,
        "by_stability": by_stability,
    }



def get_gana_metadata() -> dict[str, tuple[str, list[str]]]:
    nested_tools = get_gana_nested_tools()
    return {
        gana_name: (
            GANA_SHORT_DESC.get(gana_name, f"Gana {gana_name}"),
            nested_tools.get(gana_name, []),
        )
        for gana_name in GANA_NAMES
    }



@lru_cache(maxsize=1)
def _cached_callable_tool_names() -> tuple[str, ...]:
    return tuple(tool.name for tool in TOOL_REGISTRY)


def get_callable_tool_names() -> list[str]:
    return list(_cached_callable_tool_names())



@lru_cache(maxsize=1)
def _cached_callable_tool_definitions() -> tuple[ToolDefinition, ...]:
    return tuple(TOOL_REGISTRY)


def get_callable_tool_definitions() -> list[ToolDefinition]:
    return list(_cached_callable_tool_definitions())



def get_callable_tool_definition(name: str) -> ToolDefinition | None:
    return get_tool(name)
