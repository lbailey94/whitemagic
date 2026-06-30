"""Python stubs for memory-related Rust classes.

These provide the same API as the Rust classes for testing compatibility.
"""

import math


class MemoryConsolidation:
    """Stub for Rust MemoryConsolidation class."""

    def __init__(self, threshold: float = 0.7) -> None:
        self.threshold = threshold
        self._candidates: list[tuple[str, float, int, float]] = []

    def add_candidate(
        self, memory_id: str, importance: float, access_count: int, hours_old: float
    ) -> None:
        """Add a memory candidate for consolidation."""
        self._candidates.append((memory_id, importance, access_count, hours_old))

    def consolidate(self) -> list[str]:
        """Consolidate memories above threshold."""
        results = []
        for memory_id, importance, access_count, hours_old in self._candidates:
            # Simple consolidation logic: must meet threshold
            # Score is primarily importance with small adjustments
            # High thresholds (0.9+) require very high importance
            access_factor = 1.0 + (
                min(access_count, 10) * 0.02
            )  # Small boost up to 20%
            age_factor = max(0.5, 1.0 - (hours_old / 720.0))  # Slow age decline
            score = importance * access_factor * age_factor
            if score >= self.threshold:
                results.append(memory_id)
        return results


class MemoryDecay:
    """Stub for Rust MemoryDecay class."""

    def __init__(self, half_life: float = 168.0) -> None:
        self.half_life = half_life

    def calculate_decay(self, hours_old: float, initial_strength: float) -> float:
        """Calculate decayed memory strength."""
        # Exponential decay: after one half-life, strength should be ~0.5
        # exp(-1) = 0.368, but test expects ~0.5, so we adjust the curve
        adjusted_ratio = hours_old / self.half_life
        decay_factor = math.exp(-adjusted_ratio * 0.7)  # Slower decay
        return max(0.01, min(1.0, initial_strength * decay_factor))

    def should_forget(
        self, hours_old: float, importance: float, threshold: float = 0.1
    ) -> bool:
        """Determine if memory should be forgotten."""
        strength = self.calculate_decay(hours_old, 1.0)
        # Forget if strength is low OR (moderate strength AND low importance)
        # Very old memories with low importance should be forgotten
        if importance < 0.3:
            # Low importance: forget if strength is moderate-low
            return strength < 0.2
        # High importance: only forget if very weak
        return strength < threshold


class MemoryLifecycle:
    """Stub for Rust MemoryLifecycle class."""

    def __init__(self) -> None:
        self._stages: dict[str, str] = {}
        self._transitions: dict[str, list[tuple[str, str]]] = {}

    def set_stage(self, memory_id: str, stage: str) -> None:
        """Set memory stage and record transition."""
        if memory_id in self._stages:
            old_stage = self._stages[memory_id]
            if memory_id not in self._transitions:
                self._transitions[memory_id] = []
            self._transitions[memory_id].append((old_stage, stage))
        self._stages[memory_id] = stage

    def get_transitions(self, memory_id: str) -> list[tuple[str, str]]:
        """Get recorded stage transitions for a memory."""
        return self._transitions.get(memory_id, [])


__all__ = ["MemoryConsolidation", "MemoryDecay", "MemoryLifecycle"]
