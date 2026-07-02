"""Unit tests for neuro-cognitive hot-path modules."""

import os
import tempfile

os.environ.setdefault("WM_STATE_ROOT", tempfile.mkdtemp(prefix="wm_test_hotpath_"))
os.environ.setdefault("WM_SILENT_INIT", "1")

from whitemagic.core.memory.neuro_hotpath import (  # noqa: E402
    ThalamicGating,
    PredictiveCoder,
    MomentumDynamics,
    get_thalamic_gating,
    get_predictive_coder,
    get_momentum_dynamics,
)


class TestThalamicGating:
    def test_default_context(self):
        g = ThalamicGating()
        assert g.get_context() == "default"

    def test_set_context(self):
        g = ThalamicGating()
        g.set_context("coding")
        assert g.get_context() == "coding"

    def test_unknown_context_falls_back(self):
        g = ThalamicGating()
        g.set_context("nonexistent")
        assert g.get_context() == "default"

    def test_compute_weights(self):
        g = ThalamicGating()
        g.set_context("coding")
        w = g.compute_weights(["codex", "citta", "universal"])
        assert w["codex"] > w["citta"]
        assert w["codex"] > w["universal"]

    def test_apply_to_scores(self):
        g = ThalamicGating()
        g.set_context("introspection")
        result = g.apply_to_scores([("citta", 1.0), ("codex", 1.0)])
        citta = [s for n, s in result if n == "citta"][0]
        codex = [s for n, s in result if n == "codex"][0]
        assert citta > codex

    def test_stats(self):
        g = ThalamicGating()
        g.compute_weights(["universal"])
        s = g.stats()
        assert "total_calls" in s
        assert "backend" in s
        assert s["backend"] in ("rust", "python")


class TestPredictiveCoder:
    def test_empty_predict(self):
        c = PredictiveCoder(5, 4)
        assert c.predict() == [0.0, 0.0, 0.0, 0.0]

    def test_observe_and_predict(self):
        c = PredictiveCoder(5, 3)
        c.observe([1.0, 0.0, 0.0])
        c.observe([0.0, 1.0, 0.0])
        pred = c.predict()
        assert abs(pred[0] - 0.5) < 0.01
        assert abs(pred[1] - 0.5) < 0.01

    def test_prediction_error_zero_for_matching(self):
        c = PredictiveCoder(5, 3)
        c.observe([1.0, 1.0, 1.0])
        assert c.prediction_error([1.0, 1.0, 1.0]) < 0.01

    def test_prediction_error_nonzero_for_different(self):
        c = PredictiveCoder(5, 3)
        c.observe([1.0, 0.0, 0.0])
        assert c.prediction_error([0.0, 1.0, 0.0]) > 0.5

    def test_window_eviction(self):
        c = PredictiveCoder(2, 2)
        c.observe([1.0, 0.0])
        c.observe([0.0, 1.0])
        c.observe([1.0, 1.0])
        pred = c.predict()
        assert abs(pred[0] - 0.5) < 0.01
        assert abs(pred[1] - 1.0) < 0.01

    def test_novelty_score(self):
        c = PredictiveCoder(5, 3)
        c.observe([1.0, 0.0, 0.0])
        e = c.prediction_error([1.0, 0.0, 0.0])
        n = c.novelty_score(e)
        assert 0.0 <= n <= 1.0

    def test_stats(self):
        c = PredictiveCoder(5, 3)
        c.process([1.0, 0.0, 0.0])
        s = c.stats()
        assert "total_predictions" in s
        assert "backend" in s


class TestMomentumDynamics:
    def test_empty(self):
        m = MomentumDynamics()
        assert m.get("nonexistent") == 0.0

    def test_update_and_get(self):
        m = MomentumDynamics()
        m.update({"node1": 0.8})
        assert m.get("node1") > 0.0

    def test_momentum_accumulates(self):
        m = MomentumDynamics()
        m.update({"n": 0.5})
        m1 = m.get("n")
        m.update({"n": 0.5})
        m2 = m.get("n")
        assert m2 > m1

    def test_decay_reduces(self):
        m = MomentumDynamics(0.9, 0.5)
        m.update({"n": 0.8})
        m1 = m.get("n")
        m.decay()
        m2 = m.get("n")
        assert m2 < m1

    def test_decay_prunes_weak(self):
        m = MomentumDynamics(0.9, 0.1)
        m.update({"weak": 0.01})
        m.decay()
        assert m.get("weak") == 0.0

    def test_apply_momentum(self):
        m = MomentumDynamics()
        m.update({"a": 1.0})
        boosted = m.apply_momentum([("a", 0.5), ("b", 0.5)])
        a = [s for n, s in boosted if n == "a"][0]
        b = [s for n, s in boosted if n == "b"][0]
        assert a > b

    def test_active_nodes(self):
        m = MomentumDynamics()
        m.update({"high": 0.9, "low": 0.05})
        active = m.active_nodes(0.1)
        assert len(active) == 1
        assert active[0][0] == "high"

    def test_stats(self):
        m = MomentumDynamics()
        m.update({"n": 0.5})
        s = m.stats()
        assert "total_updates" in s
        assert "backend" in s


class TestSingletons:
    def test_get_thalamic_gating(self):
        g = get_thalamic_gating()
        assert g is not None
        assert g is get_thalamic_gating()

    def test_get_predictive_coder(self):
        c = get_predictive_coder()
        assert c is not None
        assert c is get_predictive_coder()

    def test_get_momentum_dynamics(self):
        m = get_momentum_dynamics()
        assert m is not None
        assert m is get_momentum_dynamics()
