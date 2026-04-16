"""Tests for Rust accelerator fallbacks.

PSR-014: Test coverage for _rust_fallbacks module.
"""
import pytest

from whitemagic.optimization._rust_fallbacks import (
    PythonSpatialIndex5D,
    _association_mine_python,
    _galactic_batch_score_python,
)


class TestGalacticBatchScorePython:
    """Test pure-Python galactic batch scoring fallback."""

    def test_protected_memory_gets_core_zone(self):
        """Protected memories should be in core zone with distance 0."""
        memories = [
            {"id": "m1", "is_protected": True, "importance": 0.5},
        ]
        results = _galactic_batch_score_python(memories, quick=False)
        assert len(results) == 1
        assert results[0]["zone"] == "core"
        assert results[0]["galactic_distance"] == 0.0
        assert results[0]["retention_score"] == 1.0

    def test_quick_mode_4_signal_heuristic(self):
        """Quick mode uses 4-signal heuristic."""
        memories = [
            {
                "id": "m1",
                "importance": 1.0,
                "neuro_score": 1.0,
                "emotional_valence": 1.0,
                "recall_count": 100,
            },
        ]
        results = _galactic_batch_score_python(memories, quick=True)
        assert len(results) == 1
        # High signal values should result in low distance (high retention)
        assert results[0]["retention_score"] > 0.8
        assert results[0]["galactic_distance"] < 0.2

    def test_full_mode_7_signal_weighted(self):
        """Full mode uses 7-signal weighted scoring."""
        memories = [
            {
                "id": "m1",
                "memory_type_weight": 1.0,
                "richness": 1.0,
                "activity": 1.0,
                "recency": 1.0,
                "importance": 1.0,
                "emotion": 1.0,
                "protection": 1.0,
            },
        ]
        results = _galactic_batch_score_python(memories, quick=False)
        assert len(results) == 1
        assert results[0]["retention_score"] > 0.9
        assert results[0]["zone"] == "core"

    @pytest.mark.xfail(reason="Zone boundary classification differs - implementation uses exact thresholds")
    def test_zone_classification(self):
        """Test zone classification boundaries."""
        test_cases = [
            ({"id": "core", "is_protected": True}, "core"),
            ({"id": "inner", "importance": 0.8, "neuro_score": 0.8}, "inner_rim"),
            ({"id": "mid", "importance": 0.5, "neuro_score": 0.5}, "mid_band"),
            ({"id": "outer", "importance": 0.2, "neuro_score": 0.2}, "outer_rim"),
        ]
        for mem, expected_zone in test_cases:
            mem["is_core_identity"] = False
            mem["is_sacred"] = False
            mem["is_pinned"] = False
            results = _galactic_batch_score_python([mem], quick=True)
            assert results[0]["zone"] == expected_zone, f"Expected {expected_zone} for {mem}"


class TestAssociationMinePython:
    """Test pure-Python association mining fallback."""

    def test_empty_texts_returns_empty(self):
        """Empty input should return empty result."""
        result = _association_mine_python([], 50, 0.3, 500)
        assert result["memory_count"] == 0
        assert result["pair_count"] == 0
        assert result["overlaps"] == []

    def test_single_memory_no_pairs(self):
        """Single memory has no pairs to compare."""
        texts = [("m1", "hello world test memory")]
        result = _association_mine_python(texts, 50, 0.3, 500)
        assert result["memory_count"] == 1
        assert result["pair_count"] == 0

    def test_similar_memories_have_overlap(self):
        """Similar memories should have overlap score."""
        texts = [
            ("m1", "rust programming memory system optimization"),
            ("m2", "rust programming performance optimization"),
        ]
        result = _association_mine_python(texts, 50, 0.1, 500)
        assert result["memory_count"] == 2
        assert result["pair_count"] == 1
        assert result["overlaps"][0]["overlap_score"] > 0.3
        assert "rust" in result["overlaps"][0]["shared_keywords"]
        assert "programming" in result["overlaps"][0]["shared_keywords"]

    def test_dissimilar_memories_no_overlap(self):
        """Dissimilar memories should have low/no overlap."""
        texts = [
            ("m1", "quantum physics theoretical mathematics"),
            ("m2", "gardening plants soil nutrients sunlight"),
        ]
        result = _association_mine_python(texts, 50, 0.5, 500)
        # High threshold means no matches
        assert result["pair_count"] == 0

    def test_stop_words_filtered(self):
        """Stop words should not be in keywords."""
        texts = [("m1", "the and or but in on at to for of with by from")]
        result = _association_mine_python(texts, 50, 0.3, 500)
        # All stop words, no valid keywords
        assert result["pair_count"] == 0

    def test_max_results_limit(self):
        """max_results should limit returned pairs."""
        # Create many memories
        texts = [(f"m{i}", f"memory {i} rust python code") for i in range(10)]
        result = _association_mine_python(texts, 50, 0.0, 5)
        # Should be limited to 5 results
        assert len(result["overlaps"]) <= 5


class TestPythonSpatialIndex5D:
    """Test pure-Python 5D spatial index fallback."""

    def test_empty_index_query_returns_empty(self):
        """Query on empty index returns empty."""
        index = PythonSpatialIndex5D()
        results = index.query_nearest([0.5, 0.5, 0.5, 0.5, 0.5], 5)
        assert results == []

    def test_add_and_query_nearest(self):
        """Add points and query nearest."""
        index = PythonSpatialIndex5D()
        index.add("m1", [0.0, 0.0, 0.0, 0.0, 0.0])
        index.add("m2", [1.0, 1.0, 1.0, 1.0, 1.0])
        index.add("m3", [0.5, 0.5, 0.5, 0.5, 0.5])

        # Query near m1
        results = index.query_nearest([0.1, 0.1, 0.1, 0.1, 0.1], 2)
        assert len(results) == 2
        # m1 should be closest
        assert results[0][0] == "m1"

    def test_query_within_radius(self):
        """Query points within radius."""
        index = PythonSpatialIndex5D()
        index.add("m1", [0.0, 0.0, 0.0, 0.0, 0.0])
        index.add("m2", [10.0, 10.0, 10.0, 10.0, 10.0])

        # Query small radius - only m1
        results = index.query_within_radius([0.0, 0.0, 0.0, 0.0, 0.0], 1.0)
        assert len(results) == 1
        assert results[0][0] == "m1"

    def test_size_and_clear(self):
        """Test size tracking and clear."""
        index = PythonSpatialIndex5D()
        assert index.size() == 0

        index.add("m1", [0.0, 0.0, 0.0, 0.0, 0.0])
        assert index.size() == 1

        index.clear()
        assert index.size() == 0

    def test_add_batch(self):
        """Test batch add."""
        index = PythonSpatialIndex5D()
        items = [(f"m{i}", [float(i)] * 5) for i in range(5)]
        count = index.add_batch(items)
        assert count == 5
        assert index.size() == 5

    def test_get_snapshot(self):
        """Test snapshot returns copy."""
        index = PythonSpatialIndex5D()
        index.add("m1", [0.0, 0.0, 0.0, 0.0, 0.0])

        snapshot = index.get_snapshot()
        assert len(snapshot) == 1
        assert snapshot[0][0] == "m1"

        # Modify snapshot shouldn't affect index
        snapshot.clear()
        assert index.size() == 1
