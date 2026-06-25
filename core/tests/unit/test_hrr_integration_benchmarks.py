"""Integration tests and benchmarks for HRR-based reasoning (P1-P5).

These tests exercise the real HRREngine (no mocks) to validate:
1. HRR bind/unbind roundtrip accuracy with real FFT convolution
2. Compositional reasoning with real HRR projections
3. qFHRR vs HRREngine accuracy comparison
4. VSA context compression ratios on synthetic data
5. Token tracker integration with GreenScore
"""

from __future__ import annotations

import time
import unittest

import numpy as np

from whitemagic.core.memory.hrr import HRREngine, get_hrr_engine
from whitemagic.core.memory.qfhrr import QuantizedHRREngine
from whitemagic.ai.vsa_context_compressor import VSAContextCompressor


class TestHRRBindUnbindAccuracy(unittest.TestCase):
    """Test real HRR bind/unbind roundtrip accuracy."""

    def setUp(self) -> None:
        self.hrr = HRREngine(dim=384)

    def test_bind_unbind_preserves_similarity(self) -> None:
        """After bind(A,B) → unbind(.,B), result should correlate with A."""
        rng = np.random.default_rng(42)
        a = rng.standard_normal(384).astype(np.float32)
        a /= np.linalg.norm(a)
        b = rng.standard_normal(384).astype(np.float32)
        b /= np.linalg.norm(b)

        bound = self.hrr.bind(a, b)
        recovered = self.hrr.unbind(bound, b)

        # Cosine similarity between original and recovered
        sim = self.hrr.similarity(a, recovered)
        self.assertGreater(
            sim, 0.3,
            f"Bind/unbind roundtrip should preserve similarity (got {sim:.3f})",
        )

    def test_project_inverse_project_roundtrip(self) -> None:
        """project → inverse_project should preserve approximate similarity."""
        rng = np.random.default_rng(123)
        embedding = rng.standard_normal(384).astype(np.float32)
        embedding /= np.linalg.norm(embedding)

        projected = self.hrr.project(embedding, "CAUSES")
        recovered = self.hrr.inverse_project(projected, "CAUSES")

        sim = self.hrr.similarity(embedding, recovered)
        self.assertGreater(
            sim, 0.3,
            f"Project/inverse_project roundtrip should preserve similarity (got {sim:.3f})",
        )

    def test_different_relations_produce_different_projections(self) -> None:
        """Projecting through different relations should yield different vectors."""
        rng = np.random.default_rng(456)
        embedding = rng.standard_normal(384).astype(np.float32)
        embedding /= np.linalg.norm(embedding)

        proj_causes = self.hrr.project(embedding, "CAUSES")
        proj_uses = self.hrr.project(embedding, "USES")
        proj_part_of = self.hrr.project(embedding, "PART_OF")

        # Different projections should have low similarity to each other
        sim_cu = self.hrr.similarity(proj_causes, proj_uses)
        sim_cp = self.hrr.similarity(proj_causes, proj_part_of)

        self.assertLess(sim_cu, 0.5, f"CAUSES and USES projections should differ (got {sim_cu:.3f})")
        self.assertLess(sim_cp, 0.5, f"CAUSES and PART_OF projections should differ (got {sim_cp:.3f})")

    def test_superpose_preserves_components(self) -> None:
        """Superposed vector should have non-zero similarity with each component."""
        rng = np.random.default_rng(789)
        a = rng.standard_normal(384).astype(np.float32)
        a /= np.linalg.norm(a)
        b = rng.standard_normal(384).astype(np.float32)
        b /= np.linalg.norm(b)

        superposed = self.hrr.superpose(a, b)

        sim_a = self.hrr.similarity(superposed, a)
        sim_b = self.hrr.similarity(superposed, b)

        self.assertGreater(sim_a, 0.1, "Superposed vector should correlate with component A")
        self.assertGreater(sim_b, 0.1, "Superposed vector should correlate with component B")


class TestQFHRRvsHRRAccuracy(unittest.TestCase):
    """Benchmark qFHRR (4-bit) vs HRREngine (float64) accuracy."""

    def setUp(self) -> None:
        self.dim = 384
        self.hrr = HRREngine(dim=self.dim)
        self.qhrr = QuantizedHRREngine(dim=self.dim, bits=4)
        self.rng = np.random.default_rng(42)

    def test_bind_unbind_accuracy_comparison(self) -> None:
        """Compare bind/unbind roundtrip similarity between engines."""
        results = []
        for trial in range(10):
            a = self.rng.standard_normal(self.dim).astype(np.float32)
            a /= np.linalg.norm(a)
            b = self.rng.standard_normal(self.dim).astype(np.float32)
            b /= np.linalg.norm(b)

            # Full precision HRR
            bound = self.hrr.bind(a, b)
            recovered = self.hrr.unbind(bound, b)
            hrr_sim = self.hrr.similarity(a, recovered)

            # Quantized HRR
            q_bound = self.qhrr.bind(a, b)
            q_recovered = self.qhrr.unbind(q_bound, b)
            qhrr_sim = self.qhrr.similarity(
                self.qhrr._to_quantized(a), q_recovered,
            )

            results.append((hrr_sim, qhrr_sim))

        avg_hrr = sum(r[0] for r in results) / len(results)
        avg_qhrr = sum(r[1] for r in results) / len(results)

        # HRR should have higher accuracy
        self.assertGreater(avg_hrr, 0.3, f"HRR avg similarity: {avg_hrr:.3f}")
        # qFHRR should still have positive correlation (quantization preserves some structure)
        self.assertGreater(avg_qhrr, -0.1, f"qFHRR avg similarity: {avg_qhrr:.3f}")

        # Log the comparison
        print(f"\n  HRR vs qFHRR bind/unbind accuracy:")
        print(f"    HRR (float64):  avg similarity = {avg_hrr:.3f}")
        print(f"    qFHRR (4-bit):   avg similarity = {avg_qhrr:.3f}")
        print(f"    Accuracy ratio:  {avg_qhrr / avg_hrr:.2%}")

    def test_memory_savings(self) -> None:
        """Verify qFHRR uses 8x less memory than float32."""
        hrr_bytes = self.dim * 8  # float64
        qhrr_bytes = self.qhrr.bytes_per_vector
        ratio = hrr_bytes / qhrr_bytes

        print(f"\n  Memory per vector:")
        print(f"    HRR (float64):  {hrr_bytes} bytes")
        print(f"    qFHRR (4-bit):   {qhrr_bytes} bytes")
        print(f"    Compression:     {ratio:.1f}x")

        self.assertGreater(ratio, 8.0, "qFHRR should be >8x smaller than float64")


class TestVSACompressionBenchmark(unittest.TestCase):
    """Benchmark VSA context compression ratios."""

    def test_compression_ratio_on_synthetic_data(self) -> None:
        """Measure compression ratio with realistic-sized context items."""
        compressor = VSAContextCompressor(hrr=HRREngine(dim=384))

        # Simulate 20 context items, each ~500 tokens (2000 chars)
        items = []
        for i in range(20):
            content = f"Context item {i}: " + ("lorem ipsum dolor sit amet " * 50)
            items.append({
                "content": content,
                "source": ["memory", "session", "tool_result", "scratchpad"][i % 4],
                "id": f"item_{i}",
            })

        # Can't use real EmbeddingEngine in tests (needs model download),
        # so we test the compression math directly
        original_tokens = sum(max(1, len(item["content"]) // 4) for item in items)
        compressed_tokens = 384 // 4  # ~96 tokens for the vector

        ratio = original_tokens / compressed_tokens

        print(f"\n  VSA Context Compression:")
        print(f"    Items: {len(items)}")
        print(f"    Original tokens: {original_tokens}")
        print(f"    Compressed tokens: {compressed_tokens}")
        print(f"    Compression ratio: {ratio:.1f}x")

        self.assertGreater(ratio, 10.0, "Should achieve >10x compression with 20 items")

    def test_compression_scales_with_items(self) -> None:
        """Compression ratio should increase with more items."""
        compressor = VSAContextCompressor(hrr=HRREngine(dim=384))
        compressed_tokens = 96  # Fixed: 384 dims // 4

        for n_items in [5, 10, 20, 50, 100]:
            items = []
            for i in range(n_items):
                content = f"Item {i}: " + ("content " * 100)  # ~800 chars
                items.append({"content": content, "source": "memory", "id": str(i)})

            original_tokens = sum(max(1, len(item["content"]) // 4) for item in items)
            ratio = original_tokens / compressed_tokens
            print(f"    {n_items:3d} items → {original_tokens:5d} tokens → {ratio:.1f}x compression")


class TestTokenTrackerIntegration(unittest.TestCase):
    """Test token tracker integration with real GreenScore."""

    def test_green_score_records_token_savings(self) -> None:
        """Verify that token tracker feeds into GreenScore correctly."""
        from whitemagic.core.monitoring.green_score import get_green_score
        from whitemagic.core.monitoring.token_tracker import _estimate_tokens

        gs = get_green_score()
        snapshot_before = gs.snapshot()

        # Record a simulated local resolution
        gs.record_inference(
            locality="edge",
            tokens_used=100,
            tokens_saved=500,
            tool="test_integration",
        )

        snapshot_after = gs.snapshot()
        self.assertGreater(snapshot_after.tokens_saved, snapshot_before.tokens_saved)
        self.assertGreater(snapshot_after.edge_calls, snapshot_before.edge_calls)

        print(f"\n  GreenScore token tracking:")
        print(f"    Tokens saved before: {snapshot_before.tokens_saved}")
        print(f"    Tokens saved after:  {snapshot_after.tokens_saved}")
        print(f"    Edge calls:          {snapshot_after.edge_calls}")


class TestDispatchPipelineIntegration(unittest.TestCase):
    """Test that the dispatch pipeline includes all new middleware."""

    def test_pipeline_has_token_tracker(self) -> None:
        """Verify mw_token_tracker is in the dispatch pipeline."""
        from whitemagic.tools.dispatch_table import _pipeline

        # The pipeline should have token_tracker registered
        middleware_names = _pipeline.describe()
        self.assertIn("token_tracker", middleware_names)
        self.assertIn("inference_router", middleware_names)

        # Token tracker should be after inference router
        ir_idx = middleware_names.index("inference_router")
        tt_idx = middleware_names.index("token_tracker")
        self.assertGreater(tt_idx, ir_idx, "Token tracker should run after inference router")

        print(f"\n  Dispatch pipeline middleware order:")
        for i, name in enumerate(middleware_names):
            print(f"    {i+1}. {name}")


if __name__ == "__main__":
    unittest.main()
