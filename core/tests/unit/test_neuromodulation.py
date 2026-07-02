"""Unit tests for neuromodulation system."""

import os
import tempfile

os.environ.setdefault("WM_STATE_ROOT", tempfile.mkdtemp(prefix="wm_test_neuro_mod_"))
os.environ.setdefault("WM_SILENT_INIT", "1")
os.environ.setdefault("WM_SKIP_POLYGLOT", "1")

from whitemagic.core.memory.neuromodulation import compute, modulate, reset, stats  # noqa: E402


class TestCompute:
    def test_basic_compute(self):
        result = compute(novelty=0.8, reward=0.9, stability=0.7, coherence=0.6, focus=0.8, activity_level=0.5)
        assert "da" in result
        assert "sht" in result
        assert "ach" in result
        assert 0 <= result["da"] <= 1.0
        assert 0 <= result["sht"] <= 1.0
        assert 0 <= result["ach"] <= 1.0
        assert "learning_rate_boost" in result
        assert "consolidation_priority" in result
        assert "attention_focus" in result

    def test_high_novelty_boosts_da(self):
        reset()
        r_low = compute(novelty=0.1, reward=0.1, stability=0.5, coherence=0.5, focus=0.5, activity_level=0.5)
        reset()
        r_high = compute(novelty=0.9, reward=0.9, stability=0.5, coherence=0.5, focus=0.5, activity_level=0.5)
        assert r_high["da"] > r_low["da"]

    def test_high_focus_boosts_ach(self):
        reset()
        r_low = compute(novelty=0.5, reward=0.5, stability=0.5, coherence=0.5, focus=0.1, activity_level=0.1)
        reset()
        r_high = compute(novelty=0.5, reward=0.5, stability=0.5, coherence=0.5, focus=0.9, activity_level=0.9)
        assert r_high["ach"] > r_low["ach"]

    def test_high_stability_boosts_sht(self):
        reset()
        r_low = compute(novelty=0.5, reward=0.5, stability=0.1, coherence=0.1, focus=0.5, activity_level=0.5)
        reset()
        r_high = compute(novelty=0.5, reward=0.5, stability=0.9, coherence=0.9, focus=0.5, activity_level=0.5)
        assert r_high["sht"] > r_low["sht"]

    def test_decay_over_time(self):
        reset()
        r1 = compute(novelty=0.9, reward=0.9, stability=0.5, coherence=0.5, focus=0.5, activity_level=0.5)
        r2 = compute(novelty=0.1, reward=0.1, stability=0.5, coherence=0.5, focus=0.5, activity_level=0.5)
        # DA should decay with low novelty/reward
        assert r2["da"] < r1["da"]


class TestModulate:
    def test_modulate_memories(self):
        memories = [
            {"memory_id": "m1", "importance": 0.5, "novelty": 0.8, "is_active": True},
            {"memory_id": "m2", "importance": 0.9, "novelty": 0.2, "is_active": False},
        ]
        result = modulate(memories, da=0.8, sht=0.7, ach=0.6)
        assert result["total"] == 2
        assert all("modulated_importance" in m for m in result["modulated"])
        # Active memory should get ACh boost
        assert result["modulated"][0]["ach_boost"] > 0
        # Inactive memory should get no ACh boost
        assert result["modulated"][1]["ach_boost"] == 0

    def test_modulate_empty(self):
        result = modulate([])
        assert result["total"] == 0


class TestReset:
    def test_reset(self):
        compute(novelty=0.9, reward=0.9)
        result = reset()
        assert result["status"] == "success"


class TestStats:
    def test_stats(self):
        s = stats()
        assert "da" in s
        assert "sht" in s
        assert "ach" in s
        assert "total_computations" in s
        assert "backend" in s
        assert s["backend"] in ("julia", "python")
