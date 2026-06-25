"""Tests for VSA + GraphWalker walk context compression."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from whitemagic.core.memory.graph_walker import GraphWalker


class TestVSAWalkContextCompression(unittest.TestCase):
    """Test VSA compression of graph walk results."""

    def setUp(self) -> None:
        self.walker = GraphWalker()

    def _make_results(self, n: int = 10) -> list[dict]:
        """Generate synthetic walk results."""
        results = []
        for i in range(n):
            results.append({
                "memory_id": f"mem_{i}",
                "title": f"Memory {i}",
                "content": f"This is memory item {i} about topic {i % 3}. "
                           f"It contains relevant information about concept {i}.",
                "importance": 0.5 + i * 0.05,
                "source": "anchor" if i < 3 else "graph_walk",
                "rrf_score": 0.9 - i * 0.05,
                "walk_paths": [],
            })
        return results

    def test_compress_empty_results(self) -> None:
        """Empty results should return empty compression."""
        result = self.walker.compress_walk_context([], query="test")
        self.assertEqual(result["summary"], "")
        self.assertEqual(result["original_count"], 0)
        self.assertEqual(result["compression_ratio"], 1.0)

    @patch("whitemagic.ai.vsa_context_compressor.get_vsa_context_compressor")
    def test_compress_with_vsa(self, mock_get_compressor: MagicMock) -> None:
        """VSA compression should produce compact summary."""
        from whitemagic.ai.vsa_context_compressor import VSACompressedContext

        mock_compressor = MagicMock()
        mock_result = VSACompressedContext(
            vector=[0.1] * 384,
            summary="[VSA Compressed: 10 items → 1 vector]\n- [anchor] Memory 0: This is memory item 0\n- [graph_walk] Memory 3: This is memory item 3",
            item_count=10,
            original_tokens=500,
            compressed_tokens=30,
            compression_ratio=16.7,
            method="hrr_superposition",
        )
        mock_compressor.compress.return_value = mock_result
        mock_get_compressor.return_value = mock_compressor

        results = self._make_results(10)
        result = self.walker.compress_walk_context(results, query="topic 0")

        self.assertEqual(result["original_count"], 10)
        self.assertEqual(result["method"], "hrr_superposition")
        self.assertGreater(result["compression_ratio"], 1.0)
        self.assertIn("VSA Compressed", result["summary"])

    @patch("whitemagic.ai.vsa_context_compressor.get_vsa_context_compressor")
    def test_compress_fallback_when_vsa_unavailable(self, mock_get_compressor: MagicMock) -> None:
        """Should fall back to truncation when VSA unavailable."""
        mock_get_compressor.side_effect = ImportError("no VSA")

        results = self._make_results(10)
        result = self.walker.compress_walk_context(results, query="test", max_text_items=3)

        self.assertEqual(result["method"], "truncation_fallback")
        self.assertEqual(result["original_count"], 10)
        self.assertGreater(result["compression_ratio"], 1.0)
        self.assertIsNone(result["vector"])

    @patch("whitemagic.ai.vsa_context_compressor.get_vsa_context_compressor")
    def test_compression_ratio_scales_with_result_count(self, mock_get_compressor: MagicMock) -> None:
        """More results should yield higher compression ratios."""
        from whitemagic.ai.vsa_context_compressor import VSACompressedContext

        def make_mock_result(items_count, summary_text):
            return VSACompressedContext(
                vector=[0.1] * 384,
                summary=summary_text,
                item_count=items_count,
                original_tokens=items_count * 50,
                compressed_tokens=30,
                compression_ratio=items_count * 50 / 30,
                method="hrr_superposition",
            )

        mock_compressor = MagicMock()
        mock_compressor.compress.side_effect = lambda items, **kw: make_mock_result(
            len(items), "[VSA Compressed summary]",
        )
        mock_get_compressor.return_value = mock_compressor

        small = self.walker.compress_walk_context(self._make_results(5), query="test")
        large = self.walker.compress_walk_context(self._make_results(50), query="test")

        print(f"\n  Compression ratio: 5 items={small['compression_ratio']}x, 50 items={large['compression_ratio']}x")
        self.assertGreater(large["compression_ratio"], small["compression_ratio"])

    @patch.object(GraphWalker, "hybrid_recall")
    @patch("whitemagic.ai.vsa_context_compressor.get_vsa_context_compressor")
    def test_hybrid_recall_compressed(self, mock_get_compressor: MagicMock, mock_recall: MagicMock) -> None:
        """hybrid_recall_compressed should return both results and compressed summary."""
        from whitemagic.ai.vsa_context_compressor import VSACompressedContext

        mock_recall.return_value = self._make_results(8)

        mock_compressor = MagicMock()
        mock_result = VSACompressedContext(
            vector=[0.1] * 384,
            summary="[VSA Compressed: 8 items → 1 vector]\n- Top items listed here",
            item_count=8,
            original_tokens=400,
            compressed_tokens=25,
            compression_ratio=16.0,
            method="hrr_superposition",
        )
        mock_compressor.compress.return_value = mock_result
        mock_get_compressor.return_value = mock_compressor

        result = self.walker.hybrid_recall_compressed("test query", hops=2)

        self.assertIn("results", result)
        self.assertIn("compressed", result)
        self.assertEqual(len(result["results"]), 8)
        self.assertEqual(result["compressed"]["original_count"], 8)
        self.assertGreater(result["compressed"]["compression_ratio"], 1.0)


if __name__ == "__main__":
    unittest.main()
