"""Tests for Objective J — Dream Cycle as Bayesian Update Pass."""
from __future__ import annotations

from whitemagic.core.evolution.bayesian_dream import (
    BAYESIAN_ROLE_MAP,
    DREAM_PHASES,
    BayesianDreamResult,
    check_convergence,
    kl_distance,
    run_bayesian_dream,
)


class TestDreamPhaseMapping:
    def test_12_phases_defined(self):
        assert len(DREAM_PHASES) == 12

    def test_all_phases_have_roles(self):
        for phase in DREAM_PHASES:
            assert phase in BAYESIAN_ROLE_MAP
            assert "role" in BAYESIAN_ROLE_MAP[phase]
            assert "math" in BAYESIAN_ROLE_MAP[phase]

    def test_phase_order(self):
        assert DREAM_PHASES[0] == "triage"
        assert DREAM_PHASES[-1] == "harmonize"
        assert DREAM_PHASES[5] == "kaizen"

    def test_key_roles(self):
        assert BAYESIAN_ROLE_MAP["triage"]["role"] == "prior_selection"
        assert BAYESIAN_ROLE_MAP["harmonize"]["role"] == "convergence_check"
        assert BAYESIAN_ROLE_MAP["kaizen"]["role"] == "action_selection"
        assert BAYESIAN_ROLE_MAP["prediction"]["role"] == "forward_simulation"


class TestKLDistance:
    def test_same_distribution(self):
        assert kl_distance(0.5, 0.5) < 1e-6

    def test_different_distributions(self):
        assert kl_distance(0.1, 0.9) > 0.0

    def test_symmetric(self):
        assert abs(kl_distance(0.3, 0.7) - kl_distance(0.7, 0.3)) < 1e-6

    def test_non_negative(self):
        for p1 in [0.1, 0.3, 0.5, 0.7, 0.9]:
            for p2 in [0.1, 0.3, 0.5, 0.7, 0.9]:
                assert kl_distance(p1, p2) >= 0.0


class TestConvergenceCheck:
    def test_converged(self):
        converged, delta = check_convergence(0.5, 0.51, epsilon=0.1)
        assert converged is True
        assert delta < 0.1

    def test_not_converged(self):
        converged, delta = check_convergence(0.1, 0.9, epsilon=0.01)
        assert converged is False
        assert delta > 0.01


class TestRunBayesianDream:
    def test_basic_run(self):
        result = run_bayesian_dream(
            initial_prior=0.5,
            evidence=[0.8, 0.7, 0.9],
            max_iterations=2,
        )
        assert isinstance(result, BayesianDreamResult)
        assert len(result.phases) == 12 * result.iterations
        assert result.iterations >= 1
        assert 0.0 < result.final_posterior < 1.0

    def test_no_evidence(self):
        result = run_bayesian_dream(
            initial_prior=0.5,
            evidence=None,
            max_iterations=1,
        )
        assert result.iterations == 1
        assert len(result.phases) == 12

    def test_convergence_terminates_early(self):
        # With no evidence and same prior, should converge quickly
        result = run_bayesian_dream(
            initial_prior=0.5,
            evidence=[],
            max_iterations=5,
            convergence_epsilon=0.5,  # Large threshold for quick convergence
        )
        assert result.converged is True

    def test_all_phases_present(self):
        result = run_bayesian_dream(max_iterations=1)
        phase_names = [p.phase for p in result.phases]
        for expected in DREAM_PHASES:
            assert expected in phase_names

    def test_phase_results_have_roles(self):
        result = run_bayesian_dream(max_iterations=1)
        for phase in result.phases:
            assert phase.bayesian_role != ""
            assert phase.math != ""

    def test_harmonize_has_convergence_data(self):
        result = run_bayesian_dream(max_iterations=1)
        harmonize = [p for p in result.phases if p.phase == "harmonize"]
        assert len(harmonize) >= 1
        assert "delta" in harmonize[-1].metadata

    def test_kaizen_selects_action(self):
        result = run_bayesian_dream(
            initial_prior=0.7,
            evidence=[0.8, 0.9],
            max_iterations=1,
        )
        kaizen = [p for p in result.phases if p.phase == "kaizen"]
        assert "selected_action" in kaizen[-1].metadata

    def test_decay_applied(self):
        result = run_bayesian_dream(
            initial_prior=0.8,
            evidence=[0.9],
            max_iterations=1,
            decay_gamma=0.5,
        )
        decay = [p for p in result.phases if p.phase == "decay"]
        assert "gamma" in decay[-1].metadata
        assert decay[-1].metadata["gamma"] == 0.5
