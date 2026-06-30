"""
Confidence-based agentic execution system.

Enables AI agents to assess confidence and execute tasks autonomously
based on multiple factors including tests, reversibility, and past success.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ConfidenceLevel(Enum):
    """Confidence levels for agentic execution."""

    FULL = "full"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


@dataclass
class ConfidenceFactors:
    """Factors that contribute to confidence assessment."""

    test_coverage: float = 0.0
    reversibility: float = 0.0
    past_success_rate: float = 0.0
    complexity: float = 0.0
    familiarity: float = 0.0
    risk_level: float = 0.0

    def composite(self) -> float:
        """Compute weighted composite confidence score."""
        weights = {
            "test_coverage": 0.25,
            "reversibility": 0.20,
            "past_success_rate": 0.25,
            "complexity": 0.10,
            "familiarity": 0.10,
            "risk_level": 0.10,
        }
        # risk_level is inverted (high risk = low confidence)
        scores = {
            "test_coverage": self.test_coverage,
            "reversibility": self.reversibility,
            "past_success_rate": self.past_success_rate,
            "complexity": self.complexity,
            "familiarity": self.familiarity,
            "risk_level": 1.0 - self.risk_level,
        }
        return sum(weights[k] * scores[k] for k in weights)


@dataclass
class ConfidenceAssessor:
    """Assesses confidence for autonomous task execution."""

    factors: ConfidenceFactors = field(default_factory=ConfidenceFactors)
    thresholds: dict[str, float] = field(
        default_factory=lambda: {
            "full": 0.90,
            "high": 0.75,
            "medium": 0.55,
            "low": 0.35,
        }
    )

    def assess(self) -> ConfidenceLevel:
        """Assess current confidence level."""
        score = self.factors.composite()
        if score >= self.thresholds["full"]:
            return ConfidenceLevel.FULL
        elif score >= self.thresholds["high"]:
            return ConfidenceLevel.HIGH
        elif score >= self.thresholds["medium"]:
            return ConfidenceLevel.MEDIUM
        elif score >= self.thresholds["low"]:
            return ConfidenceLevel.LOW
        return ConfidenceLevel.NONE

    def should_proceed_autonomously(self) -> bool:
        """Whether the agent should proceed without human confirmation."""
        level = self.assess()
        return level in (ConfidenceLevel.FULL, ConfidenceLevel.HIGH)

    def should_request_confirmation(self) -> bool:
        """Whether the agent should request human confirmation."""
        level = self.assess()
        return level in (ConfidenceLevel.MEDIUM, ConfidenceLevel.LOW)

    def should_abort(self) -> bool:
        """Whether the agent should abort the task."""
        return self.assess() == ConfidenceLevel.NONE

    def report(self) -> dict[str, Any]:
        """Get detailed confidence report."""
        score = self.factors.composite()
        level = self.assess()
        return {
            "level": level.value,
            "score": round(score, 3),
            "factors": {
                "test_coverage": self.factors.test_coverage,
                "reversibility": self.factors.reversibility,
                "past_success_rate": self.factors.past_success_rate,
                "complexity": self.factors.complexity,
                "familiarity": self.factors.familiarity,
                "risk_level": self.factors.risk_level,
            },
            "autonomous": self.should_proceed_autonomously(),
            "needs_confirmation": self.should_request_confirmation(),
            "abort": self.should_abort(),
        }
