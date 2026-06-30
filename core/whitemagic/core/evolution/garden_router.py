"""Garden-Routed Improvement Evaluation (Objective L).

Routes improvements through the garden system. Each garden maintains its
own calibration curve, priors, and evaluation criteria.

Gardens:
- Courage: Hard refactors, architectural changes (high variance, high upside)
- Wisdom: Documentation, knowledge organization (reliable, modest)
- Play: Experimental features, novel approaches (high novelty, uncertain)
- Grief: Debt reduction, deprecation, cleanup (necessary, low energy)
- Mystery: Research, exploration, unknown-unknown discovery (high info value)

Portfolio balance ensures improvements span multiple gardens.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Garden definitions with default priors
GARDEN_CONFIG: dict[str, dict[str, Any]] = {
    "courage": {
        "description": "Hard refactors, architectural changes",
        "prior_mean": 0.5,
        "prior_variance": 0.2,  # High variance
        "confidence_threshold": 0.7,  # Requires high confidence
        "mc_trial_multiplier": 1.5,  # More trials for risky changes
    },
    "wisdom": {
        "description": "Documentation, knowledge organization",
        "prior_mean": 0.8,
        "prior_variance": 0.05,  # Low variance, reliable
        "confidence_threshold": 0.5,
        "mc_trial_multiplier": 0.8,
    },
    "play": {
        "description": "Experimental features, novel approaches",
        "prior_mean": 0.4,
        "prior_variance": 0.25,  # Highest variance
        "confidence_threshold": 0.5,
        "mc_trial_multiplier": 2.0,  # Most trials — uncertain outcomes
    },
    "grief": {
        "description": "Debt reduction, deprecation, cleanup",
        "prior_mean": 0.7,
        "prior_variance": 0.08,
        "confidence_threshold": 0.5,
        "mc_trial_multiplier": 0.8,
    },
    "mystery": {
        "description": "Research, exploration, unknown-unknown discovery",
        "prior_mean": 0.3,
        "prior_variance": 0.3,  # Very uncertain
        "confidence_threshold": 0.4,  # Low threshold — worth trying
        "mc_trial_multiplier": 2.5,  # Most trials
    },
}


@dataclass
class GardenCalibration:
    """Per-garden calibration tracking."""

    garden: str
    brier_score: float = 0.25  # Starting Brier score
    outcome_count: int = 0
    success_count: int = 0
    confidence_history: list[float] = field(default_factory=list)
    actual_history: list[float] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if self.outcome_count == 0:
            return GARDEN_CONFIG.get(self.garden, {}).get("prior_mean", 0.5)
        return self.success_count / self.outcome_count

    def update_brier(self, predicted: float, actual: float) -> float:
        """Update Brier score with new outcome."""
        self.confidence_history.append(predicted)
        self.actual_history.append(actual)
        self.outcome_count += 1
        if actual >= 0.5:
            self.success_count += 1
        # Running average Brier score
        brier = (predicted - actual) ** 2
        n = self.outcome_count
        self.brier_score = ((n - 1) * self.brier_score + brier) / n
        return self.brier_score


class GardenRouter:
    """Routes improvements through gardens and manages portfolio balance."""

    def __init__(self) -> None:
        self._calibration: dict[str, GardenCalibration] = {
            g: GardenCalibration(garden=g) for g in GARDEN_CONFIG
        }

    def classify(self, category: str, description: str = "") -> str:
        """Classify an improvement into a garden.

        Uses the improvement category and description keywords.

        Args:
            category: The improvement category from kaizen.
            description: Optional description text.

        Returns:
            Garden name.
        """
        desc_lower = description.lower()

        # Check description keywords first (more specific)
        if any(
            kw in desc_lower
            for kw in ["refactor", "architecture", "rewrite", "restructure"]
        ):
            return "courage"
        elif any(
            kw in desc_lower
            for kw in ["doc", "documentation", "naming", "organize", "quality"]
        ):
            return "wisdom"
        elif any(
            kw in desc_lower
            for kw in ["experiment", "novel", "creative", "new feature", "prototype"]
        ):
            return "play"
        elif any(
            kw in desc_lower
            for kw in ["debt", "deprecat", "cleanup", "remove", "delete"]
        ):
            return "grief"
        elif any(
            kw in desc_lower
            for kw in ["research", "explore", "unknown", "discover", "investigate"]
        ):
            return "mystery"
        else:
            # Fall back to category
            if category == "quality":
                return "wisdom"
            elif category == "performance":
                return "courage"
            elif category == "gap":
                return "mystery"
            elif category == "emergence":
                return "play"
            elif category == "codebase_quality":
                return "grief"
            return "wisdom"

    def get_prior(self, garden: str) -> tuple[float, float]:
        """Get (mean, variance) prior for a garden."""
        config = GARDEN_CONFIG.get(garden, GARDEN_CONFIG["wisdom"])
        return (config["prior_mean"], config["prior_variance"])

    def get_confidence_threshold(self, garden: str) -> float:
        """Get confidence threshold for action."""
        return GARDEN_CONFIG.get(garden, {}).get("confidence_threshold", 0.5)

    def get_mc_trial_multiplier(self, garden: str) -> float:
        """Get MC trial allocation multiplier."""
        return GARDEN_CONFIG.get(garden, {}).get("mc_trial_multiplier", 1.0)

    def record_outcome(self, garden: str, predicted: float, actual: float) -> float:
        """Record an outcome and update garden calibration.

        Returns updated Brier score.
        """
        cal = self._calibration.get(garden)
        if cal is None:
            cal = GardenCalibration(garden=garden)
            self._calibration[garden] = cal
        return cal.update_brier(predicted, actual)

    def get_portfolio_balance(
        self,
        hypotheses: list[dict[str, Any]],
    ) -> dict[str, float]:
        """Compute portfolio balance across gardens.

        Args:
            hypotheses: List of hypothesis dicts with 'garden' field.

        Returns:
            Dict of garden → fraction of total.
        """
        if not hypotheses:
            return {g: 0.0 for g in GARDEN_CONFIG}

        counts: dict[str, int] = {g: 0 for g in GARDEN_CONFIG}
        for h in hypotheses:
            g = h.get("garden", "wisdom")
            counts[g] = counts.get(g, 0) + 1

        total = len(hypotheses)
        return {g: c / total for g, c in counts.items()}

    def get_portfolio_targets(self, system_state: str = "balanced") -> dict[str, float]:
        """Get target portfolio allocation based on system state.

        Args:
            system_state: "balanced", "high_debt", "stagnation", or "chaos"

        Returns:
            Target fractions per garden.
        """
        if system_state == "high_debt":
            return {
                "courage": 0.1,
                "wisdom": 0.1,
                "play": 0.1,
                "grief": 0.6,
                "mystery": 0.1,
            }
        elif system_state == "stagnation":
            return {
                "courage": 0.3,
                "wisdom": 0.1,
                "play": 0.3,
                "grief": 0.1,
                "mystery": 0.2,
            }
        elif system_state == "chaos":
            return {
                "courage": 0.1,
                "wisdom": 0.5,
                "play": 0.1,
                "grief": 0.2,
                "mystery": 0.1,
            }
        else:  # balanced
            return {
                "courage": 0.2,
                "wisdom": 0.3,
                "play": 0.2,
                "grief": 0.15,
                "mystery": 0.15,
            }

    def check_balance(
        self,
        current: dict[str, float],
        targets: dict[str, float],
        tolerance: float = 0.15,
    ) -> dict[str, Any]:
        """Check if portfolio is within tolerance of targets.

        Returns:
            Dict with 'balanced' bool and 'deficits' dict.
        """
        deficits = {}
        balanced = True
        for garden, target in targets.items():
            actual = current.get(garden, 0.0)
            diff = target - actual
            if diff > tolerance:
                deficits[garden] = diff
                balanced = False
        return {"balanced": balanced, "deficits": deficits}

    def get_calibration(self, garden: str) -> GardenCalibration | None:
        return self._calibration.get(garden)

    def get_all_calibration(self) -> dict[str, GardenCalibration]:
        return dict(self._calibration)

    def get_stats(self) -> dict[str, Any]:
        return {
            "gardens": {
                g: {
                    "brier_score": cal.brier_score,
                    "outcome_count": cal.outcome_count,
                    "success_rate": cal.success_rate,
                }
                for g, cal in self._calibration.items()
            },
        }
