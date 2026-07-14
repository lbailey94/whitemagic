"""AutoGen adapter — WhiteMagic memory and tools for AutoGen agents.

Usage:
    from whitemagic.adapters.autogen import register_whitemagic_tools
    register_whitemagic_tools(agent, galaxy="universal")
"""

from __future__ import annotations

from typing import Any


def register_whitemagic_tools(
    agent: Any,
    galaxy: str = "universal",
    tools: list[str] | None = None,
) -> None:
    """Register WhiteMagic tools with an AutoGen agent.

    Args:
        agent: AutoGen ConversableAgent instance
        galaxy: WhiteMagic galaxy to use for memory operations
        tools: Optional list of tool names to register (default: search, create, health)
    """
    from whitemagic.tools.unified_api import call_tool
    import json

    default_tools = tools or ["search_memories", "create_memory", "health"]

    tool_descriptions = {
        "search_memories": "Search WhiteMagic memories by semantic query. Args: query (str), limit (int, default 10).",
        "create_memory": "Create a new memory in WhiteMagic. Args: content (str), tags (list[str]).",
        "health": "Check WhiteMagic system health. No arguments.",
    }

    def make_executor(tool_name: str):
        def executor(**kwargs: Any) -> str:
            kwargs.setdefault("galaxy", galaxy)
            result = call_tool(tool_name, **kwargs)
            return json.dumps(result, default=str)
        return executor

    for tool_name in default_tools:
        agent.register_function(
            function_map={
                tool_name: make_executor(tool_name),
            }
        )

        # Register the tool's schema if the agent supports it
        if hasattr(agent, "register_tool"):
            try:
                from whitemagic.tools.registry import get_all_tools
                for td in get_all_tools():
                    if td.name == tool_name:
                        agent.register_tool(
                            name=tool_name,
                            description=tool_descriptions.get(tool_name, td.description),
                            input_schema=td.input_schema,
                        )
                        break
            except Exception:
                pass


class WhiteMagicAgentMixin:
    """Mixin to add WhiteMagic memory to any AutoGen agent.

    Usage:
        class MyAgent(WhiteMagicAgentMixin, ConversableAgent):
            pass
    """

    def init_whitemagic(self, galaxy: str = "universal") -> None:
        """Initialize WhiteMagic memory for this agent."""
        self._wm_galaxy = galaxy
        register_whitemagic_tools(self, galaxy=galaxy)

    def remember(self, content: str, tags: list[str] | None = None) -> str:
        """Store a memory."""
        from whitemagic.tools.unified_api import call_tool
        result = call_tool("create_memory", content=content, galaxy=self._wm_galaxy, tags=tags or [])
        return result.get("data", {}).get("id", "") if result.get("status") == "success" else ""

    def recall(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Recall memories."""
        from whitemagic.tools.unified_api import call_tool
        result = call_tool("search_memories", query=query, galaxy=self._wm_galaxy, limit=limit)
        if result.get("status") != "success":
            return []
        data = result.get("data", result.get("results", []))
        return data if isinstance(data, list) else []
