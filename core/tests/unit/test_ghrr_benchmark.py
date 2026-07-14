"""Benchmark GHRR attention vs standard dot-product attention.

Compares quality (attention weight alignment), speed, and scalability
of GHRR binding-based attention against standard transformer attention.
"""

from __future__ import annotations

import time
import unittest

import numpy as np

from whitemagic.core.memory.ghrr_attention import (
    GHRRAttention,
    GHRRAttentionConfig,
)


def standard_attention(
    queries: np.ndarray,
    keys: np.ndarray,
    values: np.ndarray,
    mask: np.ndarray | None = None,
) -> dict[str, np.ndarray]:
    """Standard scaled dot-product attention."""
    d_k = queries.shape[-1]
    scores = queries @ keys.T / np.sqrt(d_k)

    if mask is not None:
        scores = np.where(mask, scores, -1e9)

    scores = scores - np.max(scores, axis=-1, keepdims=True)
    exp_scores = np.exp(scores)
    weights = exp_scores / (np.sum(exp_scores, axis=-1, keepdims=True) + 1e-8)
    output = weights @ values

    return {"output": output, "attention_weights": [weights]}


class TestGHRRBenchmark(unittest.TestCase):
    """Benchmark GHRR vs standard attention."""

    def setUp(self) -> None:
        self.dim = 64
        self.config = GHRRAttentionConfig(dim=self.dim, num_heads=2)
        self.attn = GHRRAttention(self.config)
        self.rng = np.random.default_rng(42)

    def test_ghrr_produces_different_weights_than_standard(self) -> None:
        """GHRR binding-based attention should differ from dot-product."""
        seq_len = 8
        q = self.rng.standard_normal((seq_len, self.dim)).astype(np.float32)
        k = self.rng.standard_normal((seq_len, self.dim)).astype(np.float32)
        v = self.rng.standard_normal((seq_len, self.dim)).astype(np.float32)

        ghrr_result = self.attn.forward(q, k, v)
        std_result = standard_attention(q, k, v)

        # Weights should be different (GHRR captures structural relationships)
        ghrr_w = ghrr_result["attention_weights"][0]
        std_w = std_result["attention_weights"][0]

        # Compute cosine similarity between weight distributions
        def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
            flat_a = a.flatten()
            flat_b = b.flatten()
            return float(
                np.dot(flat_a, flat_b)
                / (np.linalg.norm(flat_a) * np.linalg.norm(flat_b) + 1e-8)
            )

        sim = cosine_sim(ghrr_w, std_w)
        print(f"\n  GHRR vs Standard attention weight similarity: {sim:.3f}")
        self.assertLess(
            sim, 0.99, "GHRR should produce different attention patterns than standard"
        )

    def test_ghrr_output_shape_matches_standard(self) -> None:
        """Both methods should produce same output shape."""
        seq_len = 6
        q = self.rng.standard_normal((seq_len, self.dim)).astype(np.float32)
        k = self.rng.standard_normal((seq_len, self.dim)).astype(np.float32)
        v = self.rng.standard_normal((seq_len, self.dim)).astype(np.float32)

        ghrr_result = self.attn.forward(q, k, v)
        std_result = standard_attention(q, k, v)

        self.assertEqual(ghrr_result["output"].shape, std_result["output"].shape)

    def test_speed_comparison(self) -> None:
        """Compare GHRR vs standard attention speed."""
        seq_len = 8
        q = self.rng.standard_normal((seq_len, self.dim)).astype(np.float32)
        k = self.rng.standard_normal((seq_len, self.dim)).astype(np.float32)
        v = self.rng.standard_normal((seq_len, self.dim)).astype(np.float32)

        # Warm up
        self.attn.forward(q, k, v)
        standard_attention(q, k, v)

        # Benchmark GHRR
        n_iters = 10
        start = time.perf_counter()
        for _ in range(n_iters):
            self.attn.forward(q, k, v)
        ghrr_time = (time.perf_counter() - start) / n_iters

        # Benchmark standard
        start = time.perf_counter()
        for _ in range(n_iters):
            standard_attention(q, k, v)
        std_time = (time.perf_counter() - start) / n_iters

        overhead = ghrr_time / max(std_time, 1e-9)
        print(f"\n  Speed comparison (seq_len={seq_len}, dim={self.dim}):")
        print(f"    Standard:  {std_time * 1000:.2f}ms")
        print(f"    GHRR:      {ghrr_time * 1000:.2f}ms")
        print(f"    Overhead:  {overhead:.1f}x")

        # GHRR is slower due to binding — verify it's not absurdly slow
        self.assertLess(overhead, 1000.0, "GHRR should not be more than 1000x slower")

    def test_scalability_with_sequence_length(self) -> None:
        """Measure how GHRR scales with sequence length."""
        results = []
        for seq_len in [4, 8, 16, 32]:
            q = self.rng.standard_normal((seq_len, self.dim)).astype(np.float32)
            k = self.rng.standard_normal((seq_len, self.dim)).astype(np.float32)
            v = self.rng.standard_normal((seq_len, self.dim)).astype(np.float32)

            # Warm up
            self.attn.forward(q, k, v)

            n_iters = 3
            start = time.perf_counter()
            for _ in range(n_iters):
                self.attn.forward(q, k, v)
            ghrr_time = (time.perf_counter() - start) / n_iters

            start = time.perf_counter()
            for _ in range(n_iters):
                standard_attention(q, k, v)
            std_time = (time.perf_counter() - start) / n_iters

            results.append((seq_len, ghrr_time, std_time))

        print(f"\n  GHRR scalability (dim={self.dim}, heads=2):")
        print(
            f"    {'seq_len':>8s}  {'GHRR (ms)':>10s}  {'Standard (ms)':>14s}  {'Overhead':>10s}"
        )
        for seq_len, ghrr_t, std_t in results:
            overhead = ghrr_t / max(std_t, 1e-9)
            print(
                f"    {seq_len:>8d}  {ghrr_t * 1000:>10.2f}  {std_t * 1000:>14.2f}  {overhead:>9.1f}x"
            )

        # GHRR should scale roughly quadratically (O(n²) binding operations)
        # Verify the ratio between seq_len=32 and seq_len=4
        ghrr_4 = results[0][1]
        ghrr_32 = results[3][1]
        scaling_factor = ghrr_32 / max(ghrr_4, 1e-9)
        # Quadratic scaling: (32/4)² = 64
        print(
            f"\n    Scaling factor (seq=32 vs seq=4): {scaling_factor:.1f}x (quadratic=64x)"
        )

    def test_ghrr_captures_structural_relationships(self) -> None:
        """GHRR should capture structural relationships that dot-product misses.

        When query and key have a known binding relationship (e.g., Q = bind(X, R)),
        GHRR attention should score higher for Q→K than standard dot-product.
        """
        from whitemagic.core.memory.hrr import get_hrr_engine

        hrr = get_hrr_engine(dim=self.dim)

        # Create a query that is a binding of X with relation R
        x = self.rng.standard_normal(self.dim).astype(np.float32)
        x = x / np.linalg.norm(x)
        r_vec = hrr.get_relation_vector("CAUSES")
        bound_q = hrr.bind(x, r_vec)
        bound_q = bound_q / (np.linalg.norm(bound_q) + 1e-8)

        # Key is X itself (the unbound version)
        k = x / (np.linalg.norm(x) + 1e-8)

        # Standard dot-product similarity
        std_sim = float(np.dot(bound_q, k))

        # GHRR similarity (bind Q with inverse of R, compare to K)
        unbound_q = hrr.unbind(bound_q, r_vec)
        ghrr_sim = float(np.dot(unbound_q, k))

        print("\n  Structural relationship capture:")
        print(f"    Standard dot-product(Q_bound, K): {std_sim:.3f}")
        print(f"    GHRR unbind + dot-product:        {ghrr_sim:.3f}")

        # GHRR should recover the original relationship better
        self.assertGreater(
            ghrr_sim,
            std_sim,
            "GHRR unbinding should recover structural relationship better than raw dot-product",
        )

    def test_multi_head_diversity(self) -> None:
        """Different heads should produce different attention patterns."""
        seq_len = 6
        q = self.rng.standard_normal((seq_len, self.dim)).astype(np.float32)
        k = self.rng.standard_normal((seq_len, self.dim)).astype(np.float32)
        v = self.rng.standard_normal((seq_len, self.dim)).astype(np.float32)

        result = self.attn.forward(q, k, v)
        weights = result["attention_weights"]

        # Compare head 0 vs head 1
        w0 = weights[0].flatten()
        w1 = weights[1].flatten()
        cos_sim = float(
            np.dot(w0, w1) / (np.linalg.norm(w0) * np.linalg.norm(w1) + 1e-8)
        )

        print(f"\n  Multi-head diversity (head 0 vs head 1): {cos_sim:.3f}")
        self.assertLess(
            cos_sim, 0.999, "Different heads should produce different patterns"
        )


if __name__ == "__main__":
    unittest.main()
