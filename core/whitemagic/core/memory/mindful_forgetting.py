# ruff: noqa: BLE001
"""Mindful Forgetting - Multi-Signal Memory Retention.
===================================================
Inspired by CyberBrains' hippocampal model: memories expire unless
tagged as important by *multiple independent subsystems*.

A memory's retention score is computed from several independent signals:
  1. Semantic importance  (governor / tool usage frequency)
  2. Emotional salience   (limbic / garden affect tags)
  3. Recency & recall     (hippocampal access patterns)
  4. Connection density   (how many other memories link to it)
  5. Pattern relevance    (does it participate in discovered patterns?)

If the composite retention score drops below a threshold, the memory
enters a "forgetting queue" and is eventually archived (not destroyed —
mindful forgetting is gentle).

Usage:
    from whitemagic.core.memory.mindful_forgetting import (
        get_retention_engine, RetentionEngine
    )

    engine = get_retention_engine()
    verdict = engine.evaluate(memory)
    # verdict.retain == True/False
    # verdict.score  == 0.0-1.0
    # verdict.signals == breakdown

    # Batch sweep (run periodically via slow-lane scheduler):
    report = engine.sweep()
"""

import logging
import math
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from whitemagic.core.memory.unified_types import Memory, MemoryState, MemoryType

logger = logging.getLogger(__name__)


@dataclass
class RetentionSignal:
    """One subsystem's vote on whether a memory should be retained."""

    name: str           # e.g. "semantic", "emotional", "recency"
    score: float        # 0.0 (forget) to 1.0 (absolutely keep)
    weight: float       # How much this signal matters (default 1.0)
    reason: str = ""    # Human-readable explanation


@dataclass
class RetentionVerdict:
    """Final retention decision for a single memory."""

    memory_id: str
    retain: bool
    score: float               # Composite retention score 0.0-1.0
    signals: list[RetentionSignal]
    state_before: MemoryState
    recommended_action: str    # "keep", "decay", "archive", "protect"

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to/from dict.

        Returns:
            dict[str, Any]
        """
        return {
            "memory_id": self.memory_id,
            "retain": self.retain,
            "score": round(self.score, 4),
            "recommended_action": self.recommended_action,
            "state_before": self.state_before.value,
            "signals": [
                {"name": s.name, "score": round(s.score, 3), "weight": s.weight, "reason": s.reason}
                for s in self.signals
            ],
        }


def _semantic_signal(mem: Memory) -> RetentionSignal:
    """How important is this memory's content to the system's knowledge?"""
    # importance field is the primary indicator (set by governor/tool usage)
    score = mem.importance
    reason = f"importance={mem.importance:.2f}"

    # Boost for long-term or pattern memories
    if mem.memory_type in (MemoryType.LONG_TERM, MemoryType.PATTERN, MemoryType.IMMUNE):
        score = min(1.0, score + 0.15)
        reason += f", type_boost={mem.memory_type.name}"

    return RetentionSignal(name="semantic", score=score, weight=1.0, reason=reason)


def _emotional_signal(mem: Memory) -> RetentionSignal:
    """Emotional salience — strong feelings (positive or negative) anchor memories."""
    # Absolute valence: both very positive and very negative memories are salient
    abs_valence = abs(mem.emotional_valence or 0.0)
    emotional_weight = mem.emotional_weight if hasattr(mem, "emotional_weight") else 0.5

    score = max(abs_valence, emotional_weight)
    reason = f"valence={mem.emotional_valence or 0.0:.2f}, weight={emotional_weight:.2f}"

    return RetentionSignal(name="emotional", score=score, weight=0.8, reason=reason)


def _recency_signal(mem: Memory) -> RetentionSignal:
    """How recently and frequently has this memory been accessed?"""
    days_since = mem.days_since_recall
    recall_count = mem.recall_count

    # Exponential recency decay (half-life = memory's own half_life_days)
    recency = 0.5 ** (days_since / max(mem.half_life_days, 1.0))

    # Frequency bonus (log scale, capped)
    freq_bonus = min(0.3, math.log1p(recall_count) * 0.05)

    score = min(1.0, recency + freq_bonus)
    reason = f"days_since_recall={days_since:.1f}, recalls={recall_count}, half_life={mem.half_life_days}"

    return RetentionSignal(name="recency", score=score, weight=0.9, reason=reason)


def _connection_signal(mem: Memory) -> RetentionSignal:
    """Memories with many strong links to other memories are harder to forget."""
    n_links = len(mem.links)
    if n_links == 0:
        return RetentionSignal(name="connection", score=0.1, weight=0.7, reason="no links")

    avg_strength = sum(link.strength for link in mem.links.values()) / n_links
    # More links + stronger links = higher retention
    density = min(1.0, (n_links / 10.0) * avg_strength)
    reason = f"links={n_links}, avg_strength={avg_strength:.2f}"

    return RetentionSignal(name="connection", score=density, weight=0.7, reason=reason)


def _protection_signal(mem: Memory) -> RetentionSignal:
    """Hard overrides: protected, core identity, sacred, or pinned memories never forget."""
    if mem.is_protected or mem.is_core_identity or mem.is_sacred or mem.is_pinned:
        reasons = []
        if mem.is_protected:
            reasons.append("protected")
        if mem.is_core_identity:
            reasons.append("core_identity")
        if mem.is_sacred:
            reasons.append("sacred")
        if mem.is_pinned:
            reasons.append("pinned")
        return RetentionSignal(
            name="protection", score=1.0, weight=100.0,
            reason=f"hard_protect: {', '.join(reasons)}",
        )

    return RetentionSignal(name="protection", score=0.0, weight=0.0, reason="not protected")


DEFAULT_EVALUATORS = [
    _semantic_signal,
    _emotional_signal,
    _recency_signal,
    _connection_signal,
    _protection_signal,
]


@dataclass
class SweepReport:
    """Results from a retention sweep."""

    total_evaluated: int = 0
    retained: int = 0
    decayed: int = 0
    archived: int = 0
    protected: int = 0
    verdicts: list[RetentionVerdict] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to/from dict.

        Returns:
            dict[str, Any]
        """
        return {
            "total_evaluated": self.total_evaluated,
            "retained": self.retained,
            "decayed": self.decayed,
            "archived": self.archived,
            "protected": self.protected,
            "timestamp": self.timestamp.isoformat(),
        }


class RetentionEngine:
    """Multi-signal retention engine.

    Evaluates each memory against independent signals and produces a
    composite retention verdict. Plugs into the slow-lane of the
    TemporalScheduler for periodic sweeps.
    """

    def __init__(
        self,
        retain_threshold: float = 0.35,
        archive_threshold: float = 0.15,
        evaluators: list[Callable] | None = None,
    ):
        self._retain_threshold = retain_threshold
        self._archive_threshold = archive_threshold
        self._evaluators = evaluators or list(DEFAULT_EVALUATORS)
        self._lock = threading.RLock()

        # Stats
        self._total_evaluations: int = 0
        self._total_sweeps: int = 0

    def evaluate(self, mem: Memory) -> RetentionVerdict:
        """Evaluate a single memory for retention."""
        signals: list[RetentionSignal] = []
        for evaluator in self._evaluators:
            try:
                sig = evaluator(mem)
                signals.append(sig)
            except Exception as exc:
                logger.warning("Retention evaluator %s failed: %s", evaluator.__name__, exc, exc_info=True)

        # Compute weighted average
        total_weight = sum(s.weight for s in signals if s.weight > 0)
        if total_weight == 0:
            composite = 0.5
        else:
            composite = sum(s.score * s.weight for s in signals) / total_weight
        composite = max(0.0, min(1.0, composite))

        # Determine action
        if any(s.name == "protection" and s.score >= 1.0 for s in signals):
            action = "protect"
            retain = True
        elif composite >= self._retain_threshold:
            action = "keep"
            retain = True
        elif composite >= self._archive_threshold:
            action = "decay"
            retain = True  # still alive, but weakening
        else:
            action = "archive"
            retain = False

        self._total_evaluations += 1

        return RetentionVerdict(
            memory_id=mem.id,
            retain=retain,
            score=composite,
            signals=signals,
            state_before=mem.state,
            recommended_action=action,
        )

    def sweep(self, memories: list[Memory] | None = None, persist: bool = False) -> SweepReport:
        """Evaluate all provided memories (or fetch from UnifiedMemory).

        Applies decay / galactic rotation according to verdicts.
        **No memory is ever deleted** — archived memories are rotated
        to the galactic edge, not destroyed.

        Args:
            memories: List of memories to evaluate (or None to auto-load).
            persist: If True, persist retention scores and galactic
                     distances to the database via the backend.

        """
        if memories is None:
            try:
                from whitemagic.core.memory.unified import get_unified_memory
                um = get_unified_memory()
                memories = um.list_recent(limit=5000)
            except Exception as exc:
                logger.error("Retention sweep: could not load memories: %s", exc, exc_info=True)
                return SweepReport()

        # Optionally get backend for persistence
        backend = None
        if persist:
            try:
                from whitemagic.core.memory.unified import get_unified_memory
                backend = get_unified_memory().backend
            except ImportError as e:
                logger.debug("Unified memory unavailable for persistence: %s", e, exc_info=True)

        report = SweepReport()
        for mem in memories:
            verdict = self.evaluate(mem)
            report.total_evaluated += 1
            report.verdicts.append(verdict)

            if verdict.recommended_action == "protect":
                report.protected += 1
            elif verdict.recommended_action == "keep":
                report.retained += 1
            elif verdict.recommended_action == "decay":
                report.decayed += 1
                # Apply gentle decay
                mem.decay()
            elif verdict.recommended_action == "archive":
                report.archived += 1
                # Rotate to galactic edge — NEVER delete
                mem.neuro_score = max(mem.min_score, mem.neuro_score * 0.5)
                if backend:
                    backend.archive_to_edge(mem.id, galactic_distance=0.90)

            # Persist retention score if requested
            if persist and backend:
                backend.update_retention_score(mem.id, verdict.score)

        self._total_sweeps += 1
        logger.info(
            "🌌 Retention sweep #%s: "
            "%s evaluated, "
            "%s kept, %s decayed, "
            "%s rotated to edge, %s protected",
         self._total_sweeps, report.total_evaluated, report.retained, report.decayed, report.archived, report.protected)
        return report

    def add_evaluator(self, evaluator: Callable) -> None:
        """Add a custom retention signal evaluator."""
        self._evaluators.append(evaluator)

    def set_thresholds(self, retain: float, archive: float) -> None:
        """
        Perform the set thresholds operation.

        Args:
            retain: Parameter description.
            archive: Parameter description.

        Returns:
            None
        """
        self._retain_threshold = retain
        self._archive_threshold = archive

    def get_stats(self) -> dict[str, Any]:
        """
        Get the stats.

        Returns:
            dict[str, Any]
        """
        return {
            "total_evaluations": self._total_evaluations,
            "total_sweeps": self._total_sweeps,
            "retain_threshold": self._retain_threshold,
            "archive_threshold": self._archive_threshold,
            "evaluator_count": len(self._evaluators),
            **self._neuro_score_stats(),
        }

    def _neuro_score_stats(self) -> dict[str, Any]:
        """Get neuro_score-specific stats."""
        return {
            "neuro_score_decay_interval_hours": getattr(self, "_decay_interval_hours", 24.0),
            "neuro_score_last_decay": getattr(self, "_last_decay_run", None),
        }

    def calculate_score(self, memory: Any, detailed: bool = False) -> Any:
        """Calculate neuro_score for a NeuralMemory.

        Delegates to the neuro_score calculation functions.
        """
        from whitemagic.core.memory.neural.neuro_score import calculate_neuro_score
        return calculate_neuro_score(memory, detailed)

    def update_score(self, memory: Any) -> Any:
        """Update a NeuralMemory's neuro_score based on current state."""
        from whitemagic.core.memory.neural.neuro_score import calculate_neuro_score
        score = calculate_neuro_score(memory)
        if isinstance(score, float):
            memory.neuro_score = score
        else:
            memory.neuro_score = score.final_score
        return memory

    def on_recall(self, memory: Any) -> Any:
        """Called when a NeuralMemory is recalled/accessed. Boosts strength."""
        memory.recall()
        return self.update_score(memory)

    def on_create(self, memory: Any) -> Any:
        """Called when a NeuralMemory is created. Applies auto-protection and scoring."""
        try:
            from whitemagic.core.memory.neural.identity_anchors import (
                auto_protect_memory,
            )
            memory = auto_protect_memory(memory)
        except ImportError:
            logger.debug("Optional dependency unavailable: ImportError")
        return self.update_score(memory)

    def process_decay(self, memories: list[Any]) -> list[Any]:
        """Process decay for a batch of NeuralMemories.

        Returns list of memories that should be archived.
        """
        from whitemagic.core.memory.neural.neuro_score import calculate_neuro_score
        to_archive = []

        for memory in memories:
            memory.decay()
            score = calculate_neuro_score(memory)
            if isinstance(score, float):
                memory.neuro_score = score
            else:
                memory.neuro_score = score.final_score

            if memory.should_archive():
                to_archive.append(memory)

        self._last_decay_run = datetime.now()
        return to_archive

    def should_run_decay(self) -> bool:
        """Check if it's time to run decay processing."""
        if not hasattr(self, "_last_decay_run") or self._last_decay_run is None:
            return True
        hours_since = (datetime.now() - self._last_decay_run).total_seconds() / 3600
        return hours_since >= getattr(self, "_decay_interval_hours", 24.0)

    def get_weak_memories(self, memories: list[Any]) -> list[Any]:
        """Get memories that are fading or weak (candidates for review)."""
        try:
            from whitemagic.core.memory.neural.neural_memory import MemoryState
            return [m for m in memories if m.state in (MemoryState.FADING, MemoryState.WEAK)]
        except ImportError:
            return []

    def get_neuro_stats(self, memories: list[Any]) -> dict[str, Any]:
        """Get statistics about memory health (NeuroScoreEngine compatible)."""
        if not memories:
            return {"total": 0, "by_state": {}, "average_score": 0, "protected_count": 0}

        try:
            from whitemagic.core.memory.neural.neural_memory import MemoryState
            by_state = {}
            for state in MemoryState:
                count = len([m for m in memories if m.state == state])
                if count > 0:
                    by_state[state.value] = count
        except ImportError:
            by_state = {}

        avg_score = sum(m.neuro_score for m in memories) / len(memories)
        protected = len([m for m in memories if m.is_protected])

        return {
            "total": len(memories),
            "by_state": by_state,
            "average_score": round(avg_score, 3),
            "protected_count": protected,
            "archive_candidates": len([m for m in memories if m.should_archive()]),
        }


_engine_instance: RetentionEngine | None = None
_engine_lock = threading.RLock()


def get_retention_engine(
    retain_threshold: float = 0.35,
    archive_threshold: float = 0.15,
) -> RetentionEngine:
    """Get or create the global RetentionEngine singleton."""
    global _engine_instance
    with _engine_lock:
        if _engine_instance is None:
            _engine_instance = RetentionEngine(
                retain_threshold=retain_threshold,
                archive_threshold=archive_threshold,
            )
        return _engine_instance
