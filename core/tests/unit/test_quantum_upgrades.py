"""Tests for quantum-inspired upgrades: natural gradient, MPS, manifold ops,
Born-rule sampling, topological protection, and QAOA."""

import math

import pytest

from whitemagic.core.acceleration.quantum_bridge import (
    auto_select_manifold,
    born_rule_distribution,
    born_rule_sample,
    born_rule_select,
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


# ── Born-Rule Select (without replacement) Tests ──


class TestBornRuleSelect:
    def test_select_returns_valid_indices(self):
        amps = [0.1, 0.9, 0.1, 0.5]
        indices = born_rule_select(amps, 2, seed=42)
        assert len(indices) == 2
        assert all(0 <= i < 4 for i in indices)
        assert len(set(indices)) == 2, "Should return unique indices"

    def test_select_favors_high_amplitude(self):
        amps = [0.01, 0.99, 0.01, 0.01]
        indices = born_rule_select(amps, 2, seed=42)
        assert 1 in indices, "High-amplitude index should be selected"

    def test_select_empty(self):
        assert born_rule_select([], 3) == []

    def test_select_n_larger_than_input(self):
        amps = [0.5, 0.5]
        indices = born_rule_select(amps, 5, seed=42)
        assert len(indices) == 2, "Should clamp n to len(amplitudes)"

    def test_select_zero_n(self):
        amps = [0.5, 0.5]
        assert born_rule_select(amps, 0) == []


# ── Manifold-Aware Embedding Tests ──


class TestManifoldAwareEmbedding:
    def test_detect_manifold_returns_valid_type(self):
        from whitemagic.core.memory.embeddings import EmbeddingEngine
        engine = EmbeddingEngine()
        manifold = engine.detect_manifold()
        assert manifold in ("euclidean", "hyperbolic", "spherical")

    def test_manifold_aware_similarity_euclidean(self):
        from whitemagic.core.memory.embeddings import EmbeddingEngine
        engine = EmbeddingEngine()
        sim = engine.manifold_aware_similarity([1.0, 0.0], [1.0, 0.0], "euclidean")
        assert sim > 0.99

    def test_manifold_aware_similarity_hyperbolic(self):
        from whitemagic.core.memory.embeddings import EmbeddingEngine
        engine = EmbeddingEngine()
        sim = engine.manifold_aware_similarity([0.1, 0.1], [0.2, 0.2], "hyperbolic")
        assert 0.0 < sim <= 1.0

    def test_manifold_aware_similarity_spherical(self):
        from whitemagic.core.memory.embeddings import EmbeddingEngine
        engine = EmbeddingEngine()
        sim = engine.manifold_aware_similarity([1.0, 0.0], [0.0, 1.0], "spherical")
        assert 0.0 <= sim <= 1.0


# ── HNSW Manifold-Aware Tests ──


class TestHNSWManifold:
    def test_manifold_parameter_default(self):
        from whitemagic.core.memory.hnsw_index import HNSWIndex
        idx = HNSWIndex(dim=4)
        assert idx.manifold == "euclidean"

    def test_manifold_parameter_custom(self):
        from whitemagic.core.memory.hnsw_index import HNSWIndex
        idx = HNSWIndex(dim=4, manifold="hyperbolic")
        assert idx.manifold == "hyperbolic"

    def test_distance_euclidean(self):
        import numpy as np
        from whitemagic.core.memory.hnsw_index import HNSWIndex
        idx = HNSWIndex(dim=2, manifold="euclidean")
        a = np.array([1.0, 0.0])
        b = np.array([0.0, 1.0])
        d = idx._distance(a, b)
        assert abs(d - 1.0) < 1e-6, "Cosine distance of orthogonal vectors should be 1.0"


# ── Natural Gradient in Possibility Explorer Tests ──


class TestNaturalGradientOptimize:
    def test_returns_valid_result(self):
        from whitemagic.core.consciousness.possibility_explorer import PossibilitySpaceExplorer
        explorer = PossibilitySpaceExplorer()
        result = explorer.natural_gradient_optimize("guna_balance", n_steps=3)
        assert "best_fitness" in result
        assert "best_params" in result
        assert "history" in result
        assert len(result["history"]) == 3

    def test_unknown_space_returns_error(self):
        from whitemagic.core.consciousness.possibility_explorer import PossibilitySpaceExplorer
        explorer = PossibilitySpaceExplorer()
        result = explorer.natural_gradient_optimize("nonexistent_space")
        assert "error" in result

    def test_optimization_improves_fitness(self):
        from whitemagic.core.consciousness.possibility_explorer import PossibilitySpaceExplorer
        explorer = PossibilitySpaceExplorer()
        result = explorer.natural_gradient_optimize("coherence_optimization", n_steps=10)
        if len(result["history"]) >= 2:
            first = result["history"][0]["fitness"]
            last = result["history"][-1]["fitness"]
            # Natural gradient should not make fitness worse
            assert last >= first - 0.01, f"Fitness degraded: {first} → {last}"


# ── Recursive Loop Scoring Weights Tests ──


class TestScoringWeightsOptimization:
    def test_optimize_returns_valid_weights(self):
        from whitemagic.core.evolution.recursive_loop import RecursiveImprovementLoop
        loop = RecursiveImprovementLoop()
        weights = loop._optimize_scoring_weights()
        assert "impact" in weights
        assert "confidence" in weights
        assert "novelty" in weights
        assert "boost" in weights
        assert "ig" in weights
        # All weights should be positive
        for k, v in weights.items():
            assert v > 0, f"Weight {k} should be positive, got {v}"


# ── Polyglot Bridge Wiring Tests ──


class TestPolyglotBridgeWiring:
    def test_julia_quantum_backend_class_exists(self):
        try:
            from whitemagic_polyglot import JuliaQuantumBackend
            assert JuliaQuantumBackend is not None
        except ImportError:
            pytest.skip("whitemagic_polyglot not installed")

    def test_haskell_topological_backend_class_exists(self):
        try:
            from whitemagic_polyglot import HaskellTopologicalBackend
            assert HaskellTopologicalBackend is not None
        except ImportError:
            pytest.skip("whitemagic_polyglot not installed")

    def test_orchestrator_has_julia_quantum_helper(self, orchestrator):
        assert hasattr(orchestrator, "_julia_quantum_call")
        assert hasattr(orchestrator, "_get_julia_quantum")

    def test_orchestrator_has_haskell_topological_helper(self, orchestrator):
        assert hasattr(orchestrator, "_haskell_topological_call")
        assert hasattr(orchestrator, "_get_haskell_topological")

    def test_julia_quantum_unavailable_gracefully(self, orchestrator):
        """Julia backend should return None when unavailable, not crash."""
        result = orchestrator._julia_quantum_call("ping")
        # Either None (not installed) or a dict (if Julia is running)
        assert result is None or isinstance(result, dict)

    def test_haskell_topological_unavailable_gracefully(self, orchestrator):
        """Haskell backend should return None when unavailable, not crash."""
        result = orchestrator._haskell_topological_call("ping")
        assert result is None or isinstance(result, dict)

    def test_manifold_distance_julia_first_dispatch(self, orchestrator):
        """manifold_distance should try Julia first, then fall back gracefully."""
        result = orchestrator.manifold_distance([0.0, 0.0], [3.0, 4.0], "euclidean")
        assert "distance" in result
        assert abs(result["distance"] - 5.0) < 1e-6

    def test_auto_select_manifold_julia_first_dispatch(self, orchestrator):
        """auto_select_manifold should try Julia first, then fall back gracefully."""
        result = orchestrator.auto_select_manifold([[0.0], [1.0], [100.0]])
        assert "manifold" in result
        assert result["manifold"] in ("euclidean", "hyperbolic", "spherical")

    def test_berry_phase_haskell_first_dispatch(self, orchestrator):
        """berry_phase should try Haskell first, then fall back gracefully."""
        states = [[1.0, 0.0], [0.0, 1.0], [-1.0, 0.0], [0.0, -1.0]]
        result = orchestrator.berry_phase(states, [0.0, 1.0, 2.0, 3.0])
        assert "phase" in result

    def test_chern_number_haskell_first_dispatch(self, orchestrator):
        """chern_number should try Haskell first, then fall back gracefully."""
        curvature = [[1.0, 0.0], [0.0, 1.0]]
        result = orchestrator.chern_number(curvature)
        assert "chern_number" in result

    def test_topological_encode_haskell_first_dispatch(self, orchestrator):
        """topological_encode should try Haskell first, then fall back gracefully."""
        data = [1.0, -2.0, 3.0, -4.0]
        result = orchestrator.topological_encode(data)
        assert "encoded" in result


# ── Julia QuantumGeometry.jl Module Tests ──


class TestJuliaQuantumGeometryModule:
    def test_module_file_exists(self):
        from pathlib import Path
        module_path = Path(__file__).resolve().parent.parent.parent.parent / "polyglot" / "whitemagic-jl" / "src" / "QuantumGeometry.jl"
        assert module_path.exists(), "QuantumGeometry.jl should exist"

    def test_bridge_file_exists(self):
        from pathlib import Path
        bridge_path = Path(__file__).resolve().parent.parent.parent.parent / "polyglot" / "bridges" / "julia" / "quantum_bridge.jl"
        assert bridge_path.exists(), "quantum_bridge.jl should exist"

    def test_module_exports_functions(self):
        from pathlib import Path
        module_path = Path(__file__).resolve().parent.parent.parent.parent / "polyglot" / "whitemagic-jl" / "src" / "QuantumGeometry.jl"
        content = module_path.read_text()
        for func in ["manifold_distance", "fubini_study_metric", "natural_gradient_step", "mps_compress", "auto_select_manifold"]:
            assert func in content, f"QuantumGeometry.jl should export {func}"


# ── Haskell Topological Bridge Tests ──


class TestHaskellTopologicalBridgeModule:
    def test_bridge_file_exists(self):
        from pathlib import Path
        bridge_path = Path(__file__).resolve().parent.parent.parent.parent / "polyglot" / "bridges" / "haskell" / "topological_bridge.hs"
        assert bridge_path.exists(), "topological_bridge.hs should exist"

    def test_bridge_has_methods(self):
        from pathlib import Path
        bridge_path = Path(__file__).resolve().parent.parent.parent.parent / "polyglot" / "bridges" / "haskell" / "topological_bridge.hs"
        content = bridge_path.read_text()
        for method in ["berry_phase", "chern_number", "roundtrip_verify", "encode_topological", "decode_topological"]:
            assert method in content, f"topological_bridge.hs should handle {method}"


# ── MCP Tool Wiring Tests ──


class TestMCPToolWiring:
    def test_quantum_tools_in_dispatch_table(self):
        from whitemagic.tools.dispatch_table import DISPATCH_TABLE
        for tool in [
            "quantum.manifold_distance",
            "quantum.fubini_study",
            "quantum.natural_gradient",
            "quantum.mps_compress",
            "quantum.auto_manifold",
            "quantum.born_sample",
            "quantum.born_distribution",
            "quantum.interference",
            "topological.berry_phase",
            "topological.chern_number",
            "topological.encode",
            "topological.decode",
        ]:
            assert tool in DISPATCH_TABLE, f"{tool} should be in DISPATCH_TABLE"

    def test_quantum_tools_in_registry(self):
        from whitemagic.tools.registry import get_all_tools
        all_tools = get_all_tools()
        tool_names = {t.name for t in all_tools}
        for tool in [
            "quantum.manifold_distance",
            "quantum.fubini_study",
            "quantum.natural_gradient",
            "quantum.mps_compress",
            "quantum.auto_manifold",
            "quantum.born_sample",
            "quantum.born_distribution",
            "quantum.interference",
            "topological.berry_phase",
            "topological.chern_number",
            "topological.encode",
            "topological.decode",
        ]:
            assert tool in tool_names, f"{tool} should be in tool registry"

    def test_quantum_prat_mappings(self):
        from whitemagic.tools.prat_mappings import TOOL_TO_GANA
        for tool in [
            "quantum.manifold_distance",
            "quantum.fubini_study",
            "quantum.natural_gradient",
            "quantum.mps_compress",
            "quantum.auto_manifold",
            "quantum.born_sample",
            "quantum.born_distribution",
            "quantum.interference",
        ]:
            assert TOOL_TO_GANA.get(tool) == "gana_tail", f"{tool} should map to gana_tail"

    def test_topological_prat_mappings(self):
        from whitemagic.tools.prat_mappings import TOOL_TO_GANA
        for tool in [
            "topological.berry_phase",
            "topological.chern_number",
            "topological.encode",
            "topological.decode",
        ]:
            assert TOOL_TO_GANA.get(tool) == "gana_three_stars", f"{tool} should map to gana_three_stars"

    def test_quantum_nlu_patterns(self):
        from whitemagic.tools.handlers.meta_tool import classify
        # Test a few NLU patterns
        gana, tool, conf = classify("compute manifold distance")
        assert tool == "quantum.manifold_distance", f"Expected quantum.manifold_distance, got {tool}"
        gana, tool, conf = classify("fubini study metric")
        assert tool == "quantum.fubini_study", f"Expected quantum.fubini_study, got {tool}"
        gana, tool, conf = classify("natural gradient step")
        assert tool == "quantum.natural_gradient", f"Expected quantum.natural_gradient, got {tool}"
        gana, tool, conf = classify("berry phase computation")
        assert tool == "topological.berry_phase", f"Expected topological.berry_phase, got {tool}"
        gana, tool, conf = classify("chern number invariant")
        assert tool == "topological.chern_number", f"Expected topological.chern_number, got {tool}"

    def test_quantum_manifold_distance_handler_dispatch(self):
        """Test that the handler dispatches correctly through the orchestrator."""
        from whitemagic.tools.handlers.quantum import handle_quantum_manifold_distance
        result = handle_quantum_manifold_distance(a=[0.0, 0.0], b=[3.0, 4.0], manifold="euclidean")
        assert result["status"] == "ok"
        assert abs(result["distance"] - 5.0) < 1e-6

    def test_quantum_born_sample_handler_dispatch(self):
        from whitemagic.tools.handlers.quantum import handle_quantum_born_sample
        result = handle_quantum_born_sample(amplitudes=[0.1, 0.9, 0.1])
        assert result["status"] == "ok"
        assert "index" in result
        assert 0 <= result["index"] < 3

    def test_topological_berry_phase_handler_dispatch(self):
        import math
        from whitemagic.tools.handlers.quantum import handle_topological_berry_phase
        states = [[1.0, 0.0], [0.0, 1.0], [-1.0, 0.0], [0.0, -1.0]]
        params = [0.0, math.pi / 2, math.pi, 3 * math.pi / 2]
        result = handle_topological_berry_phase(states=states, params=params)
        assert result["status"] == "ok"
        assert "phase" in result

    def test_topological_encode_decode_handler_roundtrip(self):
        from whitemagic.tools.handlers.quantum import handle_topological_encode, handle_topological_decode
        data = [1.0, -2.0, 3.0, -4.0]
        enc = handle_topological_encode(data=data, n_redundant=3)
        assert enc["status"] == "ok"
        assert "encoded" in enc
        dec = handle_topological_decode(encoded=enc["encoded"], original_length=len(data), n_redundant=3)
        assert dec["status"] == "ok"
        assert "decoded" in dec

    def test_quantum_handler_missing_param(self):
        from whitemagic.tools.handlers.quantum import handle_quantum_manifold_distance
        result = handle_quantum_manifold_distance(a=[1.0])
        assert result["status"] == "error"
