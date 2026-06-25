# ruff: noqa: BLE001
"""Multi-Agent Librarian System

Three specialized agents for autonomous memory management:
1. Librarian: Extracts memories from logs, chats, and documents
2. Editor/Hygienist: Refactors, deduplicates, and cleans memory
3. Planner: Generates task lists from memory + goals

These agents work autonomously to maintain memory health.

Recovered 2026-06-18 from the legacy_reference_dump archive
(pre-v15 era). Refactored for v22 conventions:
  - Returns storage-agnostic dicts (not NeuralMemory objects)
  - Uses pluggable MemoryStorage protocol (defaults to in-memory)
  - No dependency on the removed `neural_system` module
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Storage Protocol — pluggable backend (defaults to in-memory list)
# ---------------------------------------------------------------------------


class MemoryStorage(Protocol):
    """Minimal storage interface for the Librarian agents.

    v22's MemoryManager satisfies this contract; tests / standalone use
    can supply InMemoryStorage or any other implementation.
    """

    def create_memory(
        self,
        title: str,
        content: str,
        memory_type: str = "short_term",
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]: ...


class InMemoryStorage:
    """In-memory storage for tests / standalone use."""

    def __init__(self) -> None:
        self._memories: list[dict[str, Any]] = []

    def create_memory(
        self,
        title: str,
        content: str,
        memory_type: str = "short_term",
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Create a new memory.

        Args:
            title: Parameter description.
            content: Parameter description.
            memory_type: Parameter description.
            tags: Parameter description.

        Returns:
            dict[str, Any]
        """
        mem = {
            "title": title,
            "content": content,
            "memory_type": memory_type,
            "tags": list(tags or []),
            "created_at": datetime.now().isoformat(),
            "id": f"mem_{len(self._memories)}",
            **kwargs,
        }
        self._memories.append(mem)
        return {"success": True, "id": mem["id"], **mem}

    @property
    def memories(self) -> list[dict[str, Any]]:
        """
        Perform the memories operation.

        Returns:
            list[dict[str, Any]]
        """
        return list(self._memories)


def _get_default_storage() -> MemoryStorage:
    """Try to wire to MemoryManager (whitemagic.core.memory.manager); fall back to in-memory."""
    try:
        from whitemagic.core.memory.manager import get_memory_manager  # type: ignore

        manager = get_memory_manager()

        class _ManagerStorage:
            def create_memory(
                self,
                title: str,
                content: str,
                memory_type: str = "short_term",
                tags: list[str] | None = None,
                **kwargs: Any,
            ) -> dict[str, Any]:
                """
                Create a new memory.

                Args:
                    title: Parameter description.
                    content: Parameter description.
                    memory_type: Parameter description.
                    tags: Parameter description.

                Returns:
                    dict[str, Any]
                """
                return manager.create_memory(
                    title=title,
                    content=content,
                    memory_type=memory_type,
                    tags=tags or [],
                    **kwargs,
                )

        return _ManagerStorage()
    except Exception as e:
        logger.debug("Operation failed: %s", e)
        return InMemoryStorage()


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class ExtractedMemory:
    """A memory candidate extracted by the Librarian agent."""

    content: str
    title: str
    tags: list[str] = field(default_factory=list)
    confidence: float = 0.5
    source: str = "unknown"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


# ---------------------------------------------------------------------------
# Agent 1: Librarian — extraction
# ---------------------------------------------------------------------------


class LibrarianAgent:
    """Extracts memories from logs, chats, and documents."""

    # Patterns that signal memorable content
    MEMORY_INDICATORS = [
        r"(?:remember|note|important):? (.+)",
        r"(?:key point|takeaway):? (.+)",
        r"(?:learned|discovered) (?:that )?(.+)",
        r"(?:decision|chose|selected):? (.+)",
        r"(?:TODO|task):? (.+)",
    ]

    # Words that signal definitive statements in assistant messages
    ACTION_WORDS = ["decided", "created", "implemented", "fixed", "discovered", "learned"]

    MIN_CONTENT_LENGTH = 15  # Skip very short matches

    def __init__(self, storage: MemoryStorage | None = None) -> None:
        self.storage: MemoryStorage = storage or _get_default_storage()
        self._compiled_patterns = [re.compile(p, re.IGNORECASE) for p in self.MEMORY_INDICATORS]

    def extract_from_text(self, text: str, source: str = "unknown") -> list[ExtractedMemory]:
        """Extract memorable content from free-form text."""
        extracted: list[ExtractedMemory] = []

        # Split into sentences (preserves question marks)
        sentences = re.split(r"[.!?]\s+", text)

        for sentence in sentences:
            if not sentence.strip():
                continue

            # Check for explicit memory indicators
            for pattern in self._compiled_patterns:
                match = pattern.search(sentence)
                if match:
                    content = match.group(1).strip()
                    if len(content) > self.MIN_CONTENT_LENGTH:
                        extracted.append(
                            ExtractedMemory(
                                content=content,
                                title=f"Extracted: {content[:50]}...",
                                tags=["extracted", "librarian"],
                                confidence=0.7,
                                source=source,
                            )
                        )

            # Also extract questions (often important context)
            if "?" in sentence and len(sentence) > 20:
                extracted.append(
                    ExtractedMemory(
                        content=sentence.strip(),
                        title=f"Question: {sentence[:50]}...",
                        tags=["question", "extracted"],
                        confidence=0.5,
                        source=source,
                    )
                )

        return extracted

    def extract_from_conversation(
        self, messages: list[dict[str, str]]
    ) -> list[ExtractedMemory]:
        """Extract memories from chat messages.

        Args:
            messages: List of {"role": "user|assistant|system", "content": "..."}
        """
        extracted: list[ExtractedMemory] = []

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if not content:
                continue

            if role == "user":
                memories = self.extract_from_text(content, source="conversation_user")
                extracted.extend(memories)
            elif role == "assistant":
                lower = content.lower()
                if any(word in lower for word in self.ACTION_WORDS):
                    extracted.append(
                        ExtractedMemory(
                            content=content[:500],
                            title=f"Action: {content[:50]}...",
                            tags=["action", "conversation"],
                            confidence=0.8,
                            source="conversation_assistant",
                        )
                    )

        return extracted

    def store_extracted(self, extracted: list[ExtractedMemory]) -> list[dict[str, Any]]:
        """Store extracted memories in the configured storage."""
        stored: list[dict[str, Any]] = []
        for item in extracted:
            try:
                result = self.storage.create_memory(
                    title=item.title,
                    content=item.content,
                    memory_type="short_term",
                    tags=item.tags + ["librarian", "extracted"],
                    importance=item.confidence,
                    source=item.source,
                    timestamp=item.timestamp,
                )
                stored.append(result)
            except Exception as e:
                logger.warning("Failed to store extracted memory: %s", e, exc_info=True)
        return stored


# ---------------------------------------------------------------------------
# Agent 2: Editor — dedup, merge, hygiene
# ---------------------------------------------------------------------------


class EditorAgent:
    """Refactors, deduplicates, and cleans memory."""

    def __init__(self, storage: MemoryStorage | None = None) -> None:
        self.storage: MemoryStorage = storage or _get_default_storage()

    def find_duplicates(
        self,
        memories: list[dict[str, Any]],
        threshold: float = 0.85,
    ) -> list[tuple[int, int, float]]:
        """Find pairs of duplicate or very similar memories.

        Returns:
            List of (index1, index2, similarity) tuples where similarity >= threshold.
        """
        duplicates: list[tuple[int, int, float]] = []
        for i, mem1 in enumerate(memories):
            content1 = mem1.get("content", "")
            for j in range(i + 1, len(memories)):
                content2 = memories[j].get("content", "")
                sim = self._calculate_similarity(content1, content2)
                if sim >= threshold:
                    duplicates.append((i, j, sim))
        return duplicates

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Jaccard word-overlap similarity (0.0 to 1.0)."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        if not words1 or not words2:
            return 0.0
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        return intersection / union if union > 0 else 0.0

    def merge_duplicates(
        self, memories: list[dict[str, Any]], duplicates: list[tuple[int, int, float]]
    ) -> list[dict[str, Any]]:
        """Merge duplicate pairs and return a deduplicated list.

        For each pair, keep the one with the higher importance/confidence
        and merge the other into it (content, tags, metadata).
        """
        if not duplicates:
            return list(memories)

        # Build a union-find to merge connected components
        parent: dict[int, int] = {i: i for i in range(len(memories))}

        def find(x: int) -> int:
            """
            Perform the find operation.

            Args:
                x: Parameter description.

            Returns:
                int
            """
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(x: int, y: int) -> None:
            """
            Perform the union operation.

            Args:
                x: Parameter description.
                y: Parameter description.

            Returns:
                None
            """
            px, py = find(x), find(y)
            if px != py:
                # Keep the higher-importance as the new root
                if memories[px].get("importance", 0) >= memories[py].get("importance", 0):
                    parent[py] = px
                else:
                    parent[px] = py

        for i, j, _ in duplicates:
            union(i, j)

        # Group by root
        groups: dict[int, list[int]] = {}
        for i in range(len(memories)):
            groups.setdefault(find(i), []).append(i)

        # Merge each group
        merged: list[dict[str, Any]] = []
        for indices in groups.values():
            primary = dict(memories[indices[0]])  # copy
            for idx in indices[1:
                ]:
                other = memories[idx]
                # Append other content if different
                if other.get("content") and other["content"] != primary.get("content"):
                    primary["content"] = (
                        f"{primary.get('content', '')}\n\n"
                        f"[Merged from duplicate:]\n{other['content']}"
                    )
                # Union tags
                primary_tags = set(primary.get("tags", []))
                primary_tags.update(other.get("tags", []))
                primary["tags"] = list(primary_tags)
                # Combine importance
                primary["importance"] = max(
                    primary.get("importance", 0.0),
                    other.get("importance", 0.0),
                )
            merged.append(primary)

        logger.info(
            "Merged %s -> %s memories "
            "(%s duplicates removed)"
        , len(memories), len(merged), len(memories) - len(merged))
        return merged


# ---------------------------------------------------------------------------
# Agent 3: Planner — task generation from memory + goals
# ---------------------------------------------------------------------------


class PlannerAgent:
    """Generates task lists from memory + goals."""

    # Action verbs that signal task-ness
    TASK_VERBS = [
        "implement", "create", "fix", "refactor", "add", "remove",
        "update", "investigate", "analyze", "document", "test",
    ]

    def __init__(self) -> None:
        self._task_pattern = re.compile(
            r"\b(" + "|".join(self.TASK_VERBS) + r")\b\s+(.+?)(?:\.|$)",
            re.IGNORECASE,
        )

    def extract_tasks_from_memories(
        self, memories: list[dict[str, Any]]
    ) -> list[dict[str, str]]:
        """Extract actionable tasks from memory content."""
        tasks: list[dict[str, str]] = []

        for mem in memories:
            content = mem.get("content", "")
            source_id = mem.get("id", "unknown")
            for match in self._task_pattern.finditer(content):
                verb, target = match.group(1), match.group(2).strip()
                # Trim target at first sentence end
                target = re.split(r"[.!?]\s", target, maxsplit=1)[0]
                if len(target) > 10:
                    # Skip very short matches
                    tasks.append({
                        "verb": verb.lower(),
                        "target": target,
                        "source_memory_id": source_id,
                        "priority": mem.get("importance", 0.5),
                    })
        return tasks

    def plan_from_goal(
        self, goal: str, memories: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        """Generate a plan structure from a goal + relevant memories."""
        memories = memories or []
        relevant = self._find_relevant_memories(goal, memories)
        tasks = self.extract_tasks_from_memories(relevant)
        return {
            "goal": goal,
            "relevant_memories": len(relevant),
            "extracted_tasks": tasks,
            "task_count": len(tasks),
        }

    def _find_relevant_memories(
        self, goal: str, memories: list[dict[str, Any]], limit: int = 10
    ) -> list[dict[str, Any]]:
        """Find memories most relevant to the goal (by word overlap)."""
        goal_words = set(goal.lower().split())
        scored: list[tuple[float, dict[str, Any]]] = []
        for mem in memories:
            content = mem.get("content", "").lower()
            words = set(content.split())
            if not goal_words or not words:
                continue
            overlap = len(goal_words & words) / len(goal_words)
            if overlap > 0:
                scored.append((overlap, mem))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored[:limit]]


__all__ = [
    "MemoryStorage",
    "InMemoryStorage",
    "ExtractedMemory",
    "LibrarianAgent",
    "EditorAgent",
    "PlannerAgent",
]
