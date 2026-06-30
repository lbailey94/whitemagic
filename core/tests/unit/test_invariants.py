"""Tests for Objective W — Observer Effect & Self-Reference Invariants."""

from __future__ import annotations

from whitemagic.core.evolution.invariants import (
    GODEL_UNDECIDABLE,
    NON_INVARIANT_METRICS,
    InvariantSnapshot,
    InvariantTracker,
)


class TestInvariantSnapshot:
    def test_creation(self):
        snap = InvariantSnapshot(
            timestamp="2026-06-23T18:00:00",
            total_memories=100,
            total_tags=200,
            unique_tags=50,
            shannon_entropy=3.5,
        )
        assert snap.total_memories == 100
        assert snap.shannon_entropy == 3.5
        assert snap.test_count is None

    def test_delta_from(self):
        before = InvariantSnapshot(
            timestamp="t1",
            total_memories=100,
            total_tags=200,
            unique_tags=50,
            shannon_entropy=3.5,
        )
        after = InvariantSnapshot(
            timestamp="t2",
            total_memories=110,
            total_tags=220,
            unique_tags=55,
            shannon_entropy=3.6,
        )
        deltas = after.delta_from(before)
        assert deltas["total_memories_delta"] == 10.0
        assert deltas["total_tags_delta"] == 20.0
        assert deltas["unique_tags_delta"] == 5.0
        assert deltas["shannon_entropy_delta"] == 0.1


class TestInvariantTracker:
    def test_classify_metric_invariant(self):
        assert InvariantTracker.classify_metric("total_memories") == "invariant"
        assert InvariantTracker.classify_metric("test_count") == "invariant"

    def test_classify_metric_non_invariant(self):
        assert InvariantTracker.classify_metric("brier_score") == "non_invariant"
        assert (
            InvariantTracker.classify_metric("kaizen_proposal_count") == "non_invariant"
        )
        assert InvariantTracker.classify_metric("novelty_score") == "non_invariant"

    def test_is_godel_undecidable_true(self):
        for q in GODEL_UNDECIDABLE:
            assert InvariantTracker.is_godel_undecidable(q) is True

    def test_is_godel_undecidable_false(self):
        assert InvariantTracker.is_godel_undecidable("is_my_code_correct") is False

    def test_check_invariants_held(self):
        before = InvariantSnapshot(
            timestamp="t1",
            total_memories=100,
            total_tags=200,
            unique_tags=50,
            shannon_entropy=3.5,
            test_count=1470,
        )
        after = InvariantSnapshot(
            timestamp="t2",
            total_memories=110,
            total_tags=220,
            unique_tags=55,
            shannon_entropy=3.6,
            test_count=1470,
        )
        tracker = InvariantTracker()
        result = tracker.check_invariants(before, after)
        assert result["invariants_held"] is True
        assert result["violations"] == []

    def test_check_invariants_violated_memories_decrease(self):
        before = InvariantSnapshot(
            timestamp="t1",
            total_memories=100,
            total_tags=200,
            unique_tags=50,
            shannon_entropy=3.5,
        )
        after = InvariantSnapshot(
            timestamp="t2",
            total_memories=90,
            total_tags=200,
            unique_tags=50,
            shannon_entropy=3.5,
        )
        tracker = InvariantTracker()
        result = tracker.check_invariants(before, after)
        assert result["invariants_held"] is False
        assert len(result["violations"]) == 1

    def test_check_invariants_violated_tests_decrease(self):
        before = InvariantSnapshot(
            timestamp="t1",
            total_memories=100,
            total_tags=200,
            unique_tags=50,
            shannon_entropy=3.5,
            test_count=1470,
        )
        after = InvariantSnapshot(
            timestamp="t2",
            total_memories=100,
            total_tags=200,
            unique_tags=50,
            shannon_entropy=3.5,
            test_count=1400,
        )
        tracker = InvariantTracker()
        result = tracker.check_invariants(before, after)
        assert result["invariants_held"] is False
        assert any("test_count" in v for v in result["violations"])

    def test_check_invariants_entropy_drop(self):
        before = InvariantSnapshot(
            timestamp="t1",
            total_memories=100,
            total_tags=200,
            unique_tags=50,
            shannon_entropy=4.0,
        )
        after = InvariantSnapshot(
            timestamp="t2",
            total_memories=100,
            total_tags=200,
            unique_tags=50,
            shannon_entropy=3.0,
        )
        tracker = InvariantTracker()
        result = tracker.check_invariants(before, after)
        assert result["invariants_held"] is False

    def test_uncertainty_principle_satisfied(self):
        tracker = InvariantTracker()
        result = tracker.uncertainty_principle(
            delta_measurement=0.5,
            delta_system_state=0.5,
        )
        assert result["principle_satisfied"] is True
        assert result["product"] == 0.25

    def test_uncertainty_principle_not_satisfied(self):
        tracker = InvariantTracker()
        result = tracker.uncertainty_principle(
            delta_measurement=0.01,
            delta_system_state=0.01,
        )
        assert result["principle_satisfied"] is False
        assert result["product"] < result["h_self"]

    def test_uncertainty_principle_interpretation(self):
        tracker = InvariantTracker()
        # Low system change → reliable
        r1 = tracker.uncertainty_principle(0.5, 0.001)
        assert "reliable" in r1["interpretation"]
        # High system change → unreliable
        r2 = tracker.uncertainty_principle(0.5, 0.5)
        assert "unreliable" in r2["interpretation"]

    def test_get_tracking_guidance_invariant(self):
        tracker = InvariantTracker()
        guidance = tracker.get_tracking_guidance("total_memories")
        assert guidance["classification"] == "invariant"
        assert "long-term" in guidance["guidance"]

    def test_get_tracking_guidance_non_invariant(self):
        tracker = InvariantTracker()
        guidance = tracker.get_tracking_guidance("brier_score")
        assert guidance["classification"] == "non_invariant"
        assert "short-term" in guidance["guidance"]

    def test_get_history_empty(self):
        tracker = InvariantTracker()
        assert tracker.get_history() == []

    def test_snapshot_graceful_degradation(self):
        # Snapshot with invalid DB path should not crash
        tracker = InvariantTracker(db_path="/nonexistent/path.db")
        snap = tracker.snapshot(test_count=100)
        assert snap.total_memories == 0
        assert snap.test_count == 100
        assert tracker.get_history() == [snap]

    def test_non_invariant_metrics_list_not_empty(self):
        assert len(NON_INVARIANT_METRICS) > 0
