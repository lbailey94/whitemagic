"""Tests for Objective Z — Zen Meta-Strategy."""

from __future__ import annotations

from whitemagic.core.evolution.zen_meta import (
    STRATEGY_ARMS,
    MetaBandit,
    MetaFeatures,
)


class TestMetaFeatures:
    def test_defaults(self):
        mf = MetaFeatures()
        assert mf.discovery_rate == 0.5
        assert mf.calibration_error == 0.2

    def test_to_vector(self):
        mf = MetaFeatures()
        vec = mf.to_vector()
        assert len(vec) == 7


class TestMetaBandit:
    def test_initial_selection(self):
        bandit = MetaBandit(arms=["A", "B", "C"])
        ctx = MetaFeatures()
        selected = bandit.select(ctx)
        # Should select first unexplored arm
        assert selected in ["A", "B", "C"]

    def test_update_changes_priorities(self):
        bandit = MetaBandit(arms=["A", "B", "C"])
        ctx = MetaFeatures()
        # Pull A with high reward
        bandit.update("A", ctx, reward=1.0)
        bandit.update("A", ctx, reward=1.0)
        # Pull B with low reward
        bandit.update("B", ctx, reward=0.1)
        bandit.update("B", ctx, reward=0.1)
        # A should have higher mean reward
        stats_a = bandit.get_arm_stats("A")
        stats_b = bandit.get_arm_stats("B")
        assert stats_a.mean_reward > stats_b.mean_reward

    def test_explores_all_arms_first(self):
        bandit = MetaBandit(arms=["A", "B", "C"])
        ctx = MetaFeatures()
        selected_arms = set()
        for _ in range(3):
            arm = bandit.select(ctx)
            selected_arms.add(arm)
            bandit.update(arm, ctx, reward=0.5)
        # Should have explored all 3 arms
        assert len(selected_arms) == 3

    def test_get_best_strategies(self):
        bandit = MetaBandit(arms=["A", "B", "C"])
        ctx = MetaFeatures()
        bandit.update("A", ctx, reward=0.9)
        bandit.update("B", ctx, reward=0.3)
        bandit.update("C", ctx, reward=0.6)
        best = bandit.get_best_strategies(n=2)
        assert best[0][0] == "A"
        assert best[0][1] > best[1][1]

    def test_strategy_recommendations(self):
        bandit = MetaBandit()
        ctx = MetaFeatures(
            discovery_rate=0.1,  # Low
            calibration_error=0.4,  # High
            portfolio_balance=0.3,  # Imbalanced
            info_gain_rate=0.1,  # Low
        )
        rec = bandit.get_strategy_recommendations(ctx)
        assert "recommended_strategy" in rec
        assert "reasoning" in rec
        assert len(rec["reasoning"]) > 0  # Should have recommendations

    def test_stats(self):
        bandit = MetaBandit(arms=["A", "B"])
        ctx = MetaFeatures()
        bandit.update("A", ctx, reward=0.8)
        stats = bandit.get_stats()
        assert stats["total_pulls"] == 1
        assert stats["arms_explored"] == 1

    def test_default_arms(self):
        bandit = MetaBandit()
        stats = bandit.get_stats()
        assert stats["total_arms"] == len(STRATEGY_ARMS)

    def test_arm_stats(self):
        bandit = MetaBandit(arms=["A"])
        ctx = MetaFeatures()
        bandit.update("A", ctx, reward=0.5)
        stats = bandit.get_arm_stats("A")
        assert stats.pulls == 1
        assert stats.mean_reward == 0.5
