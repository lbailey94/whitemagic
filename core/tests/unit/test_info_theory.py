"""Tests for Objective P — Information-Theoretic Exploration."""

from __future__ import annotations

from whitemagic.core.evolution.info_theory import (
    AdaptiveWeights,
    compute_exploration_score,
    information_gain,
    kl_divergence,
    shannon_entropy,
    system_uncertainty,
)


class TestShannonEntropy:
    def test_zero_or_one(self):
        assert shannon_entropy(0.0) == 0.0
        assert shannon_entropy(1.0) == 0.0

    def test_half_is_one_bit(self):
        assert abs(shannon_entropy(0.5) - 1.0) < 1e-10

    def test_symmetric(self):
        assert abs(shannon_entropy(0.3) - shannon_entropy(0.7)) < 1e-10

    def test_range(self):
        for p in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
            assert 0.0 <= shannon_entropy(p) <= 1.0


class TestKLDivergence:
    def test_same_distribution(self):
        assert abs(kl_divergence(0.5, 0.5)) < 1e-6

    def test_different_distribution(self):
        assert kl_divergence(0.9, 0.1) > 0.0

    def test_non_negative(self):
        for p in [0.1, 0.3, 0.5, 0.7, 0.9]:
            for q in [0.1, 0.3, 0.5, 0.7, 0.9]:
                assert kl_divergence(p, q) >= 0.0


class TestInformationGain:
    def test_certain_outcome_zero_ig(self):
        """If p=0 or p=1, no information is gained from observing."""
        assert information_gain(0.0) == 0.0
        assert information_gain(1.0) == 0.0

    def test_uncertain_outcome_positive_ig(self):
        """If p=0.5, observing the outcome gives maximum information."""
        ig = information_gain(0.5)
        assert ig > 0.0

    def test_ig_decreases_with_confidence(self):
        """More confident predictions have less information gain.

        IG is highest near p=0.5 (maximum uncertainty) and drops
        toward 0 at p=0 or p=1.
        """
        ig_certain = information_gain(0.01)
        ig_mid = information_gain(0.5)
        assert ig_mid > ig_certain

    def test_ig_positive_for_uncertain(self):
        """IG should be positive for uncertain predictions."""
        assert information_gain(0.3) > 0.0
        assert information_gain(0.7) > 0.0
        assert information_gain(0.5) > 0.0


class TestAdaptiveWeights:
    def test_defaults(self):
        w = AdaptiveWeights()
        assert w.alpha > 0
        assert w.beta > 0
        assert w.gamma > 0

    def test_adapt_high_uncertainty(self):
        w = AdaptiveWeights()
        w.adapt(0.9)  # High uncertainty
        # Beta should be higher than when uncertainty is low
        assert w.beta > w.alpha

    def test_adapt_low_uncertainty(self):
        w = AdaptiveWeights()
        w.adapt(0.1)  # Low uncertainty
        # Alpha should be higher than when uncertainty is high
        assert w.alpha > w.beta

    def test_adapt_normalizes(self):
        w = AdaptiveWeights()
        w.adapt(0.5)
        total = w.alpha + w.beta + w.gamma
        assert abs(total - 1.0) < 1e-6

    def test_adapt_zero_entropy(self):
        w = AdaptiveWeights()
        w.adapt(0.0)
        total = w.alpha + w.beta + w.gamma
        assert abs(total - 1.0) < 1e-6


class TestExplorationScore:
    def test_basic(self):
        result = compute_exploration_score(
            predicted_impact=0.8,
            p_success=0.7,
            novelty=0.5,
        )
        assert "score" in result
        assert "information_gain" in result
        assert 0.0 <= result["score"] <= 1.0

    def test_with_custom_weights(self):
        w = AdaptiveWeights(alpha=0.6, beta=0.2, gamma=0.2)
        result = compute_exploration_score(
            predicted_impact=0.9,
            p_success=0.5,
            novelty=0.3,
            weights=w,
        )
        assert result["alpha"] == 0.6

    def test_certain_outcome(self):
        result = compute_exploration_score(
            predicted_impact=0.8,
            p_success=1.0,
            novelty=0.0,
        )
        assert result["information_gain"] == 0.0


class TestSystemUncertainty:
    def test_empty(self):
        assert system_uncertainty([]) == 0.0

    def test_all_certain(self):
        assert system_uncertainty([1.0, 1.0, 1.0]) == 0.0

    def test_all_uncertain(self):
        u = system_uncertainty([0.5, 0.5, 0.5])
        assert abs(u - 1.0) < 1e-6

    def test_mixed(self):
        u = system_uncertainty([0.1, 0.5, 0.9])
        assert 0.0 < u < 1.0
