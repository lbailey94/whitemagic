"""Bicameral Improvement Debate (Objective O).

Uses the bicameral reasoning system to debate each improvement.
Left hemisphere argues for (benefits, feasibility), right argues
against (risks, opportunity cost). Debate quality is itself a signal.

Metrics:
- Agreement score: how close are the two sides? High = low information
- Contention score: how much do they disagree? High = high information
- Convergence: did the debate move either side?

Contention score is used as an exploration boost: improvements where
both sides make strong arguments are worth more than ones where one
side dominates.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DebateArgument:
    """A single argument in a bicameral debate."""
    side: str  # "left" (advocate) or "right" (skeptic)
    claim: str
    strength: float  # 0-1
    evidence: list[str] = field(default_factory=list)


@dataclass
class DebateResult:
    """Result of a bicameral improvement debate."""
    hypothesis_id: str
    left_score: float       # Advocate's final score (0-1)
    right_score: float      # Skeptic's final score (0-1, lower = more skeptical)
    left_arguments: list[DebateArgument] = field(default_factory=list)
    right_arguments: list[DebateArgument] = field(default_factory=list)
    agreement: float = 0.0  # 1 - |left - right|
    contention: float = 0.0  # |left - right|
    convergence: float = 0.0  # How much positions moved
    initial_left: float = 0.5
    initial_right: float = 0.5
    transcript: list[str] = field(default_factory=list)

    @property
    def net_score(self) -> float:
        """Net evaluation score after debate."""
        return (self.left_score + (1.0 - self.right_score)) / 2.0

    @property
    def is_high_contention(self) -> bool:
        """True if both sides make strong cases."""
        return self.contention > 0.3 and self.left_score > 0.5 and self.right_score > 0.5


class BicameralDebate:
    """Debates improvements using bicameral reasoning.

    Left hemisphere (advocate): argues for based on predicted impact,
    alignment with goals, feasibility.
    Right hemisphere (skeptic): argues against based on risk,
    opportunity cost, potential side effects, historical failure rate.
    """

    def __init__(self) -> None:
        self._debates: dict[str, DebateResult] = {}
        self._calibration: list[tuple[float, bool]] = []  # (contention, was_skeptic_right)

    def debate(
        self,
        hypothesis_id: str,
        predicted_impact: float,
        feasibility: float = 0.7,
        risk: float = 0.3,
        historical_failure_rate: float = 0.3,
        opportunity_cost: float = 0.2,
    ) -> DebateResult:
        """Conduct a bicameral debate on a hypothesis.

        Args:
            hypothesis_id: The hypothesis to debate.
            predicted_impact: Predicted impact (0-1).
            feasibility: How feasible is it (0-1).
            risk: Risk level (0-1).
            historical_failure_rate: Failure rate of similar improvements.
            opportunity_cost: Cost of not doing other improvements (0-1).

        Returns:
            DebateResult with scores, arguments, and metrics.
        """
        # Initial positions
        initial_left = predicted_impact * feasibility
        initial_right = 1.0 - (risk * 0.5 + historical_failure_rate * 0.3 + opportunity_cost * 0.2)

        # Left (advocate) arguments
        left_args = [
            DebateArgument(
                side="left",
                claim=f"Predicted impact is {predicted_impact:.0%}",
                strength=predicted_impact,
                evidence=["MC simulation", "impact analysis"],
            ),
            DebateArgument(
                side="left",
                claim=f"Feasibility is {feasibility:.0%}",
                strength=feasibility,
                evidence=["resource analysis", "codebase scan"],
            ),
        ]

        # Right (skeptic) arguments
        right_args = [
            DebateArgument(
                side="right",
                claim=f"Risk level is {risk:.0%}",
                strength=risk,
                evidence=["risk assessment", "failure mode analysis"],
            ),
            DebateArgument(
                side="right",
                claim=f"Historical failure rate for similar improvements is {historical_failure_rate:.0%}",
                strength=historical_failure_rate,
                evidence=["outcome database", "pattern matching"],
            ),
            DebateArgument(
                side="right",
                claim=f"Opportunity cost is {opportunity_cost:.0%}",
                strength=opportunity_cost,
                evidence=["portfolio analysis"],
            ),
        ]

        # Debate rounds — each side adjusts based on the other's arguments
        left_score = initial_left
        right_score = initial_right

        # Round 1: Left presents → Right adjusts
        left_strength = sum(a.strength for a in left_args) / len(left_args)
        right_score = right_score * (1 - left_strength * 0.2)

        # Round 2: Right presents → Left adjusts
        right_strength = sum(a.strength for a in right_args) / len(right_args)
        left_score = left_score * (1 - right_strength * 0.15)

        # Round 3: Convergence attempt
        gap = abs(left_score - right_score)
        if gap < 0.2:
            # Close enough → converge
            avg = (left_score + right_score) / 2
            left_score = left_score * 0.7 + avg * 0.3
            right_score = right_score * 0.7 + avg * 0.3

        # Compute metrics
        agreement = 1.0 - abs(left_score - right_score)
        contention = abs(left_score - right_score)
        convergence = abs(initial_left - left_score) + abs(initial_right - right_score)

        transcript = [
            f"Left initial: {initial_left:.2f}, Right initial: {initial_right:.2f}",
            f"Left final: {left_score:.2f}, Right final: {right_score:.2f}",
            f"Agreement: {agreement:.2f}, Contention: {contention:.2f}",
        ]

        result = DebateResult(
            hypothesis_id=hypothesis_id,
            left_score=left_score,
            right_score=right_score,
            left_arguments=left_args,
            right_arguments=right_args,
            agreement=agreement,
            contention=contention,
            convergence=convergence,
            initial_left=initial_left,
            initial_right=initial_right,
            transcript=transcript,
        )

        self._debates[hypothesis_id] = result
        return result

    def get_exploration_boost(self, hypothesis_id: str) -> float:
        """Get exploration boost from debate contention.

        High contention (both sides make strong cases) → boost exploration.
        Low contention (one side dominates) → no boost.

        Returns:
            Boost in [0, 0.2].
        """
        result = self._debates.get(hypothesis_id)
        if result is None:
            return 0.0
        if result.is_high_contention:
            return min(0.2, result.contention * 0.3)
        return 0.0

    def record_validation(self, hypothesis_id: str, skeptic_was_right: bool) -> None:
        """Record whether the skeptic's concerns were validated.

        Used for calibrating future debates.
        """
        result = self._debates.get(hypothesis_id)
        if result is None:
            return
        self._calibration.append((result.contention, skeptic_was_right))

    def get_debate(self, hypothesis_id: str) -> DebateResult | None:
        return self._debates.get(hypothesis_id)

    def get_all_debates(self) -> dict[str, DebateResult]:
        return dict(self._debates)

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_debates": len(self._debates),
            "high_contention": sum(1 for d in self._debates.values() if d.is_high_contention),
            "avg_contention": (
                sum(d.contention for d in self._debates.values()) / len(self._debates)
                if self._debates else 0.0
            ),
            "calibration_count": len(self._calibration),
        }
