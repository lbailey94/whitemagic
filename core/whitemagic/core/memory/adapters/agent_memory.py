"""AgentMemory — Three-tier memory facade for AI agents.

Provides a single, clean interface to WhiteMagic's three memory tiers:

    >>> from whitemagic.core.memory.adapters import AgentMemory
    >>> mem = AgentMemory()
    >>>
    >>> # Short-term: bounded working memory (Miller's Law 7±2)
    >>> mem.short_term.add("current task", importance=0.8)
    >>> mem.short_term.get_active()
    >>>
    >>> # Long-term: persistent semantic memory with search
    >>> mem.long_term.store("API X has rate limit 100/min", tags=["api"])
    >>> mem.long_term.search("rate limits", limit=5)
    >>> mem.long_term.consolidate()
    >>>
    >>> # Episodic: conversation/session memory
    >>> mem.episodic.record(role="user", content="Fix the auth bug")
    >>> mem.episodic.recall_recent(10)
    >>> mem.episodic.recall_progressive(token_budget=500)

This facade wraps:
    - WorkingMemory (short-term, LRU, activation decay)
    - UnifiedMemory (long-term, SQLite, HNSW, FTS5, galaxy partitioning)
    - SessionRecorder (episodic, chronological, progressive recall)
"""

from __future__ import annotations

import logging
from typing import Any

from whitemagic.core.intelligence.working_memory import WorkingMemory
from whitemagic.core.memory.session_recorder import SessionRecorder
from whitemagic.core.memory.unified import UnifiedMemory
from whitemagic.core.memory.unified_types import MemoryType

logger = logging.getLogger(__name__)


class ShortTermMemory:
    """Short-term memory tier — bounded working memory with LRU eviction.

    Wraps WorkingMemory (Miller's Law 7±2 chunks, activation decay,
    importance-weighted retention, rehearsal, chunking).
    """

    def __init__(self, capacity: int = 7) -> None:
        self._wm = WorkingMemory(capacity=capacity)

    def add(
        self,
        content: str,
        memory_id: str | None = None,
        title: str = "",
        importance: float = 0.5,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Bring an item into working memory focus.

        If at capacity, evicts the lowest-activation chunk.
        If already present, rehearses it (boosts activation).
        """
        from uuid import uuid4

        mid = memory_id or str(uuid4())
        chunk = self._wm.attend(
            memory_id=mid,
            content=content,
            title=title,
            importance=importance,
            tags=tags,
        )
        return chunk.to_dict()

    def get_active(self, max_tokens: int | None = None) -> list[dict[str, Any]]:
        """Get active chunks sorted by activation (highest first).

        Args:
            max_tokens: Optional token budget (chars / 4) to limit output.
        """
        return self._wm.get_context(max_tokens=max_tokens)

    def get_active_ids(self) -> list[str]:
        """Get IDs of all active chunks."""
        return self._wm.get_active_ids()

    def group(self, chunk_ids: list[str], group_id: str, group_title: str = "") -> dict[str, Any] | None:
        """Group multiple chunks into one slot (cognitive chunking)."""
        chunk = self._wm.group(chunk_ids, group_id, group_title)
        return chunk.to_dict() if chunk else None

    def forget(self, memory_id: str) -> bool:
        """Explicitly remove a chunk from working memory."""
        return self._wm.forget(memory_id)

    def clear(self) -> None:
        """Clear all working memory."""
        self._wm.clear()

    def status(self) -> dict[str, Any]:
        """Get working memory status (capacity, used, available, chunks)."""
        return self._wm.get_status()

    @property
    def capacity(self) -> int:
        return self._wm.capacity


class LongTermMemory:
    """Long-term memory tier — persistent semantic memory with search.

    Wraps UnifiedMemory (SQLite backend, HNSW vector index, FTS5 full-text,
    galaxy partitioning, content-hash dedup, surprise-gated ingestion,
    5D holographic coordinates, Hebbian link strengthening).
    """

    def __init__(self, base_path: Any | None = None) -> None:
        self._um = UnifiedMemory(base_path=base_path) if base_path else UnifiedMemory()

    def store(
        self,
        content: str,
        title: str | None = None,
        tags: set[str] | None = None,
        importance: float = 0.5,
        emotional_valence: float = 0.0,
        memory_type: MemoryType | str = MemoryType.LONG_TERM,
        galaxy: str = "universal",
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Store a persistent memory. Returns the memory ID.

        Args:
            content: The memory content (text or structured data).
            title: Optional display title.
            tags: Optional tags for filtering.
            importance: 0.0-1.0 static weight.
            emotional_valence: -1.0 to 1.0 (negative to positive).
            memory_type: Memory type (defaults to LONG_TERM).
            galaxy: Target galaxy (universal, sessions, codex, etc.).
            metadata: Optional structured metadata.
        """
        mem = self._um.store(
            content=content,
            memory_type=memory_type,
            tags=tags,
            emotional_valence=emotional_valence,
            importance=importance,
            metadata=metadata,
            title=title,
            galaxy=galaxy,
        )
        return mem.id if hasattr(mem, "id") else str(mem)

    def search(
        self,
        query: str | None = None,
        tags: set[str] | None = None,
        memory_type: MemoryType | None = None,
        min_importance: float = 0.0,
        limit: int = 10,
        galaxy: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search memories with various filters (FTS5 + tag + type).

        Args:
            query: Full-text search query.
            tags: Filter by tags (AND logic).
            memory_type: Filter by memory type.
            min_importance: Minimum importance threshold.
            limit: Maximum results.
            galaxy: Restrict to a specific galaxy.
        """
        results = self._um.search(
            query=query,
            tags=tags,
            memory_type=memory_type,
            min_importance=min_importance,
            limit=limit,
            galaxy=galaxy,
        )
        return [m.to_dict() for m in results]

    def search_similar(
        self,
        query: str,
        memory_type: MemoryType | None = None,
        threshold: float = 0.1,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Semantic similarity search using embeddings + HNSW.

        Args:
            query: Text to find similar memories for.
            memory_type: Filter by memory type.
            threshold: Minimum similarity score (0.0-1.0).
            limit: Maximum results.
        """
        results = self._um.search_similar(
            query=query,
            memory_type=memory_type,
            threshold=threshold,
            limit=limit,
        )
        return [m.to_dict() for m in results]

    def search_hybrid(
        self,
        query: str,
        limit: int = 10,
        galaxy: str | None = None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Hybrid search: FTS5 + semantic + reranking (best of both).

        This is the recommended search method for most use cases.
        """
        results = self._um.search_hybrid(query=query, limit=limit, galaxy=galaxy, **kwargs)
        return [m.to_dict() for m in results]

    def recall(self, memory_id: str) -> dict[str, Any] | None:
        """Recall a specific memory by ID. Boosts its neuro_score."""
        mem = self._um.recall(memory_id)
        return mem.to_dict() if mem else None

    def consolidate(self) -> int:
        """Trigger memory consolidation (prune weak memories, rotate to archive).

        Returns the number of memories pruned.
        """
        return self._um.prune()

    def link(
        self,
        source_id: str,
        target_id: str,
        link_type: str = "related",
        strength: float = 0.5,
    ) -> bool:
        """Create a link between two memories (Hebbian association).

        Args:
            source_id: Source memory ID.
            target_id: Target memory ID.
            link_type: One of: related, extends, contradicts, supersedes, temporal, causal, cascade.
            strength: Link strength (0.0-1.0).
        """
        from whitemagic.core.memory.unified_types import LinkType

        link_map = {
            "related": LinkType.RELATED,
            "extends": LinkType.EXTENDS,
            "contradicts": LinkType.CONTRADICTS,
            "supersedes": LinkType.SUPERSEDES,
            "temporal": LinkType.TEMPORAL,
            "causal": LinkType.CAUSAL,
            "cascade": LinkType.CASCADE,
        }
        lt = link_map.get(link_type, LinkType.RELATED)
        mem = self._um.recall(source_id)
        if mem is None:
            return False
        mem.add_link(target_id, lt, strength)
        return True

    def stats(self) -> dict[str, Any]:
        """Get memory system statistics."""
        return self._um.get_stats()


class EpisodicMemory:
    """Episodic memory tier — conversation/session memory with chronological ordering.

    Wraps SessionRecorder (per-session sequence numbers, role tags,
    turn types, progressive recall, selective replay, cross-session
    continuity, sleep consolidation).
    """

    def __init__(self, session_id: str | None = None) -> None:
        self._sr = SessionRecorder(session_id=session_id)

    @property
    def session_id(self) -> str:
        """Current session ID."""
        return self._sr.session_id

    @property
    def sequence(self) -> int:
        """Current sequence number."""
        return self._sr.sequence

    def record(
        self,
        role: str,
        content: str,
        turn_type: str = "message",
        importance: float = 0.5,
        emotional_valence: float | None = None,
        tags: set[str] | None = None,
    ) -> str:
        """Record a conversation turn as a persistent episodic memory.

        Args:
            role: "user" or "ai".
            content: The turn content.
            turn_type: One of: message, decision, breakthrough, question, answer, code_change, error, summary, context.
            importance: 0.0-1.0 importance weight.
            emotional_valence: -1.0 to 1.0. Auto-detected if None.
            tags: Additional tags.

        Returns:
            Memory ID of the recorded turn.
        """
        if role == "user":
            return self._sr.record_user(
                content=content,
                turn_type=turn_type,
                importance=importance,
                emotional_valence=emotional_valence,
                tags=tags,
            )
        elif role == "ai":
            return self._sr.record_ai(
                content=content,
                turn_type=turn_type,
                importance=importance,
                emotional_valence=emotional_valence,
                tags=tags,
            )
        else:
            raise ValueError(f"role must be 'user' or 'ai', got '{role}'")

    def recall_recent(self, n: int = 10) -> list[dict[str, Any]]:
        """Recall the last N turns in chronological order (oldest to newest)."""
        return self._sr.recall_recent(n=n)

    def recall_progressive(self, token_budget: int = 2000) -> list[dict[str, Any]]:
        """Progressive recall within a token budget.

        Returns compact previews for as many turns as fit within the budget.
        Use format_context(turns, full=True) to expand specific turns.
        """
        return self._sr.recall_progressive(token_budget=token_budget)

    def recall_selective(
        self,
        turn_types: list[str] | None = None,
        min_importance: float = 0.7,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Selective replay — only turns matching types and importance.

        The Dakera pattern: replay only decisions, breakthroughs, and errors
        with high importance. Reduces token cost by ~80%.
        """
        return self._sr.recall_selective(
            turn_types=turn_types,
            min_importance=min_importance,
            limit=limit,
        )

    def recall_by_query(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Semantic search within session memories."""
        return self._sr.recall_by_query(query=query, limit=limit)

    def format_context(
        self,
        turns: list[dict[str, Any]],
        full: bool = False,
    ) -> str:
        """Format turns as a context block for LLM injection.

        Args:
            turns: List of turn dicts from recall_*.
            full: If True, include full content. If False, compact preview only.
        """
        return self._sr.format_context(turns, full=full)

    def get_continuity(self, n: int = 10) -> dict[str, Any]:
        """Get recent turns from the *previous* session for context injection.

        This is the "where we left off" mechanism for cross-session continuity.
        """
        return self._sr.get_continuity_turns(n=n)

    def consolidate_session(self, min_importance: float = 0.7) -> dict[str, Any]:
        """Promote important session turns to long-term memory (sleep consolidation).

        Converts episodic session memories into long-term semantic knowledge.
        Only turns with importance >= min_importance are promoted.
        Decisions, breakthroughs, and errors are prioritized.
        """
        return self._sr.consolidate_session(min_importance=min_importance)

    def stats(self) -> dict[str, Any]:
        """Get session statistics."""
        return self._sr.get_stats()


class AgentMemory:
    """Three-tier agent memory system — the unified facade.

    Provides short-term, long-term, and episodic memory in one interface.

    Usage:
        >>> mem = AgentMemory()
        >>>
        >>> # Short-term: 7±2 active chunks with LRU eviction
        >>> mem.short_term.add("current task context", importance=0.8)
        >>> active = mem.short_term.get_active()
        >>>
        >>> # Long-term: persistent, searchable, galaxy-partitioned
        >>> mem.long_term.store("Learned API X rate limit", tags=["api"])
        >>> results = mem.long_term.search("rate limits", limit=5)
        >>>
        >>> # Episodic: conversation turns with progressive recall
        >>> mem.episodic.record(role="user", content="Fix the auth bug")
        >>> context = mem.episodic.recall_progressive(token_budget=500)
        >>> formatted = mem.episodic.format_context(context)

    Args:
        working_memory_capacity: Number of short-term slots (default 7, Miller's Law).
        session_id: Optional session ID for episodic memory.
        base_path: Optional base path for memory database.
    """

    def __init__(
        self,
        working_memory_capacity: int = 7,
        session_id: str | None = None,
        base_path: Any | None = None,
    ) -> None:
        self.short_term = ShortTermMemory(capacity=working_memory_capacity)
        self.long_term = LongTermMemory(base_path=base_path)
        self.episodic = EpisodicMemory(session_id=session_id)

    def store(self, content: str, **kwargs: Any) -> str:
        """Quick store to long-term memory. Returns memory ID."""
        return self.long_term.store(content, **kwargs)

    def search(self, query: str, **kwargs: Any) -> list[dict[str, Any]]:
        """Quick search across long-term memory."""
        return self.long_term.search(query=query, **kwargs)

    def recall(self, memory_id: str) -> dict[str, Any] | None:
        """Recall a specific memory by ID."""
        return self.long_term.recall(memory_id)

    def stats(self) -> dict[str, Any]:
        """Get aggregate statistics across all three tiers."""
        return {
            "short_term": self.short_term.status(),
            "long_term": self.long_term.stats(),
            "episodic": self.episodic.stats(),
        }

    def clear_short_term(self) -> None:
        """Clear working memory (does not affect long-term or episodic)."""
        self.short_term.clear()

    def consolidate(self) -> dict[str, Any]:
        """Run full consolidation across all tiers.

        - Short-term: decay and evict inactive chunks
        - Long-term: prune weak memories (rotate to archive)
        - Episodic: promote important turns to long-term
        """
        pruned = self.long_term.consolidate()
        promoted = self.episodic.consolidate_session()
        return {
            "long_term_pruned": pruned,
            "episodic_promoted": promoted,
        }


# Singleton
_agent_memory: AgentMemory | None = None


def get_agent_memory(
    working_memory_capacity: int = 7,
    session_id: str | None = None,
) -> AgentMemory:
    """Get or create the global AgentMemory singleton."""
    global _agent_memory
    if _agent_memory is None or session_id is not None:
        _agent_memory = AgentMemory(
            working_memory_capacity=working_memory_capacity,
            session_id=session_id,
        )
    return _agent_memory


def reset_agent_memory() -> None:
    """Reset the singleton (for testing)."""
    global _agent_memory
    _agent_memory = None
