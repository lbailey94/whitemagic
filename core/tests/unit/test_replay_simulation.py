"""Unit tests for replay simulation system."""

import os
import tempfile

os.environ.setdefault("WM_STATE_ROOT", tempfile.mkdtemp(prefix="wm_test_replay_"))
os.environ.setdefault("WM_SILENT_INIT", "1")
os.environ.setdefault("WM_SKIP_POLYGLOT", "1")

from whitemagic.core.memory.replay_simulation import (  # noqa: E402
    batch_replay,
    replay,
    stats,
)


class TestReplay:
    def test_empty_sequence(self):
        result = replay([])
        assert result["total_items"] == 0
        assert result["trajectory_count"] == 0

    def test_basic_replay(self):
        seq = [
            {"memory_id": "m1", "timestamp": 0.0, "importance": 0.8, "galaxy": "universal"},
            {"memory_id": "m2", "timestamp": 5.0, "importance": 0.7, "galaxy": "universal"},
            {"memory_id": "m3", "timestamp": 10.0, "importance": 0.9, "galaxy": "codex"},
        ]
        result = replay(seq)
        assert result["total_items"] == 3
        assert len(result["replayed"]) == 3
        # STDP should boost items near neighbors
        assert all(r["replay_strength"] >= 0 for r in result["replayed"])

    def test_stdp_strengthens_close_memories(self):
        seq = [
            {"memory_id": "a", "timestamp": 0.0, "importance": 0.5},
            {"memory_id": "b", "timestamp": 2.0, "importance": 0.5},
        ]
        result = replay(seq)
        # Both should have boosted strength from STDP
        assert result["replayed"][0]["replay_strength"] > 0.5
        assert result["replayed"][1]["replay_strength"] > 0.5

    def test_stdp_window_cutoff(self):
        seq = [
            {"memory_id": "x", "timestamp": 0.0, "importance": 0.5},
            {"memory_id": "y", "timestamp": 100.0, "importance": 0.5},
        ]
        result = replay(seq)
        # No STDP boost because dt > window
        assert abs(result["replayed"][0]["replay_strength"] - 0.5) < 0.01
        assert abs(result["replayed"][1]["replay_strength"] - 0.5) < 0.01

    def test_trajectory_detection(self):
        seq = [
            {"memory_id": "t1", "timestamp": 0.0, "importance": 0.9},
            {"memory_id": "t2", "timestamp": 3.0, "importance": 0.9},
            {"memory_id": "t3", "timestamp": 6.0, "importance": 0.9},
        ]
        result = replay(seq)
        assert result["trajectory_count"] >= 1
        assert any(["t1", "t2", "t3"] == t or ["t1", "t2"] == t for t in result["trajectories"])


class TestBatchReplay:
    def test_batch(self):
        batches = [
            [{"memory_id": "b1", "timestamp": 0.0, "importance": 0.8}],
            [{"memory_id": "b2", "timestamp": 0.0, "importance": 0.7}, {"memory_id": "b3", "timestamp": 5.0, "importance": 0.6}],
        ]
        result = batch_replay(batches)
        assert result["total"] == 2


class TestStats:
    def test_stats(self):
        s = stats()
        assert "total_replays" in s
        assert "backend" in s
        assert s["backend"] in ("haskell", "python")
