"""Unit tests for neuro-cognitive extensions: homeostatic scaling, disinhibition, TRN hard gate, Rust PyO3."""

import os
import tempfile

import pytest

os.environ.setdefault("WM_SKIP_POLYGLOT", "1")
os.environ.setdefault("WM_SILENT_INIT", "1")
os.environ.setdefault("WM_STATE_ROOT", tempfile.mkdtemp(prefix="wm_test_ext_"))


class TestHomeostaticScaling:
    """Test homeostatic edge scaling in sleep consolidation."""

    def test_report_has_edges_scaled(self):
        from whitemagic.core.memory.sleep_consolidation import ConsolidationReport
        r = ConsolidationReport()
        d = r.to_dict()
        assert "edges_scaled" in d
        assert d["edges_scaled"] == 0

    def test_scaling_method_exists(self):
        from whitemagic.core.memory.sleep_consolidation import SleepConsolidation
        c = SleepConsolidation()
        assert hasattr(c, "_homeostatic_scaling")

    def test_scaling_pulls_toward_target(self, tmp_path):
        import sqlite3
        from whitemagic.core.memory.sleep_consolidation import SleepConsolidation

        db = str(tmp_path / "test.db")
        conn = sqlite3.connect(db)
        conn.execute(
            "CREATE TABLE associations (source_id TEXT, target_id TEXT, strength REAL, "
            "direction TEXT, relation_type TEXT, edge_type TEXT, created_at TEXT, ingestion_time TEXT)"
        )
        for _ in range(5):
            conn.execute(
                "INSERT INTO associations VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ("a", "b", 0.9, "forward", "test", "edge", "now", "now"),
            )
        conn.commit()
        conn.close()

        consol = SleepConsolidation()
        scaled = consol._homeostatic_scaling({"test": db})
        assert scaled == 5

        conn = sqlite3.connect(db)
        strengths = [r[0] for r in conn.execute("SELECT strength FROM associations").fetchall()]
        conn.close()
        mean = sum(strengths) / len(strengths)
        assert mean < 0.9  # Should have moved toward 0.5
        assert mean > 0.5  # But not all the way (5% step)


class TestDisinhibitionModel:
    """Test sleep/wake state-dependent gating."""

    def test_initial_state_is_wake(self):
        from whitemagic.core.memory.disinhibition import DisinhibitionModel, WAKE
        model = DisinhibitionModel()
        state = model.get_state()
        assert state["state_code"] == WAKE
        assert state["state"] == "Wake"

    def test_state_transition_cycle(self):
        from whitemagic.core.memory.disinhibition import DisinhibitionModel, WAKE, LIGHT_SLEEP, DEEP_SLEEP, REM
        model = DisinhibitionModel()
        assert model.get_state()["state_code"] == WAKE
        assert model.transition()["state_code"] == LIGHT_SLEEP
        assert model.transition()["state_code"] == DEEP_SLEEP
        assert model.transition()["state_code"] == REM
        assert model.transition()["state_code"] == WAKE

    def test_weights_differ_by_state(self):
        from whitemagic.core.memory.disinhibition import DisinhibitionModel, WAKE, DEEP_SLEEP
        model = DisinhibitionModel()
        wake_weights = model.get_weights()
        model.set_state(DEEP_SLEEP)
        sleep_weights = model.get_weights()
        assert wake_weights != sleep_weights
        assert sleep_weights["sessions"] < wake_weights["sessions"]

    def test_rem_boosts_dreams(self):
        from whitemagic.core.memory.disinhibition import DisinhibitionModel, REM, WAKE
        model = DisinhibitionModel()
        wake_w = model.get_weights()
        model.set_state(REM)
        rem_w = model.get_weights()
        assert rem_w["dreams"] > wake_w["dreams"]

    def test_disinhibition_levels(self):
        from whitemagic.core.memory.disinhibition import DisinhibitionModel, WAKE, DEEP_SLEEP
        model = DisinhibitionModel()
        assert model.get_state()["disinhibition_level"] == 1.0
        model.set_state(DEEP_SLEEP)
        assert model.get_state()["disinhibition_level"] == 0.2

    def test_stats(self):
        from whitemagic.core.memory.disinhibition import DisinhibitionModel
        model = DisinhibitionModel()
        s = model.stats()
        assert "state" in s
        assert "backend" in s
        assert "total_transitions" in s


class TestThalamicHardGate:
    """Test three-level hard gate for galaxy access."""

    def test_default_allows_all(self):
        from whitemagic.core.memory.thalamic_hard_gate import ThalamicHardGate
        gate = ThalamicHardGate()
        assert gate.check("codex", activation=0.5) is True
        assert gate.check("dreams", activation=0.5) is True

    def test_coding_blocks_citta(self):
        from whitemagic.core.memory.thalamic_hard_gate import ThalamicHardGate
        gate = ThalamicHardGate()
        gate.set_context("coding")
        assert gate.check("citta", activation=0.9) is False
        assert gate.check("codex", activation=0.9) is True

    def test_low_activation_blocked(self):
        from whitemagic.core.memory.thalamic_hard_gate import ThalamicHardGate
        gate = ThalamicHardGate()
        assert gate.check("codex", activation=0.05) is False
        assert gate.check("codex", activation=0.15) is False  # Below PFC threshold
        assert gate.check("codex", activation=0.25) is True

    def test_batch_check(self):
        from whitemagic.core.memory.thalamic_hard_gate import ThalamicHardGate
        gate = ThalamicHardGate()
        gate.set_context("coding")
        results = gate.batch_check([("codex", 0.5), ("citta", 0.5), ("dreams", 0.5)])
        assert results[0] == ("codex", True)
        assert results[1] == ("citta", False)
        assert results[2] == ("dreams", False)

    def test_stats(self):
        from whitemagic.core.memory.thalamic_hard_gate import ThalamicHardGate
        gate = ThalamicHardGate()
        gate.set_context("coding")
        gate.check("citta", activation=0.5)
        gate.check("codex", activation=0.5)
        s = gate.stats()
        assert s["total_checks"] == 2
        assert s["total_blocked"] == 1


class TestRustPyO3Backend:
    """Test that Rust PyO3 backend is available and working."""

    def test_rust_module_imports(self):
        import wm_neuro
        assert hasattr(wm_neuro, "PredictiveCoder")
        # ThalamicGate and MomentumDynamics are Python-only (PyO3 FFI overhead > compute)

    def test_predictive_coder_rust(self):
        import wm_neuro
        pc = wm_neuro.PredictiveCoder(window_size=3, dim=4)
        pc.observe([1.0, 0.0, 0.0, 0.0])
        pc.observe([0.9, 0.1, 0.0, 0.0])
        error = pc.prediction_error([0.8, 0.2, 0.0, 0.0])
        assert error > 0.0
        assert pc.total_predictions == 1

    def test_momentum_dynamics_python(self):
        from whitemagic.core.memory.neuro_hotpath import MomentumDynamics
        md = MomentumDynamics(momentum_coeff=0.9, decay_rate=0.85)
        md.update({"node_a": 0.5, "node_b": 0.3})
        md.update({"node_a": 0.4})
        assert md.get("node_a") > 0.5  # 0.5*0.9 + 0.4 = 0.85
        assert md.stats()["backend"] == "python"

    def test_thalamic_gating_python(self):
        from whitemagic.core.memory.neuro_hotpath import ThalamicGating
        tg = ThalamicGating()
        tg.set_context("coding")
        assert tg.get_context() == "coding"
        assert tg.stats()["backend"] == "python"

    def test_python_wrapper_backend_assignment(self):
        from whitemagic.core.memory.neuro_hotpath import get_thalamic_gating, get_predictive_coder, get_momentum_dynamics
        assert get_thalamic_gating().stats()["backend"] == "python"  # PyO3 FFI overhead > dict lookup
        assert get_predictive_coder().stats()["backend"] == "rust"    # 19x speedup for vector math
        assert get_momentum_dynamics().stats()["backend"] == "python"  # PyO3 FFI overhead > dict update
