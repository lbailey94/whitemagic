"""Tests for Research DAG — Experiment lineage tracking."""

import os
import tempfile

os.environ.setdefault("WM_STATE_ROOT", tempfile.mkdtemp())
os.environ.setdefault("WM_SKIP_POLYGLOT", "1")
os.environ.setdefault("WM_SILENT_INIT", "1")

import pytest

from whitemagic.core.evolution.research_dag import (
    Experiment,
    ExperimentStage,
    ResearchDAG,
    ResearchDomain,
    get_research_dag,
)


@pytest.fixture
def dag():
    """Get a fresh ResearchDAG instance for each test."""
    dag = get_research_dag()
    dag._initialized = False
    dag._cache.clear()
    dag._ensure_table()
    return dag


class TestExperimentDataclass:
    def test_experiment_creation(self):
        exp = Experiment(
            experiment_id="test_001",
            hypothesis="Test hypothesis about guna balance",
            domain=ResearchDomain.COGNITIVE,
        )
        assert exp.stage == ExperimentStage.HYPOTHESIS
        assert exp.fitness_score == 0.0
        assert exp.galactic_zone == "core"

    def test_experiment_to_dict(self):
        exp = Experiment(
            experiment_id="test_002",
            hypothesis="Test",
            domain=ResearchDomain.MEMORY,
            fitness_score=0.85,
        )
        d = exp.to_dict()
        assert d["experiment_id"] == "test_002"
        assert d["domain"] == "memory"
        assert d["fitness_score"] == 0.85

    def test_experiment_stage_values(self):
        assert ExperimentStage.HYPOTHESIS.value == "hypothesis"
        assert ExperimentStage.BREAKTHROUGH.value == "breakthrough"
        assert ExperimentStage.FAILED.value == "failed"

    def test_research_domain_values(self):
        assert ResearchDomain.COGNITIVE.value == "cognitive"
        assert ResearchDomain.SYNTHESIS.value == "synthesis"


class TestResearchDAG:
    def test_submit_hypothesis(self, dag):
        exp = dag.submit_hypothesis(
            hypothesis="Higher sattvic ratio improves coherence",
            domain=ResearchDomain.COGNITIVE,
            parameters={"sattvic_target": 0.25},
            agent_id="test_agent",
        )
        assert exp.experiment_id is not None
        assert exp.stage == ExperimentStage.HYPOTHESIS
        assert exp.hypothesis == "Higher sattvic ratio improves coherence"
        assert exp.agent_id == "test_agent"

    def test_record_trial(self, dag):
        exp = dag.submit_hypothesis(
            hypothesis="Test trial",
            domain=ResearchDomain.EVOLUTION,
        )
        trial = dag.record_trial(exp.experiment_id, parameters={"test": 0.5})
        assert trial is not None
        assert trial.stage == ExperimentStage.TRIAL
        assert trial.parameters.get("test") == 0.5

    def test_record_result(self, dag):
        exp = dag.submit_hypothesis(
            hypothesis="Test result",
            domain=ResearchDomain.COGNITIVE,
        )
        dag.record_trial(exp.experiment_id)
        result = dag.record_result(
            exp.experiment_id,
            fitness_score=0.55,
            outcome={"metric": "coherence"},
        )
        assert result is not None
        assert result.stage == ExperimentStage.RESULT
        assert result.fitness_score == 0.55
        assert result.galactic_zone == "mid_band"

    def test_record_result_breakthrough(self, dag):
        exp = dag.submit_hypothesis(
            hypothesis="Test breakthrough",
            domain=ResearchDomain.COGNITIVE,
        )
        dag.record_trial(exp.experiment_id)
        result = dag.record_result(
            exp.experiment_id,
            fitness_score=0.92,
        )
        assert result.stage == ExperimentStage.BREAKTHROUGH
        assert result.galactic_zone == "core"

    def test_record_critique(self, dag):
        exp = dag.submit_hypothesis(
            hypothesis="Test critique",
            domain=ResearchDomain.MEMORY,
        )
        dag.record_trial(exp.experiment_id)
        dag.record_result(exp.experiment_id, fitness_score=0.5)

        result = dag.record_critique(
            exp.experiment_id,
            critic_agent_id="critic_001",
            score=9,
            notes="Excellent approach",
        )
        assert result is not None
        assert len(result.critiques) == 1
        assert result.critiques[0]["score"] == 9
        # Score >= 8 should promote to breakthrough
        assert result.stage == ExperimentStage.BREAKTHROUGH

    def test_record_critique_low_score(self, dag):
        exp = dag.submit_hypothesis(
            hypothesis="Test low critique",
            domain=ResearchDomain.COGNITIVE,
        )
        dag.record_trial(exp.experiment_id)
        dag.record_result(exp.experiment_id, fitness_score=0.5)

        result = dag.record_critique(
            exp.experiment_id,
            critic_agent_id="critic_002",
            score=4,
            notes="Needs work",
        )
        assert result.stage != ExperimentStage.BREAKTHROUGH

    def test_mark_failed(self, dag):
        exp = dag.submit_hypothesis(
            hypothesis="Test failure",
            domain=ResearchDomain.EVOLUTION,
        )
        result = dag.mark_failed(exp.experiment_id, reason="Timeout")
        assert result is not None
        assert result.stage == ExperimentStage.FAILED
        assert result.galactic_zone == "far_edge"
        assert result.metadata.get("failure_reason") == "Timeout"

    def test_get_lineage(self, dag):
        # Create parent experiment
        parent = dag.submit_hypothesis(
            hypothesis="Parent hypothesis",
            domain=ResearchDomain.COGNITIVE,
        )
        dag.record_trial(parent.experiment_id)
        dag.record_result(parent.experiment_id, fitness_score=0.85)

        # Create child inspired by parent
        child = dag.submit_hypothesis(
            hypothesis="Child hypothesis",
            domain=ResearchDomain.COGNITIVE,
            inspiration_ids=[parent.experiment_id],
        )

        lineage = dag.get_lineage(child.experiment_id)
        assert lineage["experiment_id"] == child.experiment_id
        assert len(lineage["ancestors"]) >= 1
        assert lineage["ancestors"][0]["experiment_id"] == parent.experiment_id

    def test_get_breakthroughs(self, dag):
        # Create some experiments
        for i in range(5):
            exp = dag.submit_hypothesis(
                hypothesis=f"Breakthrough test {i}",
                domain=ResearchDomain.COGNITIVE,
            )
            dag.record_trial(exp.experiment_id)
            dag.record_result(exp.experiment_id, fitness_score=0.8 + i * 0.02)

        breakthroughs = dag.get_breakthroughs(domain=ResearchDomain.COGNITIVE)
        assert len(breakthroughs) >= 5
        # Should be sorted by fitness descending
        assert breakthroughs[0].fitness_score >= breakthroughs[-1].fitness_score

    def test_get_experiments(self, dag):
        exp = dag.submit_hypothesis(
            hypothesis="Query test",
            domain=ResearchDomain.MEMORY,
        )
        experiments = dag.get_experiments(domain=ResearchDomain.MEMORY)
        assert any(e.experiment_id == exp.experiment_id for e in experiments)

    def test_get_stats(self, dag):
        # Create a few experiments
        for i in range(3):
            dag.submit_hypothesis(
                hypothesis=f"Stats test {i}",
                domain=ResearchDomain.COGNITIVE,
            )

        stats = dag.get_stats()
        assert "total_experiments" in stats
        assert "by_stage" in stats
        assert "by_domain" in stats
        assert stats["total_experiments"] >= 3

    def test_get_domain_leaderboard(self, dag):
        for i in range(5):
            exp = dag.submit_hypothesis(
                hypothesis=f"Leaderboard test {i}",
                domain=ResearchDomain.COGNITIVE,
            )
            dag.record_trial(exp.experiment_id)
            dag.record_result(exp.experiment_id, fitness_score=0.5 + i * 0.1)

        leaderboard = dag.get_domain_leaderboard(ResearchDomain.COGNITIVE)
        assert len(leaderboard) > 0
        assert "rank" in leaderboard[0]
        assert "fitness_score" in leaderboard[0]
        # Should be sorted by fitness descending
        assert leaderboard[0]["fitness_score"] >= leaderboard[-1]["fitness_score"]

    def test_fitness_to_zone(self, dag):
        assert dag._fitness_to_zone(0.9) == "core"
        assert dag._fitness_to_zone(0.7) == "inner_rim"
        assert dag._fitness_to_zone(0.5) == "mid_band"
        assert dag._fitness_to_zone(0.3) == "outer_rim"
        assert dag._fitness_to_zone(0.1) == "far_edge"

    def test_clear_cache(self, dag):
        exp = dag.submit_hypothesis(
            hypothesis="Cache test",
            domain=ResearchDomain.COGNITIVE,
        )
        assert exp.experiment_id in dag._cache
        dag.clear_cache()
        assert len(dag._cache) == 0

    def test_nonexistent_experiment(self, dag):
        assert dag._load("nonexistent_id") is None
        assert dag.record_trial("nonexistent") is None
        assert dag.record_result("nonexistent", 0.5) is None
        assert dag.record_critique("nonexistent", "agent", 5) is None
