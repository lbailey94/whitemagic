"""Tests for Objective F — Holographic Improvement Trajectory."""
from __future__ import annotations

from whitemagic.core.evolution.holographic_trajectory import (
    HolographicPosition,
    TrajectoryTracker,
    VelocityVector,
    compute_position,
    semantic_hash_1d,
)


class TestHolographicPosition:
    def test_defaults(self):
        pos = HolographicPosition()
        assert pos.to_tuple() == (0.0, 0.0, 0.0, 0.0, 0.0)

    def test_distance_to_self(self):
        pos = HolographicPosition(x=1, y=2, z=3, w=4, v=5)
        assert pos.distance_to(pos) == 0.0

    def test_distance_to_other(self):
        p1 = HolographicPosition(x=0, y=0, z=0, w=0, v=0)
        p2 = HolographicPosition(x=3, y=4, z=0, w=0, v=0)
        assert abs(p1.distance_to(p2) - 5.0) < 1e-6


class TestSemanticHash:
    def test_deterministic(self):
        assert semantic_hash_1d("test") == semantic_hash_1d("test")

    def test_different_text_different_hash(self):
        assert semantic_hash_1d("foo") != semantic_hash_1d("bar")

    def test_in_range(self):
        for text in ["a", "b", "long description here", ""]:
            val = semantic_hash_1d(text)
            assert 0.0 <= val < 1.0


class TestComputePosition:
    def test_basic(self):
        pos = compute_position(
            description="Fix untitled memories",
            predicted_impact=0.8,
            cycle=5,
        )
        assert pos.x == 5.0
        assert pos.v == 0.8
        assert 0.0 <= pos.y < 1.0

    def test_clamps_impact(self):
        pos = compute_position("test", predicted_impact=1.5, cycle=1)
        assert pos.v == 1.0

    def test_clamps_valence(self):
        pos = compute_position("test", predicted_impact=0.5, cycle=1, emotional_valence=2.0)
        assert pos.z == 1.0


class TestVelocityVector:
    def test_drifting(self):
        v = VelocityVector(dv=-0.1)
        assert v.is_drifting is True

    def test_not_drifting(self):
        v = VelocityVector(dv=0.1)
        assert v.is_drifting is False

    def test_magnitude(self):
        v = VelocityVector(dx=3, dy=4)
        assert abs(v.magnitude - 5.0) < 1e-6


class TestTrajectoryTracker:
    def test_record_and_retrieve(self):
        tracker = TrajectoryTracker()
        pos = tracker.record("h1", "Fix bugs", 0.8, cycle=1)
        assert pos.v == 0.8
        traj = tracker.get_trajectory("h1")
        assert traj is not None
        assert len(traj.points) == 1

    def test_velocity_after_two_points(self):
        tracker = TrajectoryTracker()
        tracker.record("h1", "Fix bugs", 0.8, cycle=1)
        tracker.record("h1", "Fix bugs", 0.6, cycle=2)
        vel = tracker.get_velocity("h1")
        assert vel is not None
        assert vel.dv < 0  # Impact decreased

    def test_velocity_none_with_one_point(self):
        tracker = TrajectoryTracker()
        tracker.record("h1", "Fix bugs", 0.8, cycle=1)
        assert tracker.get_velocity("h1") is None

    def test_detect_drifting(self):
        tracker = TrajectoryTracker()
        tracker.record("h1", "Fix bugs", 0.8, cycle=1)
        tracker.record("h1", "Fix bugs", 0.5, cycle=2)
        tracker.record("h2", "Add tests", 0.3, cycle=1)
        tracker.record("h2", "Add tests", 0.6, cycle=2)
        drifting = tracker.detect_drifting()
        assert "h1" in drifting
        assert "h2" not in drifting

    def test_detect_convergence(self):
        tracker = TrajectoryTracker()
        # Two hypotheses with same description and impact → same region
        tracker.record("h1", "same desc", 0.7, cycle=1)
        tracker.record("h2", "same desc", 0.7, cycle=1)
        groups = tracker.detect_convergence(threshold=0.5)
        assert len(groups) >= 1
        # Should contain both h1 and h2
        all_in_groups = [hid for group in groups for hid in group]
        assert "h1" in all_in_groups
        assert "h2" in all_in_groups

    def test_no_convergence_with_one_hypothesis(self):
        tracker = TrajectoryTracker()
        tracker.record("h1", "desc", 0.7, cycle=1)
        groups = tracker.detect_convergence()
        assert groups == []

    def test_get_stats(self):
        tracker = TrajectoryTracker()
        tracker.record("h1", "desc", 0.7, cycle=1)
        tracker.record("h1", "desc", 0.5, cycle=2)
        tracker.record("h2", "other", 0.8, cycle=1)
        stats = tracker.get_stats()
        assert stats["total_tracked"] == 2
        assert stats["with_velocity"] == 1
        assert "drifting_count" in stats
