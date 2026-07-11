"""AutoGen memory adapter — use WhiteMagic as AutoGen's memory backend.

Installation:
    pip install wm-memory autogen-agentpy

Usage:
    from wm_memory.adapters import WhiteMagicAutoGenMemory

    memory = WhiteMagicAutoGenMemory()
    # Pass to AutoGen agents or group chat
"""

from __future__ import annotations

import logging
from typing import Any

from whitemagic.core.memory.adapters.agent_memory import AgentMemory

logger = logging.getLogger(__name__)


class WhiteMagicAutoGenMemory:
    """AutoGen-compatible memory backed by WhiteMagic.

    AutoGen's memory protocol expects add(), retrieve(), and clear().
    This adapter wraps AgentMemory to provide that interface while
    leveraging WhiteMagic's three-tier architecture with episodic
    recording of multi-agent conversations.

    Args:
        agent_memory: Optional pre-configured AgentMemory instance.
        session_id: Optional session ID.
    """

    def __init__(
        self,
        agent_memory: AgentMemory | None = None,
        session_id: str | None = None,
    ) -> None:
        self._am = agent_memory or AgentMemory(session_id=session_id)

    def add(self, content: str, agent_name: str = "user", **kwargs: Any) -> str:
        """Add a message to memory.

        Args:
            content: The message content.
            agent_name: Name of the agent (used as role).
            **kwargs: Additional metadata (importance, turn_type, tags).
        """
        importance = kwargs.get("importance", 0.5)
        turn_type = kwargs.get("turn_type", "message")
        tags = kwargs.get("tags", set())

        role = "user" if agent_name.lower() in ("user", "human", "me") else "ai"

        mem_id = self._am.episodic.record(
            role=role,
            content=f"[{agent_name}] {content}",
            turn_type=turn_type,
            importance=importance,
            tags=tags | {f"agent:{agent_name}"} if tags else {f"agent:{agent_name}"},
        )

        if importance >= 0.7:
            self._am.long_term.store(
                content=content,
                title=f"[{agent_name}] {content[:60]}",
                tags={f"agent:{agent_name}", "autogen"} | (tags if tags else set()),
                importance=importance,
            )

        return mem_id

    def retrieve(
        self,
        query: str | None = None,
        agent_name: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Retrieve relevant memories.

        Args:
            query: Optional search query. If None, returns recent turns.
            agent_name: Optional filter by agent name.
            limit: Maximum results.
        """
        if query:
            results = self._am.long_term.search_hybrid(query=query, limit=limit)
        else:
            results = self._am.episodic.recall_recent(n=limit)

        if agent_name and results:
            results = [r for r in results if f"agent:{agent_name}" in r.get("tags", [])]

        return results

    def get_context(self, query: str | None = None, token_budget: int = 2000) -> str:
        """Get formatted context for LLM injection."""
        if query:
            results = self._am.long_term.search_hybrid(query=query, limit=5)
            parts = [f"- {r.get('title', '')}: {str(r.get('content', ''))[:200]}" for r in results]
            return "\n".join(parts) if parts else ""

        turns = self._am.episodic.recall_progressive(token_budget=token_budget)
        return self._am.episodic.format_context(turns, full=False)

    def clear(self) -> None:
        """Clear short-term memory only. Episodic and long-term persist."""
        self._am.clear_short_term()

    def summary(self) -> dict[str, Any]:
        """Get memory summary across all tiers."""
        return self._am.stats()
