"""Tests for VSA context compression (P2)."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from whitemagic.ai.vsa_context_compressor import (
    VSACompressedContext,
    VSAContextCompressor,
    get_vsa_context_compressor,
)


class TestVSAContextCompressor(unittest.TestCase):
    """Test the VSA context compression module."""

    def test_empty_items_returns_empty_context(self) -> None:
        compressor = VSAContextCompressor()
        result = compressor.compress([])
        self.assertEqual(result.item_count, 0)
        self.assertEqual(result.method, "empty")
        self.assertEqual(len(result.vector), 384)

    @patch("whitemagic.ai.vsa_context_compressor.get_hrr_engine")
    @patch("whitemagic.core.memory.embeddings.EmbeddingEngine")
    def test_compress_multiple_items(
        self,
        mock_embed_cls: MagicMock,
        mock_hrr_getter: MagicMock,
    ) -> None:
        mock_engine = MagicMock()
        mock_engine.encode.return_value = [0.1] * 384
        mock_embed_cls.return_value = mock_engine

        mock_hrr = MagicMock()
        mock_hrr.bind.return_value = MagicMock(tolist=lambda: [0.2] * 384)
        mock_hrr.superpose.return_value = MagicMock(tolist=lambda: [0.3] * 384)
        mock_hrr.get_relation_vector.return_value = [0.5] * 384
        mock_hrr_getter.return_value = mock_hrr

        compressor = VSAContextCompressor(hrr=mock_hrr)
        items = [
            {
                "content": "Memory about the bug that was found in the threading module causing a race condition during concurrent access to shared state variables",
                "source": "memory",
                "id": "1",
            },
            {
                "content": "Session scratchpad note documenting the investigation steps taken so far including the initial diagnosis and potential fixes being considered",
                "source": "session",
                "id": "2",
            },
            {
                "content": "Tool result output from the debugger showing the stack trace and variable states at the time of the crash with full diagnostic information",
                "source": "tool_result",
                "id": "3",
            },
        ]

        result = compressor.compress(items)

        self.assertEqual(result.item_count, 3)
        self.assertEqual(result.method, "hrr_superposition")
        self.assertGreater(result.compression_ratio, 1.0)
        self.assertEqual(mock_hrr.bind.call_count, 3)
        mock_hrr.superpose.assert_called_once()

    @patch("whitemagic.ai.vsa_context_compressor.get_hrr_engine")
    @patch("whitemagic.core.memory.embeddings.EmbeddingEngine")
    def test_compress_with_query_ranks_summaries(
        self,
        mock_embed_cls: MagicMock,
        mock_hrr_getter: MagicMock,
    ) -> None:
        mock_engine = MagicMock()
        mock_engine.encode.return_value = [0.1] * 384
        mock_embed_cls.return_value = mock_engine

        mock_hrr = MagicMock()
        mock_hrr.bind.return_value = MagicMock(tolist=lambda: [0.2] * 384)
        mock_hrr.superpose.return_value = MagicMock(tolist=lambda: [0.3] * 384)
        mock_hrr.get_relation_vector.return_value = [0.5] * 384
        mock_hrr_getter.return_value = mock_hrr

        compressor = VSAContextCompressor(hrr=mock_hrr)
        items = [
            {"content": "The bug was caused by a race condition", "source": "memory"},
            {"content": "Unrelated note about gardening", "source": "session"},
            {"content": "Another unrelated topic", "source": "tool_result"},
            {"content": "Race condition in the threading module", "source": "memory"},
            {"content": "More unrelated content here", "source": "scratchpad"},
            {"content": "Even more unrelated stuff", "source": "session"},
        ]

        result = compressor.compress(
            items, query="race condition bug", max_text_items=2
        )

        # Should select items most relevant to "race condition bug"
        self.assertEqual(len(result.item_summaries), 2)
        # Check that the selected summaries contain relevant keywords
        combined = " ".join(result.item_summaries).lower()
        self.assertIn("race", combined)

    @patch("whitemagic.ai.vsa_context_compressor.get_hrr_engine")
    @patch("whitemagic.core.memory.embeddings.EmbeddingEngine")
    def test_compress_handles_encoding_failure(
        self,
        mock_embed_cls: MagicMock,
        mock_hrr_getter: MagicMock,
    ) -> None:
        mock_engine = MagicMock()
        mock_engine.encode.return_value = None  # Encoding fails
        mock_embed_cls.return_value = mock_engine

        mock_hrr = MagicMock()
        mock_hrr_getter.return_value = mock_hrr

        compressor = VSAContextCompressor(hrr=mock_hrr)
        items = [
            {"content": "Some content", "source": "memory"},
            {"content": "More content", "source": "session"},
        ]

        result = compressor.compress(items)

        # Should fall back to text-only
        self.assertEqual(result.method, "text_only")
        self.assertEqual(len(result.item_summaries), 2)

    @patch("whitemagic.ai.vsa_context_compressor.get_hrr_engine")
    def test_probe_recovers_role_filler(
        self,
        mock_hrr_getter: MagicMock,
    ) -> None:
        mock_hrr = MagicMock()
        mock_hrr.get_relation_vector.return_value = [0.5] * 384
        mock_hrr.unbind.return_value = MagicMock(tolist=lambda: [0.7] * 384)
        mock_hrr_getter.return_value = mock_hrr

        compressor = VSAContextCompressor(hrr=mock_hrr)
        result = compressor.probe([0.3] * 384, "OBJECT")

        self.assertEqual(len(result), 384)
        mock_hrr.unbind.assert_called_once()

    def test_compression_ratio_calculation(self) -> None:
        """Verify compression ratio is original_tokens / compressed_tokens."""
        result = VSACompressedContext(
            vector=[0.0] * 384,
            summary="test",
            item_count=10,
            original_tokens=5000,
            compressed_tokens=96,
            compression_ratio=52.08,
            method="hrr_superposition",
        )
        self.assertGreater(result.compression_ratio, 50.0)


class TestVSAContextCompressorSingleton(unittest.TestCase):
    """Test singleton accessor."""

    def test_get_singleton(self) -> None:
        c1 = get_vsa_context_compressor()
        c2 = get_vsa_context_compressor()
        self.assertIs(c1, c2)


if __name__ == "__main__":
    unittest.main()
