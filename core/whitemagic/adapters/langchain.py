"""LangChain adapter — WhiteMagic memory and tools for LangChain agents.

Usage:
    from whitemagic.adapters.langchain import WhiteMagicMemory

    memory = WhiteMagicMemory(galaxy="universal", user_id="alice")
    agent = create_react_agent(llm, tools, memory=memory)
"""

from __future__ import annotations

from typing import Any


class WhiteMagicMemory:
    """LangChain-compatible memory backed by WhiteMagic.

    Drop-in replacement for ConversationBufferMemory with semantic search.
    """

    def __init__(
        self,
        galaxy: str = "universal",
        user_id: str = "default",
        search_limit: int = 10,
        memory_key: str = "history",
    ) -> None:
        self.galaxy = galaxy
        self.user_id = user_id
        self.search_limit = search_limit
        self.memory_key = memory_key

    def _call(self, tool: str, **kwargs: Any) -> dict[str, Any]:
        from whitemagic.tools.unified_api import call_tool
        return call_tool(tool, **kwargs)

    def save_context(self, inputs: dict[str, str], outputs: dict[str, str]) -> None:
        """Save a conversation turn to WhiteMagic memory."""
        human_msg = inputs.get("input", inputs.get("human_input", ""))
        ai_msg = outputs.get("output", outputs.get("ai_response", ""))

        if human_msg:
            self._call(
                "create_memory",
                content=f"Human: {human_msg}",
                galaxy=self.galaxy,
                tags=["conversation", "human"],
            )
        if ai_msg:
            self._call(
                "create_memory",
                content=f"AI: {ai_msg}",
                galaxy=self.galaxy,
                tags=["conversation", "ai"],
            )

    def load_memory_variables(self, inputs: dict[str, str]) -> dict[str, str]:
        """Load relevant memories from WhiteMagic."""
        query = inputs.get("input", inputs.get("human_input", ""))
        if not query:
            return {self.memory_key: ""}

        result = self._call(
            "search_memories",
            query=query,
            galaxy=self.galaxy,
            limit=self.search_limit,
        )

        if result.get("status") != "success":
            return {self.memory_key: ""}

        data = result.get("data", result.get("results", []))
        if isinstance(data, list):
            memories = [item.get("content", "") for item in data if isinstance(item, dict)]
            return {self.memory_key: "\n".join(memories)}

        return {self.memory_key: ""}

    def clear(self) -> None:
        """Clear all memories in this galaxy (use with caution)."""
        # WhiteMagic doesn't have a bulk delete — this is a no-op for safety
        pass

    @property
    def return_messages(self) -> bool:
        """Whether to return messages as a list or string."""
        return False


class WhiteMagicTool:
    """Wrap a WhiteMagic tool as a LangChain Tool."""

    def __init__(self, tool_name: str, description: str | None = None) -> None:
        self.tool_name = tool_name
        self._description = description

    @property
    def name(self) -> str:
        return self.tool_name

    @property
    def description(self) -> str:
        if self._description:
            return self._description
        try:
            from whitemagic.tools.registry import get_all_tools
            for td in get_all_tools():
                if td.name == self.tool_name:
                    return td.description
        except Exception:  # noqa: BLE001
            pass
        return f"WhiteMagic tool: {self.tool_name}"

    def run(self, **kwargs: Any) -> str:
        """Execute the tool and return a string result."""
        import json

        from whitemagic.tools.unified_api import call_tool
        result = call_tool(self.tool_name, **kwargs)
        return json.dumps(result, default=str)

    async def arun(self, **kwargs: Any) -> str:
        """Async execution (falls back to sync)."""
        return self.run(**kwargs)


class WhiteMagicToolkit:
    """Collection of common WhiteMagic tools for LangChain agents."""

    def __init__(self, galaxy: str = "universal") -> None:
        self.galaxy = galaxy

    def get_tools(self) -> list[WhiteMagicTool]:
        """Return list of WhiteMagic tools."""
        return [
            WhiteMagicTool("search_memories", "Search WhiteMagic memories by semantic query"),
            WhiteMagicTool("create_memory", "Create a new memory in WhiteMagic"),
            WhiteMagicTool("health", "Check WhiteMagic system health"),
            WhiteMagicTool("capabilities", "List WhiteMagic capabilities"),
        ]
