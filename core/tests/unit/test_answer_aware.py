"""Tests for answer-aware retrieval module."""

import pytest
from unittest.mock import MagicMock, patch

from whitemagic.core.memory.answer_aware import (
    extract_answer_hints,
    content_boost,
    answer_aware_search,
    _NON_ENTITIES,
)


class TestExtractAnswerHints:
    def test_what_did_say_about(self):
        hints = extract_answer_hints("What did Alice say about machine learning?")
        assert hints["entity"] == "Alice"
        assert hints["topic"] == "machine learning"

    def test_what_is_the_x_of_y(self):
        hints = extract_answer_hints("What is the location of entity_003?")
        assert hints["entity"] == "entity_003"
        assert hints["topic"] == "location"

    def test_what_is_entity_role(self):
        hints = extract_answer_hints("What is entity_012 role?")
        assert hints["entity"] == "entity_012"
        assert hints["topic"] == "role"

    def test_what_did_bob_do(self):
        hints = extract_answer_hints("What did Bob do?")
        assert hints["entity"] == "Bob"

    def test_non_entity_filtered(self):
        hints = extract_answer_hints("What is the weather?")
        assert "entity" not in hints or hints["entity"].lower() not in _NON_ENTITIES

    def test_no_hints_for_plain_statement(self):
        hints = extract_answer_hints("The sky is blue.")
        assert hints == {}

    def test_fallback_capitalized(self):
        hints = extract_answer_hints("Tell me about Python")
        assert hints.get("entity") == "Python"

    def test_fallback_filters_non_entities(self):
        hints = extract_answer_hints("What about The project?")
        assert hints.get("entity") != "The"


class TestContentBoost:
    def _make_mem(self, id: str, content: str, score: float = 0.5):
        mem = MagicMock()
        mem.id = id
        mem.content = content
        mem.metadata = {"similarity_score": score}
        return mem

    def test_no_results(self):
        assert content_boost("test", []) == []

    def test_single_result_unchanged(self):
        mem = self._make_mem("1", "test content")
        result = content_boost("test", [mem])
        assert len(result) == 1

    def test_entity_topic_cooccurrence_boosted(self):
        m1 = self._make_mem("1", "Alice talked about something else", 0.5)
        m2 = self._make_mem("2", "Alice said machine learning is great", 0.4)
        results = [m1, m2]
        boosted = content_boost("What did Alice say about machine learning?", results)
        # m2 should be boosted because it contains both "alice" and "machine learning"
        assert boosted[0].id == "2"
        assert boosted[0].metadata["answer_aware_boost"] > 0

    def test_no_hints_no_change(self):
        m1 = self._make_mem("1", "content one", 0.5)
        m2 = self._make_mem("2", "content two", 0.4)
        results = content_boost("plain text query", [m1, m2])
        # Should not crash, order may or may not change
        assert len(results) == 2


class TestAnswerAwareSearch:
    def _make_mem(self, id: str, content: str, score: float = 0.5):
        mem = MagicMock()
        mem.id = id
        mem.content = content
        mem.metadata = {"similarity_score": score}
        return mem

    def test_no_results(self):
        assert answer_aware_search("test", []) == []

    def test_no_hints_passthrough(self):
        m1 = self._make_mem("1", "content")
        result = answer_aware_search("plain text", [m1])
        assert len(result) == 1

    def test_secondary_search_merges(self):
        m1 = self._make_mem("1", "Alice mentioned something", 0.5)
        m2 = self._make_mem("2", "Alice said machine learning is fascinating", 0.6)

        backend = MagicMock()
        m3 = self._make_mem("3", "Alice wrote about machine learning in her blog", 0.7)
        backend.search.return_value = [m3]

        results = answer_aware_search(
            "What did Alice say about machine learning?",
            [m1, m2],
            backend=backend,
            galaxy="test",
        )
        # Should have merged secondary result
        assert len(results) == 3
        ids = [r.id for r in results]
        assert "3" in ids
