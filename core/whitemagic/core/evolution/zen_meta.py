"""Zen Meta-Strategy (Objective Z).

The system observes which improvement objectives (A-Y) are working and
dynamically reconfigures its own improvement process. This is the
meta-level — the system improves *how it improves*.

Meta-features (state of the improvement system):
- Discovery rate (novel improvements per cycle)
- Calibration error (Brier score gap)
- Portfolio guna balance
- Yield curve shape
- Information gain rate
- Convergence rate (dream cycle)
- External validation correlation

Meta-strategy selector: a contextual bandit (meta-bandit) that selects
which improvement strategy to emphasize.

Arms: {A (automated outcomes), B (interaction MC), D (surprisal exploration),
       Q (thermodynamic scheduling), P (info-theoretic), ...}

Hierarchy:
  Level 0: Apply improvements
  Level 1: Improve prediction of improvements (MC, Brier)
  Level 2: Improve exploration of improvements (P, Q, D)
  Level 3: Improve the improvement strategy (Z, meta-bandit)
  Level 4: Improve the meta-strategy (R, predictive coding Layer 4)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MetaFeatures:
    """State of the improvement system — context for the meta-bandit."""
    discovery_rate: float = 0.5       # Novel improvements per cycle
    calibration_error: float = 0.2    # Brier score gap
    portfolio_balance: float = 0.5    # Guna balance (0=imbalanced, 1=balanced)
    yield_curve_shape: float = 0.5    # 0=decaying, 1=compounding
    info_gain_rate: float = 0.3       # Information gain per cycle
    convergence_rate: float = 0.5     # Dream cycle convergence
    external_validation: float = 0.5  # Correlation with external assessment

    def to_vector(self) -> list[float]:
        return [
            self.discovery_rate,
            self.calibration_error,
            self.portfolio_balance,
            self.yield_curve_shape,
            self.info_gain_rate,
            self.convergence_rate,
            self.external_validation,
        ]


# Strategy arms
STRATEGY_ARMS = [
    "A_automated_outcomes",
    "B_interaction_mc",
    "D_surprisal_exploration",
    "E_variance_reduction",
    "F_holographic_trajectory",
    "G_galactic_lifecycle",
    "H_hrr_composition",
    "I_resonance_transfer",
    "J_bayesian_dream",
    "K_valence_utility",
    "L_garden_routing",
    "N_constellation_eval",
    "O_bicameral_debate",
    "P_info_theoretic",
    "Q_thermodynamic",
    "R_predictive_coding",
    "T_causal_ledger",
    "U_dependency_graph",
    "V_guna_classification",
    "Y_yield_curve",
]


@dataclass
class ArmStats:
    """Statistics for a single meta-bandit arm."""
    arm: str
    pulls: int = 0
    total_reward: float = 0.0
    contexts: list[list[float]] = field(default_factory=list)
    rewards: list[float] = field(default_factory=list)

    @property
    def mean_reward(self) -> float:
        if self.pulls == 0:
            return 0.0
        return self.total_reward / self.pulls

    @property
    def confidence(self) -> float:
        """U CB confidence bound."""
        if self.pulls == 0:
            return float("inf")
        return math.sqrt(2 * math.log(max(self.pulls + 1, 2)) / self.pulls)


class MetaBandit:
    """Contextual bandit for meta-strategy selection.

    Uses UCB (Upper Confidence Bound) for exploration-exploitation.
    Each arm represents an improvement strategy objective.
    """

    def __init__(self, arms: list[str] | None = None, exploration_weight: float = 1.0) -> None:
        self._arms = arms or list(STRATEGY_ARMS)
        self._exploration_weight = exploration_weight
        self._stats: dict[str, ArmStats] = {arm: ArmStats(arm=arm) for arm in self._arms}
        self._total_pulls = 0
        self._history: list[tuple[str, MetaFeatures, float]] = []

    def select(self, context: MetaFeatures) -> str:
        """Select the best strategy arm for the current context.

        Uses UCB: score = mean_reward + exploration_weight * confidence

        Args:
            context: Current meta-features.

        Returns:
            Selected arm name.
        """
        best_arm = self._arms[0]
        best_score = float("-inf")

        for arm in self._arms:
            stats = self._stats[arm]
            if stats.pulls == 0:
                # Always try unexplored arms first
                return arm

            ucb_score = stats.mean_reward + self._exploration_weight * stats.confidence
            if ucb_score > best_score:
                best_score = ucb_score
                best_arm = arm

        return best_arm

    def update(self, arm: str, context: MetaFeatures, reward: float) -> None:
        """Update the bandit with observed reward.

        Args:
            arm: The arm that was pulled.
            context: The context when the arm was pulled.
            reward: Observed reward (e.g., improvement in invariant metrics).
        """
        stats = self._stats.get(arm)
        if stats is None:
            return
        stats.pulls += 1
        stats.total_reward += reward
        stats.contexts.append(context.to_vector())
        stats.rewards.append(reward)
        self._total_pulls += 1
        self._history.append((arm, context, reward))

    def get_arm_stats(self, arm: str) -> ArmStats | None:
        return self._stats.get(arm)

    def get_best_strategies(self, n: int = 5) -> list[tuple[str, float]]:
        """Get top-n strategies by mean reward."""
        ranked = sorted(
            [(arm, stats.mean_reward) for arm, stats in self._stats.items()],
            key=lambda x: x[1],
            reverse=True,
        )
        return ranked[:n]

    def get_strategy_recommendations(self, context: MetaFeatures) -> dict[str, Any]:
        """Get strategy recommendations for the current system state.

        Args:
            context: Current meta-features.

        Returns:
            Dict with recommended strategy and reasoning.
        """
        selected = self.select(context)
        reasoning = []

        if context.discovery_rate < 0.3:
            reasoning.append("Low discovery rate → emphasize exploration strategies (D, P)")
        if context.calibration_error > 0.3:
            reasoning.append("High calibration error → emphasize MC variance reduction (E, B)")
        if context.portfolio_balance < 0.4:
            reasoning.append("Portfolio imbalanced → emphasize guna/garden routing (V, L)")
        if context.yield_curve_shape < 0.3:
            reasoning.append("Yield curve decaying → shift to compounding improvements (Y)")
        if context.info_gain_rate < 0.2:
            reasoning.append("Low information gain → emphasize info-theoretic exploration (P)")
        if context.convergence_rate < 0.3:
            reasoning.append("Dream cycle not converging → check predictive coding (R)")
        if context.external_validation < 0.4:
            reasoning.append("External validation weak → check invariant metrics (W, X)")

        return {
            "recommended_strategy": selected,
            "reasoning": reasoning,
            "context_summary": {
                "discovery_rate": context.discovery_rate,
                "calibration_error": context.calibration_error,
                "portfolio_balance": context.portfolio_balance,
                "info_gain_rate": context.info_gain_rate,
            },
            "top_strategies": self.get_best_strategies(3),
        }

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_pulls": self._total_pulls,
            "total_arms": len(self._arms),
            "arms_explored": sum(1 for s in self._stats.values() if s.pulls > 0),
            "best_strategies": self.get_best_strategies(3),
            "avg_reward": (
                sum(s.total_reward for s in self._stats.values()) / max(self._total_pulls, 1)
            ),
        }
