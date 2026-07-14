"""Tests for Possibility Space Explorer — Monte Carlo simulation."""

import os
import tempfile

os.environ.setdefault("WM_STATE_ROOT", tempfile.mkdtemp())
os.environ.setdefault("WM_SKIP_POLYGLOT", "1")
os.environ.setdefault("WM_SILENT_INIT", "1")


from whitemagic.core.consciousness.possibility_explorer import (
    ExplorationResult,
    PossibilitySpaceExplorer,
)


class TestPossibilitySpaceExplorer:
    def test_explore_guna_balance(self):
        explorer = PossibilitySpaceExplorer()
        result = explorer.explore("guna_balance", n_trials=50)

        assert result.space_name == "guna_balance"
        assert result.n_trials == 50
        assert result.best_trial is not None
        assert result.best_trial.fitness_score > 0.0
        assert len(result.top_trials) <= 10

    def test_explore_coherence(self):
        explorer = PossibilitySpaceExplorer()
        result = explorer.explore("coherence_optimization", n_trials=30)

        assert result.n_trials == 30
        assert result.avg_fitness >= 0.0

    def test_explore_emergence(self):
        explorer = PossibilitySpaceExplorer()
        result = explorer.explore("emergence_thresholds", n_trials=30)

        assert result.n_trials == 30
        assert "tag_cluster_threshold" in result.parameter_sensitivity

    def test_explore_health(self):
        explorer = PossibilitySpaceExplorer()
        result = explorer.explore("health_setpoints", n_trials=30)

        assert result.n_trials == 30
        assert "coherence_threshold" in result.parameter_sensitivity

    def test_sensitivity_analysis(self):
        explorer = PossibilitySpaceExplorer()
        result = explorer.explore("guna_balance", n_trials=100)

        # Sensitivity should be computed for all params
        assert "sattvic_target" in result.parameter_sensitivity
        assert "rajasic_target" in result.parameter_sensitivity
        assert "tamasic_target" in result.parameter_sensitivity
        # Sensitivity values are absolute correlations [0, 1]
        for v in result.parameter_sensitivity.values():
            assert 0.0 <= v <= 1.0

    def test_best_params_stored(self):
        explorer = PossibilitySpaceExplorer()
        explorer.explore("guna_balance", n_trials=50)

        best = explorer.get_best_params("guna_balance")
        assert best is not None
        assert "sattvic_target" in best

    def test_get_status(self):
        explorer = PossibilitySpaceExplorer()
        explorer.explore("guna_balance", n_trials=10)

        status = explorer.get_status()
        assert "spaces_explored" in status
        assert "best_params" in status
        assert "guna_balance" in status["best_params"]

    def test_get_report(self):
        explorer = PossibilitySpaceExplorer()
        explorer.explore("guna_balance", n_trials=10)
        report = explorer.get_report()
        assert "POSSIBILITY SPACE" in report

    def test_guna_balance_fitness_ideal(self):
        explorer = PossibilitySpaceExplorer()
        # At exact target ratio, fitness should be high
        params = {
            "sattvic_target": 1/6,
            "rajasic_target": 2/6,
            "tamasic_target": 3/6,
        }
        score = explorer._guna_balance_fitness(params)
        assert score > 0.9

    def test_guna_balance_fitness_off_target(self):
        explorer = PossibilitySpaceExplorer()
        params = {
            "sattvic_target": 0.5,
            "rajasic_target": 0.5,
            "tamasic_target": 0.0,
        }
        score = explorer._guna_balance_fitness(params)
        assert score < 0.5

    def test_explore_all(self):
        explorer = PossibilitySpaceExplorer()
        results = explorer.explore_all(n_trials_per_space=10)
        assert "guna_balance" in results
        assert "coherence_optimization" in results
        assert len(results) == 4

    def test_custom_params(self):
        explorer = PossibilitySpaceExplorer()
        custom = {"test_param": (0.0, 1.0)}
        result = explorer.explore("custom_space", n_trials=20, custom_params=custom)
        assert result.n_trials == 20
        assert result.best_trial is not None

    def test_exploration_result_to_dict(self):
        result = ExplorationResult(space_name="test", n_trials=10)
        d = result.to_dict()
        assert d["space_name"] == "test"
        assert d["n_trials"] == 10
