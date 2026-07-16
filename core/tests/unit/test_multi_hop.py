"""Tests for multi-hop aggregation module."""

import pytest
from unittest.mock import MagicMock

from whitemagic.core.memory.multi_hop import (
    _extract_result_entities,
    _extract_key_terms,
    multi_hop_search,
)


class TestExtractResultEntities:
    def _make_mem(self, content: str):
        mem = MagicMock()
        mem.content = content
        return mem

    def test_capitalized_entities(self):
        results = [self._make_mem("Alice works on project Alpha")]
        entities = _extract_result_entities(results)
        assert "Alice" in entities
        assert "Alpha" in entities

    def test_entity_id_pattern(self):
        results = [self._make_mem("entity_012 has project Eta")]
        entities = _extract_result_entities(results)
        assert "entity_012" in entities

    def test_multi_word_proper_noun(self):
        results = [self._make_mem("New York is a city")]
        entities = _extract_result_entities(results)
        assert "New York" in entities

    def test_dedup(self):
        results = [
            self._make_mem("Alice likes cats"),
            self._make_mem("Alice also likes dogs"),
        ]
        entities = _extract_result_entities(results)
        assert entities.count("Alice") == 1

    def test_top_k_limit(self):
        results = [
            self._make_mem("Alice and Bob and Carol and Dave"),
        ]
        entities = _extract_result_entities(results, top_k=1)
        # Should extract from only the first result
        assert len(entities) >= 2


class TestExtractKeyTerms:
    def test_basic(self):
        terms = _extract_key_terms("What team is the person working on project Eta on?")
        assert "eta" in terms
        assert "what" not in terms
        assert "the" not in terms

    def test_stops_removed(self):
        terms = _extract_key_terms("Who is the person working on project Alpha")
        assert "alpha" in terms
        assert "who" not in terms
        assert "person" not in terms  # "person" is in stop list

    def test_empty_query(self):
        terms = _extract_key_terms("")
        assert terms == []


class TestMultiHopSearch:
    def _make_mem(self, id: str, content: str, score: float = 0.5):
        mem = MagicMock()
        mem.id = id
        mem.content = content
        mem.metadata = {"similarity_score": score, "blended_score": score}
        return mem

    def test_no_results(self):
        assert multi_hop_search("test", []) == []

    def test_no_backend_passthrough(self):
        m1 = self._make_mem("1", "content")
        result = multi_hop_search("test", [m1], backend=None)
        assert len(result) == 1

    def test_secondary_search_finds_hop2(self):
        # Hop 1: find who works on project Eta
        m1 = self._make_mem("1", "entity_012 has project Eta", 0.8)
        # Hop 2: secondary search should find team memory
        m2 = self._make_mem("2", "entity_012 has team frontend", 0.6)

        backend = MagicMock()
        backend.search.return_value = [m2]

        results = multi_hop_search(
            "What team is the person working on project Eta on?",
            [m1],
            backend=backend,
            galaxy="test",
        )
        # Should have merged the secondary result
        assert len(results) == 2
        ids = [r.id for r in results]
        assert "2" in ids

    def test_primary_results_boosted_over_secondary(self):
        m1 = self._make_mem("1", "entity_012 has project Eta", 0.8)
        m2 = self._make_mem("2", "entity_012 has team frontend", 0.3)

        backend = MagicMock()
        backend.search.return_value = [m2]

        results = multi_hop_search(
            "What team is the person working on project Eta on?",
            [m1],
            backend=backend,
            galaxy="test",
        )
        # Primary result should rank higher
        assert results[0].id == "1"

    def test_max_results_limit(self):
        m1 = self._make_mem("1", "entity_001 has project Alpha")
        m2 = self._make_mem("2", "entity_002 has project Beta")
        m3 = self._make_mem("3", "entity_003 has project Gamma")

        backend = MagicMock()
        backend.search.return_value = [m2, m3]

        results = multi_hop_search(
            "What about project Alpha?",
            [m1],
            backend=backend,
            galaxy="test",
            max_results=2,
        )
        assert len(results) <= 2
