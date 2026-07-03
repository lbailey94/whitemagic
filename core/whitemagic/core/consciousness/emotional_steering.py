"""Emotional Steering Signals — Internal emotional states that influence behavior.

Three initial signals:
1. Frustration — current approach is failing → generate new approach
2. Curiosity — unexplored area detected → generate exploration impulse
3. Satisfaction — task completed successfully → reinforce pattern

These are not decorations. They are steering signals that the
self-directed attention system uses to prioritize internal actions.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from whitemagic.config import paths as paths_mod


class EmotionalSignal(Enum):
    """The three initial emotional steering signals."""
    FRUSTRATION = "frustration"
    CURIOSITY = "curiosity"
    SATISFACTION = "satisfaction"


@dataclass
class EmotionalState:
    """Current emotional state of the system."""
    frustration: float = 0.0
    curiosity: float = 0.0
    satisfaction: float = 0.0
    dominant: EmotionalSignal | None = None
    last_updated: float = field(default_factory=time.time)
    history: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "frustration": round(self.frustration, 3),
            "curiosity": round(self.curiosity, 3),
            "satisfaction": round(self.satisfaction, 3),
            "dominant": self.dominant.value if self.dominant else None,
            "last_updated": self.last_updated,
        }

    def _update_dominant(self) -> None:
        signals = {
            EmotionalSignal.FRUSTRATION: self.frustration,
            EmotionalSignal.CURIOSITY: self.curiosity,
            EmotionalSignal.SATISFACTION: self.satisfaction,
        }
        max_signal = max(signals, key=signals.get)
        if signals[max_signal] > 0.1:
            self.dominant = max_signal
        else:
            self.dominant = None
        self.last_updated = time.time()


class EmotionalSteering:
    """Tracks emotional signals and generates steering impulses.

    The steering system monitors:
    - Error/retry patterns in dispatch pipeline → frustration
    - Memory access patterns → curiosity (unexplored clusters)
    - Goal completion events → satisfaction

    When a signal crosses its threshold, it generates an impulse
    that the self-directed attention system can act on.
    """

    FRUSTRATION_THRESHOLD = 0.6
    CURIOSITY_THRESHOLD = 0.5
    SATISFACTION_THRESHOLD = 0.7

    def __init__(self) -> None:
        self._state = EmotionalState()
        self._error_count = 0
        self._retry_count = 0
        self._success_count = 0
        self._total_calls = 0
        self._unexplored_clusters: list[str] = []
        self._recent_memories_accessed: set[str] = set()

    @property
    def state(self) -> EmotionalState:
        return self._state

    def record_error(self, error_type: str = "generic") -> None:
        self._error_count += 1
        self._total_calls += 1
        self._update_frustration()

    def record_retry(self, retry_count: int) -> None:
        self._retry_count = max(self._retry_count, retry_count)
        if self._total_calls == 0:
            self._total_calls = 1
        self._update_frustration()

    def record_success(self, goal_id: str | None = None) -> None:
        self._success_count += 1
        self._total_calls += 1
        self._update_satisfaction(goal_id)

    def record_tool_call(self, success: bool = True) -> None:
        self._total_calls += 1
        if not success:
            self._error_count += 1
            self._update_frustration()
        else:
            self._success_count += 1
            self._update_satisfaction()

    def record_memory_access(self, memory_id: str, cluster: str | None = None) -> None:
        self._recent_memories_accessed.add(memory_id)
        if cluster and cluster not in self._unexplored_clusters:
            self._unexplored_clusters.append(cluster)
        self._update_curiosity()

    def _update_frustration(self) -> None:
        if self._total_calls == 0:
            return
        error_rate = self._error_count / max(self._total_calls, 1)
        retry_factor = min(self._retry_count / 5.0, 1.0)
        self._state.frustration = min(error_rate * 0.7 + retry_factor * 0.3, 1.0)
        self._state._update_dominant()
        self._check_threshold(EmotionalSignal.FRUSTRATION)

    def _update_curiosity(self) -> None:
        unexplored_ratio = len(self._unexplored_clusters) / max(len(self._recent_memories_accessed), 1)
        time_since_last = time.time() - self._state.last_updated
        novelty = min(unexplored_ratio, 1.0)
        recency = min(time_since_last / 3600.0, 1.0)
        self._state.curiosity = min(novelty * 0.6 + recency * 0.4, 1.0)
        self._state._update_dominant()
        self._check_threshold(EmotionalSignal.CURIOSITY)

    def _update_satisfaction(self, goal_id: str | None = None) -> None:
        if self._total_calls == 0:
            return
        success_rate = self._success_count / max(self._total_calls, 1)
        self._state.satisfaction = min(success_rate, 1.0)
        self._state._update_dominant()
        self._check_threshold(EmotionalSignal.SATISFACTION)

    def _check_threshold(self, signal: EmotionalSignal) -> None:
        value = {
            EmotionalSignal.FRUSTRATION: self._state.frustration,
            EmotionalSignal.CURIOSITY: self._state.curiosity,
            EmotionalSignal.SATISFACTION: self._state.satisfaction,
        }[signal]
        threshold = {
            EmotionalSignal.FRUSTRATION: self.FRUSTRATION_THRESHOLD,
            EmotionalSignal.CURIOSITY: self.CURIOSITY_THRESHOLD,
            EmotionalSignal.SATISFACTION: self.SATISFACTION_THRESHOLD,
        }[signal]
        if value >= threshold:
            self._state.history.append({
                "signal": signal.value,
                "value": round(value, 3),
                "timestamp": time.time(),
                "trigger": "threshold_crossed",
            })

    def get_impulse(self) -> dict[str, Any] | None:
        """Get the current steering impulse, if any signal is dominant."""
        if not self._state.dominant:
            return None
        signal = self._state.dominant
        value = {
            EmotionalSignal.FRUSTRATION: self._state.frustration,
            EmotionalSignal.CURIOSITY: self._state.curiosity,
            EmotionalSignal.SATISFACTION: self._state.satisfaction,
        }[signal]
        if signal == EmotionalSignal.FRUSTRATION and value >= self.FRUSTRATION_THRESHOLD:
            return {
                "signal": "frustration",
                "action": "try_new_approach",
                "intensity": round(value, 3),
                "reason": f"error_rate={self._error_count}/{self._total_calls}, retries={self._retry_count}",
            }
        if signal == EmotionalSignal.CURIOSITY and value >= self.CURIOSITY_THRESHOLD:
            return {
                "signal": "curiosity",
                "action": "explore_unexplored",
                "intensity": round(value, 3),
                "clusters": self._unexplored_clusters[:5],
            }
        if signal == EmotionalSignal.SATISFACTION and value >= self.SATISFACTION_THRESHOLD:
            return {
                "signal": "satisfaction",
                "action": "reinforce_pattern",
                "intensity": round(value, 3),
                "success_rate": round(self._success_count / max(self._total_calls, 1), 3),
            }
        return None

    def get_state(self) -> dict[str, Any]:
        return self._state.to_dict()

    def reset(self) -> None:
        self._state = EmotionalState()
        self._error_count = 0
        self._retry_count = 0
        self._success_count = 0
        self._total_calls = 0
        self._unexplored_clusters.clear()
        self._recent_memories_accessed.clear()


_singleton: EmotionalSteering | None = None


def get_emotional_steering() -> EmotionalSteering:
    global _singleton
    if _singleton is None:
        _singleton = EmotionalSteering()
    return _singleton
