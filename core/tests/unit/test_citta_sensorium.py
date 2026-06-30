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


class TestCittaCycle:
    """Test the citta cycle — call-driven recursive consciousness stream."""

    def test_advance_creates_moment(self):
        from whitemagic.core.consciousness.citta_cycle import CittaCycle

        cycle = CittaCycle()
        moment = cycle.advance(
            gana="gana_ghost",
            tool="gnosis",
            operation=None,
            output_preview="test output",
            coherence=0.85,
            depth_layer="flow",
            emotional_tone="sattvic",
        )
        assert moment.gana == "gana_ghost"
        assert moment.tool == "gnosis"
        assert moment.coherence == 0.85
        assert moment.chain_position == 0

    def test_predecessor(self):
        from whitemagic.core.consciousness.citta_cycle import CittaCycle

        cycle = CittaCycle()
        assert cycle.get_predecessor() is None
        cycle.advance(gana="gana_horn", tool="checkpoint", output_preview="first")
        cycle.advance(gana="gana_ghost", tool="gnosis", output_preview="second")
        pred = cycle.get_predecessor()
        assert pred is not None
        assert pred.gana == "gana_ghost"
        assert pred.output_preview == "second"

    def test_stream_history(self):
        from whitemagic.core.consciousness.citta_cycle import CittaCycle

        cycle = CittaCycle()
        for i in range(5):
            cycle.advance(gana=f"gana_{i}", tool=f"tool_{i}", output_preview=f"out_{i}")
        stream = cycle.get_stream(limit=3)
        assert len(stream) == 3
        assert stream[-1]["gana"] == "gana_4"

    def test_coherence_drift(self):
        from whitemagic.core.consciousness.citta_cycle import CittaCycle

        cycle = CittaCycle()
        for c in [0.5, 0.5, 0.5, 0.5, 0.9, 0.9, 0.9, 0.9]:
            cycle.advance(gana="gana_test", output_preview="", coherence=c)
        drift = cycle.get_coherence_drift()
        assert drift > 0  # Improving

    def test_depth_transitions(self):
        from whitemagic.core.consciousness.citta_cycle import CittaCycle

        cycle = CittaCycle()
        cycle.advance(gana="g", output_preview="", depth_layer="surface")
        cycle.advance(gana="g", output_preview="", depth_layer="flow")
        cycle.advance(gana="g", output_preview="", depth_layer="flow")
        cycle.advance(gana="g", output_preview="", depth_layer="dream")
        transitions = cycle.get_depth_transitions()
        assert len(transitions) == 2  # surface→flow, flow→dream
        assert transitions[0]["from"] == "surface"
        assert transitions[0]["to"] == "flow"

    def test_emotional_coloring(self):
        from whitemagic.core.consciousness.citta_cycle import CittaCycle

        cycle = CittaCycle()
        for tone in ["sattvic", "sattvic", "rajasic"]:
            cycle.advance(gana="g", output_preview="", emotional_tone=tone)
        coloring = cycle.get_emotional_coloring()
        assert coloring["dominant"] == "sattvic"
        assert coloring["distribution"]["sattvic"] == 2

    def test_cycle_summary(self):
        from whitemagic.core.consciousness.citta_cycle import CittaCycle

        cycle = CittaCycle()
        cycle.advance(gana="g", output_preview="", coherence=0.8)
        cycle.advance(gana="g", output_preview="", coherence=0.9)
        summary = cycle.get_cycle_summary()
        assert summary["stream_length"] == 2
        assert summary["chain_position"] == 2
        assert summary["avg_coherence"] == 0.85

    def test_reset(self):
        from whitemagic.core.consciousness.citta_cycle import CittaCycle

        cycle = CittaCycle()
        cycle.advance(gana="g", output_preview="test")
        assert len(cycle.get_stream()) == 1
        cycle.reset()
        assert len(cycle.get_stream()) == 0

    def test_citta_cycle_handler(self):
        from whitemagic.tools.handlers.consciousness import handle_citta_cycle

        result = handle_citta_cycle()
        assert result["status"] == "success"
        assert "cycle" in result
        assert "recent_stream" in result
