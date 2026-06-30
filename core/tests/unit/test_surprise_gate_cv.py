"""Tests for cardinality velocity-enhanced surprise gate."""
import time
from collections import deque
from unittest.mock import patch

from whitemagic.core.memory.surprise_gate import (
    CardinalityVelocity,
    SurpriseAction,
    SurpriseGate,
)


class TestCardinalityVelocity:
    def test_velocity_empty(self):
        cv = CardinalityVelocity(window_seconds=60, samples=deque(maxlen=100))
        assert cv.velocity() == 0.0

    def test_velocity_single_sample(self):
        cv = CardinalityVelocity(window_seconds=60, samples=deque(maxlen=100))
        cv.record(100)
        assert cv.velocity() == 0.0

    def test_velocity_two_samples(self):
        cv = CardinalityVelocity(window_seconds=60, samples=deque(maxlen=100))
        cv.record(100)
        time.sleep(0.01)
        cv.record(200)
        v = cv.velocity()
        assert v > 0.0

    def test_velocity_prunes_old_samples(self):
        cv = CardinalityVelocity(window_seconds=0.05, samples=deque(maxlen=100))
        cv.record(100)
        time.sleep(0.1)
        cv.record(200)
        # First sample should be pruned
        assert len(cv.samples) == 1

    def test_is_accelerating_false_for_few_samples(self):
        cv = CardinalityVelocity(window_seconds=60, samples=deque(maxlen=100))
        cv.record(100)
        cv.record(200)
        assert cv.is_accelerating() is False

    def test_is_accelerating_true(self):
        cv = CardinalityVelocity(window_seconds=60, samples=deque(maxlen=100))
        # Slow growth first
        cv.samples.append((time.time() - 10, 100))
        cv.samples.append((time.time() - 8, 110))
        # Fast growth second half
        cv.samples.append((time.time() - 2, 200))
        cv.samples.append((time.time(), 400))
        assert cv.is_accelerating() is True


class TestSurpriseGateCardinality:
    def test_gate_initializes_with_cv(self):
        gate = SurpriseGate(enable_cardinality_velocity=True)
        assert gate._enable_cv is True
        assert gate._cardinality_hll is not None
        assert gate._velocity is not None

    def test_gate_without_cv(self):
        gate = SurpriseGate(enable_cardinality_velocity=False)
        assert gate._enable_cv is False
        assert gate._cardinality_hll is None

    def test_adaptive_thresholds_start_at_defaults(self):
        gate = SurpriseGate(high_threshold=3.0, low_threshold=1.0)
        assert gate._adaptive_high == 3.0
        assert gate._adaptive_low == 1.0

    def test_stats_include_cv_info(self):
        gate = SurpriseGate(enable_cardinality_velocity=True)
        stats = gate.get_stats()
        assert "cardinality_velocity" in stats
        assert "adaptive_high_threshold" in stats
        assert "adaptive_low_threshold" in stats
        assert "distinct_seen" in stats

    def test_stats_without_cv(self):
        gate = SurpriseGate(enable_cardinality_velocity=False)
        stats = gate.get_stats()
        assert "cardinality_velocity" not in stats

    def test_adjust_thresholds_relaxes_on_acceleration(self):
        gate = SurpriseGate(high_threshold=3.0, low_threshold=1.0)
        # Simulate accelerating cardinality
        now = time.time()
        gate._velocity.samples.append((now - 10, 100))
        gate._velocity.samples.append((now - 8, 120))
        gate._velocity.samples.append((now - 2, 300))
        gate._velocity.samples.append((now, 600))
        gate._adjust_thresholds()
        assert gate._adaptive_high > 3.0  # Relaxed

    def test_adjust_thresholds_tightens_on_low_velocity(self):
        gate = SurpriseGate(high_threshold=3.0, low_threshold=1.0)
        # Simulate near-zero velocity (plateau)
        now = time.time()
        gate._velocity.samples.append((now - 10, 100))
        gate._velocity.samples.append((now, 101))
        gate._adjust_thresholds()
        assert gate._adaptive_high < 3.0  # Tightened

    def test_adjust_thresholds_drifts_to_default(self):
        gate = SurpriseGate(high_threshold=3.0, low_threshold=1.0)
        # Set adaptive away from defaults
        gate._adaptive_high = 4.0
        gate._adaptive_low = 1.5
        # Normal velocity (not accelerating, not low)
        now = time.time()
        gate._velocity.samples.append((now - 10, 100))
        gate._velocity.samples.append((now, 150))
        gate._adjust_thresholds()
        # Should drift toward defaults
        assert gate._adaptive_high < 4.0
        assert gate._adaptive_low < 1.5

    def test_evaluate_tracks_cardinality(self):
        gate = SurpriseGate(enable_cardinality_velocity=True)
        # Mock embedding engine as unavailable to ensure consistent CREATE verdict
        # (without this, a prior test may load embeddings causing REINFORCE)
        with patch(
            "whitemagic.core.memory.embeddings.get_embedding_engine",
            side_effect=ImportError("test mock"),
        ):
            verdict = gate.evaluate("test content for cardinality tracking")
        assert verdict.action in (SurpriseAction.CREATE, SurpriseAction.CREATE_BOOSTED)
        stats = gate.get_stats()
        assert stats["distinct_seen"] > 0
