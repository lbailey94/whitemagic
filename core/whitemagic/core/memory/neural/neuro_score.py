# ruff: noqa: BLE001
"""🧮 Neuro Score Engine - Hebbian Learning Calculations.

"Neurons that fire together wire together"

This module calculates memory strength based on:
- Recency: Recent access = stronger
- Frequency: More recalls = stronger
- Novelty: New information = initial boost
- Emotional weight: Important = stronger
- Connections: Well-linked = stronger

Created: December 2, 2025 (Hanuman Tuesday)
"""

import logging
import math
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from whitemagic.core.memory.neural.neural_memory import MemoryState, NeuralMemory

logger = logging.getLogger(__name__)


@dataclass
class ScoreBreakdown:
    """Detailed breakdown of neuro_score calculation."""

    recency_component: float
    frequency_component: float
    novelty_component: float
    emotional_component: float
    connection_component: float
    final_score: float
    is_protected: bool
    is_accelerated: bool

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to/from dict.

        Returns:
            dict[str, Any]
        """
        return {
            "recency": round(self.recency_component, 3),
            "frequency": round(self.frequency_component, 3),
            "novelty": round(self.novelty_component, 3),
            "emotional": round(self.emotional_component, 3),
            "connections": round(self.connection_component, 3),
            "final_score": round(self.final_score, 3),
            "is_protected": self.is_protected,
        }


# === SCORE WEIGHTS ===
# How much each component contributes to final score

WEIGHTS = {
    "recency": 0.30,      # 30% - Recent access matters most
    "frequency": 0.30,    # 30% - Frequent use strengthens
    "novelty": 0.20,      # 20% - New info gets initial boost
    "emotional": 0.10,    # 10% - Importance/resonance
    "connections": 0.10,  # 10% - Well-linked memories persist
}


def calculate_recency_factor(memory: NeuralMemory) -> float:
    """Calculate recency component (0.0 to 1.0).

    Uses exponential decay based on half-life.
    Recently accessed = high score.
    """
    days_since: float = memory.days_since_recall
    half_life: float = memory.half_life_days

    # Exponential decay: score = 0.5^(days/half_life)
    factor: float = 0.5 ** (days_since / half_life)

    return float(min(1.0, max(0.0, factor)))


def calculate_frequency_factor(memory: NeuralMemory) -> float:
    """Calculate frequency component (0.0 to 1.0).

    Uses logarithmic growth - diminishing returns.
    More recalls = higher score, but plateaus.
    """
    recalls = memory.recall_count

    if recalls == 0:
        return 0.0

    # Logarithmic growth: log(1 + recalls) / log(1 + max_recalls)
    # Assumes ~100 recalls is "maximum" for normalization
    factor = math.log1p(recalls) / math.log1p(100)

    return min(1.0, max(0.0, factor))


def calculate_novelty_factor(memory: NeuralMemory) -> float:
    """Calculate novelty component (0.0 to 1.0).

    New information starts high, decays as it becomes familiar.
    """
    return memory.novelty_score


def calculate_emotional_factor(memory: NeuralMemory) -> float:
    """Calculate emotional component (0.0 to 1.0).

    Based on emotional_weight set during creation or by anchors.
    """
    return memory.emotional_weight


def calculate_connection_factor(memory: NeuralMemory) -> float:
    """Calculate connection component (0.0 to 1.0).

    Well-connected memories are more likely to be recalled.
    """
    connections = memory.connection_count

    if connections == 0:
        return 0.0

    # Normalize: 10+ connections = max score
    factor = min(1.0, connections / 10.0)

    return factor


def calculate_neuro_score(memory: NeuralMemory, detailed: bool = False) -> float | ScoreBreakdown:
    """Calculate the overall neuro_score for a memory.

    Args:
        memory: The NeuralMemory to score
        detailed: If True, return ScoreBreakdown instead of float

    Returns:
        Float score (0.0 to 1.0) or ScoreBreakdown if detailed=True

    """
    # Protected memories always have max score
    if memory.is_protected:
        if detailed:
            return ScoreBreakdown(
                recency_component=1.0,
                frequency_component=1.0,
                novelty_component=1.0,
                emotional_component=1.0,
                connection_component=1.0,
                final_score=1.0,
                is_protected=True,
                is_accelerated=False,
            )
        return 1.0

    # Legacy Python Fallback
    # Calculate each component
    recency = calculate_recency_factor(memory)
    frequency = calculate_frequency_factor(memory)
    novelty = calculate_novelty_factor(memory)
    emotional = calculate_emotional_factor(memory)
    connections = calculate_connection_factor(memory)

    # Weighted sum
    score = (
        recency * WEIGHTS["recency"] +
        frequency * WEIGHTS["frequency"] +
        novelty * WEIGHTS["novelty"] +
        emotional * WEIGHTS["emotional"] +
        connections * WEIGHTS["connections"]
    )

    # Clamp to valid range, respecting minimum
    final_score = max(memory.min_score, min(1.0, score))

    if detailed:
        return ScoreBreakdown(
            recency_component=recency,
            frequency_component=frequency,
            novelty_component=novelty,
            emotional_component=emotional,
            connection_component=connections,
            final_score=final_score,
            is_protected=False,
            is_accelerated=False,
        )

    return final_score


class NeuroScoreEngine:
    """Backward-compat shim — fused into RetentionEngine (slot 24, Dipper 斗).

    All neuro_score management logic now lives in
    whitemagic.core.memory.mindful_forgetting.RetentionEngine.

    This class delegates to the RetentionEngine singleton for all
    score management, decay processing, and recall boosting.
    """

    def __init__(
        self,
        archive_threshold: float = 0.2,
        decay_interval_hours: float = 24.0,
        auto_protect: bool = True,
    ) -> None:
        from whitemagic.core.memory.mindful_forgetting import get_retention_engine
        self._engine = get_retention_engine(archive_threshold=archive_threshold)
        self._engine._decay_interval_hours = decay_interval_hours
        self._engine._auto_protect = auto_protect
        self.archive_threshold = archive_threshold
        self.decay_interval_hours = decay_interval_hours
        self.auto_protect = auto_protect

    @property
    def _last_decay_run(self) -> datetime | None:
        return getattr(self._engine, "_last_decay_run", None)

    @_last_decay_run.setter
    def _last_decay_run(self, value: datetime | None) -> None:
        self._engine._last_decay_run = value

    def calculate_score(self, memory: NeuralMemory, detailed: bool = False) -> float | ScoreBreakdown:
        """Calculate neuro_score for a memory."""
        return calculate_neuro_score(memory, detailed)

    def update_score(self, memory: NeuralMemory) -> NeuralMemory:
        """Update memory's neuro_score based on current state."""
        return self._engine.update_score(memory)

    def on_recall(self, memory: NeuralMemory) -> NeuralMemory:
        """Called when memory is recalled/accessed."""
        return self._engine.on_recall(memory)

    def on_create(self, memory: NeuralMemory) -> NeuralMemory:
        """Called when memory is created."""
        return self._engine.on_create(memory)

    def process_decay(self, memories: list[NeuralMemory]) -> list[NeuralMemory]:
        """Process decay for a batch of memories."""
        return self._engine.process_decay(memories)

    def should_run_decay(self) -> bool:
        """Check if it's time to run decay processing."""
        return self._engine.should_run_decay()

    def get_memories_by_state(
        self,
        memories: list[NeuralMemory],
        state: MemoryState,
    ) -> list[NeuralMemory]:
        """Filter memories by state."""
        return [m for m in memories if m.state == state]

    def get_weak_memories(self, memories: list[NeuralMemory]) -> list[NeuralMemory]:
        """Get memories that are fading or weak."""
        return self._engine.get_weak_memories(memories)

    def get_stats(self, memories: list[NeuralMemory]) -> dict[str, Any]:
        """Get statistics about memory health."""
        return self._engine.get_neuro_stats(memories)


# === SINGLETON ===
_engine: NeuroScoreEngine | None = None


def get_engine() -> NeuroScoreEngine:
    """Get the singleton NeuroScoreEngine instance."""
    global _engine
    if _engine is None:
        _engine = NeuroScoreEngine()
    return _engine
