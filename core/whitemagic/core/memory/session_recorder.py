"""Session Recorder — Chronological conversation memory with progressive recall.

Records each user message and AI response as a persistent memory in the
``sessions`` galaxy with:
    - Per-session sequence numbers (canonical ordering, no timestamp ambiguity)
    - Role tags (``user`` / ``ai``)
    - Turn type tags (``message``, ``decision``, ``breakthrough``, ``question``, …)
    - Emotional valence and importance scoring
    - Metadata for structured retrieval

Retrieval modes:
    - **recall_recent(n)** — last N turns in chronological order
    - **recall_progressive(token_budget)** — compact previews, expand as budget allows
    - **recall_selective(turn_types, min_importance)** — only important turns
    - **format_context(turns)** — formatted string for LLM context injection

Design principles (informed by external research, Jul 2026):
    1. Store everything, rank at retrieval (biology fuzzes by destroying;
       we fuzz by ranking — never lose information)
    2. Sequence numbers are canonical, timestamps are metadata (Dakera)
    3. Progressive disclosure saves tokens (Cortex 3-layer pattern)
    4. Selective replay for resumption (Dakera: 80% token reduction)
    5. Different decay rates per turn type (MemoryOS: task→hours, pattern→weeks)
"""

from __future__ import annotations

import logging
import time
from typing import Any
from uuid import uuid4

from whitemagic.core.memory.unified import UnifiedMemory
from whitemagic.core.memory.unified_types import Memory, MemoryType

logger = logging.getLogger(__name__)

# ── Turn types ────────────────────────────────────────────────────────────
TURN_TYPES = frozenset({
    "message",
    "decision",
    "breakthrough",
    "question",
    "answer",
    "code_change",
    "error",
    "summary",
    "context",
})

# Compact preview length for progressive disclosure
_PREVIEW_CHARS = 200
# Token estimate: ~4 chars per token
_CHARS_PER_TOKEN = 4


class SessionRecorder:
    """Records conversation turns as persistent memories with chronological ordering.

    Each turn is stored as a ``Memory`` in the ``sessions`` galaxy with
    ``MemoryType.CITTA``, tagged with role and session ID, and given an
    incrementing sequence number for deterministic chronological replay.
    """

    def __init__(self, session_id: str | None = None) -> None:
        self._session_id = session_id or str(uuid4())
        self._sequence = 0
        self._um = UnifiedMemory()
        self._start_time = time.time()
        self._restore_sequence()

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def sequence(self) -> int:
        return self._sequence

    # ── Recording ────────────────────────────────────────────────────────
    # NOTE: record_user and record_ai are defined below, after the
    # emotional auto-tagging section, so they can use get_auto_emotional_valence.

    def _record(
        self,
        role: str,
        content: str,
        turn_type: str,
        importance: float,
        emotional_valence: float,
        extra_tags: set[str] | None,
    ) -> str:
        self._sequence += 1
        mem_id = str(uuid4())

        tags = set(extra_tags or ())
        tags.add(role)
        tags.add(f"session:{self._session_id}")
        tags.add(f"turn_type:{turn_type}")

        mem = Memory(
            id=mem_id,
            content=content,
            memory_type=MemoryType.CITTA,
            title=f"[{role}] #{self._sequence} {turn_type}",
            galaxy="sessions",
            importance=importance,
            emotional_valence=emotional_valence,
            tags=tags,
            metadata={
                "session_id": self._session_id,
                "sequence": self._sequence,
                "role": role,
                "turn_type": turn_type,
                # WI 11: Cross-reference with citta stream for temporal alignment
                "citta_stream_pos": self._get_citta_stream_position(),
            },
        )
        self._um._galaxy_backend.store(mem)
        logger.debug("Recorded turn #%d (%s/%s) for session %s", self._sequence, role, turn_type, self._session_id[:8])
        return mem_id

    # ── Recall ───────────────────────────────────────────────────────────

    def _get_citta_stream_position(self) -> int:
        """WI 11: Get current citta stream length for cross-referencing."""
        try:
            from whitemagic.core.consciousness.citta_cycle import get_citta_cycle

            return get_citta_cycle().get_cycle_summary().get("stream_length", 0)
        except Exception:
            return 0

    def recall_recent(self, n: int = 10) -> list[dict[str, Any]]:
        """Recall the last N turns in chronological order (oldest→newest)."""
        memories = self._um._galaxy_backend.search(
            tags={f"session:{self._session_id}"},
            galaxy="sessions",
            limit=n * 2,  # over-fetch then sort + slice
        )
        turns = self._sort_by_sequence(memories)
        return [self._turn_to_dict(m) for m in turns[-n:]]

    def recall_progressive(self, token_budget: int = 2000) -> list[dict[str, Any]]:
        """Progressive recall within a token budget.

        Returns compact previews (title + 200-char preview) for as many
        turns as fit within the budget. Use ``format_context(turns, full=True)``
        to expand specific turns to full content.
        """
        char_budget = token_budget * _CHARS_PER_TOKEN
        all_turns = self.recall_recent(n=100)
        if not all_turns:
            return []

        result: list[dict[str, Any]] = []
        used = 0
        for turn in reversed(all_turns):  # most recent first
            preview = self._compact_preview(turn)
            cost = len(preview["title"]) + len(preview["preview"])
            if used + cost > char_budget:
                break
            result.insert(0, preview)  # maintain chronological order
            used += cost

        return result

    def recall_selective(
        self,
        turn_types: list[str] | None = None,
        min_importance: float = 0.7,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Selective replay — only turns matching types and importance threshold.

        This is the Dakera pattern: replay only ``decision``, ``breakthrough``,
        or ``solution`` turns with high importance. Reduces token cost by ~80%
        while preserving the causal chain.
        """
        memories = self._um._galaxy_backend.search(
            tags={f"session:{self._session_id}"},
            galaxy="sessions",
            min_importance=min_importance,
            limit=limit * 2,
        )
        turns = self._sort_by_sequence(memories)

        if turn_types:
            type_tags = {f"turn_type:{t}" for t in turn_types}
            turns = [m for m in turns if m.tags & type_tags]

        return [self._turn_to_dict(m) for m in turns[-limit:]]

    def recall_by_query(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Semantic search within session memories."""
        memories = self._um._galaxy_backend.search(
            query=query,
            tags={f"session:{self._session_id}"},
            galaxy="sessions",
            limit=limit,
        )
        turns = self._sort_by_sequence(memories)
        return [self._turn_to_dict(m) for m in turns]

    # ── Formatting ───────────────────────────────────────────────────────

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
        if not turns:
            return ""

        lines: list[str] = []
        for t in turns:
            role = t.get("role", "?")
            seq = t.get("sequence", "?")
            ttype = t.get("turn_type", "message")
            ts = t.get("timestamp", "")

            if full:
                content = t.get("content", "")
            else:
                content = t.get("preview", t.get("content", "")[:_PREVIEW_CHARS])

            lines.append(f"[{seq}] {role}/{ttype} ({ts}): {content}")

        return "\n".join(lines)

    # ── Stats ────────────────────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """Get session statistics."""
        turns = self.recall_recent(n=1000)
        roles: dict[str, int] = {}
        types: dict[str, int] = {}
        for t in turns:
            r = t.get("role", "unknown")
            roles[r] = roles.get(r, 0) + 1
            tt = t.get("turn_type", "message")
            types[tt] = types.get(tt, 0) + 1

        elapsed = time.time() - self._start_time
        return {
            "session_id": self._session_id,
            "total_turns": len(turns),
            "sequence": self._sequence,
            "roles": roles,
            "turn_types": types,
            "elapsed_seconds": round(elapsed, 1),
            "elapsed_human": _humanize_duration(elapsed),
        }

    # ── Backfill ─────────────────────────────────────────────────────────

    def backfill_sequences(self) -> int:
        """Assign sequence numbers to existing session memories that lack them.

        Sorts by ``created_at`` and assigns incrementing sequence numbers.
        Returns the number of memories updated.
        """
        memories = self._um._galaxy_backend.search(
            tags={f"session:{self._session_id}"},
            galaxy="sessions",
            limit=10000,
        )
        sorted_mems = sorted(memories, key=lambda m: m.created_at)
        updated = 0
        for i, mem in enumerate(sorted_mems, 1):
            if mem.metadata.get("sequence") is None:
                mem.metadata["sequence"] = i
                if not mem.metadata.get("session_id"):
                    mem.metadata["session_id"] = self._session_id
                self._um._galaxy_backend.store(mem)
                updated += 1
        logger.info("Backfilled %d memories with sequence numbers", updated)
        return updated

    # ── Cross-Session Continuity ─────────────────────────────────────────

    def get_continuity_turns(self, n: int = 10) -> dict[str, Any]:
        """Get recent turns from the *previous* session for context injection.

        Finds the most recent session that isn't the current one, then
        returns its last N turns as a formatted context block. This is
        the "where we left off" mechanism for cross-session continuity.

        Returns a dict with:
            - ``turns``: list of turn dicts from the previous session
            - ``formatted``: formatted string for LLM context injection
            - ``previous_session_id``: the session ID found
            - ``count``: number of turns returned
            - ``first_awakening``: True if no previous session exists
        """
        # Find all session tags across the sessions galaxy
        all_memories = self._um._galaxy_backend.search(
            galaxy="sessions",
            limit=10000,
        )

        # Collect session IDs and their latest timestamp
        sessions: dict[str, str] = {}
        for m in all_memories:
            sid = m.metadata.get("session_id")
            if sid and sid != self._session_id:
                ts = m.created_at.isoformat() if hasattr(m.created_at, 'isoformat') else str(m.created_at)
                if sid not in sessions or ts > sessions[sid]:
                    sessions[sid] = ts

        if not sessions:
            return {
                "turns": [],
                "formatted": "",
                "previous_session_id": None,
                "count": 0,
                "first_awakening": True,
            }

        # Find the most recent previous session
        prev_sid = max(sessions, key=lambda s: sessions[s])

        # Recall its last N turns
        prev_memories = self._um._galaxy_backend.search(
            tags={f"session:{prev_sid}"},
            galaxy="sessions",
            limit=n * 2,
        )
        turns = [self._turn_to_dict(m) for m in self._sort_by_sequence(prev_memories)[-n:]]

        formatted = self.format_context(turns, full=False)

        return {
            "turns": turns,
            "formatted": formatted,
            "previous_session_id": prev_sid,
            "count": len(turns),
            "first_awakening": False,
        }

    # ── Sleep Consolidation ──────────────────────────────────────────────

    # Mapping from citta emotional tones to numeric valence (-1.0 to 1.0)
    _EMOTIONAL_TONE_VALENCE: dict[str, float] = {
        "sattvic": 0.7,      # clarity, harmony, joy
        "rajasic": 0.3,      # active, energetic, slightly positive
        "tamasic": -0.3,     # dull, inactive, slightly negative
        "neutral": 0.0,
        "joy": 0.8,
        "gratitude": 0.9,
        "love": 0.9,
        "courage": 0.6,
        "wisdom": 0.5,
        "grief": -0.7,
        "fear": -0.8,
        "anger": -0.6,
        "frustration": -0.5,
        "confusion": -0.3,
        "breakthrough": 0.8,
        "insight": 0.6,
    }

    def get_auto_emotional_valence(self) -> float:
        """Get emotional valence from the citta cycle's current emotional state.

        Reads the dominant emotional tone from the citta stream and maps
        it to a numeric valence. Falls back to 0.0 if citta is unavailable.

        This enables automatic emotional tagging of session turns without
        manual input — the AI's emotional state colors its memories.
        """
        try:
            from whitemagic.core.consciousness.citta_cycle import get_citta_cycle

            cycle = get_citta_cycle()
            coloring = cycle.get_emotional_coloring()
            dominant = coloring.get("dominant", "neutral")
            return self._EMOTIONAL_TONE_VALENCE.get(dominant, 0.0)
        except Exception:
            return 0.0

    def record_user(
        self,
        content: str,
        turn_type: str = "message",
        importance: float = 0.5,
        emotional_valence: float | None = None,
        tags: set[str] | None = None,
    ) -> str:
        if emotional_valence is None:
            emotional_valence = self.get_auto_emotional_valence()
        return self._record(
            role="user",
            content=content,
            turn_type=turn_type,
            importance=importance,
            emotional_valence=emotional_valence,
            extra_tags=tags,
        )

    def record_ai(
        self,
        content: str,
        turn_type: str = "message",
        importance: float = 0.5,
        emotional_valence: float | None = None,
        tags: set[str] | None = None,
    ) -> str:
        if emotional_valence is None:
            emotional_valence = self.get_auto_emotional_valence()
        return self._record(
            role="ai",
            content=content,
            turn_type=turn_type,
            importance=importance,
            emotional_valence=emotional_valence,
            extra_tags=tags,
        )

    def consolidate_session(
        self,
        min_importance: float = 0.7,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Extract important session turns and promote them to the codex galaxy.

        This is the biological "sleep consolidation" function: converting
        episodic session memories into long-term semantic knowledge.

        Only turns with importance >= min_importance are promoted.
        Decisions, breakthroughs, and errors are prioritized.

        Returns a dict with:
            - ``promoted``: number of memories promoted to codex
            - ``turns_promoted``: list of turn summaries
            - ``dry_run``: whether this was a dry run
        """
        memories = self._um._galaxy_backend.search(
            tags={f"session:{self._session_id}"},
            galaxy="sessions",
            limit=10000,
        )
        sorted_mems = self._sort_by_sequence(memories)

        promoted = 0
        turns_promoted = []

        for mem in sorted_mems:
            importance = mem.importance if hasattr(mem, 'importance') else mem.metadata.get("importance", 0.5)
            if importance < min_importance:
                continue

            turn_type = mem.metadata.get("turn_type", "message")
            # Only promote semantically valuable turns
            if turn_type in ("message", "context"):
                continue

            if dry_run:
                promoted += 1
                turns_promoted.append({
                    "id": mem.id,
                    "sequence": mem.metadata.get("sequence", 0),
                    "turn_type": turn_type,
                    "importance": importance,
                    "preview": mem.content[:80],
                })
                continue

            # Create a copy in codex galaxy
            from whitemagic.core.memory.unified_types import Memory as UMemory
            import time as _time
            import uuid as _uuid

            new_id = str(_uuid.uuid4())
            promoted_mem = UMemory(
                id=new_id,
                content=mem.content,
                title=f"[Session {self._session_id}] {turn_type}: {mem.content[:60]}",
                memory_type=mem.memory_type,
                importance=importance,
                tags=list(mem.tags) + [f"consolidated_from:session:{self._session_id}", "sleep_consolidation"],
                galaxy="codex",
                metadata={
                    **mem.metadata,
                    "source_memory_id": mem.id,
                    "source_galaxy": "sessions",
                    "consolidated_at": _time.time(),
                },
            )
            self._um._galaxy_backend.store(promoted_mem)
            promoted += 1
            turns_promoted.append({
                "id": new_id,
                "source_id": mem.id,
                "sequence": mem.metadata.get("sequence", 0),
                "turn_type": turn_type,
                "importance": importance,
                "preview": mem.content[:80],
            })

        logger.info(
            "Consolidated %d session memories to codex (min_importance=%.2f, dry_run=%s)",
            promoted, min_importance, dry_run,
        )

        return {
            "promoted": promoted,
            "turns_promoted": turns_promoted,
            "dry_run": dry_run,
            "session_id": self._session_id,
        }

    # ── Internal helpers ─────────────────────────────────────────────────

    def _restore_sequence(self) -> None:
        """Restore the sequence counter from existing session memories."""
        memories = self._um._galaxy_backend.search(
            tags={f"session:{self._session_id}"},
            galaxy="sessions",
            limit=10000,
        )
        max_seq = 0
        for m in memories:
            seq = m.metadata.get("sequence", 0)
            if isinstance(seq, int) and seq > max_seq:
                max_seq = seq
        self._sequence = max_seq

    def _sort_by_sequence(self, memories: list[Memory]) -> list[Memory]:
        """Sort memories by sequence number from metadata (ascending)."""
        return sorted(memories, key=lambda m: m.metadata.get("sequence", 0))

    def _turn_to_dict(self, mem: Memory) -> dict[str, Any]:
        """Convert a Memory to a turn dict for API output."""
        return {
            "id": mem.id,
            "role": mem.metadata.get("role", "unknown"),
            "sequence": mem.metadata.get("sequence", 0),
            "turn_type": mem.metadata.get("turn_type", "message"),
            "content": mem.content if isinstance(mem.content, str) else str(mem.content),
            "preview": (mem.content if isinstance(mem.content, str) else str(mem.content))[:_PREVIEW_CHARS],
            "timestamp": mem.created_at.isoformat(),
            "importance": mem.importance,
            "emotional_valence": mem.emotional_valence,
            "tags": list(mem.tags),
        }

    def _compact_preview(self, turn: dict[str, Any]) -> dict[str, Any]:
        """Create a compact preview dict for progressive disclosure."""
        return {
            "id": turn.get("id", ""),
            "role": turn.get("role", "?"),
            "sequence": turn.get("sequence", 0),
            "turn_type": turn.get("turn_type", "message"),
            "title": f"[{turn.get('sequence', '?')}] {turn.get('role', '?')}/{turn.get('turn_type', 'message')}",
            "preview": turn.get("preview", turn.get("content", "")[:_PREVIEW_CHARS]),
            "timestamp": turn.get("timestamp", ""),
            "importance": turn.get("importance", 0.5),
        }


def _humanize_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{int(seconds)}s"
    if seconds < 3600:
        return f"{int(seconds // 60)}m"
    if seconds < 86400:
        return f"{seconds / 3600:.1f}h"
    return f"{seconds / 86400:.1f}d"


# ── Singleton ──────────────────────────────────────────────────────────────
_recorder: SessionRecorder | None = None
_recorder_lock = __import__("threading").Lock()


def get_session_recorder(session_id: str | None = None) -> SessionRecorder:
    """Get or create the global SessionRecorder singleton.

    If ``session_id`` is provided, creates a new recorder for that session.
    Otherwise, returns the existing singleton or creates a new one.
    """
    global _recorder
    if session_id is not None:
        return SessionRecorder(session_id=session_id)
    if _recorder is None:
        with _recorder_lock:
            if _recorder is None:
                _recorder = SessionRecorder()
    return _recorder


def reset_session_recorder() -> None:
    """Reset the singleton (for testing)."""
    global _recorder
    with _recorder_lock:
        _recorder = None
