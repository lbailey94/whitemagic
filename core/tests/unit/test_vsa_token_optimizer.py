"""Tests for VSA-integrated TokenOptimizer."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from whitemagic.core.intelligence.agentic.token_optimizer import TokenOptimizer


class TestVSAIntegration(unittest.TestCase):
    """Test VSA compression integration in TokenOptimizer."""

    def test_small_context_uses_truncation(self) -> None:
        """Small contexts should use truncation, not VSA."""
        opt = TokenOptimizer()
        # Small context — should not trigger VSA
        query = "test query"
        context = "This is a small context that fits in the budget."

        q, ctx, saved = opt.optimize_query(query, context)

        # Should not have VSA header
        self.assertNotIn("[VSA Compressed", ctx)

    @patch("whitemagic.ai.vsa_context_compressor.get_vsa_context_compressor")
    def test_large_context_uses_vsa(self, mock_get_compressor: MagicMock) -> None:
        """Large contexts should trigger VSA compression."""
        # Mock the VSA compressor
        mock_compressor = MagicMock()
        from whitemagic.ai.vsa_context_compressor import VSACompressedContext

        mock_result = VSACompressedContext(
            vector=[0.1] * 384,
            summary="[VSA Compressed: 5 items → 1 vector]\n- [context] relevant chunk 1\n- [context] relevant chunk 2",
            item_count=5,
            original_tokens=2000,
            compressed_tokens=50,
            compression_ratio=40.0,
            method="hrr_superposition",
        )
        mock_compressor.compress.return_value = mock_result
        mock_get_compressor.return_value = mock_compressor

        opt = TokenOptimizer()
        # Large context > 2000 chars
        large_context = "This is a test paragraph. " * 200  # ~5000 chars

        q, ctx, saved = opt.optimize_query("test query", large_context)

        # Should have VSA header in compressed context
        self.assertIn("[VSA Compressed", ctx)
        self.assertGreater(saved, 0)
        mock_compressor.compress.assert_called_once()

    @patch("whitemagic.ai.vsa_context_compressor.get_vsa_context_compressor")
    def test_vsa_falls_back_on_failure(self, mock_get_compressor: MagicMock) -> None:
        """If VSA fails, should fall back to truncation."""
        mock_compressor = MagicMock()
        mock_compressor.compress.side_effect = RuntimeError("HRR engine not available")
        mock_get_compressor.return_value = mock_compressor

        opt = TokenOptimizer()
        large_context = "This is a test. " * 300  # ~4500 chars

        q, ctx, saved = opt.optimize_query("test", large_context)

        # Should have fallen back to truncation (no VSA header)
        self.assertNotIn("[VSA Compressed", ctx)
        # Should still have some context
        self.assertGreater(len(ctx), 0)

    @patch("whitemagic.ai.vsa_context_compressor.get_vsa_context_compressor")
    def test_vsa_preserves_relevant_content(self, mock_get_compressor: MagicMock) -> None:
        """VSA summary should preserve content relevant to the query."""
        from whitemagic.ai.vsa_context_compressor import VSACompressedContext

        mock_compressor = MagicMock()
        mock_result = VSACompressedContext(
            vector=[0.1] * 384,
            summary="[VSA Compressed: 3 items → 1 vector]\n- [context] The bug was caused by a race condition\n- [context] Thread safety issue in module X",
            item_count=3,
            original_tokens=1500,
            compressed_tokens=30,
            compression_ratio=50.0,
            method="hrr_superposition",
        )
        mock_compressor.compress.return_value = mock_result
        mock_get_compressor.return_value = mock_compressor

        opt = TokenOptimizer()
        large_context = "Some context about threading. " * 200

        q, ctx, saved = opt.optimize_query("race condition bug", large_context)

        self.assertIn("race condition", ctx.lower())
        self.assertGreater(saved, 1000)  # Should save significant tokens

    def test_vsa_compress_method_splits_paragraphs(self) -> None:
        """_vsa_compress should split context into paragraph-aware chunks."""
        opt = TokenOptimizer()

        # Create context with clear paragraphs
        context = "Paragraph one about topic A.\n\n" * 20
        context += "Paragraph two about topic B.\n\n" * 20

        with patch("whitemagic.ai.vsa_context_compressor.get_vsa_context_compressor") as mock_get:
            from whitemagic.ai.vsa_context_compressor import VSACompressedContext

            mock_compressor = MagicMock()
            mock_result = VSACompressedContext(
                vector=[0.1] * 384,
                summary="[VSA Compressed: 5 items → 1 vector]\ntest",
                item_count=5,
                original_tokens=500,
                compressed_tokens=10,
                compression_ratio=50.0,
                method="hrr_superposition",
            )
            mock_compressor.compress.return_value = mock_result
            mock_get.return_value = mock_compressor

            result = opt._vsa_compress(context, "test query")

            # Check that compress was called with multiple items
            call_args = mock_compressor.compress.call_args
            items = call_args[0][0]  # First positional arg
            self.assertGreater(len(items), 1, "Should split context into multiple chunks")

    def test_cache_still_works_with_vsa(self) -> None:
        """Cache should still work when VSA compression is used."""
        opt = TokenOptimizer()

        # First call should cache
        query = "cached query"
        context = "Small cached context."
        q1, ctx1, saved1 = opt.optimize_query(query, context)

        # Second call with same query+context should hit cache
        q2, ctx2, saved2 = opt.optimize_query(query, context)

        # Results should be identical (from cache)
        self.assertEqual(ctx1, ctx2)


if __name__ == "__main__":
    unittest.main()
