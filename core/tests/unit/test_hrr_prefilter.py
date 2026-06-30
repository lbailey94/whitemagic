"""Tests for HRR pre-filtering in CoreAccessLayer hybrid_recall."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

import numpy as np


class TestHRRPreFilter(unittest.TestCase):
    """Test HRR pre-filtering in CoreAccessLayer."""

    def setUp(self) -> None:
        from whitemagic.core.intelligence.core_access import CoreAccessLayer

        self.cal = CoreAccessLayer()

    def test_hrr_cache_empty_when_no_db(self) -> None:
        """HRR cache should be empty when DB has no embeddings."""
        # _refresh_hrr_cache will fail gracefully without a real DB
        self.cal._hrr_cache_ids = []
        self.cal._hrr_cache_vecs = np.zeros((0, 384), dtype=np.uint8)
        self.cal._hrr_cache_count = 0

        result = self.cal._hrr_prefilter("test query", top_n=5)
        self.assertEqual(result, [])

    def test_hrr_prefilter_with_mock_cache(self) -> None:
        """HRR pre-filter should return ranked candidates from cache."""
        # Manually populate cache with synthetic data
        from whitemagic.core.memory.qfhrr import get_quantized_hrr_engine

        engine = get_quantized_hrr_engine(bits=8, dim=64)

        # Create 10 synthetic embeddings — first 3 are similar, rest are random
        rng = np.random.default_rng(42)
        base = rng.standard_normal(64).astype(np.float32)
        base = base / np.linalg.norm(base)

        similar = [
            base + rng.standard_normal(64).astype(np.float32) * 0.1 for _ in range(3)
        ]
        random_vecs = [rng.standard_normal(64).astype(np.float32) for _ in range(7)]

        all_vecs = similar + random_vecs
        ids = [f"mem_{i}" for i in range(10)]

        quantized = np.array(
            [engine._to_quantized(v) for v in all_vecs], dtype=np.uint8
        )

        self.cal._hrr_cache_ids = ids
        self.cal._hrr_cache_vecs = quantized
        self.cal._hrr_cache_count = 10

        # Mock the embedding engine to return our base vector as query
        with patch(
            "whitemagic.core.memory.embeddings.get_embedding_engine"
        ) as mock_engine:
            mock_eng = MagicMock()
            mock_eng.encode.return_value = base.tolist()
            mock_engine.return_value = mock_eng

            result = self.cal._hrr_prefilter("test query", top_n=5)

        self.assertGreater(len(result), 0)
        self.assertLessEqual(len(result), 5)

        # Top results should be from the similar group (mem_0, mem_1, mem_2)
        top_ids = {mid for mid, _ in result[:3]}
        similar_ids = {"mem_0", "mem_1", "mem_2"}
        overlap = top_ids & similar_ids
        self.assertGreaterEqual(
            len(overlap), 2, "Top HRR results should include similar vectors"
        )

    def test_hrr_prefilter_returns_empty_on_error(self) -> None:
        """HRR pre-filter should return empty list on encoding failure."""
        self.cal._hrr_cache_ids = ["mem_0"]
        self.cal._hrr_cache_vecs = np.zeros((1, 64), dtype=np.uint8)
        self.cal._hrr_cache_count = 1

        with patch(
            "whitemagic.core.memory.embeddings.get_embedding_engine"
        ) as mock_engine:
            mock_eng = MagicMock()
            mock_eng.encode.return_value = None  # Encoding fails
            mock_engine.return_value = mock_eng

            result = self.cal._hrr_prefilter("test", top_n=5)
            self.assertEqual(result, [])

    def test_invalidate_hrr_cache(self) -> None:
        """invalidate_hrr_cache should clear all cache fields."""
        self.cal._hrr_cache_ids = ["mem_a", "mem_b"]
        self.cal._hrr_cache_vecs = np.array([[1, 2], [3, 4]], dtype=np.uint8)
        self.cal._hrr_cache_count = 2

        self.cal.invalidate_hrr_cache()

        self.assertIsNone(self.cal._hrr_cache_ids)
        self.assertIsNone(self.cal._hrr_cache_vecs)
        self.assertEqual(self.cal._hrr_cache_count, 0)


class TestHybridRecallWithHRR(unittest.TestCase):
    """Test hybrid_recall with HRR pre-filtering enabled."""

    def setUp(self) -> None:
        from whitemagic.core.intelligence.core_access import CoreAccessLayer

        self.cal = CoreAccessLayer()
        # Prevent real DB access
        self.cal._hrr_cache_ids = []
        self.cal._hrr_cache_vecs = None
        self.cal._hrr_cache_count = 0

    def test_hybrid_recall_without_prefilter(self) -> None:
        """hybrid_recall should work with use_hrr_prefilter=False."""
        with patch.object(self.cal, "_get_conn") as mock_conn:
            mock_conn.return_value = MagicMock()
            with patch(
                "whitemagic.core.memory.embeddings.get_embedding_engine"
            ) as mock_eng:
                mock_e = MagicMock()
                mock_e.search_similar.return_value = []
                mock_eng.return_value = mock_e

                result = self.cal.hybrid_recall(
                    "test",
                    k=5,
                    use_hrr_prefilter=False,
                )
                self.assertEqual(result, [])

    def test_hybrid_recall_fallback_to_hrr_on_embedding_failure(self) -> None:
        """If embedding search fails but HRR pre-filter succeeded, use HRR results."""
        # Populate HRR cache with mock data
        self.cal._hrr_cache_ids = ["mem_a", "mem_b"]
        self.cal._hrr_cache_vecs = np.array([[1, 2, 3], [4, 5, 6]], dtype=np.uint8)
        self.cal._hrr_cache_count = 2

        # Mock _hrr_prefilter to return candidates
        hrr_candidates = [("mem_a", 0.8), ("mem_b", 0.6)]
        with patch.object(self.cal, "_hrr_prefilter", return_value=hrr_candidates):
            with patch(
                "whitemagic.core.memory.embeddings.get_embedding_engine"
            ) as mock_eng:
                mock_e = MagicMock()
                mock_e.search_similar.side_effect = RuntimeError("model load failed")
                mock_eng.return_value = mock_e

                # Mock graph channel to return empty
                with patch.object(
                    self.cal, "query_association_subgraph", return_value=[]
                ):
                    # Mock the DB fetch for titles
                    with patch.object(self.cal, "_get_conn") as mock_conn:
                        mock_conn_obj = MagicMock()
                        mock_conn_obj.execute.return_value.fetchone.return_value = None
                        mock_conn_obj.execute.return_value.fetchall.return_value = []
                        mock_conn.return_value = mock_conn_obj

                        result = self.cal.hybrid_recall(
                            "test",
                            k=5,
                            use_hrr_prefilter=True,
                        )

        # Should have results from HRR fallback
        self.assertGreater(len(result), 0)
        result_ids = {r.memory_id for r in result}
        self.assertIn("mem_a", result_ids)


if __name__ == "__main__":
    unittest.main()
