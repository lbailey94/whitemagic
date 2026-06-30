"""Guna-Based Improvement Classification (Objective V).

Classifies improvements by the three gunas (sattvic, rajasic, tamasic)
and balances the portfolio dynamically based on system state.

- Sattvic (clarity, harmony): documentation, naming, organization
  - Low risk, reliable, modest impact. Prior: high mean, low variance.
- Rajasic (action, energy): new features, acceleration, optimization
  - High energy, high variance, high upside. Prior: moderate mean, high variance.
- Tamasic (inertia, dissolution): debt reduction, deprecation, cleanup
  - Necessary but low energy. Prior: low mean, low variance.

Portfolio balance target:
  High technical debt → increase tamasic allocation
  Stagnation → increase rajasic allocation
  Chaos/instability → increase sattvic allocation
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class Guna(Enum):
    """Three gunas for improvement classification."""

    SATTVIC = "sattvic"  # Clarity, harmony
    RAJASIC = "rajasic"  # Action, energy
    TAMASIC = "tamasic"  # Inertia, dissolution


GUNA_CONFIG: dict[Guna, dict[str, Any]] = {
    Guna.SATTVIC: {
        "description": "Documentation, naming, organization, quality",
        "prior_mean": 0.8,
        "prior_variance": 0.05,
        "keywords": [
            "doc",
            "naming",
            "organize",
            "quality",
            "clean",
            "clarify",
            "standardize",
        ],
    },
    Guna.RAJASIC: {
        "description": "New features, acceleration, expansion, optimization",
        "prior_mean": 0.5,
        "prior_variance": 0.2,
        "keywords": [
            "feature",
            "accelerat",
            "optim",
            "new",
            "expand",
            "performance",
            "speed",
            "parallel",
        ],
    },
    Guna.TAMASIC: {
        "description": "Debt reduction, deprecation, cleanup, removal",
        "prior_mean": 0.6,
        "prior_variance": 0.05,
        "keywords": [
            "debt",
            "deprecat",
            "cleanup",
            "remove",
            "delete",
            "archive",
            "purge",
            "strip",
        ],
    },
}


@dataclass
class GunaPortfolio:
    """Portfolio allocation across gunas."""

    sattvic: float = 0.33
    rajasic: float = 0.34
    tamasic: float = 0.33

    def to_dict(self) -> dict[str, float]:
        return {
            "sattvic": self.sattvic,
            "rajasic": self.rajasic,
            "tamasic": self.tamasic,
        }

    @property
    def dominant(self) -> Guna:
        """Return the dominant guna in the portfolio."""
        values = {
            Guna.SATTVIC: self.sattvic,
            Guna.RAJASIC: self.rajasic,
            Guna.TAMASIC: self.tamasic,
        }
        return max(values, key=values.get)  # type: ignore[arg-type]


class GunaClassifier:
    """Classifies improvements by guna and manages portfolio balance."""

    def __init__(self) -> None:
        self._classification_history: list[tuple[str, Guna]] = []
        self._guna_counts: dict[Guna, int] = {g: 0 for g in Guna}
        self._guna_outcomes: dict[Guna, list[float]] = {g: [] for g in Guna}

    def classify(self, category: str, description: str = "") -> Guna:
        """Classify an improvement into a guna.

        Args:
            category: Improvement category from kaizen.
            description: Description text.

        Returns:
            The Guna classification.
        """
        desc_lower = description.lower()

        # Score each guna by keyword matches in description only
        scores: dict[Guna, int] = {g: 0 for g in Guna}
        for guna, config in GUNA_CONFIG.items():
            for kw in config["keywords"]:
                if kw in desc_lower:
                    scores[guna] += 1

        # Pick highest scoring guna
        best = max(scores, key=scores.get)  # type: ignore[arg-type]
        if scores[best] == 0:
            # No keyword match — default by category
            if category == "quality":
                return Guna.SATTVIC
            elif category == "performance":
                return Guna.RAJASIC
            elif category == "codebase_quality":
                return Guna.TAMASIC
            return Guna.SATTVIC

        self._classification_history.append((description, best))
        self._guna_counts[best] += 1
        return best

    def get_prior(self, guna: Guna) -> tuple[float, float]:
        """Get (mean, variance) prior for a guna."""
        config = GUNA_CONFIG.get(guna, GUNA_CONFIG[Guna.SATTVIC])
        return (config["prior_mean"], config["prior_variance"])

    def record_outcome(self, guna: Guna, success: bool) -> None:
        """Record an outcome for a guna classification."""
        self._guna_outcomes[guna].append(1.0 if success else 0.0)

    def get_success_rate(self, guna: Guna) -> float:
        """Get observed success rate for a guna."""
        outcomes = self._guna_outcomes[guna]
        if not outcomes:
            return GUNA_CONFIG[guna]["prior_mean"]
        return sum(outcomes) / len(outcomes)

    def get_current_portfolio(self) -> GunaPortfolio:
        """Get current portfolio balance based on classifications."""
        total = sum(self._guna_counts.values())
        if total == 0:
            return GunaPortfolio()
        return GunaPortfolio(
            sattvic=self._guna_counts[Guna.SATTVIC] / total,
            rajasic=self._guna_counts[Guna.RAJASIC] / total,
            tamasic=self._guna_counts[Guna.TAMASIC] / total,
        )

    def get_target_portfolio(self, system_state: str = "balanced") -> GunaPortfolio:
        """Get target portfolio based on system state.

        Args:
            system_state: "balanced", "high_debt", "stagnation", or "chaos"

        Returns:
            Target GunaPortfolio.
        """
        if system_state == "high_debt":
            return GunaPortfolio(sattvic=0.2, rajasic=0.2, tamasic=0.6)
        elif system_state == "stagnation":
            return GunaPortfolio(sattvic=0.2, rajasic=0.6, tamasic=0.2)
        elif system_state == "chaos":
            return GunaPortfolio(sattvic=0.6, rajasic=0.2, tamasic=0.2)
        else:
            return GunaPortfolio(sattvic=0.4, rajasic=0.3, tamasic=0.3)

    def check_balance(
        self,
        current: GunaPortfolio,
        target: GunaPortfolio,
        tolerance: float = 0.15,
    ) -> dict[str, Any]:
        """Check if portfolio is within tolerance of targets."""
        deficits = {}
        balanced = True
        for guna in Guna:
            g_name = guna.value
            c_val = current.to_dict()[g_name]
            t_val = target.to_dict()[g_name]
            diff = t_val - c_val
            if abs(diff) > tolerance:
                deficits[g_name] = diff
                balanced = False
        return {"balanced": balanced, "deficits": deficits}

    def get_stats(self) -> dict[str, Any]:
        return {
            "classifications": len(self._classification_history),
            "guna_counts": {g.value: c for g, c in self._guna_counts.items()},
            "success_rates": {g.value: self.get_success_rate(g) for g in Guna},
            "current_portfolio": self.get_current_portfolio().to_dict(),
        }
