"""Tests for HRR-based compositional reasoning (P1)."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from whitemagic.core.intelligence.agentic.compositional_reasoning import (
    CompositionalReasoner,
    CompositionalResult,
    _extract_relation,
    reason_compositionally,
)


class TestRelationExtraction(unittest.TestCase):
    """Test natural language → relation extraction."""

    def test_extracts_causes(self) -> None:
        result = _extract_relation("what caused the outage?")
        self.assertIsNotNone(result)
        subject, relation, direction = result
        self.assertEqual(relation, "CAUSES")
        self.assertEqual(direction, "inverse")
        self.assertEqual(subject, "the outage")

    def test_extracts_uses(self) -> None:
        result = _extract_relation("what uses the memory engine?")
        self.assertIsNotNone(result)
        subject, relation, direction = result
        self.assertEqual(relation, "USES")
        self.assertEqual(direction, "inverse")

    def test_extracts_part_of(self) -> None:
        result = _extract_relation("what is part of the core system?")
        self.assertIsNotNone(result)
        subject, relation, direction = result
        self.assertEqual(relation, "PART_OF")
        self.assertEqual(direction, "forward")

    def test_extracts_similar_to(self) -> None:
        result = _extract_relation("what is similar to the graph walker?")
        self.assertIsNotNone(result)
        self.assertEqual(result[1], "SIMILAR_TO")

    def test_no_relation_returns_none(self) -> None:
        self.assertIsNone(_extract_relation("what is the version?"))
        self.assertIsNone(_extract_relation("hello world"))
        self.assertIsNone(_extract_relation("store this memory"))

    def test_extracts_creates(self) -> None:
        result = _extract_relation("what creates the embeddings?")
        self.assertIsNotNone(result)
        self.assertEqual(result[1], "CREATES")


class TestCompositionalReasoner(unittest.TestCase):
    """Test the CompositionalReasoner class."""

    def test_can_resolve_relation_query(self) -> None:
        reasoner = CompositionalReasoner()
        self.assertTrue(reasoner.can_resolve("what caused the bug?"))
        self.assertTrue(reasoner.can_resolve("what uses the HRR engine?"))

    def test_cannot_resolve_non_relation_query(self) -> None:
        reasoner = CompositionalReasoner()
        self.assertFalse(reasoner.can_resolve("what is the version?"))
        self.assertFalse(reasoner.can_resolve("hello"))

    @patch(
        "whitemagic.core.intelligence.agentic.compositional_reasoning.get_hrr_engine"
    )
    @patch("whitemagic.core.memory.embeddings.get_embedding_engine")
    def test_resolve_returns_unresolved_when_no_embedding(
        self,
        mock_embed_getter: MagicMock,
        mock_hrr_getter: MagicMock,
    ) -> None:
        mock_engine = MagicMock()
        mock_engine.encode.return_value = None
        mock_embed_getter.return_value = mock_engine

        reasoner = CompositionalReasoner(hrr=mock_hrr_getter.return_value)
        result = reasoner.resolve("what caused the outage?")

        self.assertFalse(result.resolved)
        self.assertEqual(result.method, "encoding_failed")

    @patch(
        "whitemagic.core.intelligence.agentic.compositional_reasoning.get_hrr_engine"
    )
    @patch("whitemagic.core.memory.embeddings.get_embedding_engine")
    def test_resolve_returns_result_with_matches(
        self,
        mock_embed_getter: MagicMock,
        mock_hrr_getter: MagicMock,
    ) -> None:
        # Setup embedding engine
        mock_engine = MagicMock()
        mock_engine.encode.return_value = [0.1] * 384
        mock_engine.search_similar_by_vector.return_value = [
            {
                "memory_id": "abc123",
                "similarity": 0.85,
                "content": "The bug was caused by a race condition",
            },
            {
                "memory_id": "def456",
                "similarity": 0.72,
                "content": "Related to concurrent access",
            },
        ]
        mock_embed_getter.return_value = mock_engine

        # Setup HRR engine
        mock_hrr = MagicMock()
        mock_hrr.inverse_project.return_value = MagicMock(tolist=lambda: [0.2] * 384)

        reasoner = CompositionalReasoner(hrr=mock_hrr)
        result = reasoner.resolve("what caused the outage?")

        self.assertTrue(result.resolved)
        self.assertEqual(result.relation, "CAUSES")
        self.assertEqual(result.method, "hrr:inverse:CAUSES")
        self.assertEqual(len(result.matches), 2)
        self.assertGreater(result.tokens_saved, 0)
        mock_hrr.inverse_project.assert_called_once()

    @patch(
        "whitemagic.core.intelligence.agentic.compositional_reasoning.get_hrr_engine"
    )
    @patch("whitemagic.core.memory.embeddings.EmbeddingEngine")
    def test_resolve_uses_project_for_forward_direction(
        self,
        mock_embed_cls: MagicMock,
        mock_hrr_getter: MagicMock,
    ) -> None:
        mock_engine = MagicMock()
        mock_engine.encode.return_value = [0.1] * 384
        mock_engine.search_similar_by_vector.return_value = []
        mock_embed_cls.return_value = mock_engine

        mock_hrr = MagicMock()
        mock_hrr.project.return_value = MagicMock(tolist=lambda: [0.3] * 384)

        reasoner = CompositionalReasoner(hrr=mock_hrr)
        result = reasoner.resolve("what is part of the core system?")

        # Should use project (forward), not inverse_project
        mock_hrr.project.assert_called_once()
        mock_hrr.inverse_project.assert_not_called()
        self.assertFalse(result.resolved)  # No matches

    def test_resolve_non_relation_query_returns_unresolved(self) -> None:
        reasoner = CompositionalReasoner()
        result = reasoner.resolve("what is the version?")
        self.assertFalse(result.resolved)
        self.assertEqual(result.method, "none")


class TestCompositionalResult(unittest.TestCase):
    """Test the CompositionalResult dataclass."""

    def test_default_values(self) -> None:
        result = CompositionalResult(
            resolved=False,
            answer="",
            method="none",
            confidence=0.0,
        )
        self.assertFalse(result.resolved)
        self.assertEqual(result.matches, [])
        self.assertEqual(result.tokens_saved, 0)


if __name__ == "__main__":
    unittest.main()
