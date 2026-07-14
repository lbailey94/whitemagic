"""CrewAI adapter — WhiteMagic memory and tools for CrewAI agents.

Usage:
    from whitemagic.adapters.crewai import WhiteMagicCrewMemory
    memory = WhiteMagicCrewMemory(galaxy="universal")
"""

from __future__ import annotations

from typing import Any


class WhiteMagicCrewMemory:
    """CrewAI-compatible memory backed by WhiteMagic."""

    def __init__(
        self,
        galaxy: str = "universal",
        user_id: str = "default",
        search_limit: int = 10,
    ) -> None:
        self.galaxy = galaxy
        self.user_id = user_id
        self.search_limit = search_limit
        self._storage: list[dict[str, str]] = []

    def _call(self, tool: str, **kwargs: Any) -> dict[str, Any]:
        from whitemagic.tools.unified_api import call_tool
        return call_tool(tool, **kwargs)

    def store(self, content: str, metadata: dict[str, str] | None = None) -> str:
        """Store a memory."""
        tags = list(metadata.keys()) if metadata else []
        result = self._call(
            "create_memory",
            content=content,
            galaxy=self.galaxy,
            tags=tags,
        )
        mem_id = result.get("data", {}).get("id", "") if result.get("status") == "success" else ""
        if mem_id:
            self._storage.append({"id": mem_id, "content": content})
        return mem_id

    def search(self, query: str, n_results: int = 5) -> list[dict[str, str]]:
        """Search memories semantically."""
        result = self._call(
            "search_memories",
            query=query,
            galaxy=self.galaxy,
            limit=n_results,
        )
        if result.get("status") != "success":
            return []
        data = result.get("data", result.get("results", []))
        if isinstance(data, list):
            return [
                {"id": item.get("id", ""), "content": item.get("content", "")}
                for item in data if isinstance(item, dict)
            ]
        return []

    def get_all(self) -> list[dict[str, str]]:
        """Get all stored memories."""
        return self._storage.copy()

    def clear(self) -> None:
        """Clear memory references (does not delete from WhiteMagic)."""
        self._storage.clear()


class WhiteMagicCrewTools:
    """CrewAI tool collection backed by WhiteMagic."""

    def __init__(self, galaxy: str = "universal") -> None:
        self.galaxy = galaxy
        self.memory = WhiteMagicCrewMemory(galaxy=galaxy)

    def search(self, query: str) -> str:
        """Search WhiteMagic memories."""
        results = self.memory.search(query)
        import json
        return json.dumps(results, default=str)

    def remember(self, content: str) -> str:
        """Store a memory in WhiteMagic."""
        return self.memory.store(content)

    def health(self) -> str:
        """Check WhiteMagic health."""
        result = self._call("health")
        import json
        return json.dumps(result, default=str)

    def _call(self, tool: str, **kwargs: Any) -> dict[str, Any]:
        from whitemagic.tools.unified_api import call_tool
        return call_tool(tool, **kwargs)
