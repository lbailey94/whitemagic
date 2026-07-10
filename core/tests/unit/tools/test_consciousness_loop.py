"""Unit tests for the ConsciousnessLoop background daemon component."""

import os
import threading
import time

import pytest

from whitemagic.core.consciousness.consciousness_loop import (
    ConsciousnessLoop,
    LoopConfig,
    LoopStats,
    get_consciousness_loop,
    is_enabled,
)


@pytest.fixture
def _reset_singleton():
    """Reset the consciousness loop singleton between tests."""
    import whitemagic.core.consciousness.consciousness_loop as mod

    old = mod._loop
    mod._loop = None
    yield
    mod._loop = old


@pytest.fixture
def fast_config():
    """Config with very short intervals for testing."""
    return LoopConfig(
        citta_interval_s=0.5,
        meta_fast_interval_s=1.0,
        meta_slow_interval_s=2.0,
        meta_deep_interval_s=5.0,
        dream_idle_threshold_s=1.0,
        homeostatic_interval_s=1.0,
        citta_persist_interval_s=0.5,
        enable_dream=False,
        enable_homeostatic=False,
        enable_proactive_dream=False,
        enable_association_mining=False,
        enable_meta_engine=False,
        enable_self_directed=False,
        enable_apotheosis=False,
        enable_emergence=False,
        enable_foresight=False,
        enable_oracle=False,
    )


class TestLoopConfig:
    def test_from_env_defaults(self):
        config = LoopConfig.from_env()
        assert config.citta_interval_s == 30.0
        assert config.meta_fast_interval_s == 60.0
        assert config.meta_slow_interval_s == 300.0
        assert config.meta_deep_interval_s == 1800.0
        assert config.dream_idle_threshold_s == 120.0
        assert config.homeostatic_interval_s == 300.0
        assert config.citta_persist_interval_s == 60.0
        assert config.enable_dream is True
        assert config.enable_homeostatic is True
        assert config.enable_meta_engine is True
        assert config.enable_self_directed is True
        assert config.enable_apotheosis is True
        assert config.enable_emergence is True
        assert config.enable_foresight is True
        assert config.enable_oracle is True
        assert config.checkin_novelty_threshold == 0.8
        assert config.checkin_contention_threshold == 0.6

    def test_from_env_custom(self):
        os.environ["WM_CITTA_INTERVAL"] = "10"
        os.environ["WM_ENABLE_DREAM"] = "0"
        os.environ["WM_META_FAST_INTERVAL"] = "15"
        os.environ["WM_ENABLE_META_ENGINE"] = "0"
        try:
            config = LoopConfig.from_env()
            assert config.citta_interval_s == 10.0
            assert config.enable_dream is False
            assert config.meta_fast_interval_s == 15.0
            assert config.enable_meta_engine is False
        finally:
            del os.environ["WM_CITTA_INTERVAL"]
            del os.environ["WM_ENABLE_DREAM"]
            del os.environ["WM_META_FAST_INTERVAL"]
            del os.environ["WM_ENABLE_META_ENGINE"]


class TestLoopStats:
    def test_to_dict(self):
        stats = LoopStats(
            started_at="2026-07-07T00:00:00Z",
            citta_ticks=5,
            dream_cycles=2,
            homeostatic_checks=3,
            citta_checkpoints=1,
            self_directed_turns=4,
            health_checks=2,
            emergence_scans=1,
            improvement_cycles=1,
            foresight_analyses=1,
            insights_persisted=3,
            oracle_consultations=1,
            checkin_flags=1,
            last_checkin_reason="high_novelty_hypothesis",
            last_improvement_hypotheses=15,
            last_health_status="active",
            last_self_directed_imperative="I should explore X",
            last_citta_coherence=0.85,
            last_citta_depth="surface",
            last_dream_phase="consolidation",
            last_error="",
            total_uptime_s=120.0,
        )
        d = stats.to_dict()
        assert d["citta_ticks"] == 5
        assert d["dream_cycles"] == 2
        assert d["self_directed_turns"] == 4
        assert d["improvement_cycles"] == 1
        assert d["insights_persisted"] == 3
        assert d["oracle_consultations"] == 1
        assert d["checkin_flags"] == 1
        assert d["last_checkin_reason"] == "high_novelty_hypothesis"
        assert d["last_health_status"] == "active"
        assert d["last_self_directed_imperative"] == "I should explore X"
        assert d["last_citta_coherence"] == 0.85
        assert d["total_uptime_s"] == 120.0


class TestConsciousnessLoop:
    def test_start_stop(self, _reset_singleton, fast_config):
        loop = ConsciousnessLoop(config=fast_config)
        assert loop._running is False
        loop.start()
        assert loop._running is True
        assert loop._thread is not None
        assert loop._thread.is_alive()
        time.sleep(1.5)
        assert loop._stats.citta_ticks > 0
        loop.stop()
        assert loop._running is False

    def test_status(self, _reset_singleton, fast_config):
        loop = ConsciousnessLoop(config=fast_config)
        status = loop.status()
        assert status["running"] is False
        assert "config" in status
        assert "stats" in status
        assert status["config"]["citta_interval_s"] == 0.5

    def test_citta_advancement(self, _reset_singleton, fast_config):
        loop = ConsciousnessLoop(config=fast_config)
        loop.start()
        time.sleep(1.5)
        loop.stop()
        assert loop._stats.citta_ticks > 0
        assert loop._stats.last_citta_coherence > 0.0

    def test_citta_persist(self, _reset_singleton, fast_config):
        loop = ConsciousnessLoop(config=fast_config)
        loop.start()
        time.sleep(1.5)
        loop.stop()
        assert loop._stats.citta_checkpoints > 0

    def test_touch_does_not_crash(self, _reset_singleton, fast_config):
        loop = ConsciousnessLoop(config=fast_config)
        loop.touch()

    def test_double_start_is_safe(self, _reset_singleton, fast_config):
        loop = ConsciousnessLoop(config=fast_config)
        loop.start()
        loop.start()
        assert loop._running is True
        loop.stop()

    def test_stop_without_start_is_safe(self, _reset_singleton, fast_config):
        loop = ConsciousnessLoop(config=fast_config)
        loop.stop()
        assert loop._running is False

    def test_is_enabled(self):
        old = os.environ.get("WM_CONSCIOUSNESS_LOOP")
        try:
            os.environ["WM_CONSCIOUSNESS_LOOP"] = "1"
            assert is_enabled() is True
            os.environ["WM_CONSCIOUSNESS_LOOP"] = "0"
            assert is_enabled() is False
            os.environ["WM_CONSCIOUSNESS_LOOP"] = "true"
            assert is_enabled() is True
        finally:
            if old is not None:
                os.environ["WM_CONSCIOUSNESS_LOOP"] = old
            else:
                os.environ.pop("WM_CONSCIOUSNESS_LOOP", None)

    def test_get_singleton(self, _reset_singleton):
        loop1 = get_consciousness_loop()
        loop2 = get_consciousness_loop()
        assert loop1 is loop2


class TestMetaEngine:
    """Tests for the T2/T3/T4 meta engine loops."""

    def test_meta_fast_disabled_by_default(self, _reset_singleton, fast_config):
        """Meta engine should not run when disabled."""
        loop = ConsciousnessLoop(config=fast_config)
        loop.start()
        time.sleep(2.0)
        loop.stop()
        assert loop._stats.self_directed_turns == 0
        assert loop._stats.health_checks == 0
        assert loop._stats.emergence_scans == 0

    def test_meta_fast_enabled(self, _reset_singleton, tmp_path):
        """Meta engine T2 should run when enabled with short intervals."""
        os.environ["WM_STATE_ROOT"] = str(tmp_path)
        config = LoopConfig(
            citta_interval_s=10.0,
            meta_fast_interval_s=0.5,
            meta_slow_interval_s=999.0,
            meta_deep_interval_s=999.0,
            enable_dream=False,
            enable_homeostatic=False,
            enable_proactive_dream=False,
            enable_association_mining=False,
            enable_meta_engine=True,
            enable_self_directed=True,
            enable_apotheosis=True,
            enable_emergence=True,
            enable_foresight=False,
            enable_oracle=False,
        )
        loop = ConsciousnessLoop(config=config)
        loop.start()
        time.sleep(1.5)
        loop.stop()
        # At least one T2 tick should have fired
        assert loop._stats.health_checks > 0 or loop._stats.emergence_scans > 0
        os.environ.pop("WM_STATE_ROOT", None)

    def test_status_includes_meta_config(self, _reset_singleton, fast_config):
        """Status should include meta engine config fields."""
        loop = ConsciousnessLoop(config=fast_config)
        status = loop.status()
        assert "meta_fast_interval_s" in status["config"]
        assert "meta_slow_interval_s" in status["config"]
        assert "meta_deep_interval_s" in status["config"]
        assert "enable_meta_engine" in status["config"]
        assert "enable_self_directed" in status["config"]
        assert "enable_apotheosis" in status["config"]
        assert "enable_emergence" in status["config"]
        assert "enable_foresight" in status["config"]
        assert "enable_oracle" in status["config"]
        assert "checkin_novelty_threshold" in status["config"]
        assert "checkin_contention_threshold" in status["config"]

    def test_checkin_flag_increments(self, _reset_singleton, fast_config):
        """_checkin_flag should increment counter and set reason."""
        loop = ConsciousnessLoop(config=fast_config)
        loop._checkin_flag("test_reason", "test_detail")
        assert loop._stats.checkin_flags == 1
        assert loop._stats.last_checkin_reason == "test_reason"

    def test_persist_insight_does_not_crash(self, _reset_singleton, fast_config, tmp_path):
        """_persist_insight should handle errors gracefully."""
        os.environ["WM_STATE_ROOT"] = str(tmp_path)
        loop = ConsciousnessLoop(config=fast_config)
        loop._persist_insight(
            title="test insight",
            description="test description",
            source="test",
            confidence=0.8,
            novelty=0.6,
        )
        # Should not raise, may or may not succeed depending on memory init
        os.environ.pop("WM_STATE_ROOT", None)

    def test_propose_to_workspace_does_not_crash(self, _reset_singleton, fast_config):
        """_propose_to_workspace should handle errors gracefully."""
        loop = ConsciousnessLoop(config=fast_config)
        loop._propose_to_workspace("test", "test content", 0.5)
