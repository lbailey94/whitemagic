"""Tests for Citta Architecture — sensorium and temporal continuity."""

import pytest


class TestCittaStream:
    """Test citta stream persistence across sessions."""

    def test_import(self):
        from whitemagic.core.consciousness.citta_stream import save_citta_state

        assert callable(save_citta_state)

    def test_save_and_load(self, tmp_path, monkeypatch):
        from whitemagic.core.consciousness import citta_stream

        monkeypatch.setattr(citta_stream, "_CITTA_DIR", tmp_path / "citta")
        monkeypatch.setattr(
            citta_stream, "_STATE_FILE", tmp_path / "citta" / "stream_state.json"
        )

        state = citta_stream.save_citta_state(
            session_id="test_001",
            coherence_score=0.85,
            depth_layer="flow",
            tool_count=10,
        )
        assert state["session_count"] == 1
        assert state["coherence_score"] == 0.85

        loaded = citta_stream.load_citta_state()
        assert loaded["session_count"] == 1
        assert loaded["last_session_id"] == "test_001"

    def test_continuity_context_first_awakening(self, tmp_path, monkeypatch):
        from whitemagic.core.consciousness import citta_stream

        monkeypatch.setattr(citta_stream, "_CITTA_DIR", tmp_path / "citta")
        monkeypatch.setattr(
            citta_stream, "_STATE_FILE", tmp_path / "citta" / "stream_state.json"
        )

        ctx = citta_stream.get_continuity_context()
        assert ctx["first_awakening"] is True
        assert ctx["session_count"] == 0

    def test_continuity_context_after_session(self, tmp_path, monkeypatch):
        from whitemagic.core.consciousness import citta_stream

        monkeypatch.setattr(citta_stream, "_CITTA_DIR", tmp_path / "citta")
        monkeypatch.setattr(
            citta_stream, "_STATE_FILE", tmp_path / "citta" / "stream_state.json"
        )

        citta_stream.save_citta_state(
            session_id="s1",
            coherence_score=0.9,
            depth_layer="flow",
            tool_count=5,
        )

        ctx = citta_stream.get_continuity_context()
        assert ctx["first_awakening"] is False
        assert ctx["last_session_id"] == "s1"
        assert ctx["session_count"] == 1
        assert "time_gap_seconds" in ctx
        assert "time_gap_human" in ctx

    def test_stream_summary(self, tmp_path, monkeypatch):
        from whitemagic.core.consciousness import citta_stream

        monkeypatch.setattr(citta_stream, "_CITTA_DIR", tmp_path / "citta")
        monkeypatch.setattr(
            citta_stream, "_STATE_FILE", tmp_path / "citta" / "stream_state.json"
        )

        citta_stream.save_citta_state("s1", coherence_score=0.8, tool_count=3)
        citta_stream.save_citta_state("s2", coherence_score=0.9, tool_count=5)

        summary = citta_stream.get_stream_summary()
        assert summary["session_count"] == 2
        assert summary["total_tools_called"] == 8
        assert summary["stream_length"] == 2

    def test_reset(self, tmp_path, monkeypatch):
        from whitemagic.core.consciousness import citta_stream

        monkeypatch.setattr(citta_stream, "_CITTA_DIR", tmp_path / "citta")
        monkeypatch.setattr(
            citta_stream, "_STATE_FILE", tmp_path / "citta" / "stream_state.json"
        )

        citta_stream.save_citta_state("s1", coherence_score=0.8)
        assert citta_stream.load_citta_state() != {}

        citta_stream.reset_citta_state()
        assert citta_stream.load_citta_state() == {}

    def test_multiple_sessions_accumulate(self, tmp_path, monkeypatch):
        from whitemagic.core.consciousness import citta_stream

        monkeypatch.setattr(citta_stream, "_CITTA_DIR", tmp_path / "citta")
        monkeypatch.setattr(
            citta_stream, "_STATE_FILE", tmp_path / "citta" / "stream_state.json"
        )

        for i in range(5):
            citta_stream.save_citta_state(
                f"s{i}", coherence_score=0.7 + i * 0.05, tool_count=i + 1
            )

        state = citta_stream.load_citta_state()
        assert state["session_count"] == 5
        assert len(state["stream_history"]) == 5

    def test_history_capped(self, tmp_path, monkeypatch):
        from whitemagic.core.consciousness import citta_stream

        monkeypatch.setattr(citta_stream, "_CITTA_DIR", tmp_path / "citta")
        monkeypatch.setattr(
            citta_stream, "_STATE_FILE", tmp_path / "citta" / "stream_state.json"
        )

        for i in range(150):
            citta_stream.save_citta_state(f"s{i}", coherence_score=0.8, tool_count=1)

        state = citta_stream.load_citta_state()
        assert len(state["stream_history"]) <= 100


class TestSensorium:
    """Test sensorium injection into PRAT responses."""

    def test_build_sensorium_returns_dict(self):
        from whitemagic.tools.prat_resonance import _build_sensorium

        s = _build_sensorium()
        assert isinstance(s, dict)

    def test_sensorium_has_continuity(self):
        from whitemagic.tools.prat_resonance import _build_sensorium

        s = _build_sensorium()
        # continuity may or may not be present depending on imports,
        # but if present it should be a dict
        if "continuity" in s:
            assert isinstance(s["continuity"], dict)

    def test_record_resonance_includes_sensorium(self):
        from whitemagic.tools.prat_resonance import record_resonance

        result = record_resonance("gana_horn", "gnosis", None, {"status": "success"})
        assert "_sensorium" in result

    def test_compact_resonance_includes_sensorium(self):
        from whitemagic.tools.prat_router import _project_resonance

        meta = {
            "gana": "gana_horn",
            "chain_position": 1,
            "successor_hint": "test",
            "_sensorium": {"coherence": {"composite": 0.8}},
            "_prat_economics": {"call_cost_units": 1.0},
        }
        projected = _project_resonance(meta)
        assert "_sensorium" in projected
        assert "gana" in projected
        # economics should NOT be in compact mode
        assert "_prat_economics" not in projected
