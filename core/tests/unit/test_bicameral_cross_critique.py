"""Tests for BicameralReasoner embedding-based cross-critique."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from whitemagic.core.intelligence.bicameral import (
    BicameralReasoner,
    CrossCritique,
    HemisphereResult,
)


class TestSemanticSimilarity(unittest.TestCase):
    """Test _compute_semantic_similarity method."""

    def test_returns_none_when_embedding_engine_unavailable(self) -> None:
        """Should return None when embedding engine fails to load."""
        reasoner = BicameralReasoner(left_clones=1, right_clones=1)
        with patch(
            "whitemagic.core.memory.embeddings.get_embedding_engine",
            side_effect=Exception("no model"),
        ):
            result = reasoner._compute_semantic_similarity("hello", "world")
            self.assertIsNone(result)

    def test_returns_cosine_similarity_when_available(self) -> None:
        """Should return cosine similarity when embeddings are available."""
        reasoner = BicameralReasoner(left_clones=1, right_clones=1)
        mock_engine = MagicMock()
        mock_engine.encode = MagicMock(
            side_effect=lambda text: [0.1, 0.2, 0.3] if text == "a" else [0.3, 0.2, 0.1]
        )
        with patch(
            "whitemagic.core.memory.embeddings.get_embedding_engine",
            return_value=mock_engine,
        ):
            result = reasoner._compute_semantic_similarity("a", "b")
            self.assertIsNotNone(result)
            self.assertGreater(result, 0.0)
            self.assertLessEqual(result, 1.0)

    def test_returns_none_for_zero_norm_vectors(self) -> None:
        """Should return None for zero-norm embeddings."""
        reasoner = BicameralReasoner(left_clones=1, right_clones=1)
        mock_engine = MagicMock()
        mock_engine.encode = MagicMock(return_value=[0.0, 0.0, 0.0])
        with patch(
            "whitemagic.core.memory.embeddings.get_embedding_engine",
            return_value=mock_engine,
        ):
            result = reasoner._compute_semantic_similarity("a", "b")
            self.assertIsNone(result)


class TestEmbeddingBasedCrossCritique(unittest.TestCase):
    """Test that cross-critique uses embedding similarity when available."""

    def _make_hemisphere_results(self) -> tuple[HemisphereResult, HemisphereResult]:
        left = HemisphereResult(
            hemisphere="left",
            content="We need systematic analysis and risk assessment for this project.",
            confidence=0.8,
            strategy="analytical",
        )
        right = HemisphereResult(
            hemisphere="right",
            content="This is an opportunity for creative transformation and novel patterns.",
            confidence=0.7,
            strategy="creative",
        )
        return left, right

    def test_left_critique_uses_embedding_when_available(self) -> None:
        """Left critique should use embedding similarity for agreement detection."""
        left, right = self._make_hemisphere_results()
        reasoner = BicameralReasoner(left_clones=1, right_clones=1)

        with patch.object(reasoner, "_compute_semantic_similarity", return_value=0.6):
            critique = reasoner._left_critiques_right(left, right)

        self.assertTrue(any("cosine" in a for a in critique.agreements))

    def test_left_critique_falls_back_to_word_overlap(self) -> None:
        """Left critique should fall back to word-overlap when embeddings unavailable."""
        left, right = self._make_hemisphere_results()
        reasoner = BicameralReasoner(left_clones=1, right_clones=1)

        with patch.object(reasoner, "_compute_semantic_similarity", return_value=None):
            critique = reasoner._left_critiques_right(left, right)

        # Should still produce a valid critique, just without cosine scores
        self.assertIsInstance(critique, CrossCritique)
        self.assertEqual(critique.critic, "left")
        self.assertEqual(critique.target, "right")

    def test_right_critique_uses_embedding_when_available(self) -> None:
        """Right critique should use embedding similarity for agreement detection."""
        left, right = self._make_hemisphere_results()
        reasoner = BicameralReasoner(left_clones=1, right_clones=1)

        with patch.object(reasoner, "_compute_semantic_similarity", return_value=0.6):
            critique = reasoner._right_critiques_left(left, right)

        self.assertTrue(any("cosine" in a for a in critique.agreements))
        self.assertGreater(critique.confidence_adjustment, 0.0)

    def test_low_similarity_produces_no_agreement(self) -> None:
        """Low semantic similarity should not produce agreement entries."""
        left, right = self._make_hemisphere_results()
        reasoner = BicameralReasoner(left_clones=1, right_clones=1)

        with patch.object(reasoner, "_compute_semantic_similarity", return_value=0.1):
            critique = reasoner._left_critiques_right(left, right)

        # No agreement entries for low similarity
        self.assertEqual(len(critique.agreements), 0)

    def test_moderate_similarity_produces_partial_agreement(self) -> None:
        """Moderate similarity (0.3-0.5) should produce partial agreement."""
        left, right = self._make_hemisphere_results()
        reasoner = BicameralReasoner(left_clones=1, right_clones=1)

        with patch.object(reasoner, "_compute_semantic_similarity", return_value=0.4):
            critique = reasoner._left_critiques_right(left, right)

        self.assertTrue(any("Moderate" in a for a in critique.agreements))


if __name__ == "__main__":
    unittest.main()
