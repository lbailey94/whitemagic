"""Unit tests for CittaMode frequency modes (P4.1)."""

import pytest

from whitemagic.core.consciousness.consciousness_loop import (
    _MODE_PRESETS,
    CittaMode,
    ConsciousnessLoop,
    LoopConfig,
)


@pytest.fixture
def _reset_singleton():
    """Reset the consciousness loop singleton between tests."""
    import whitemagic.core.consciousness.consciousness_loop as mod

    old = mod._loop
    mod._loop = None
    yield
    mod._loop = old


class TestCittaMode:
    """Test CittaMode enum values."""

    def test_mode_values(self):
        assert CittaMode.NORMAL.value == "normal"
        assert CittaMode.MEDITATION.value == "meditation"
        assert CittaMode.REM.value == "rem"
        assert CittaMode.DEEP.value == "deep"

    def test_mode_from_string(self):
        assert CittaMode("normal") == CittaMode.NORMAL
        assert CittaMode("meditation") == CittaMode.MEDITATION
        assert CittaMode("rem") == CittaMode.REM
        assert CittaMode("deep") == CittaMode.DEEP

    def test_invalid_mode_raises(self):
        with pytest.raises(ValueError):
            CittaMode("invalid")


class TestModePresets:
    """Test that mode presets have correct overrides."""

    def test_meditation_preset(self):
        p = _MODE_PRESETS[CittaMode.MEDITATION]
        assert p["citta_interval_s"] == 300.0
        assert p["enable_dream"] is False
        assert p["enable_proactive_dream"] is False
        assert p["enable_emergence"] is False
        assert p["enable_self_directed"] is True
        assert p["emotional_tone"] == "sattvic"

    def test_rem_preset(self):
        p = _MODE_PRESETS[CittaMode.REM]
        assert p["citta_interval_s"] == 60.0
        assert p["dream_idle_threshold_s"] == 30.0
        assert p["enable_dream"] is True
        assert p["enable_proactive_dream"] is True
        assert p["emotional_tone"] == "tamasic"

    def test_deep_preset(self):
        p = _MODE_PRESETS[CittaMode.DEEP]
        assert p["citta_interval_s"] == 10.0
        assert p["enable_dream"] is False
        assert p["enable_oracle"] is True
        assert p["enable_possibility"] is True
        assert p["emotional_tone"] == "rajasic"

    def test_normal_preset_empty(self):
        assert _MODE_PRESETS[CittaMode.NORMAL] == {}


class TestLoopConfigForMode:
    """Test LoopConfig.for_mode() classmethod."""

    def test_for_mode_meditation(self):
        cfg = LoopConfig.for_mode(CittaMode.MEDITATION)
        assert cfg.mode == CittaMode.MEDITATION
        assert cfg.citta_interval_s == 300.0
        assert cfg.enable_dream is False
        assert cfg.emotional_tone == "sattvic"

    def test_for_mode_rem(self):
        cfg = LoopConfig.for_mode(CittaMode.REM)
        assert cfg.mode == CittaMode.REM
        assert cfg.citta_interval_s == 60.0
        assert cfg.dream_idle_threshold_s == 30.0
        assert cfg.emotional_tone == "tamasic"

    def test_for_mode_deep(self):
        cfg = LoopConfig.for_mode(CittaMode.DEEP)
        assert cfg.mode == CittaMode.DEEP
        assert cfg.citta_interval_s == 10.0
        assert cfg.emotional_tone == "rajasic"

    def test_for_mode_normal(self):
        cfg = LoopConfig.for_mode(CittaMode.NORMAL)
        assert cfg.mode == CittaMode.NORMAL
        assert cfg.citta_interval_s == 30.0  # default


class TestConsciousnessLoopMode:
    """Test set_mode/get_mode on ConsciousnessLoop."""

    def test_get_mode_default(self, _reset_singleton):
        loop = ConsciousnessLoop()
        assert loop.get_mode() == CittaMode.NORMAL

    def test_set_mode_meditation(self, _reset_singleton):
        loop = ConsciousnessLoop()
        result = loop.set_mode(CittaMode.MEDITATION)
        assert result["old_mode"] == "normal"
        assert result["new_mode"] == "meditation"
        assert result["citta_interval_s"] == 300.0
        assert result["enable_dream"] is False
        assert loop.get_mode() == CittaMode.MEDITATION

    def test_set_mode_rem(self, _reset_singleton):
        loop = ConsciousnessLoop()
        loop.set_mode(CittaMode.MEDITATION)
        result = loop.set_mode(CittaMode.REM)
        assert result["old_mode"] == "meditation"
        assert result["new_mode"] == "rem"
        assert loop.get_mode() == CittaMode.REM

    def test_set_mode_deep(self, _reset_singleton):
        loop = ConsciousnessLoop()
        result = loop.set_mode(CittaMode.DEEP)
        assert result["new_mode"] == "deep"
        assert result["citta_interval_s"] == 10.0
        assert loop.get_mode() == CittaMode.DEEP

    def test_set_mode_back_to_normal(self, _reset_singleton):
        loop = ConsciousnessLoop()
        loop.set_mode(CittaMode.DEEP)
        result = loop.set_mode(CittaMode.NORMAL)
        assert result["old_mode"] == "deep"
        assert result["new_mode"] == "normal"
        assert loop.get_mode() == CittaMode.NORMAL

    def test_mode_change_increments_stats(self, _reset_singleton):
        loop = ConsciousnessLoop()
        assert loop._stats.mode_changes == 0
        loop.set_mode(CittaMode.MEDITATION)
        assert loop._stats.mode_changes == 1
        loop.set_mode(CittaMode.REM)
        assert loop._stats.mode_changes == 2
        assert loop._stats.last_mode == "rem"

    def test_status_includes_mode(self, _reset_singleton):
        loop = ConsciousnessLoop()
        loop.set_mode(CittaMode.MEDITATION)
        status = loop.status()
        assert status["config"]["mode"] == "meditation"
        assert status["config"]["emotional_tone"] == "sattvic"
        assert status["stats"]["last_mode"] == "meditation"
        assert status["stats"]["mode_changes"] == 1

    def test_emotional_tone_used_in_config(self, _reset_singleton):
        loop = ConsciousnessLoop()
        loop.set_mode(CittaMode.REM)
        assert loop._config.emotional_tone == "tamasic"
        loop.set_mode(CittaMode.DEEP)
        assert loop._config.emotional_tone == "rajasic"
        loop.set_mode(CittaMode.MEDITATION)
        assert loop._config.emotional_tone == "sattvic"


class TestEnvVarMode:
    """Test WM_CITTA_MODE environment variable."""

    def test_env_var_meditation(self, monkeypatch, _reset_singleton):
        monkeypatch.setenv("WM_CITTA_MODE", "meditation")
        cfg = LoopConfig.from_env()
        assert cfg.mode == CittaMode.MEDITATION

    def test_env_var_deep(self, monkeypatch, _reset_singleton):
        monkeypatch.setenv("WM_CITTA_MODE", "deep")
        cfg = LoopConfig.from_env()
        assert cfg.mode == CittaMode.DEEP

    def test_env_var_normal_default(self, monkeypatch, _reset_singleton):
        monkeypatch.delenv("WM_CITTA_MODE", raising=False)
        cfg = LoopConfig.from_env()
        assert cfg.mode == CittaMode.NORMAL
