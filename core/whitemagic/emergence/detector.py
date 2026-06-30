"""
Emergence Detector — Detect emergent behaviors and novel patterns.

Scans system outputs for unexpected, creative, or self-organizing
behaviors that weren't explicitly programmed.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class EmergentBehavior:
    """Record of an emergent behavior."""

    pattern: str
    context: str = ""
    confidence: float = 0.0
    trigger: str = ""
    timestamp: float = field(default_factory=time.time)
    novelty_score: float = 0.0


class EmergenceDetector:
    """Detects emergent behaviors in system outputs."""

    def __init__(self) -> None:
        self.behaviors: list[EmergentBehavior] = []
        self._known_patterns: set[str] = set()

    def observe(self, output: str, context: str = "") -> EmergentBehavior | None:
        """Observe system output for emergent patterns."""
        novelty = self._assess_novelty(output)
        if novelty < 0.3:
            return None

        behavior = EmergentBehavior(
            pattern=output[:200],
            context=context,
            confidence=min(novelty, 1.0),
            trigger="observation",
            novelty_score=novelty,
        )
        self.behaviors.append(behavior)
        self._known_patterns.add(output[:50].lower())
        logger.debug("Emergent behavior detected: novelty=%.2f", novelty)
        return behavior

    def _assess_novelty(self, output: str) -> float:
        """Assess how novel an output is."""
        if not output:
            return 0.0
        prefix = output[:50].lower()
        if prefix in self._known_patterns:
            return 0.1
        # Simple heuristic: longer outputs with unique words are more novel
        words = set(output.lower().split())
        unique_ratio = len(words) / max(len(output.split()), 1)
        return min(unique_ratio * 2, 1.0)

    def recent_behaviors(self, limit: int = 10) -> list[EmergentBehavior]:
        return self.behaviors[-limit:]

    def summary(self) -> dict[str, Any]:
        return {
            "total_behaviors": len(self.behaviors),
            "avg_novelty": (
                sum(b.novelty_score for b in self.behaviors) / len(self.behaviors)
                if self.behaviors
                else 0.0
            ),
            "known_patterns": len(self._known_patterns),
        }


_detector: EmergenceDetector | None = None


def get_detector() -> EmergenceDetector:
    global _detector
    if _detector is None:
        _detector = EmergenceDetector()
    return _detector
