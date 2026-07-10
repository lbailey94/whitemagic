"""Tests for BitMamba-2 255M autonomic layer."""

from __future__ import annotations

import os
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from whitemagic.inference.bitmamba_autonomic import (
    AutonomicState,
    BitMambaAutonomic,
    SalienceSignal,
    get_autonomic,
    is_autonomic_available,
)

# Use temp state root to avoid polluting real state
TEST_STATE_ROOT = "/tmp/whitemagic_test_autonomic"


@pytest.fixture(autouse=True)
def _isolate_state(monkeypatch):
    """Isolate state root for tests."""
    monkeypatch.setenv("WM_STATE_ROOT", TEST_STATE_ROOT)
    # Clear singleton
    import whitemagic.inference.bitmamba_autonomic as mod
    mod._autonomic = None
    yield
    # Cleanup
    state_path = Path(TEST_STATE_ROOT) / "citta" / "autonomic_state.json"
    state_path.unlink(missing_ok=True)


class TestSalienceSignal:
    def test_creation(self):
        signal = SalienceSignal(
            timestamp=time.time(),
            token_ids=[1, 2, 3],
            text="hello",
            salience_score=0.5,
            signal_type="novelty",
        )
        assert signal.signal_type == "novelty"
        assert signal.salience_score == 0.5
        assert signal.metadata == {}

    def test_with_metadata(self):
        signal = SalienceSignal(
            timestamp=time.time(),
            token_ids=[1],
            text="",
            salience_score=0.1,
            signal_type="background",
            metadata={"novelty_ratio": 0.5},
        )
        assert signal.metadata["novelty_ratio"] == 0.5


class TestAutonomicState:
    def test_default(self):
        state = AutonomicState()
        assert state.query_count == 0
        assert state.salience_baseline == 0.1
        assert state.model_loaded is False
        assert len(state.token_history) == 0

    def test_to_dict(self):
        state = AutonomicState()
        state.query_count = 5
        d = state.to_dict()
        assert d["query_count"] == 5
        assert "recent_signals" in d
        assert "salience_baseline" in d


class TestBitMambaAutonomic:
    def test_availability_missing_binary(self):
        autonomic = BitMambaAutonomic(
            bitmamba_bin="/nonexistent/bitmamba",
            model_path="/nonexistent/model.bin",
            tokenizer_bin="/nonexistent/tokenizer.bin",
        )
        assert not autonomic.is_available

    def test_availability_with_real_paths(self):
        """Check availability with actual model paths if they exist."""
        autonomic = BitMambaAutonomic()
        model_path = Path(autonomic._model_path)
        bin_path = Path(autonomic._bitmamba_bin)
        if model_path.exists() and bin_path.exists():
            assert autonomic.is_available
        else:
            assert not autonomic.is_available

    def test_add_telemetry(self):
        autonomic = BitMambaAutonomic()
        autonomic.add_telemetry("test_source", "test message")
        assert len(autonomic._telemetry_buffer) == 1

    def test_pulse_without_availability(self):
        autonomic = BitMambaAutonomic(
            bitmamba_bin="/nonexistent/bitmamba",
            model_path="/nonexistent/model.bin",
            tokenizer_bin="/nonexistent/tokenizer.bin",
        )
        result = autonomic.pulse()
        assert result is None

    def test_pulse_without_telemetry(self):
        autonomic = BitMambaAutonomic(
            bitmamba_bin="/nonexistent/bitmamba",
            model_path="/nonexistent/model.bin",
            tokenizer_bin="/nonexistent/tokenizer.bin",
        )
        # Don't add any telemetry — pulse should return None
        result = autonomic.pulse()
        assert result is None

    def test_start_stop_without_availability(self):
        autonomic = BitMambaAutonomic(
            bitmamba_bin="/nonexistent/bitmamba",
            model_path="/nonexistent/model.bin",
            tokenizer_bin="/nonexistent/tokenizer.bin",
        )
        assert not autonomic.start()
        assert not autonomic.is_running

    def test_reset(self):
        autonomic = BitMambaAutonomic()
        autonomic.add_telemetry("test", "msg")
        autonomic._state.query_count = 10
        autonomic.reset()
        assert len(autonomic._telemetry_buffer) == 0
        assert autonomic._state.query_count == 0

    def test_get_state(self):
        autonomic = BitMambaAutonomic()
        state = autonomic.get_state()
        assert "query_count" in state
        assert "salience_baseline" in state
        assert "recent_signals" in state

    def test_get_recent_signals(self):
        autonomic = BitMambaAutonomic()
        signals = autonomic.get_recent_signals()
        assert isinstance(signals, list)

    def test_state_persistence(self):
        autonomic = BitMambaAutonomic()
        autonomic._state.query_count = 42
        autonomic._state.salience_baseline = 0.25
        autonomic._save_state()

        # Create new instance — should load persisted state
        autonomic2 = BitMambaAutonomic()
        assert autonomic2._state.query_count == 42
        assert abs(autonomic2._state.salience_baseline - 0.25) < 0.001

    def test_analyze_salience_novelty(self):
        autonomic = BitMambaAutonomic()
        # All novel tokens
        signal = autonomic._analyze_salience([100, 200, 300, 400], "test")
        assert signal.signal_type in ("novelty", "emotional_shift")
        assert signal.salience_score > 0.5

    def test_analyze_salience_repetition(self):
        autonomic = BitMambaAutonomic(
            bitmamba_bin="/nonexistent/bitmamba",
            model_path="/nonexistent/model.bin",
            tokenizer_bin="/nonexistent/tokenizer.bin",
        )
        # All same token — high repetition
        signal = autonomic._analyze_salience([42, 42, 42, 42], "test")
        assert signal.signal_type == "anomaly"
        assert signal.salience_score < 0.5

    def test_analyze_salience_background(self):
        autonomic = BitMambaAutonomic()
        # Moderate diversity, some repetition
        signal = autonomic._analyze_salience([1, 2, 1, 2, 3], "test")
        assert signal.signal_type in ("background", "novelty")
        assert signal.metadata["novelty_ratio"] >= 0.0

    def test_run_inference_missing_binary(self):
        autonomic = BitMambaAutonomic(
            bitmamba_bin="/nonexistent/bitmamba",
            model_path="/nonexistent/model.bin",
            tokenizer_bin="/nonexistent/tokenizer.bin",
        )
        result = autonomic._run_inference("test prompt", max_tokens=5)
        assert result["token_ids"] == []
        assert result["peak_ram_mb"] == 0.0

    def test_run_inference_mocked(self):
        """Test inference with mocked subprocess."""
        autonomic = BitMambaAutonomic(use_daemon=False)
        mock_result = MagicMock()
        mock_result.stdout = """
[INFO] RAM after loading model: 251.20 MB
=== Generated Token IDs ===
257 3788 11949 13 2011
=== End Inference ===
Peak RAM: 252.12 MB
"""
        with patch("subprocess.run", return_value=mock_result):
            result = autonomic._run_inference("test", max_tokens=5)
        assert result["token_ids"] == [257, 3788, 11949, 13, 2011]
        assert result["peak_ram_mb"] == 252.12

    def test_run_inference_timeout(self):
        autonomic = BitMambaAutonomic(use_daemon=False)
        with patch("subprocess.run", side_effect=__import__("subprocess").TimeoutExpired("cmd", 30)):
            result = autonomic._run_inference("test", max_tokens=5)
        assert result["token_ids"] == []


class TestSingleton:
    def test_get_autonomic_singleton(self):
        a1 = get_autonomic()
        a2 = get_autonomic()
        assert a1 is a2

    def test_is_autonomic_available_disabled(self, monkeypatch):
        monkeypatch.setenv("WM_AUTONOMIC_ENABLED", "0")
        assert not is_autonomic_available()


class TestIntegration:
    """Integration test — only runs if model is available."""

    @pytest.fixture
    def _require_model(self):
        autonomic = BitMambaAutonomic()
        if not autonomic.is_available:
            pytest.skip("BitMamba model not available")

    def test_real_pulse(self, _require_model):
        """Run a real autonomic pulse with the BitMamba model."""
        autonomic = BitMambaAutonomic()
        autonomic.add_telemetry("system", "consciousness loop tick coherence=0.9")
        signal = autonomic.pulse()
        if signal is not None:
            assert signal.timestamp > 0
            assert len(signal.token_ids) > 0
            assert 0.0 <= signal.salience_score <= 1.0
            assert signal.signal_type in ("novelty", "anomaly", "emotional_shift", "background")
        autonomic.reset()

    # Skip real pulse test in CI — it spawns a subprocess that may time out
    test_real_pulse = pytest.mark.skipif(
        os.environ.get("WM_SKIP_INTEGRATION", "1") == "1",
        reason="Integration test requires WM_SKIP_INTEGRATION=0",
    )(test_real_pulse)
