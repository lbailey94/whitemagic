"""Tests for Batch 7: Edge & Performance modules."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

os.environ.setdefault("WM_STATE_ROOT", str(Path(tempfile.mkdtemp())))


class TestRustEmbeddingsBridge:
    """Test Rust embeddings bridge."""

    def test_cosine_similarity(self):
        from whitemagic.performance.rust_embeddings import RustEmbeddingsBridge
        bridge = RustEmbeddingsBridge()
        score = bridge.cosine_similarity([1, 0, 0], [1, 0, 0])
        assert abs(score - 1.0) < 0.01

    def test_cosine_similarity_orthogonal(self):
        from whitemagic.performance.rust_embeddings import RustEmbeddingsBridge
        bridge = RustEmbeddingsBridge()
        score = bridge.cosine_similarity([1, 0], [0, 1])
        assert abs(score) < 0.01

    def test_batch_similarity(self):
        from whitemagic.performance.rust_embeddings import RustEmbeddingsBridge
        bridge = RustEmbeddingsBridge()
        results = bridge.batch_similarity([1, 0], [[1, 0], [0, 1]])
        assert len(results) == 2
        assert results[0] > results[1]

    def test_benchmark(self):
        from whitemagic.performance.rust_embeddings import RustEmbeddingsBridge
        bridge = RustEmbeddingsBridge()
        result = bridge.benchmark(n=10)
        assert result["iterations"] == 10


class TestBridgeCoordinator:
    """Test bridge coordinator."""

    def test_status(self):
        from whitemagic.performance.bridge_coordinator import BridgeCoordinator
        coord = BridgeCoordinator()
        status = coord.status()
        assert "rust_embeddings" in status

    def test_summary(self):
        from whitemagic.performance.bridge_coordinator import BridgeCoordinator
        coord = BridgeCoordinator()
        summary = coord.summary()
        assert "total_bridges" in summary
        assert "available" in summary


class TestLocalEmbeddings:
    """Test local embeddings."""

    def test_add_and_search(self):
        from whitemagic.edge.embeddings import LocalEmbeddings
        emb = LocalEmbeddings()
        emb.add("1", "hello world from white magic")
        emb.add("2", "cooking recipes for pasta")
        results = emb.search("hello world")
        assert len(results) > 0
        assert results[0]["id"] == "1"

    def test_jaccard(self):
        from whitemagic.edge.embeddings import LocalEmbeddings
        emb = LocalEmbeddings()
        score = emb.jaccard_similarity("hello world", "hello there world")
        assert score > 0

    def test_summary(self):
        from whitemagic.edge.embeddings import LocalEmbeddings
        emb = LocalEmbeddings()
        emb.add("1", "test")
        summary = emb.summary()
        assert summary["total_documents"] == 1


class TestFederatedLearning:
    """Test federated learning."""

    def test_register_node(self, tmp_path):
        from whitemagic.edge.federated import FederatedLearning
        fed = FederatedLearning(data_dir=tmp_path)
        fed.register_node("node1", ["search", "embed"])
        assert "node1" in fed.nodes

    def test_share_pattern(self, tmp_path):
        from whitemagic.edge.federated import FederatedLearning
        fed = FederatedLearning(data_dir=tmp_path)
        fed.register_node("node1")
        fed.share_pattern("node1", {"type": "insight", "content": "test"})
        assert len(fed.shared_patterns) == 1

    def test_aggregate(self, tmp_path):
        from whitemagic.edge.federated import FederatedLearning
        fed = FederatedLearning(data_dir=tmp_path)
        fed.register_node("node1")
        fed.register_node("node2")
        fed.share_pattern("node1", {"type": "insight"})
        fed.share_pattern("node2", {"type": "insight"})
        agg = fed.aggregate_patterns()
        assert len(agg) >= 1


class TestSelfImprovingCascade:
    """Test self-improving cascade."""

    def test_self_critique_good(self, tmp_path):
        from whitemagic.edge.self_improving import SelfImprovingCascade
        cascade = SelfImprovingCascade(data_dir=tmp_path)
        critique = cascade.self_critique("This is a well-formed output with sufficient length.")
        assert critique["can_improve"] is False

    def test_self_critique_short(self, tmp_path):
        from whitemagic.edge.self_improving import SelfImprovingCascade
        cascade = SelfImprovingCascade(data_dir=tmp_path)
        critique = cascade.self_critique("short")
        assert critique["can_improve"] is True

    def test_improve(self, tmp_path):
        from whitemagic.edge.self_improving import SelfImprovingCascade
        cascade = SelfImprovingCascade(data_dir=tmp_path)
        result = cascade.improve("short output with TODO")
        assert "improved" in result
        assert "TODO" not in result["improved"]


class TestEdgeExporter:
    """Test edge exporter."""

    def test_export_json(self, tmp_path):
        from whitemagic.edge.export import EdgeExporter
        exporter = EdgeExporter(export_dir=tmp_path)
        path = exporter.export_json({"key": "value"}, "test")
        assert path.exists()
        assert path.suffix == ".json"

    def test_export_javascript(self, tmp_path):
        from whitemagic.edge.export import EdgeExporter
        exporter = EdgeExporter(export_dir=tmp_path)
        path = exporter.export_javascript_module({"key": "value"}, "testModule")
        assert path.exists()
        assert path.suffix == ".js"
        content = path.read_text()
        assert "testModule" in content

    def test_list_exports(self, tmp_path):
        from whitemagic.edge.export import EdgeExporter
        exporter = EdgeExporter(export_dir=tmp_path)
        exporter.export_json({"a": 1}, "file1")
        exporter.export_json({"b": 2}, "file2")
        exports = exporter.list_exports()
        assert len(exports) == 2


class TestEdgePerformanceBenchmark:
    """Test edge performance benchmark."""

    def test_benchmark_cache(self):
        from whitemagic.benchmarks.edge_performance import EdgePerformanceBenchmark
        bench = EdgePerformanceBenchmark()
        result = bench.benchmark_cache(n=10)
        assert result["iterations"] == 10
        assert "avg_read_ms" in result

    def test_summary(self):
        from whitemagic.benchmarks.edge_performance import EdgePerformanceBenchmark
        bench = EdgePerformanceBenchmark()
        bench.benchmark_cache(n=5)
        summary = bench.summary()
        assert summary["total_benchmarks"] >= 1


class TestRustBenchmark:
    """Test Rust benchmark."""

    def test_benchmark_cosine(self):
        from whitemagic.benchmarks.rust_performance import RustBenchmark
        bench = RustBenchmark()
        result = bench.benchmark_cosine_similarity(n=10, dim=16)
        assert result["iterations"] == 10

    def test_summary(self):
        from whitemagic.benchmarks.rust_performance import RustBenchmark
        bench = RustBenchmark()
        bench.benchmark_cosine_similarity(n=5, dim=8)
        summary = bench.summary()
        assert summary["total_benchmarks"] >= 1


class TestPerformanceDashboard:
    """Test performance dashboard."""

    def test_record_and_trend(self, tmp_path):
        from whitemagic.benchmarks.performance_dashboard import PerformanceDashboard
        dash = PerformanceDashboard(data_dir=tmp_path)
        dash.record_metric("latency", 5.2, "ms")
        dash.record_metric("latency", 4.8, "ms")
        trend = dash.get_trend("latency")
        assert len(trend) == 2

    def test_latest(self, tmp_path):
        from whitemagic.benchmarks.performance_dashboard import PerformanceDashboard
        dash = PerformanceDashboard(data_dir=tmp_path)
        dash.record_metric("latency", 5.2)
        dash.record_metric("throughput", 100)
        latest = dash.latest()
        assert "latency" in latest
        assert "throughput" in latest

    def test_summary(self, tmp_path):
        from whitemagic.benchmarks.performance_dashboard import PerformanceDashboard
        dash = PerformanceDashboard(data_dir=tmp_path)
        dash.record_metric("a", 1)
        summary = dash.summary()
        assert summary["total_metrics"] == 1


class TestParallelMemoryOps:
    """Test parallel memory operations."""

    def test_parallel_search(self):
        from whitemagic.parallel.memory_ops import ParallelMemoryManager
        mgr = ParallelMemoryManager(max_workers=2)

        def search_fn(query: str) -> list[dict]:
            return [{"query": query, "result": "found"}]

        results = mgr.parallel_search(["a", "b", "c"], search_fn)
        assert len(results) == 3
        mgr.shutdown()

    def test_benchmark_search(self):
        from whitemagic.parallel.memory_ops import ParallelMemoryManager
        mgr = ParallelMemoryManager(max_workers=2)

        def search_fn(query: str) -> list[dict]:
            return [{"q": query}]

        result = mgr.benchmark_search(["a", "b", "c"], search_fn)
        assert "speedup" in result
        assert result["query_count"] == 3
        mgr.shutdown()

    def test_summary(self):
        from whitemagic.parallel.memory_ops import ParallelMemoryManager
        mgr = ParallelMemoryManager(max_workers=4)
        summary = mgr.summary()
        assert summary["max_workers"] == 4
        mgr.shutdown()
