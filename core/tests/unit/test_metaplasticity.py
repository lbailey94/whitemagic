"""Unit tests for metaplasticity system."""

import os
import tempfile

os.environ.setdefault("WM_STATE_ROOT", tempfile.mkdtemp(prefix="wm_test_meta_"))
os.environ.setdefault("WM_SILENT_INIT", "1")

from whitemagic.core.memory.metaplasticity import MetaplasticityEngine  # noqa: E402


class TestMetaplasticity:
    def test_default_threshold(self):
        e = MetaplasticityEngine()
        assert e.get_threshold("new-mem") == 0.5

    def test_record_access_increases_threshold(self):
        e = MetaplasticityEngine()
        t0 = e.get_threshold("m1")
        for _ in range(10):
            e.record_access("m1")
        t1 = e.get_threshold("m1")
        assert t1 > t0

    def test_frequent_access_makes_stable(self):
        e = MetaplasticityEngine()
        # Access m-frequent many times
        for _ in range(20):
            e.record_access("m-frequent")
        # m-rare is never accessed
        assert e.get_threshold("m-frequent") > e.get_threshold("m-rare")

    def test_plasticity_score_inverse_to_threshold(self):
        e = MetaplasticityEngine()
        for _ in range(20):
            e.record_access("stable-mem")
        p_stable = e.get_plasticity_score("stable-mem")
        p_plastic = e.get_plasticity_score("never-accessed")
        assert p_plastic > p_stable

    def test_apply_modification_attenuates(self):
        e = MetaplasticityEngine()
        # Make memory very stable
        for _ in range(20):
            e.record_access("stable")
        result = e.apply_modification("stable", 1.0)
        assert result["applied_delta"] < result["requested_delta"]
        assert result["attenuation"] < 1.0

    def test_apply_modification_fresh_memory(self):
        e = MetaplasticityEngine()
        result = e.apply_modification("fresh", 0.5)
        # Fresh memory should have minimal attenuation
        assert result["applied_delta"] > 0.3

    def test_batch_update(self):
        e = MetaplasticityEngine()
        results = e.batch_update([
            {"memory_id": "b1", "delta": 0.5},
            {"memory_id": "b2", "delta": 0.8},
        ])
        assert len(results) == 2
        assert all("applied_delta" in r for r in results)

    def test_decay_all(self):
        e = MetaplasticityEngine()
        for _ in range(10):
            e.record_access("d1")
        count = e.decay_all()
        assert count >= 1

    def test_stats(self):
        e = MetaplasticityEngine()
        e.record_access("s1")
        s = e.stats()
        assert "total_updates" in s
        assert "tracked_memories" in s
        assert "avg_threshold" in s

    def test_can_modify(self):
        e = MetaplasticityEngine()
        # Fresh memory: small delta should be allowed
        assert e.can_modify("fresh", 0.5) is True
        # Very small delta might not exceed threshold
        assert e.can_modify("fresh", 0.001) is False
