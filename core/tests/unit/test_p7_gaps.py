"""Tests for P7 gap closures — ParameterMapper and multi_objective_estimate.

Tests verify:
- ParameterMapper heuristic fallback with <3 observations
- ParameterMapper learned prediction with 3+ observations
- ParameterMapper weighted nearest-neighbor interpolation
- multi_objective_estimate() returns Pareto front
- Pareto front contains non-dominated solutions only
- Hypervolume computation for 2 objectives
"""

import pytest
from unittest.mock import MagicMock

from whitemagic.oracle.parameter_mapper import ParameterMapper, get_parameter_mapper


class TestParameterMapper:
    """Test the learned parameter mapping."""

    def test_heuristic_fallback_with_no_data(self):
        mapper = ParameterMapper()
        assert not mapper.is_fitted
        result = mapper.predict_external_params(
            {"x0": 0.5, "x1": 0.3},
            ["alpha", "beta"],
        )
        # Heuristic: intro * 100
        assert result["alpha"] == 50.0
        assert result["beta"] == 30.0

    def test_heuristic_fallback_with_two_observations(self):
        mapper = ParameterMapper()
        mapper.add_observation({"x0": 0.5}, {"alpha": 10.0}, 0.8)
        mapper.add_observation({"x0": 0.3}, {"alpha": 5.0}, 0.6)
        assert not mapper.is_fitted
        # Should still use heuristic
        result = mapper.predict_external_params({"x0": 0.4}, ["alpha"])
        assert result["alpha"] == 40.0  # 0.4 * 100

    def test_learned_prediction_with_three_observations(self):
        mapper = ParameterMapper()
        mapper.add_observation({"x0": 0.5}, {"alpha": 10.0}, 0.9)
        mapper.add_observation({"x0": 0.3}, {"alpha": 5.0}, 0.7)
        mapper.add_observation({"x0": 0.4}, {"alpha": 7.0}, 0.8)
        assert mapper.is_fitted
        result = mapper.predict_external_params({"x0": 0.4}, ["alpha"])
        # Should return a weighted prediction, not heuristic
        assert isinstance(result["alpha"], float)
        # Should be between min and max of training ext params
        assert 5.0 <= result["alpha"] <= 10.0

    def test_n_observations(self):
        mapper = ParameterMapper()
        assert mapper.n_observations == 0
        mapper.add_observation({"x0": 0.5}, {"alpha": 10.0}, 0.9)
        assert mapper.n_observations == 1

    def test_reset(self):
        mapper = ParameterMapper()
        mapper.add_observation({"x0": 0.5}, {"alpha": 10.0}, 0.9)
        mapper.add_observation({"x0": 0.3}, {"alpha": 5.0}, 0.7)
        mapper.add_observation({"x0": 0.4}, {"alpha": 7.0}, 0.8)
        assert mapper.is_fitted
        mapper.reset()
        assert not mapper.is_fitted
        assert mapper.n_observations == 0

    def test_get_parameter_mapper_singleton(self):
        m1 = get_parameter_mapper()
        m2 = get_parameter_mapper()
        assert m1 is m2

    def test_heuristic_with_more_ext_than_intro(self):
        mapper = ParameterMapper()
        result = mapper.predict_external_params(
            {"x0": 0.5},
            ["alpha", "beta", "gamma"],
        )
        assert result["alpha"] == 50.0
        assert result["beta"] == 50.0  # Default mid-range
        assert result["gamma"] == 50.0

    def test_learned_prediction_favors_better_outcomes(self):
        """Observations with better outcomes should have more influence."""
        mapper = ParameterMapper()
        # High-outcome observation with alpha=100
        mapper.add_observation({"x0": 0.5}, {"alpha": 100.0}, 1.0)
        # Low-outcome observation with alpha=1
        mapper.add_observation({"x0": 0.5}, {"alpha": 1.0}, 0.01)
        # Medium-outcome observation
        mapper.add_observation({"x0": 0.5}, {"alpha": 50.0}, 0.5)
        assert mapper.is_fitted
        result = mapper.predict_external_params({"x0": 0.5}, ["alpha"])
        # Should be weighted toward high-outcome (alpha=100)
        assert result["alpha"] > 50.0


class TestMultiObjectiveEstimate:
    """Test multi-objective BO with Pareto fronts."""

    def test_multi_objective_returns_dict(self):
        from whitemagic.core.evolution.polyglot_mc import PolyglotMCOrchestrator
        mc = PolyglotMCOrchestrator()

        def fn1(x):
            return x[0]

        def fn2(x):
            return 1.0 - x[0]

        result = mc.multi_objective_estimate(
            fitness_fns=[fn1, fn2],
            param_ranges=[(0.0, 1.0)],
            n_initial=5,
            n_iterations=3,
        )
        assert isinstance(result, dict)
        assert "pareto_front" in result
        assert "hypervolume" in result
        assert result["n_objectives"] == 2

    def test_pareto_front_contains_non_dominated_only(self):
        from whitemagic.core.evolution.polyglot_mc import PolyglotMCOrchestrator
        mc = PolyglotMCOrchestrator()

        def fn1(x):
            return x[0]

        def fn2(x):
            return x[1] if len(x) > 1 else 1.0 - x[0]

        result = mc.multi_objective_estimate(
            fitness_fns=[fn1, fn2],
            param_ranges=[(0.0, 1.0), (0.0, 1.0)],
            n_initial=5,
            n_iterations=3,
        )
        front = result["pareto_front"]
        # No point in the front should be dominated by another
        for i, p1 in enumerate(front):
            for j, p2 in enumerate(front):
                if i == j:
                    continue
                # p2 should not dominate p1
                dominated = all(p2["scores"][k] >= p1["scores"][k] for k in range(2)) and \
                            any(p2["scores"][k] > p1["scores"][k] for k in range(2))
                assert not dominated, f"Point {i} is dominated by point {j}"

    def test_hypervolume_nonneg(self):
        from whitemagic.core.evolution.polyglot_mc import PolyglotMCOrchestrator
        mc = PolyglotMCOrchestrator()

        def fn1(x):
            return x[0]

        def fn2(x):
            return 1.0 - x[0]

        result = mc.multi_objective_estimate(
            fitness_fns=[fn1, fn2],
            param_ranges=[(0.0, 1.0)],
            n_initial=5,
            n_iterations=3,
        )
        assert result["hypervolume"] >= 0.0

    def test_n_evaluated_matches(self):
        from whitemagic.core.evolution.polyglot_mc import PolyglotMCOrchestrator
        mc = PolyglotMCOrchestrator()

        def fn1(x):
            return x[0]

        result = mc.multi_objective_estimate(
            fitness_fns=[fn1],
            param_ranges=[(0.0, 1.0)],
            n_initial=5,
            n_iterations=3,
        )
        assert result["n_evaluated"] > 0
        assert len(result["all_evaluated"]) == result["n_evaluated"]
