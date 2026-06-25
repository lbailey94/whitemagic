"""Information-Theoretic Exploration (Objective P).

Uses Shannon entropy and KL divergence to prioritize improvements that
maximize information gain — regardless of outcome.

Key formula:
    IG = H(P(success)) - [P(success) · H(P(success | observed_success))
                          + P(failure) · H(P(success | observed_failure))]

This is the expected reduction in entropy from observing the outcome.
Improvements with high IG are worth more than ones with predictable outcomes.

Combined with utility:
    score = α · predicted_impact + β · information_gain + γ · novelty

The α/β/γ weights adapt based on the system's current state:
- High uncertainty → increase β (explore more)
- High confidence → increase α (exploit more)
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass

logger = logging.getLogger(__name__)

try:
    from whitemagic.core.evolution._rust_bridge import call as _rust_call
except ImportError:
    _rust_call = None


def shannon_entropy(p: float) -> float:
    """Shannon entropy of a Bernoulli distribution with success probability p.

    H(p) = -p·log2(p) - (1-p)·log2(1-p)

    Returns 0 for p=0 or p=1 (no uncertainty).
    """
    if _rust_call is not None:
        result = _rust_call("shannon_entropy", p=p)
        if result is not None:
            return result["entropy"]
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -p * math.log2(p) - (1.0 - p) * math.log2(1.0 - p)


def kl_divergence(p: float, q: float) -> float:
    """KL divergence D(P || Q) for Bernoulli distributions.

    D(P||Q) = p·log(p/q) + (1-p)·log((1-p)/(1-q))
    """
    if p <= 0.0:
        p = 1e-10
    if p >= 1.0:
        p = 1.0 - 1e-10
    if q <= 0.0:
        q = 1e-10
    if q >= 1.0:
        q = 1.0 - 1e-10
    return p * math.log(p / q) + (1.0 - p) * math.log((1.0 - p) / (1.0 - q))


def information_gain(p_success: float, n_prior: int = 10) -> float:
    """Expected information gain from observing an improvement outcome.

    IG = H(P(success)) - [P(success) · H(P(success | observed_success))
                          + P(failure) · H(P(success | observed_failure))]

    Uses Beta(α, β) posterior update:
    - Prior: Beta(α=p*n, β=(1-p)*n)
    - After success: Beta(α+1, β) → posterior mean = (α+1)/(n+1)
    - After failure: Beta(α, β+1) → posterior mean = α/(n+1)

    Args:
        p_success: Current predicted probability of success.
        n_prior: Prior strength (number of pseudo-observations).

    Returns:
        Information gain in bits.
    """
    if _rust_call is not None:
        result = _rust_call("information_gain", p_success=p_success, n_prior=n_prior)
        if result is not None:
            return result["information_gain"]
    if p_success <= 0.0 or p_success >= 1.0:
        return 0.0

    alpha = max(p_success * n_prior, 0.5)
    beta = max((1.0 - p_success) * n_prior, 0.5)

    # Posterior after success
    p_after_success = (alpha + 1.0) / (alpha + beta + 1.0)
    # Posterior after failure
    p_after_failure = alpha / (alpha + beta + 1.0)

    # Entropy before observation
    h_prior = shannon_entropy(p_success)

    # Expected entropy after observation
    h_after = (
        p_success * shannon_entropy(p_after_success)
        + (1.0 - p_success) * shannon_entropy(p_after_failure)
    )

    return max(0.0, h_prior - h_after)


@dataclass
class AdaptiveWeights:
    """Adaptive α/β/γ weights for exploration scoring.

    Weights adapt based on system uncertainty:
    - High uncertainty → increase β (information gain weight)
    - High confidence → increase α (predicted impact weight)
    - Novelty always gets some weight via γ
    """
    alpha: float = 0.5  # predicted_impact weight
    beta: float = 0.3   # information_gain weight
    gamma: float = 0.2  # novelty weight

    def adapt(self, system_entropy: float, max_entropy: float = 1.0) -> None:
        """Adapt weights based on current system uncertainty.

        Args:
            system_entropy: Current Shannon entropy of the system's predictions.
                High entropy = high uncertainty = explore more.
            max_entropy: Maximum possible entropy (for normalization).
        """
        if max_entropy <= 0:
            return

        normalized = min(system_entropy / max_entropy, 1.0)

        # When uncertainty is high, shift toward exploration (β up)
        # When uncertainty is low, shift toward exploitation (α up)
        self.alpha = 0.3 + 0.4 * (1.0 - normalized)  # 0.3-0.7
        self.beta = 0.1 + 0.5 * normalized            # 0.1-0.6
        self.gamma = 0.2  # Constant

        # Normalize to sum to 1.0
        total = self.alpha + self.beta + self.gamma
        if total > 0:
            self.alpha /= total
            self.beta /= total
            self.gamma /= total


def compute_exploration_score(
    predicted_impact: float,
    p_success: float,
    novelty: float,
    weights: AdaptiveWeights | None = None,
    n_prior: int = 10,
) -> dict[str, float]:
    """Compute the exploration score for a hypothesis.

    score = α · predicted_impact + β · information_gain + γ · novelty

    Args:
        predicted_impact: Predicted impact (0-1).
        p_success: Predicted probability of success.
        novelty: Novelty score (0-1).
        weights: Adaptive weights. If None, uses defaults.
        n_prior: Prior strength for information gain computation.

    Returns:
        Dict with score, IG, and weight components.
    """
    w = weights or AdaptiveWeights()
    ig = information_gain(p_success, n_prior)

    score = (
        w.alpha * predicted_impact
        + w.beta * ig
        + w.gamma * novelty
    )

    return {
        "score": round(score, 6),
        "information_gain": round(ig, 6),
        "alpha": round(w.alpha, 4),
        "beta": round(w.beta, 4),
        "gamma": round(w.gamma, 4),
    }


def system_uncertainty(confidences: list[float]) -> float:
    """Compute overall system uncertainty from a list of confidence values.

    High variance in confidences → high uncertainty.

    Args:
        confidences: List of confidence values (0-1).

    Returns:
        Shannon entropy-like measure of system uncertainty (0-1).
    """
    if _rust_call is not None and confidences:
        result = _rust_call("system_uncertainty", confidences=confidences)
        if result is not None:
            return result["uncertainty"]
    if not confidences:
        return 0.0

    # Average entropy of individual predictions
    avg_entropy = sum(shannon_entropy(c) for c in confidences) / len(confidences)
    return avg_entropy
