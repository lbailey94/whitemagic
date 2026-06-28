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
