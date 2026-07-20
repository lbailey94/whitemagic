"""PydanticAI adapter — WhiteMagic toolset for PydanticAI agents.

Usage:
    from whitemagic.adapters.pydantic_ai import WhiteMagicToolset
    toolset = WhiteMagicToolset(galaxy="universal")
    # Use tools with PydanticAI Agent
"""

from __future__ import annotations

from typing import Any


class WhiteMagicToolset:
    """PydanticAI-compatible toolset backed by WhiteMagic."""

    def __init__(
        self,
        galaxy: str = "universal",
        tool_names: list[str] | None = None,
    ) -> None:
        self.galaxy = galaxy
        self._tool_names = tool_names or [
            "search_memories",
            "create_memory",
            "health",
            "capabilities",
        ]

    def _call(self, tool: str, **kwargs: Any) -> dict[str, Any]:
        from whitemagic.tools.unified_api import call_tool
        return call_tool(tool, **kwargs)

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        """Get OpenAI-compatible function definitions for all tools."""
        try:
            from whitemagic.tools.registry import get_all_tools
            all_tools = get_all_tools()
            return [
                {
                    "name": td.name,
                    "description": td.description,
                    "parameters": td.input_schema,
                }
                for td in all_tools
                if td.name in self._tool_names
            ]
        except Exception:  # noqa: BLE001
            return []

    def execute(self, tool_name: str, **kwargs: Any) -> dict[str, Any]:
        """Execute a tool by name."""
        kwargs.setdefault("galaxy", self.galaxy)
        return self._call(tool_name, **kwargs)

    def search_memories(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search memories semantically."""
        result = self._call("search_memories", query=query, galaxy=self.galaxy, limit=limit)
        if result.get("status") != "success":
            return []
        data = result.get("data", result.get("results", []))
        return data if isinstance(data, list) else []

    def create_memory(self, content: str, tags: list[str] | None = None) -> str:
        """Create a new memory."""
        result = self._call("create_memory", content=content, galaxy=self.galaxy, tags=tags or [])
        return result.get("data", {}).get("id", "") if result.get("status") == "success" else ""

    def health(self) -> dict[str, Any]:
        """Check system health."""
        return self._call("health")
