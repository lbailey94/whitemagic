"""LangChain memory adapter — use WhiteMagic as LangChain's memory backend.

Installation:
    pip install wm-memory langchain

Usage:
    from wm_memory.adapters import WhiteMagicMemory
    from langchain.agents import AgentExecutor, create_openai_tools_agent

    memory = WhiteMagicMemory(memory_key="chat_history", return_messages=True)
    agent = AgentExecutor(..., memory=memory)
"""

from __future__ import annotations

import logging
from typing import Any

from whitemagic.core.memory.adapters.agent_memory import AgentMemory

logger = logging.getLogger(__name__)

try:
    from langchain_core.memory import BaseMemory
    from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
    _HAS_LANGCHAIN = True
except ImportError:
    _HAS_LANGCHAIN = False
    BaseMemory = object  # type: ignore[misc, assignment]
    BaseMessage = object  # type: ignore[misc, assignment]


class WhiteMagicMemory(BaseMemory if _HAS_LANGCHAIN else object):
    """LangChain BaseMemory backed by WhiteMagic's three-tier memory.

    Stores conversation turns in episodic memory (SessionRecorder),
    retrieves context via progressive recall, and persists facts to
    long-term memory automatically.

    Args:
        memory_key: Key to use in prompt template (default "chat_history").
        return_messages: If True, return BaseMessage objects. If False, return string.
        agent_memory: Optional pre-configured AgentMemory instance.
        session_id: Optional session ID (creates new if not provided).
        auto_persist: If True, automatically store important turns to long-term memory.
    """

    def __init__(
        self,
        memory_key: str = "chat_history",
        return_messages: bool = True,
        agent_memory: AgentMemory | None = None,
        session_id: str | None = None,
        auto_persist: bool = True,
    ) -> None:
        if not _HAS_LANGCHAIN:
            raise ImportError(
                "langchain-core is required. Install with: pip install langchain-core"
            )
        self.memory_key = memory_key
        self.return_messages = return_messages
        self._am = agent_memory or AgentMemory(session_id=session_id)
        self.auto_persist = auto_persist

    @property
    def memory_variables(self) -> list[str]:
        return [self.memory_key]

    def load_memory_variables(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Load conversation history into prompt variables."""
        turns = self._am.episodic.recall_progressive(token_budget=2000)

        if self.return_messages:
            messages: list[BaseMessage] = []
            for turn in turns:
                role = turn.get("role", "user")
                content = turn.get("preview", turn.get("content", ""))
                if role == "user":
                    messages.append(HumanMessage(content=content))
                else:
                    messages.append(AIMessage(content=content))
            return {self.memory_key: messages}
        else:
            formatted = self._am.episodic.format_context(turns, full=False)
            return {self.memory_key: formatted}

    def save_context(self, inputs: dict[str, Any], outputs: dict[str, str]) -> None:
        """Save a conversation turn to episodic memory."""
        input_str = inputs.get("input", inputs.get("question", str(inputs)))
        output_str = outputs.get("output", outputs.get("answer", str(outputs)))

        self._am.episodic.record(
            role="user",
            content=input_str,
            turn_type="message",
            importance=0.5,
        )
        self._am.episodic.record(
            role="ai",
            content=output_str,
            turn_type="answer",
            importance=0.6,
        )

        if self.auto_persist:
            importance = self._classify_importance(output_str)
            if importance >= 0.7:
                self._am.long_term.store(
                    content=output_str,
                    title=f"Session turn: {input_str[:60]}",
                    tags={"auto_persisted", f"session:{self._am.episodic.session_id}"},
                    importance=importance,
                )

    def clear(self) -> None:
        """Clear short-term memory. Long-term and episodic memories persist."""
        self._am.clear_short_term()

    def _classify_importance(self, content: str) -> float:
        """Heuristic importance scoring for auto-persistence."""
        high_indicators = ["error", "bug", "fix", "important", "decision", "breakthrough", "critical"]
        medium_indicators = ["update", "change", "add", "remove", "refactor"]
        content_lower = content.lower()

        if any(w in content_lower for w in high_indicators):
            return 0.8
        if any(w in content_lower for w in medium_indicators):
            return 0.6
        return 0.4
