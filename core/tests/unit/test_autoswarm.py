"""Tests for Evolutionary Autoswarm — continuous evolutionary compute loop."""

import os
import tempfile

os.environ.setdefault("WM_STATE_ROOT", tempfile.mkdtemp())
os.environ.setdefault("WM_SKIP_POLYGLOT", "1")
os.environ.setdefault("WM_SILENT_INIT", "1")

import pytest

from whitemagic.core.evolution.autoswarm import (
    AutoswarmStats,
    CampaignConfig,
    CampaignResult,
    EvolutionaryAutoswarm,
    get_autoswarm,
)
from whitemagic.core.evolution.research_dag import ResearchDomain


@pytest.fixture
def autoswarm():
    """Get a fresh autoswarm instance with clean DAG state."""
    from whitemagic.core.evolution.research_dag import ResearchDAG
    ResearchDAG._instance = None
    EvolutionaryAutoswarm._instance = None
    swarm = get_autoswarm()
    yield swarm
    # Teardown: reset singletons to prevent state leakage in parallel tests
    EvolutionaryAutoswarm._instance = None
    ResearchDAG._instance = None


class TestCampaignConfig:
    def test_default_config(self):
        config = CampaignConfig(campaign_name="test")
        assert config.campaign_name == "test"
        assert config.domain == ResearchDomain.COGNITIVE
        assert config.n_trials == 100
        assert config.max_iterations == 10
        assert config.share_results is True
        assert config.dream_integration is True

    def test_custom_config(self):
        config = CampaignConfig(
            campaign_name="custom",
            domain=ResearchDomain.EVOLUTION,
            n_trials=50,
            max_iterations=5,
            share_results=False,
        )
        assert config.domain == ResearchDomain.EVOLUTION
        assert config.n_trials == 50
        assert config.max_iterations == 5
        assert config.share_results is False


class TestCampaignResult:
    def test_to_dict(self):
        result = CampaignResult(
            campaign_name="test",
            domain=ResearchDomain.COGNITIVE,
            experiments_run=10,
            breakthroughs=2,
            best_fitness=0.85,
        )
        d = result.to_dict()
        assert d["campaign_name"] == "test"
        assert d["experiments_run"] == 10
        assert d["breakthroughs"] == 2
        assert d["best_fitness"] == 0.85


class TestEvolutionaryAutoswarm:
    def test_run_campaign(self, autoswarm):
        config = CampaignConfig(
            campaign_name="test_campaign",
            domain=ResearchDomain.COGNITIVE,
            hypothesis_space="guna_balance",
            n_trials=10,
            max_iterations=3,
            share_results=False,
            dream_integration=False,
        )
        result = autoswarm.run_campaign(config)

        assert result.campaign_name == "test_campaign"
        assert result.experiments_run > 0
        assert result.error is None
        assert result.duration_seconds > 0

    def test_campaign_records_to_dag(self, autoswarm):
        config = CampaignConfig(
            campaign_name="dag_test",
            domain=ResearchDomain.EVOLUTION,
            hypothesis_space="emergence_thresholds",
            n_trials=5,
            max_iterations=2,
            share_results=False,
            dream_integration=False,
        )
        result = autoswarm.run_campaign(config)

        # Check that experiments were recorded in the DAG
        from whitemagic.core.evolution.research_dag import get_research_dag
        dag = get_research_dag()
        stats = dag.get_stats()
        assert stats.get("total_experiments", 0) > 0

    def test_get_status(self, autoswarm):
        status = autoswarm.get_status()
        assert "running" in status
        assert "stats" in status
        assert "recent_campaigns" in status
        assert "campaigns_run" in status["stats"]

    def test_continuous_start_stop(self, autoswarm):
        config = CampaignConfig(
            campaign_name="continuous_test",
            domain=ResearchDomain.COGNITIVE,
            n_trials=5,
            max_iterations=2,
            share_results=False,
            dream_integration=False,
        )
        autoswarm.run_continuous(
            interval_seconds=1.0,
            campaign_configs=[config],
        )
        assert autoswarm._running is True

        import time
        time.sleep(2.5)

        autoswarm.stop()
        assert autoswarm._running is False

    def test_mutate_params(self, autoswarm):
        params = {"sattvic_target": 0.2, "rajasic_target": 0.4}
        mutated = autoswarm._mutate_params(params)
        assert "sattvic_target" in mutated
        assert "rajasic_target" in mutated
        # Should be slightly different (with high probability)
        # but not guaranteed due to randomness — just check they're floats
        assert isinstance(mutated["sattvic_target"], float)

    def test_default_campaigns(self, autoswarm):
        campaigns = autoswarm._default_campaigns()
        assert len(campaigns) == 5
        names = [c.campaign_name for c in campaigns]
        assert "cognitive_optimization" in names
        assert "coherence_tuning" in names
        assert "emergence_exploration" in names
        assert "health_setpoints" in names
        assert "superforecaster_deep_optimization" in names
