"""Tests for Objective K — Emotional Valence as Utility Signal."""
from __future__ import annotations

from whitemagic.core.evolution.valence_utility import ValenceUtilityTracker


class TestRPE:
    def test_positive_rpe(self):
        tracker = ValenceUtilityTracker()
        rpe = tracker.compute_rpe(prediction=0.3, actual=0.8)
        assert rpe == 0.5  # Surprise success

    def test_negative_rpe(self):
        tracker = ValenceUtilityTracker()
        rpe = tracker.compute_rpe(prediction=0.8, actual=0.2)
        assert abs(rpe + 0.6) < 1e-6  # Surprise failure

    def test_zero_rpe(self):
        tracker = ValenceUtilityTracker()
        rpe = tracker.compute_rpe(prediction=0.5, actual=0.5)
        assert rpe == 0.0


class TestValenceTracker:
    def test_record_outcome(self):
        tracker = ValenceUtilityTracker()
        record = tracker.record_outcome("h1", prediction=0.3, actual=0.8, category="quality")
        assert record.rpe == 0.5
        assert record.valence_delta > 0

    def test_valence_accumulates(self):
        tracker = ValenceUtilityTracker(learning_rate=0.2)
        tracker.record_outcome("h1", prediction=0.3, actual=0.8, category="quality")
        tracker.record_outcome("h1", prediction=0.3, actual=0.9, category="quality")
        valence = tracker.get_valence("h1")
        assert valence > 0.1

    def test_category_valence(self):
        tracker = ValenceUtilityTracker(learning_rate=0.2)
        tracker.record_outcome("h1", prediction=0.3, actual=0.9, category="quality")
        tracker.record_outcome("h2", prediction=0.3, actual=0.9, category="quality")
        assert tracker.get_category_valence("quality") > 0

    def test_confidence_adjustment(self):
        tracker = ValenceUtilityTracker(learning_rate=0.5)
        for _ in range(10):
            tracker.record_outcome("h1", prediction=0.2, actual=1.0, category="quality")
        adj = tracker.get_confidence_adjustment("quality")
        assert adj > 0  # Positive valence → boost

    def test_confidence_adjustment_clamped(self):
        tracker = ValenceUtilityTracker(learning_rate=1.0)
        for _ in range(20):
            tracker.record_outcome("h1", prediction=0.1, actual=1.0, category="quality")
        adj = tracker.get_confidence_adjustment("quality")
        assert adj <= 0.2  # Clamped to max

    def test_preferences(self):
        tracker = ValenceUtilityTracker(learning_rate=0.3)
        for _ in range(5):
            tracker.record_outcome("h1", prediction=0.2, actual=1.0, category="quality")
        for _ in range(5):
            tracker.record_outcome("h2", prediction=0.8, actual=0.0, category="performance")
        prefs = tracker.get_preferences()
        # Quality should be preferred over performance
        assert prefs["quality"] > prefs["performance"]

    def test_get_records(self):
        tracker = ValenceUtilityTracker()
        tracker.record_outcome("h1", prediction=0.5, actual=0.5)
        tracker.record_outcome("h2", prediction=0.3, actual=0.8)
        all_records = tracker.get_records()
        assert len(all_records) == 2
        h1_records = tracker.get_records("h1")
        assert len(h1_records) == 1

    def test_stats(self):
        tracker = ValenceUtilityTracker()
        tracker.record_outcome("h1", prediction=0.3, actual=0.8, category="quality")
        stats = tracker.get_stats()
        assert stats["total_records"] == 1
        assert "avg_rpe" in stats
