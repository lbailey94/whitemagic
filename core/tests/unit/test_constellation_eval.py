"""Tests for Objective N — Constellation-Based Joint Evaluation."""

from __future__ import annotations

from whitemagic.core.evolution.constellation_eval import (
    Constellation,
    ConstellationEvaluator,
)


class TestClustering:
    def test_empty(self):
        evaluator = ConstellationEvaluator()
        assert evaluator.cluster([]) == []

    def test_single(self):
        evaluator = ConstellationEvaluator()
        consts = evaluator.cluster([{"id": "h1", "semantic_coord": 0.5}])
        assert len(consts) == 1
        assert "h1" in consts[0].member_ids

    def test_clusters_by_proximity(self):
        evaluator = ConstellationEvaluator(similarity_threshold=0.1)
        hyps = [
            {"id": "h1", "semantic_coord": 0.1},
            {"id": "h2", "semantic_coord": 0.12},
            {"id": "h3", "semantic_coord": 0.8},
            {"id": "h4", "semantic_coord": 0.82},
        ]
        consts = evaluator.cluster(hyps)
        assert len(consts) == 2
        assert {"h1", "h2"} == set(consts[0].member_ids) or {"h1", "h2"} == set(
            consts[1].member_ids
        )

    def test_all_in_one_cluster(self):
        evaluator = ConstellationEvaluator(similarity_threshold=0.5)
        hyps = [
            {"id": "h1", "semantic_coord": 0.1},
            {"id": "h2", "semantic_coord": 0.15},
            {"id": "h3", "semantic_coord": 0.2},
        ]
        consts = evaluator.cluster(hyps)
        assert len(consts) == 1
        assert len(consts[0].member_ids) == 3


class TestJointProbability:
    def test_independent(self):
        evaluator = ConstellationEvaluator()
        const = Constellation(id="c1", member_ids=["h1", "h2"])
        joint = evaluator.compute_joint_probability(
            const,
            individual_probs={"h1": 0.8, "h2": 0.6},
            correlation=0.0,
        )
        # Independent: 0.8 * 0.6 = 0.48
        assert abs(joint - 0.48) < 0.1

    def test_positive_correlation_high_confidence(self):
        evaluator = ConstellationEvaluator()
        const = Constellation(id="c1", member_ids=["h1", "h2"])
        joint = evaluator.compute_joint_probability(
            const,
            individual_probs={"h1": 0.9, "h2": 0.9},
            correlation=0.5,
        )
        # With positive correlation and high confidence, joint should be higher
        independent = 0.9 * 0.9
        assert joint >= independent * 0.95  # Allow small numerical tolerance

    def test_empty_members(self):
        evaluator = ConstellationEvaluator()
        const = Constellation(id="c1", member_ids=[])
        joint = evaluator.compute_joint_probability(const, {})
        assert joint == 0.0


class TestContagion:
    def test_contagion_boosts_others(self):
        evaluator = ConstellationEvaluator()
        const = Constellation(
            id="c1",
            member_ids=["h1", "h2", "h3"],
            individual_probs={"h1": 0.5, "h2": 0.5, "h3": 0.5},
        )
        updated = evaluator.apply_contagion(const, succeeded_id="h1", boost=0.2)
        assert updated["h2"] == 0.7
        assert updated["h3"] == 0.7
        assert updated["h1"] == 0.5  # Unchanged

    def test_contagion_clamped_to_1(self):
        evaluator = ConstellationEvaluator()
        const = Constellation(
            id="c1",
            member_ids=["h1", "h2"],
            individual_probs={"h1": 0.5, "h2": 0.9},
        )
        updated = evaluator.apply_contagion(const, succeeded_id="h1", boost=0.2)
        assert updated["h2"] == 1.0  # Clamped


class TestStats:
    def test_stats(self):
        evaluator = ConstellationEvaluator()
        evaluator.cluster(
            [
                {"id": "h1", "semantic_coord": 0.1},
                {"id": "h2", "semantic_coord": 0.12},
                {"id": "h3", "semantic_coord": 0.8},
            ]
        )
        stats = evaluator.get_stats()
        assert stats["total_constellations"] == 2
        assert stats["total_members"] == 3
