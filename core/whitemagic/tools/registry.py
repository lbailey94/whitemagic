from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

from whitemagic.tools.tool_catalog import (
    collect_authored_tool_definitions,
    synthesize_callable_tool_definitions,
)
from whitemagic.tools.tool_types import ToolCategory, ToolDefinition, ToolSafety


class LazyToolRegistry(list[ToolDefinition]):
    def __init__(self, loader: Callable[[], list[ToolDefinition]]) -> None:
        super().__init__()
        self._loader = loader
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        tools = self._loader()
        super().clear()
        super().extend(tools)
        self._loaded = True

    def __iter__(self) -> Iterator[ToolDefinition]:
        self._ensure_loaded()
        return super().__iter__()

    def __len__(self) -> int:
        self._ensure_loaded()
        return super().__len__()

    def __getitem__(self, item: Any) -> Any:
        self._ensure_loaded()
        return super().__getitem__(item)

    def __contains__(self, item: object) -> bool:
        self._ensure_loaded()
        return super().__contains__(item)

    def copy(self) -> list[ToolDefinition]:
        self._ensure_loaded()
        return list(self)

    def refresh(self) -> list[ToolDefinition]:
        self._loaded = False
        self._ensure_loaded()
        return list(self)


AUTHORED_TOOL_REGISTRY: list[ToolDefinition] = collect_authored_tool_definitions()


def _load_callable_registry() -> list[ToolDefinition]:
    return synthesize_callable_tool_definitions(AUTHORED_TOOL_REGISTRY)


TOOL_REGISTRY = LazyToolRegistry(_load_callable_registry)


def get_all_tools() -> list[ToolDefinition]:
    return TOOL_REGISTRY.copy()



def get_authored_tools() -> list[ToolDefinition]:
    return list(AUTHORED_TOOL_REGISTRY)



def refresh_tool_registry() -> list[ToolDefinition]:
    global AUTHORED_TOOL_REGISTRY
    AUTHORED_TOOL_REGISTRY = collect_authored_tool_definitions()
    return TOOL_REGISTRY.refresh()



def get_tool(name: str) -> ToolDefinition | None:
    for tool in TOOL_REGISTRY:
        if tool.name == name:
            return tool
    return None



def get_tools_by_category(category: ToolCategory) -> list[ToolDefinition]:
    return [t for t in TOOL_REGISTRY if t.category == category]



def get_tools_by_safety(safety: ToolSafety) -> list[ToolDefinition]:
    return [t for t in TOOL_REGISTRY if t.safety == safety]



def get_safe_tools() -> list[ToolDefinition]:
    return get_tools_by_safety(ToolSafety.READ)



def to_openai_tools() -> list[dict[str, Any]]:
    return [t.to_openai_function() for t in TOOL_REGISTRY]



def to_mcp_tools() -> list[dict[str, Any]]:
    return [t.to_mcp_tool() for t in TOOL_REGISTRY]



def get_tool_names() -> list[str]:
    return [t.name for t in TOOL_REGISTRY]
