"""Tests for GHRR attention research stub — P4."""

from __future__ import annotations

import unittest

import numpy as np

from whitemagic.core.memory.ghrr_attention import (
    GHRRAttention,
    GHRRAttentionConfig,
    get_ghrr_attention,
)


class TestGHRRAttention(unittest.TestCase):
    """Test the GHRR attention research stub."""

    def setUp(self) -> None:
        self.config = GHRRAttentionConfig(dim=64, num_heads=2)
        self.attn = GHRRAttention(self.config)

    def test_config_defaults(self) -> None:
        config = GHRRAttentionConfig()
        self.assertEqual(config.dim, 384)
        self.assertEqual(config.num_heads, 4)
        self.assertEqual(config.head_dim, 96)

    def test_config_head_dim_auto(self) -> None:
        config = GHRRAttentionConfig(dim=128, num_heads=4)
        self.assertEqual(config.head_dim, 32)

    def test_forward_returns_output(self) -> None:
        seq_len = 5
        dim = 64
        rng = np.random.default_rng(42)
        queries = rng.standard_normal((seq_len, dim)).astype(np.float32)
        keys = rng.standard_normal((seq_len, dim)).astype(np.float32)
        values = rng.standard_normal((seq_len, dim)).astype(np.float32)

        result = self.attn.forward(queries, keys, values)

        self.assertIn("output", result)
        self.assertEqual(result["output"].shape, (seq_len, dim))
        self.assertEqual(result["method"], "ghrr_binding_vectorized")
        self.assertEqual(result["num_heads"], 2)

    def test_forward_attention_weights_shape(self) -> None:
        seq_len = 3
        dim = 64
        rng = np.random.default_rng(42)
        queries = rng.standard_normal((seq_len, dim)).astype(np.float32)
        keys = rng.standard_normal((seq_len, dim)).astype(np.float32)
        values = rng.standard_normal((seq_len, dim)).astype(np.float32)

        result = self.attn.forward(queries, keys, values)

        weights = result["attention_weights"]
        self.assertEqual(len(weights), 2)  # num_heads
        for w in weights:
            self.assertEqual(w.shape, (seq_len, seq_len))
            # Each row should sum to ~1.0 (softmax)
            row_sums = w.sum(axis=-1)
            np.testing.assert_allclose(row_sums, 1.0, atol=1e-5)

    def test_forward_with_mask(self) -> None:
        seq_len = 4
        dim = 64
        rng = np.random.default_rng(42)
        queries = rng.standard_normal((seq_len, dim)).astype(np.float32)
        keys = rng.standard_normal((seq_len, dim)).astype(np.float32)
        values = rng.standard_normal((seq_len, dim)).astype(np.float32)

        # Causal mask
        mask = np.tril(np.ones((seq_len, seq_len), dtype=bool))

        result = self.attn.forward(queries, keys, values, mask=mask)

        weights = result["attention_weights"][0]
        # Upper triangle should be ~0
        for i in range(seq_len):
            for j in range(i + 1, seq_len):
                self.assertLess(weights[i, j], 0.01, "Masked positions should have ~0 weight")

    def test_call_alias(self) -> None:
        seq_len = 2
        dim = 64
        rng = np.random.default_rng(42)
        q = rng.standard_normal((seq_len, dim)).astype(np.float32)
        k = rng.standard_normal((seq_len, dim)).astype(np.float32)
        v = rng.standard_normal((seq_len, dim)).astype(np.float32)

        result1 = self.attn(q, k, v)
        result2 = self.attn.forward(q, k, v)
        np.testing.assert_array_equal(result1["output"], result2["output"])

    def test_get_config(self) -> None:
        config = self.attn.get_config()
        self.assertEqual(config["dim"], 64)
        self.assertEqual(config["num_heads"], 2)
        self.assertEqual(config["method"], "ghrr_binding_vectorized")
        self.assertEqual(config["research_status"], "wired_to_inference_router")

    def test_singleton(self) -> None:
        a1 = get_ghrr_attention()
        a2 = get_ghrr_attention()
        self.assertIs(a1, a2)


if __name__ == "__main__":
    unittest.main()
