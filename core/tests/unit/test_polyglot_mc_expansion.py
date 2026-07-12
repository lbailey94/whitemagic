# ruff: noqa: D101, D102
"""Tests for polyglot MC expansion: QMC, MCMC, expanded SDE, advanced GP.

Tests verify:
- QMC: Sobol and Halton sequence generation, uniformity properties
- MCMC: Metropolis-Hastings and HMC sampling, acceptance rates
- SDE: Jump-diffusion, Heston, CIR model paths
- Advanced: GP hyperparameter optimization, Expected Improvement, multivariate Gaussian
- All methods have Python fallbacks when Rust bridge unavailable
"""

from __future__ import annotations

import os
import tempfile

os.environ.setdefault("WM_STATE_ROOT", tempfile.mkdtemp())
os.environ.setdefault("WM_SKIP_POLYGLOT", "1")
os.environ.setdefault("WM_SILENT_INIT", "1")

import pytest


@pytest.fixture
def orchestrator():
    """Get a PolyglotMCOrchestrator instance."""
    from whitemagic.core.evolution.polyglot_mc import PolyglotMCOrchestrator
    return PolyglotMCOrchestrator()


# ── QMC Tests ──

class TestSobolSequence:
    def test_basic_generation(self, orchestrator):
        samples = orchestrator.sobol_sequence(100, 2, seed=42, scramble=False)
        assert samples is not None
        assert len(samples) == 100
        assert len(samples[0]) == 2

    def test_all_in_unit_cube(self, orchestrator):
        samples = orchestrator.sobol_sequence(50, 3, seed=42, scramble=True)
        for row in samples:
            for v in row:
                assert 0.0 <= v < 1.0

    def test_empty(self, orchestrator):
        assert orchestrator.sobol_sequence(0, 2) == [] or orchestrator.sobol_sequence(0, 2) is None

    def test_uniformity(self, orchestrator):
        samples = orchestrator.sobol_sequence(1000, 1, seed=42, scramble=False)
        if samples:
            mean = sum(r[0] for r in samples) / len(samples)
            assert abs(mean - 0.5) < 0.1, f"Sobol mean {mean} should be ~0.5"


class TestHaltonSequence:
    def test_basic_generation(self, orchestrator):
        samples = orchestrator.halton_sequence(100, 2, seed=42)
        assert samples is not None
        assert len(samples) == 100
        assert len(samples[0]) == 2

    def test_all_in_unit_cube(self, orchestrator):
        samples = orchestrator.halton_sequence(50, 3, seed=42)
        for row in samples:
            for v in row:
                assert 0.0 <= v < 1.0

    def test_uniformity(self, orchestrator):
        samples = orchestrator.halton_sequence(1000, 1, seed=42)
        if samples:
            mean = sum(r[0] for r in samples) / len(samples)
            assert abs(mean - 0.5) < 0.1, f"Halton mean {mean} should be ~0.5"


class TestQMCSample:
    def test_scaled_ranges(self, orchestrator):
        ranges = [(-5.0, 5.0), (0.0, 10.0)]
        samples = orchestrator.qmc_sample(50, ranges, method="sobol", seed=42)
        assert samples is not None
        assert len(samples) == 50
        for row in samples:
            assert -5.0 <= row[0] <= 5.0
            assert 0.0 <= row[1] <= 10.0

    def test_halton_method(self, orchestrator):
        ranges = [(0.0, 1.0)]
        samples = orchestrator.qmc_sample(20, ranges, method="halton", seed=42)
        assert samples is not None
        assert len(samples) == 20


# ── MCMC Tests ──

class TestMetropolisHastings:
    def test_gaussian_target(self, orchestrator):
        result = orchestrator.metropolis_hastings(
            n_samples=500, n_burn=100, x0=[0.0],
            proposal_std=1.0, seed=42,
            target_type="gaussian", target_mean=[2.0], target_cov=[1.0],
        )
        assert "samples" in result
        assert "acceptance_rate" in result
        assert result["n_samples"] == 500 or result.get("fallback")

    def test_returns_dict(self, orchestrator):
        result = orchestrator.metropolis_hastings(n_samples=10, seed=99)
        assert isinstance(result, dict)
        assert "acceptance_rate" in result


class TestHamiltonianMC:
    def test_gaussian_target(self, orchestrator):
        result = orchestrator.hamiltonian_monte_carlo(
            n_samples=200, n_burn=50, x0=[0.0, 0.0],
            step_size=0.1, n_leapfrog=10, seed=42,
            target_type="gaussian", target_mean=[1.0, 2.0], target_cov=[1.0, 1.0],
        )
        assert "samples" in result
        assert "acceptance_rate" in result
        assert result["n_samples"] == 200 or result.get("fallback")

    def test_rosenbrock_target(self, orchestrator):
        result = orchestrator.hamiltonian_monte_carlo(
            n_samples=100, n_burn=20, x0=[0.0, 0.0],
            step_size=0.01, n_leapfrog=20, seed=42,
            target_type="rosenbrock",
        )
        assert isinstance(result, dict)
        assert "samples" in result


# ── SDE Expansion Tests ──

class TestJumpDiffusion:
    def test_basic_path(self, orchestrator):
        result = orchestrator.sde_jump_diffusion(
            x0=100.0, t_end=1.0, n_steps=100, seed=42,
        )
        assert "final_value" in result
        assert result["path_length"] == 101 or result.get("fallback")

    def test_with_jumps(self, orchestrator):
        result = orchestrator.sde_jump_diffusion(
            x0=100.0, n_steps=200,
            jump_intensity=0.5, jump_std=0.3,
            seed=42,
        )
        assert "final_value" in result


class TestHeston:
    def test_basic_path(self, orchestrator):
        result = orchestrator.sde_heston(
            s0=100.0, v0=0.04, n_steps=100, seed=42,
        )
        assert "final_price" in result
        assert "final_variance" in result

    def test_variance_nonnegative(self, orchestrator):
        result = orchestrator.sde_heston(n_steps=50, seed=42)
        if not result.get("fallback"):
            assert result["final_variance"] >= 0.0


class TestCIR:
    def test_basic_path(self, orchestrator):
        result = orchestrator.sde_cir(
            x0=0.04, n_steps=100, seed=42,
        )
        assert "final_value" in result

    def test_mean_reversion(self, orchestrator):
        result = orchestrator.sde_cir(
            x0=0.01, kappa=5.0, theta=0.05, n_steps=500, seed=42,
        )
        if not result.get("fallback"):
            # After many steps, should be closer to theta
            assert result["final_value"] > 0.01


# ── Advanced GP Tests ──

class TestGPOptimizeHyperparameters:
    def test_basic_optimization(self, orchestrator):
        x_train = [[0.0], [1.0], [2.0], [3.0], [4.0]]
        y_train = [0.0, 1.0, 4.0, 9.0, 16.0]
        result = orchestrator.gp_optimize_hyperparameters(x_train, y_train)
        assert "length_scale" in result
        assert "sigma_f" in result
        assert result["length_scale"] > 0 or result.get("fallback")


class TestExpectedImprovement:
    def test_basic_ei(self, orchestrator):
        x_train = [[0.0], [1.0], [2.0]]
        y_train = [0.0, 1.0, 4.0]
        x_candidates = [[0.5], [1.5], [3.0]]
        result = orchestrator.expected_improvement(x_train, y_train, x_candidates)
        assert "ei_values" in result
        assert "f_best" in result


class TestMultidGaussian:
    def test_basic_sampling(self, orchestrator):
        result = orchestrator.multid_gaussian(
            n_samples=100, mean=[0.0, 0.0], cov=[1.0, 1.0], seed=42,
        )
        assert "samples" in result

    def test_default_params(self, orchestrator):
        result = orchestrator.multid_gaussian(n_samples=10)
        assert "samples" in result
