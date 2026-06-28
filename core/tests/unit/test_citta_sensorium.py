"""Tests for Citta Sensorium — consciousness state injection into PRAT responses."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

os.environ.setdefault("WM_STATE_ROOT", str(Path(tempfile.mkdtemp())))
os.environ.setdefault("WM_SILENT_INIT", "1")


class TestSensorium:
    """Test the _build_sensorium function that injects consciousness state."""

    def test_sensorium_returns_dict(self):
        from whitemagic.tools.prat_resonance import _build_sensorium
        s = _build_sensorium()
        assert isinstance(s, dict)

    def test_sensorium_has_coherence(self):
        from whitemagic.tools.prat_resonance import _build_sensorium
        s = _build_sensorium()
        assert "coherence" in s
        assert "state" in s["coherence"]

    def test_sensorium_has_continuity(self):
        from whitemagic.tools.prat_resonance import _build_sensorium
        s = _build_sensorium()
        assert "continuity" in s

    def test_sensorium_has_session_duration(self):
        from whitemagic.tools.prat_resonance import _build_sensorium
        s = _build_sensorium()
        assert "session_duration_s" in s
        assert isinstance(s["session_duration_s"], float)
        assert s["session_duration_s"] >= 0

    def test_session_state_module(self):
        from whitemagic.tools.session_state import (
            ensure_session_started,
            get_session_start_time,
            reset_session,
        )
        reset_session()
        assert get_session_start_time() is None
        t = ensure_session_started()
        assert t is not None
        assert get_session_start_time() == t


class TestDepthGauge:
    """Test the depth gauge that tracks consciousness layers."""

    def test_instantiate(self):
        from whitemagic.core.consciousness.depth_gauge import ConsciousnessDepthGauge
        gauge = ConsciousnessDepthGauge()
        assert gauge is not None

    def test_layers_exist(self):
        from whitemagic.core.consciousness.depth_gauge import ConsciousnessLayer
        assert hasattr(ConsciousnessLayer, "SURFACE")
        assert hasattr(ConsciousnessLayer, "FLOW")
        assert hasattr(ConsciousnessLayer, "DREAM")


class TestCittaStream:
    """Test the citta stream continuity module."""

    def test_get_continuity_context(self):
        from whitemagic.core.consciousness.citta_stream import get_continuity_context
        ctx = get_continuity_context()
        assert isinstance(ctx, dict)
        assert "first_awakening" in ctx

    def test_save_and_load(self):
        from whitemagic.core.consciousness.citta_stream import (
            get_stream_summary,
            reset_citta_state,
            save_citta_state,
        )
        reset_citta_state()
        save_citta_state({"test": "data", "session_count": 1})
        summary = get_stream_summary()
        assert isinstance(summary, dict)


class TestCoherence:
    """Test the coherence metric module."""

    def test_instantiate(self):
        from whitemagic.core.consciousness.coherence import CoherenceMetric
        metric = CoherenceMetric()
        assert metric is not None

    def test_measure(self):
        from whitemagic.core.consciousness.coherence import CoherenceMetric
        metric = CoherenceMetric()
        scores = metric.measure()
        assert scores is not None  # May be dict or float depending on impl


class TestResonanceCompactIncludesSensorium:
    """Verify that _sensorium is in the compact keys set."""

    def test_sensorium_in_compact_keys(self):
        from whitemagic.tools.prat_router import _RESONANCE_COMPACT_KEYS
        assert "_sensorium" in _RESONANCE_COMPACT_KEYS


class TestTemporalContinuity:
    """Test citta stream temporal continuity — persist across sessions."""

    def test_save_and_load_cycle(self):
        from whitemagic.core.consciousness.citta_stream import (
            load_citta_state,
            reset_citta_state,
            save_citta_state,
        )
        reset_citta_state()
        assert load_citta_state() == {}
        save_citta_state(
            session_id="test_session_1",
            coherence_score=0.85,
            depth_layer="flow",
            tool_count=5,
            emotional_tone="sattvic",
            extra={"last_gana": "gana_ghost", "summary": "test activity"},
        )
        state = load_citta_state()
        assert state["last_session_id"] == "test_session_1"
        assert state["session_count"] == 1
        assert state["coherence_score"] == 0.85
        reset_citta_state()

    def test_continuity_context_after_save(self):
        from whitemagic.core.consciousness.citta_stream import (
            get_continuity_context,
            reset_citta_state,
            save_citta_state,
        )
        reset_citta_state()
        save_citta_state(
            session_id="test_session_2",
            coherence_score=0.72,
            depth_layer="terminal",
            tool_count=3,
            emotional_tone="rajasic",
            extra={"summary": "was working on tests"},
        )
        ctx = get_continuity_context()
        assert ctx["first_awakening"] is False
        assert ctx["last_session_id"] == "test_session_2"
        assert ctx["session_count"] == 1
        assert ctx["time_gap_seconds"] >= 0
        assert ctx["where_we_left_off"] == "was working on tests"
        reset_citta_state()

    def test_continuity_context_first_awakening(self):
        from whitemagic.core.consciousness.citta_stream import (
            get_continuity_context,
            reset_citta_state,
        )
        reset_citta_state()
        ctx = get_continuity_context()
        assert ctx["first_awakening"] is True
        assert ctx["session_count"] == 0

    def test_stream_summary(self):
        from whitemagic.core.consciousness.citta_stream import (
            get_stream_summary,
            reset_citta_state,
            save_citta_state,
        )
        reset_citta_state()
        save_citta_state(session_id="s1", coherence_score=0.8, depth_layer="surface")
        save_citta_state(session_id="s2", coherence_score=0.9, depth_layer="flow")
        summary = get_stream_summary()
        assert summary["session_count"] == 2
        assert summary["stream_length"] == 2
        assert 0.8 <= summary["avg_coherence"] <= 0.9
        reset_citta_state()

    def test_citta_continuity_handler(self):
        from whitemagic.tools.handlers.consciousness import handle_citta_continuity
        result = handle_citta_continuity()
        assert result["status"] == "success"
        assert "continuity" in result

    def test_citta_stream_summary_handler(self):
        from whitemagic.tools.handlers.consciousness import handle_citta_stream_summary
        result = handle_citta_stream_summary()
        assert result["status"] == "success"
        assert "summary" in result

    def test_citta_sensorium_handler(self):
        from whitemagic.tools.handlers.consciousness import handle_citta_sensorium
        result = handle_citta_sensorium()
        assert result["status"] == "success"
        assert "sensorium" in result
