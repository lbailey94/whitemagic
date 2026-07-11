"""OpenAI Agents SDK memory adapter — use WhiteMagic as the memory backend.

Installation:
    pip install wm-memory openai-agents

Usage:
    from wm_memory.adapters import WhiteMagicOpenAIMemory
    from agents import Agent, Runner

    memory = WhiteMagicOpenAIMemory()
    agent = Agent(name="Assistant", instructions="...", memory=memory)
    result = Runner.run_sync(agent, "Hello")
"""

from __future__ import annotations

import logging
from typing import Any

from whitemagic.core.memory.adapters.agent_memory import AgentMemory

logger = logging.getLogger(__name__)


class WhiteMagicOpenAIMemory:
    """OpenAI Agents SDK memory backed by WhiteMagic.

    The OpenAI Agents SDK expects a memory interface with add()
    and retrieve() methods. This adapter wraps AgentMemory to
    provide that interface while leveraging WhiteMagic's three-tier
    architecture.

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

    def add(self, content: str, role: str = "user", **kwargs: Any) -> str:
        """Add a message to memory.

        Args:
            content: The message content.
            role: "user" or "assistant".
            **kwargs: Additional metadata (importance, turn_type, tags).
        """
        wm_role = "user" if role == "user" else "ai"
        return self._am.episodic.record(
            role=wm_role,
            content=content,
            turn_type=kwargs.get("turn_type", "message"),
            importance=kwargs.get("importance", 0.5),
            tags=kwargs.get("tags"),
        )

    def add_tool_call(
        self,
        tool_name: str,
        tool_input: str,
        tool_output: str,
        importance: float = 0.6,
    ) -> str:
        """Record a tool call as an episodic memory."""
        return self._am.episodic.record(
            role="ai",
            content=f"Tool: {tool_name}\nInput: {tool_input}\nOutput: {tool_output}",
            turn_type="code_change" if "code" in tool_name.lower() else "context",
            importance=importance,
            tags={"tool_call", f"tool:{tool_name}"},
        )

    def retrieve(
        self,
        query: str | None = None,
        limit: int = 10,
        token_budget: int = 2000,
    ) -> str:
        """Retrieve formatted context for LLM injection.

        Args:
            query: Optional search query. If None, returns recent turns.
            limit: Maximum results (used when query is provided).
            token_budget: Token budget for progressive recall.
        """
        if query:
            results = self._am.long_term.search_hybrid(query=query, limit=limit)
            parts = []
            for r in results:
                title = r.get("title", "")
                content = str(r.get("content", ""))[:300]
                parts.append(f"- {title}: {content}" if title else f"- {content}")
            return "\n".join(parts) if parts else ""

        turns = self._am.episodic.recall_progressive(token_budget=token_budget)
        return self._am.episodic.format_context(turns, full=False)

    def add_to_working_memory(self, content: str, importance: float = 0.5) -> dict[str, Any]:
        """Add an item to short-term working memory."""
        return self._am.short_term.add(content, importance=importance)

    def get_working_context(self, max_tokens: int | None = None) -> list[dict[str, Any]]:
        """Get active working memory chunks."""
        return self._am.short_term.get_active(max_tokens=max_tokens)

    def clear(self) -> None:
        """Clear short-term memory only."""
        self._am.clear_short_term()

    def summary(self) -> dict[str, Any]:
        """Get memory summary across all tiers."""
        return self._am.stats()
