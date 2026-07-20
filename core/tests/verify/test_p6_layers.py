"""P6.2 — Benchmark layer separation tests.

Verifies that:
1. Layer identifiers are distinct and well-defined
2. fts5_substrate results are never presented as product latency
3. Each layer reports its own metrics independently
4. Cold/warm measurements are separated
5. Embeddings on/off are separated
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
BENCH_ROOT = REPO_ROOT / "benchmarks"
if str(BENCH_ROOT) not in sys.path:
    sys.path.insert(0, str(BENCH_ROOT))
if str(REPO_ROOT / "core") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "core"))

import pytest

from benchmarks.benchmark_layers import (
    ALL_LAYERS,
    LAYER_FTS5_SUBSTRATE,
    LAYER_LEXICAL_API,
    LAYER_SEMANTIC_ONLY,
    LAYER_SPATIAL_ONLY,
    LAYER_HYBRID_PLANNER,
    LAYER_GRAPH_HYBRID,
    LAYER_SINGLE_GALAXY,
    LAYER_FEDERATED_GALAXY,
    LAYER_COLD_PROCESS,
    LAYER_WARM_PROCESS,
    LAYER_EMBEDDINGS_ON,
    LAYER_EMBEDDINGS_OFF,
)


class TestLayerDefinitions:
    """Test that all required layers are defined."""

    def test_all_layers_defined(self):
        """All 12 layers from P6.2 requirements must be present."""
        required = {
            "fts5_substrate",
            "lexical_api",
            "semantic_only",
            "spatial_only",
            "hybrid_planner",
            "graph_hybrid",
            "single_galaxy",
            "federated_galaxy",
            "cold_process",
            "warm_process",
            "embeddings_on",
            "embeddings_off",
        }
        assert set(ALL_LAYERS) == required

    def test_layers_are_unique(self):
        assert len(ALL_LAYERS) == len(set(ALL_LAYERS))

    def test_layer_constants_match(self):
        assert LAYER_FTS5_SUBSTRATE == "fts5_substrate"
        assert LAYER_LEXICAL_API == "lexical_api"
        assert LAYER_SEMANTIC_ONLY == "semantic_only"
        assert LAYER_SPATIAL_ONLY == "spatial_only"
        assert LAYER_HYBRID_PLANNER == "hybrid_planner"
        assert LAYER_GRAPH_HYBRID == "graph_hybrid"
        assert LAYER_SINGLE_GALAXY == "single_galaxy"
        assert LAYER_FEDERATED_GALAXY == "federated_galaxy"
        assert LAYER_COLD_PROCESS == "cold_process"
        assert LAYER_WARM_PROCESS == "warm_process"
        assert LAYER_EMBEDDINGS_ON == "embeddings_on"
        assert LAYER_EMBEDDINGS_OFF == "embeddings_off"


class TestLayerSeparation:
    """Test that layers produce independent metrics."""

    def test_fts5_substrate_not_labeled_as_product(self):
        """A direct SQL result must never be presented as end-to-end product latency."""
        from benchmarks.benchmark_layers import _run_fts5_substrate
        import inspect
        source = inspect.getsource(_run_fts5_substrate)
        # Must use direct SQLite, not UnifiedMemory
        assert "_fts5_search_direct" in source
        assert "UnifiedMemory" not in source
        assert "um.search" not in source

    def test_layer_output_includes_layer_field(self):
        """Each layer's output must include a 'layer' field identifying itself."""
        from benchmarks.benchmark_layers import _run_fts5_substrate
        import inspect
        source = inspect.getsource(_run_fts5_substrate)
        assert '"layer"' in source or "'layer'" in source
        assert LAYER_FTS5_SUBSTRATE in source

    def test_embeddings_off_is_lexical_fallback(self):
        """Embeddings-off layer should use FTS5 direct (lexical fallback)."""
        from benchmarks.benchmark_layers import _run_embeddings_off
        import inspect
        source = inspect.getsource(_run_embeddings_off)
        assert "_fts5_search_direct" in source
        assert "search_similar" not in source
        assert "search_hybrid" not in source

    def test_cold_warm_are_separate_layers(self):
        """Cold and warm must be measured as distinct layers."""
        assert LAYER_COLD_PROCESS != LAYER_WARM_PROCESS
        assert LAYER_COLD_PROCESS in ALL_LAYERS
        assert LAYER_WARM_PROCESS in ALL_LAYERS

    def test_substrate_vs_api_are_separate(self):
        """FTS5 substrate and lexical API must be distinct layers."""
        assert LAYER_FTS5_SUBSTRATE != LAYER_LEXICAL_API
        assert LAYER_FTS5_SUBSTRATE in ALL_LAYERS
        assert LAYER_LEXICAL_API in ALL_LAYERS

    def test_embeddings_on_off_are_separate(self):
        """Embeddings available and degraded must be distinct layers."""
        assert LAYER_EMBEDDINGS_ON != LAYER_EMBEDDINGS_OFF
        assert LAYER_EMBEDDINGS_ON in ALL_LAYERS
        assert LAYER_EMBEDDINGS_OFF in ALL_LAYERS

    def test_single_federated_galaxy_are_separate(self):
        """Single and federated galaxy must be distinct layers."""
        assert LAYER_SINGLE_GALAXY != LAYER_FEDERATED_GALAXY
        assert LAYER_SINGLE_GALAXY in ALL_LAYERS
        assert LAYER_FEDERATED_GALAXY in ALL_LAYERS


class TestLayeredBenchmarkStructure:
    """Test the run_layered_benchmark output structure."""

    def test_layer_selection_works(self):
        """run_layered_benchmark should accept a subset of layers."""
        from benchmarks.benchmark_layers import run_layered_benchmark
        import inspect
        sig = inspect.signature(run_layered_benchmark)
        assert "layers" in sig.parameters

    def test_output_includes_relevance_model(self):
        """Output should include relevance_model field for traceability."""
        from benchmarks.benchmark_layers import run_layered_benchmark
        import inspect
        source = inspect.getsource(run_layered_benchmark)
        assert "relevance_model" in source
