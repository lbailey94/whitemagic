"""CrewAI memory adapter — use WhiteMagic as CrewAI's memory backend.

Installation:
    pip install wm-memory crewai

Usage:
    from wm_memory.adapters import WhiteMagicCrewMemory
    from crewai import Agent, Crew, Process

    memory = WhiteMemoryCrewMemory()
    crew = Crew(agents=[...], memory=memory, process=Process.sequential)
"""

from __future__ import annotations

import logging
from typing import Any

from whitemagic.core.memory.adapters.agent_memory import AgentMemory

logger = logging.getLogger(__name__)


class WhiteMagicCrewMemory:
    """CrewAI-compatible memory backed by WhiteMagic.

    CrewAI uses a simple store/search/get_context interface.
    This adapter wraps AgentMemory to provide that interface while
    leveraging WhiteMagic's three-tier architecture.

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

    def store(self, key: str, value: str, metadata: dict[str, Any] | None = None) -> str:
        """Store a memory with a key.

        CrewAI agents call this to persist task results, observations, etc.
        """
        tags = {key} if key else set()
        if metadata:
            tags.update(metadata.get("tags", []))
        return self._am.long_term.store(
            content=value,
            title=key,
            tags=tags,
            importance=metadata.get("importance", 0.5) if metadata else 0.5,
            metadata=metadata,
        )

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Search memories by query."""
        return self._am.long_term.search_hybrid(query=query, limit=limit)

    def get_context(self, query: str, max_tokens: int = 2000) -> str:
        """Get formatted context for LLM injection.

        Combines short-term active chunks with long-term search results
        and recent episodic turns, formatted as a context string.
        """
        parts: list[str] = []

        active = self._am.short_term.get_active(max_tokens=max_tokens // 3)
        if active:
            parts.append("## Active Context")
            for chunk in active:
                parts.append(f"- {chunk.get('title', 'untitled')}: {chunk.get('content_preview', '')}")

        results = self._am.long_term.search_hybrid(query=query, limit=5)
        if results:
            parts.append("\n## Relevant Memories")
            for r in results:
                parts.append(f"- {r.get('title', 'untitled')}: {str(r.get('content', ''))[:200]}")

        turns = self._am.episodic.recall_progressive(token_budget=max_tokens // 3)
        if turns:
            parts.append("\n## Recent Conversation")
            formatted = self._am.episodic.format_context(turns, full=False)
            parts.append(formatted)

        return "\n".join(parts) if parts else ""

    def record_agent_action(
        self,
        agent_name: str,
        action: str,
        result: str,
        importance: float = 0.5,
    ) -> str:
        """Record a CrewAI agent's action and result as episodic memory."""
        return self._am.episodic.record(
            role="ai",
            content=f"[{agent_name}] {action}: {result}",
            turn_type="decision" if importance >= 0.7 else "message",
            importance=importance,
            tags={f"agent:{agent_name}", "crewai"},
        )

    def clear(self) -> None:
        """Clear short-term memory only."""
        self._am.clear_short_term()
