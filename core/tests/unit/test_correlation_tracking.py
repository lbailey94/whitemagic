"""Tests for Objective B — Interaction-Aware MC correlation tracking."""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from whitemagic.core.evolution.autodidactic_loop import (
    AutodidacticLoop,
    PatternApplication,
    PatternOutcome,
)


def _make_loop(tmp_path: Path) -> AutodidacticLoop:
    return AutodidacticLoop(db_path=tmp_path / "test_feedback.db")


def _record_pair(loop: AutodidacticLoop, pattern_a: str, pattern_b: str, success_a: bool, success_b: bool, t: float):
    """Record a pair of outcomes at the same time."""
    for pid, success in [(pattern_a, success_a), (pattern_b, success_b)]:
        app = PatternApplication(
            application_id=f"app_{pid}_{t}",
            pattern_id=pid,
            pattern_type="test",
            timestamp=t,
            initial_confidence=0.7,
            context={},
        )
        loop.record_application(app)
        outcome = PatternOutcome(
            application_id=f"app_{pid}_{t}",
            pattern_id=pid,
            success=success,
            performance_gain=None,
            quality_score=None,
            user_feedback=None,
            measured_at=t,
            metrics={},
        )
        loop.record_outcome(outcome)


class TestCorrelationTracking:
    def test_correlation_table_exists(self, tmp_path):
        loop = _make_loop(tmp_path)
        conn = sqlite3.connect(str(loop.db_path))
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pattern_correlations'")
        assert c.fetchone() is not None
        conn.close()

    def test_get_correlation_no_data(self, tmp_path):
        loop = _make_loop(tmp_path)
        assert loop.get_correlation("a", "b") == 0.0

    def test_correlation_matrix_identity(self, tmp_path):
        loop = _make_loop(tmp_path)
        matrix = loop.get_correlation_matrix(["a", "b", "c"])
        assert matrix["a"]["a"] == 1.0
        assert matrix["b"]["b"] == 1.0
        assert matrix["a"]["b"] == 0.0

    def test_update_correlations_positive(self, tmp_path):
        loop = _make_loop(tmp_path)
        base = time.time()
        # Correlated outcomes: a and b succeed/fail together
        _record_pair(loop, "a", "b", True, True, base)
        _record_pair(loop, "a", "b", False, False, base + 10)
        _record_pair(loop, "a", "b", True, True, base + 20)
        _record_pair(loop, "a", "b", False, False, base + 30)

        corr = loop.get_correlation("a", "b")
        # Should be positive (both vary together)
        assert corr > 0.0

    def test_update_correlations_negative(self, tmp_path):
        loop = _make_loop(tmp_path)
        base = time.time()
        # Record anti-correlated outcomes: when a succeeds, b fails
        _record_pair(loop, "a", "b", True, False, base)
        _record_pair(loop, "a", "b", True, False, base + 10)
        _record_pair(loop, "a", "b", False, True, base + 20)
        _record_pair(loop, "a", "b", False, True, base + 30)

        corr = loop.get_correlation("a", "b")
        # Should be negative
        assert corr < 0.0

    def test_get_all_correlations_empty(self, tmp_path):
        loop = _make_loop(tmp_path)
        assert loop.get_all_correlations() == []

    def test_get_all_correlations_with_data(self, tmp_path):
        loop = _make_loop(tmp_path)
        base = time.time()
        _record_pair(loop, "a", "b", True, True, base)
        _record_pair(loop, "a", "b", False, False, base + 10)
        _record_pair(loop, "a", "b", True, True, base + 20)
        _record_pair(loop, "a", "b", False, False, base + 30)

        corrs = loop.get_all_correlations()
        assert len(corrs) >= 1
        assert "pattern_a" in corrs[0]
        assert "correlation" in corrs[0]

    def test_correlation_matrix_with_data(self, tmp_path):
        loop = _make_loop(tmp_path)
        base = time.time()
        _record_pair(loop, "a", "b", True, True, base)
        _record_pair(loop, "a", "b", False, False, base + 10)
        _record_pair(loop, "a", "b", True, True, base + 20)
        _record_pair(loop, "a", "b", False, False, base + 30)

        matrix = loop.get_correlation_matrix(["a", "b"])
        assert matrix["a"]["a"] == 1.0
        assert matrix["b"]["b"] == 1.0
        assert matrix["a"]["b"] != 0.0
