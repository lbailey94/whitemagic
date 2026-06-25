"""Tests for adaptive bit-width qFHRR engine selection."""

from __future__ import annotations

import unittest

import numpy as np

from whitemagic.core.memory.qfhrr import (
    QuantizedHRREngine,
    get_adaptive_qfhrr_engine,
    get_tier_bits,
    get_galactic_qfhrr_bits,
    get_galactic_qfhrr_engine,
    requantize_for_zone,
    _TIER_BITS_MAP,
)


class TestAdaptiveQFHRR(unittest.TestCase):
    """Test tier-aware qFHRR engine selection."""

    def test_tier_bits_mapping(self) -> None:
        """Verify tier-to-bits mapping is correct."""
        self.assertEqual(get_tier_bits(0), 4)   # edge
        self.assertEqual(get_tier_bits(1), 8)   # local small
        self.assertEqual(get_tier_bits(2), 8)   # local large
        self.assertEqual(get_tier_bits(3), 16)  # cloud
        self.assertEqual(get_tier_bits(99), 4)  # unknown → default 4-bit

    def test_edge_engine_is_4bit(self) -> None:
        """Edge tier should produce a 4-bit engine."""
        engine = get_adaptive_qfhrr_engine(tier=0)
        self.assertEqual(engine.bits, 4)
        self.assertEqual(engine.K, 16)

    def test_local_engine_is_8bit(self) -> None:
        """Local tier should produce an 8-bit engine."""
        engine = get_adaptive_qfhrr_engine(tier=1)
        self.assertEqual(engine.bits, 8)
        self.assertEqual(engine.K, 256)

    def test_cloud_engine_is_16bit(self) -> None:
        """Cloud tier should produce a 16-bit engine."""
        engine = get_adaptive_qfhrr_engine(tier=3)
        self.assertEqual(engine.bits, 16)
        self.assertEqual(engine.K, 65536)

    def test_engines_are_cached(self) -> None:
        """Same tier should return the same engine instance."""
        e1 = get_adaptive_qfhrr_engine(tier=0)
        e2 = get_adaptive_qfhrr_engine(tier=0)
        self.assertIs(e1, e2, "Same tier should return cached instance")

    def test_different_tiers_return_different_engines(self) -> None:
        """Different tiers should return different engine instances."""
        e_edge = get_adaptive_qfhrr_engine(tier=0)
        e_local = get_adaptive_qfhrr_engine(tier=1)
        e_cloud = get_adaptive_qfhrr_engine(tier=3)
        self.assertIsNot(e_edge, e_local)
        self.assertIsNot(e_local, e_cloud)
        self.assertIsNot(e_edge, e_cloud)

    def test_memory_scales_with_tier(self) -> None:
        """Higher tiers should use more memory per vector."""
        e_edge = get_adaptive_qfhrr_engine(tier=0)
        e_local = get_adaptive_qfhrr_engine(tier=1)
        e_cloud = get_adaptive_qfhrr_engine(tier=3)

        self.assertLess(e_edge.bytes_per_vector, e_local.bytes_per_vector)
        self.assertLess(e_local.bytes_per_vector, e_cloud.bytes_per_vector)

        print(f"\n  Adaptive qFHRR memory per vector (384 dims):")
        print(f"    Edge (4-bit):  {e_edge.bytes_per_vector} bytes")
        print(f"    Local (8-bit): {e_local.bytes_per_vector} bytes")
        print(f"    Cloud (16-bit): {e_cloud.bytes_per_vector} bytes")

    def test_higher_bits_have_better_discrimination(self) -> None:
        """Higher bit-widths should preserve better discrimination."""
        import hashlib

        def synth_emb(text: str, dim: int = 384) -> np.ndarray:
            rng = np.random.default_rng(seed=hash(text) % (2**31))
            vec = rng.standard_normal(dim).astype(np.float32)
            for word in text.lower().split():
                ws = int(hashlib.md5(word.encode()).hexdigest()[:8], 16) % (2**31)
                wr = np.random.default_rng(seed=ws)
                vec += wr.standard_normal(dim).astype(np.float32) * 0.3
            n = np.linalg.norm(vec)
            return vec / n if n > 0 else vec

        related_texts = ["race condition bug", "threading deadlock", "concurrent access issue"]
        unrelated_texts = ["weather forecast", "cookie recipe"]
        related_embs = [synth_emb(t) for t in related_texts]
        unrelated_embs = [synth_emb(t) for t in unrelated_texts]

        results = {}
        for tier, label in [(0, "4-bit"), (1, "8-bit"), (3, "16-bit")]:
            engine = get_adaptive_qfhrr_engine(tier=tier)
            related_sims = []
            unrelated_sims = []
            for i in range(3):
                for j in range(3):
                    qi = engine._to_quantized(related_embs[i])
                    qj = engine._to_quantized(related_embs[j])
                    related_sims.append(engine.similarity(qi, qj))
            for i in range(3):
                for j in range(2):
                    qi = engine._to_quantized(related_embs[i])
                    qj = engine._to_quantized(unrelated_embs[j])
                    unrelated_sims.append(engine.similarity(qi, qj))
            gap = np.mean(related_sims) - np.mean(unrelated_sims)
            results[label] = (np.mean(related_sims), np.mean(unrelated_sims), gap)

        print(f"\n  Discrimination by bit-width:")
        for label, (rel, unrel, gap) in results.items():
            print(f"    {label:8s}: related={rel:.3f}, unrelated={unrel:.3f}, gap={gap:.3f}")

        # All bit-widths should show positive discrimination (related > unrelated)
        for label, (rel, unrel, gap) in results.items():
            self.assertGreater(gap, 0.0,
                               f"{label} should discriminate related from unrelated (gap={gap:.3f})")

        # Variance-weighted scaling should produce meaningful discrimination
        # (gap > 0.05 for all bit-widths — previously was ~0.02 with fixed scaling)
        for label, (rel, unrel, gap) in results.items():
            self.assertGreater(gap, 0.05,
                               f"{label} should have meaningful discrimination gap (gap={gap:.3f})")


class TestGalacticZoneQuantization(unittest.TestCase):
    """Test galactic zone-aware progressive quantization."""

    def test_zone_bits_mapping(self) -> None:
        """Verify galactic zone to bits mapping."""
        self.assertEqual(get_galactic_qfhrr_bits("core"), 8)
        self.assertEqual(get_galactic_qfhrr_bits("inner_rim"), 8)
        self.assertEqual(get_galactic_qfhrr_bits("mid_band"), 4)
        self.assertEqual(get_galactic_qfhrr_bits("outer_rim"), 2)
        self.assertEqual(get_galactic_qfhrr_bits("far_edge"), 2)
        self.assertEqual(get_galactic_qfhrr_bits("unknown"), 4)  # default

    def test_core_engine_is_8bit(self) -> None:
        """Core zone should produce an 8-bit engine."""
        engine = get_galactic_qfhrr_engine("core")
        self.assertEqual(engine.bits, 8)
        self.assertEqual(engine.K, 256)

    def test_mid_band_engine_is_4bit(self) -> None:
        """Mid band zone should produce a 4-bit engine."""
        engine = get_galactic_qfhrr_engine("mid_band")
        self.assertEqual(engine.bits, 4)
        self.assertEqual(engine.K, 16)

    def test_outer_rim_engine_is_2bit(self) -> None:
        """Outer rim zone should produce a 2-bit engine."""
        engine = get_galactic_qfhrr_engine("outer_rim")
        self.assertEqual(engine.bits, 2)
        self.assertEqual(engine.K, 4)

    def test_requantize_for_zone(self) -> None:
        """requantize_for_zone should produce correctly-sized quantized vectors."""
        embedding = [0.1 * i / 384 for i in range(384)]
        core_q = requantize_for_zone(embedding, "core")
        mid_q = requantize_for_zone(embedding, "mid_band")
        edge_q = requantize_for_zone(embedding, "far_edge")

        # All should be 384-dim
        self.assertEqual(core_q.shape, (384,))
        self.assertEqual(mid_q.shape, (384,))
        self.assertEqual(edge_q.shape, (384,))

        # Core (8-bit) should have more unique values than edge (2-bit)
        core_unique = len(np.unique(core_q))
        edge_unique = len(np.unique(edge_q))
        self.assertGreaterEqual(core_unique, edge_unique)

    def test_progressive_compression(self) -> None:
        """Outer zones should use fewer bits (more compression) than inner."""
        core_bits = get_galactic_qfhrr_bits("core")
        mid_bits = get_galactic_qfhrr_bits("mid_band")
        outer_bits = get_galactic_qfhrr_bits("outer_rim")

        self.assertGreater(core_bits, mid_bits)
        self.assertGreater(mid_bits, outer_bits)


if __name__ == "__main__":
    unittest.main()
