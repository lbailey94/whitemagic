"""Tests for quantized HRR (qFHRR) — P3."""

from __future__ import annotations

import unittest

import numpy as np

from whitemagic.core.memory.qfhrr import (
    QuantizedHRREngine,
    get_quantized_hrr_engine,
)


class TestQuantizedHRREngine(unittest.TestCase):
    """Test the integer-only quantized HRR engine."""

    def setUp(self) -> None:
        self.engine = QuantizedHRREngine(dim=64, bits=4)  # Small dim for speed

    def test_initialization(self) -> None:
        self.assertEqual(self.engine.dim, 64)
        self.assertEqual(self.engine.bits, 4)
        self.assertEqual(self.engine.K, 16)

    def test_bytes_per_vector(self) -> None:
        # 64 dims × 4 bits = 256 bits = 32 bytes
        self.assertEqual(self.engine.bytes_per_vector, 32)

    def test_compression_vs_float32(self) -> None:
        stats = self.engine.get_stats()
        # float32: 64 × 4 = 256 bytes
        # qFHRR: 32 bytes
        # ratio = 8x
        self.assertEqual(stats["compression_vs_float32"], 8.0)

    def test_quantize_and_dequantize(self) -> None:
        """Test that quantization preserves approximate values."""
        original = np.random.default_rng(42).standard_normal(64).astype(np.float32)
        original /= np.linalg.norm(original)  # Normalize to [-1, 1] range

        quantized = self.engine._to_quantized(original)
        recovered = self.engine._to_float(quantized)

        # Should be approximately correlated
        corr = np.corrcoef(original, recovered)[0, 1]
        self.assertGreater(corr, 0.5, "Quantization should preserve correlation")

    def test_bind_unbind_roundtrip(self) -> None:
        """Test that bind → unbind approximately recovers the original."""
        rng = np.random.default_rng(42)
        a = rng.standard_normal(64).astype(np.float32)
        a /= np.linalg.norm(a)
        b = rng.standard_normal(64).astype(np.float32)
        b /= np.linalg.norm(b)

        bound = self.engine.bind(a, b)
        recovered = self.engine.unbind(bound, b)

        # Convert back to float for comparison
        a_float = self.engine._to_float(self.engine._to_quantized(a))
        recovered_float = self.engine._to_float(recovered)

        # Should be positively correlated (not perfect due to quantization)
        corr = np.corrcoef(a_float, recovered_float)[0, 1]
        self.assertGreater(
            corr, 0.0, "Unbind should recover a correlated version of original"
        )

    def test_bind_is_modular_addition(self) -> None:
        """Verify binding uses modular arithmetic."""
        a = np.array([1, 5, 10, 15], dtype=np.uint8)
        b = np.array([2, 3, 8, 5], dtype=np.uint8)

        # Need to use a 4-dim engine for this test
        engine = QuantizedHRREngine(dim=4, bits=4)
        result = engine.bind(a, b)

        expected = (a.astype(np.int16) + b.astype(np.int16)) % 16
        np.testing.assert_array_equal(result, expected.astype(np.uint8))

    def test_unbind_is_modular_subtraction(self) -> None:
        """Verify unbinding uses modular subtraction."""
        bound = np.array([3, 8, 2, 4], dtype=np.uint8)
        b = np.array([2, 3, 8, 5], dtype=np.uint8)

        engine = QuantizedHRREngine(dim=4, bits=4)
        result = engine.unbind(bound, b)

        expected = (bound.astype(np.int16) - b.astype(np.int16)) % 16
        np.testing.assert_array_equal(result, expected.astype(np.uint8))

    def test_similarity_uses_lut(self) -> None:
        """Test similarity computation via lookup table."""
        a = np.zeros(64, dtype=np.uint8)  # All phase 0
        b = np.zeros(64, dtype=np.uint8)  # All phase 0

        sim = self.engine.similarity(a, b)
        # Same vectors should have similarity ~1.0
        self.assertGreater(sim, 0.99)

        # Maximum distance (K/2 apart) should be orthogonal (~0.0)
        c = np.full(64, 8, dtype=np.uint8)  # Level 8 = maximum distance from 0 for K=16
        sim_opposite = self.engine.similarity(a, c)
        self.assertLessEqual(
            sim_opposite, 0.01, "Maximum-distance levels should be orthogonal (~0.0)"
        )

    def test_relation_vectors_exist(self) -> None:
        """Test that canonical relation vectors are initialized."""
        for rel in ["CAUSES", "FOLLOWS", "PART_OF", "AGENT", "ACTION", "OBJECT"]:
            vec = self.engine.get_relation_vector(rel)
            self.assertEqual(vec.shape, (64,))
            self.assertTrue(np.all(vec < 16))

    def test_project_inverse_project(self) -> None:
        """Test project and inverse_project with relation vectors."""
        rng = np.random.default_rng(42)
        embedding = rng.standard_normal(64).astype(np.float32)
        embedding /= np.linalg.norm(embedding)

        projected = self.engine.project(embedding, "CAUSES")
        recovered = self.engine.inverse_project(projected, "CAUSES")

        # Should be approximately correlated with original
        orig_float = self.engine._to_float(self.engine._to_quantized(embedding))
        recovered_float = self.engine._to_float(recovered)
        corr = np.corrcoef(orig_float, recovered_float)[0, 1]
        self.assertGreater(
            corr, -0.1, "Project/inverse_project should not be anti-correlated"
        )

    def test_superpose(self) -> None:
        """Test superposition of multiple vectors."""
        a = np.zeros(64, dtype=np.uint8)
        b = np.full(64, 4, dtype=np.uint8)

        result = self.engine.superpose(a, b)

        # Circular mean of phase 0 and phase 4 (K=16) should be phase 2
        expected_phase = 2
        self.assertEqual(result[0], expected_phase)

    def test_get_stats(self) -> None:
        stats = self.engine.get_stats()
        self.assertIn("dim", stats)
        self.assertIn("bits", stats)
        self.assertIn("K", stats)
        self.assertIn("bytes_per_vector", stats)
        self.assertIn("compression_vs_float32", stats)
        self.assertGreater(stats["compression_vs_float32"], 1.0)


class TestQuantizedHRRSingleton(unittest.TestCase):
    """Test singleton accessor."""

    def test_get_singleton(self) -> None:
        e1 = get_quantized_hrr_engine(dim=64, bits=4)
        e2 = get_quantized_hrr_engine(dim=64, bits=4)
        self.assertIs(e1, e2)


if __name__ == "__main__":
    unittest.main()
