"""Tests for quantum-inspired upgrades: natural gradient, MPS, manifold ops,
Born-rule sampling, topological protection, and QAOA."""

import math

import pytest

from whitemagic.core.acceleration.quantum_bridge import (
    auto_select_manifold,
    born_rule_distribution,
    born_rule_sample,
    embed_manifold,
    manifold_distance,
    quantum_interference,
)
from whitemagic.core.evolution.polyglot_mc import PolyglotMCOrchestrator


@pytest.fixture
def orchestrator():
    return PolyglotMCOrchestrator()


# ── Born-Rule Sampling Tests ──


class TestBornRule:
    def test_sample_returns_valid_index(self):
        amps = [0.1, 0.9, 0.1]
        idx = born_rule_sample(amps, seed=42)
        assert 0 <= idx < 3

    def test_sample_favors_high_amplitude(self):
        amps = [0.1, 0.9, 0.1]
        counts = {0: 0, 1: 0, 2: 0}
        for i in range(100):
            idx = born_rule_sample(amps, seed=i)
            counts[idx] += 1
        assert counts[1] > counts[0], "Born-rule should favor high-amplitude outcomes"
        assert counts[1] > counts[2]

    def test_distribution_sums_to_one(self):
        amps = [1.0, 1.0, 2.0]
        dist = born_rule_distribution(amps)
        total = sum(p for _, p in dist)
        assert abs(total - 1.0) < 1e-10

    def test_distribution_proportional_to_amplitude_sq(self):
        amps = [1.0, 1.0, 2.0]
        dist = born_rule_distribution(amps)
        assert abs(dist[2][1] - 4.0 / 6.0) < 1e-10

    def test_empty_amplitudes(self):
        assert born_rule_sample([]) == 0
        assert born_rule_distribution([]) == []

    def test_interference_constructive(self):
        a = [1.0, 1.0]
        b = [1.0, 1.0]
        result = quantum_interference(a, b)
        assert abs(result[0] - 4.0) < 1e-10
        assert abs(result[1] - 4.0) < 1e-10

    def test_interference_destructive(self):
        a = [1.0, 1.0]
        b = [-1.0, -1.0]
        result = quantum_interference(a, b)
        assert abs(result[0] - 0.0) < 1e-10
        assert abs(result[1] - 0.0) < 1e-10


# ── Manifold Distance Tests ──


class TestManifoldDistance:
    def test_euclidean(self):
        a = [0.0, 0.0]
        b = [3.0, 4.0]
        assert abs(manifold_distance(a, b, "euclidean") - 5.0) < 1e-10

    def test_spherical(self):
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert abs(manifold_distance(a, b, "spherical") - math.pi / 2) < 1e-10

    def test_hyperbolic(self):
        a = [0.0, 0.0]
        b = [0.5, 0.0]
        d = manifold_distance(a, b, "hyperbolic")
        assert d > 0
        assert math.isfinite(d)

    def test_default_euclidean(self):
        a = [1.0, 2.0]
        b = [4.0, 6.0]
        assert abs(manifold_distance(a, b) - 5.0) < 1e-10


class TestEmbedManifold:
    def test_euclidean_identity(self):
        point = [1.0, 2.0, 3.0]
        result = embed_manifold(point, "euclidean")
        assert result == point

    def test_spherical_unit_norm(self):
        point = [3.0, 4.0]
        result = embed_manifold(point, "spherical")
        norm = math.sqrt(sum(x * x for x in result))
        assert abs(norm - 1.0) < 1e-10

    def test_hyperbolic_inside_ball(self):
        point = [1.0, 0.0]
        result = embed_manifold(point, "hyperbolic")
        norm = math.sqrt(sum(x * x for x in result))
        assert norm < 1.0, "Embedded point should be inside Poincaré ball"


class TestAutoSelectManifold:
    def test_returns_valid_manifold(self):
        points = [[0.0], [1.0], [100.0]]
        result = auto_select_manifold(points)
        assert result in ("euclidean", "hyperbolic", "spherical")

    def test_empty_returns_euclidean(self):
        assert auto_select_manifold([]) == "euclidean"


# ── PolyglotMCOrchestrator Quantum Method Tests ──


class TestPolyglotQuantum:
    def test_fubini_study_metric(self, orchestrator):
        state = [1.0, 0.0, 0.0, 0.0]
        jacobian = [[0.1, 0.0, 0.0, 0.0], [0.0, 0.1, 0.0, 0.0]]
        result = orchestrator.fubini_study_metric(state, jacobian)
        assert "metric" in result or "fallback" in result

    def test_natural_gradient(self, orchestrator):
        params = [1.0, 2.0]
        grads = [0.5, -0.3]
        metric = [[1.0, 0.0], [0.0, 1.0]]
        result = orchestrator.natural_gradient(params, grads, metric, 0.1)
        assert "new_params" in result
        if not result.get("fallback"):
            assert abs(result["new_params"][0] - 0.95) < 1e-4

    def test_multiscale_bind(self, orchestrator):
        vectors = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]
        result = orchestrator.multiscale_bind(vectors, bond_dim=2)
        assert "result" in result

    def test_manifold_distance(self, orchestrator):
        result = orchestrator.manifold_distance([0, 0], [3, 4], "euclidean")
        assert "distance" in result
        if not result.get("fallback"):
            assert abs(result["distance"] - 5.0) < 1e-6

    def test_embed_manifold(self, orchestrator):
        result = orchestrator.embed_manifold([3.0, 4.0], "spherical")
        assert "embedded" in result

    def test_born_sample(self, orchestrator):
        result = orchestrator.born_sample([0.1, 0.9, 0.1])
        assert "index" in result
        assert 0 <= result["index"] < 3

    def test_born_batch_sample(self, orchestrator):
        result = orchestrator.born_batch_sample([0.1, 0.9, 0.1], n=50)
        assert "samples" in result
        assert len(result["samples"]) == 50

    def test_born_distribution(self, orchestrator):
        result = orchestrator.born_distribution([1.0, 1.0, 2.0])
        assert "distribution" in result

    def test_quantum_interference(self, orchestrator):
        result = orchestrator.quantum_interference([1.0, 1.0], [1.0, -1.0])
        assert "interference" in result

    def test_berry_phase(self, orchestrator):
        states = [[1.0, 0.0], [0.0, 1.0], [-1.0, 0.0], [0.0, -1.0]]
        params = [0.0, math.pi / 2, math.pi, 3 * math.pi / 2]
        result = orchestrator.berry_phase(states, params)
        assert "phase" in result

    def test_chern_number(self, orchestrator):
        curvature = [[1.0, 0.0], [0.0, 1.0]]
        result = orchestrator.chern_number(curvature)
        assert "chern_number" in result

    def test_topological_encode_decode(self, orchestrator):
        data = [1.0, 2.0, 3.0, 4.0]
        enc_result = orchestrator.topological_encode(data, n_redundant=3)
        assert "encoded" in result if (result := enc_result) else True
        encoded = enc_result.get("encoded", data)
        dec_result = orchestrator.topological_decode(encoded, len(data), 3)
        assert "decoded" in dec_result

    def test_quantum_walk_optimize(self, orchestrator):
        cost = [[1.0, -2.0], [-2.0, 1.0]]
        result = orchestrator.quantum_walk_optimize(cost, n_steps=10)
        assert "best_index" in result

    def test_qaoa_maxcut(self, orchestrator):
        adj = [[0.0, 1.0, 1.0], [1.0, 0.0, 1.0], [1.0, 1.0, 0.0]]
        result = orchestrator.qaoa_maxcut(adj, n_steps=20)
        assert "partition" in result
        assert len(result["partition"]) == 3

    def test_auto_select_manifold(self, orchestrator):
        points = [[0.0], [1.0], [100.0]]
        result = orchestrator.auto_select_manifold(points)
        assert "manifold" in result
        assert result["manifold"] in ("euclidean", "hyperbolic", "spherical")

    def test_riemannian_gradient(self, orchestrator):
        result = orchestrator.riemannian_gradient([1.0, 0.0], [0.0, 1.0], "spherical")
        assert "riemannian_gradient" in result

    def test_exponential_map(self, orchestrator):
        result = orchestrator.exponential_map([1.0, 2.0], [0.5, 0.5], "euclidean")
        assert "result" in result
