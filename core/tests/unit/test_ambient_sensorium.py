# ruff: noqa: BLE001
"""Tests for Ambient Sensorium Layer (v24.3 §4.1)."""
from __future__ import annotations

import time

import pytest

from whitemagic.core.consciousness.ambient_sensorium import (
    AmbientSensorium,
    AmbientState,
    EnvironmentSensor,
    SystemPressureSensor,
    TemporalSensor,
    UserPatternSensor,
)


class TestSystemPressureSensor:
    def test_reads_cpu_memory_disk(self):
        sensor = SystemPressureSensor()
        if not sensor.is_available():
            pytest.skip("psutil not available")
        signals = sensor.read()
        assert len(signals) >= 2
        types = {s.signal_type for s in signals}
        assert "cpu_pressure" in types
        assert "memory_pressure" in types

    def test_signals_have_values(self):
        sensor = SystemPressureSensor()
        if not sensor.is_available():
            pytest.skip("psutil not available")
        signals = sensor.read()
        for s in signals:
            assert s.value >= 0
            assert s.confidence > 0


class TestUserPatternSensor:
    def test_tracks_idle_time(self):
        sensor = UserPatternSensor()
        signals = sensor.read()
        idle = next(s for s in signals if s.signal_type == "idle_time")
        assert idle.value >= 0

    def test_record_activity_updates(self):
        sensor = UserPatternSensor()
        time.sleep(0.1)
        signals1 = sensor.read()
        idle1 = next(s for s in signals1 if s.signal_type == "idle_time").value

        sensor.record_activity()
        signals2 = sensor.read()
        idle2 = next(s for s in signals2 if s.signal_type == "idle_time").value

        assert idle2 < idle1


class TestTemporalSensor:
    def test_classifies_time_of_day(self):
        sensor = TemporalSensor()
        signals = sensor.read()
        tod = next(s for s in signals if s.signal_type == "time_of_day")
        assert tod.value in (0.0, 1.0, 2.0, 3.0)
        assert tod.metadata["label"] in ("morning", "afternoon", "evening", "night")

    def test_reports_day_of_week(self):
        sensor = TemporalSensor()
        signals = sensor.read()
        dow = next(s for s in signals if s.signal_type == "day_of_week")
        assert 0 <= dow.value <= 6


class TestEnvironmentSensor:
    def test_reads_model_and_network(self):
        sensor = EnvironmentSensor()
        signals = sensor.read()
        types = {s.signal_type for s in signals}
        assert "model_available" in types
        assert "network_connectivity" in types


class TestAmbientSensorium:
    @pytest.fixture
    def sensorium(self):
        s = AmbientSensorium()
        s.add_source(TemporalSensor())
        s.add_source(UserPatternSensor())
        return s

    def test_compute_ambient_state(self, sensorium):
        state = sensorium.compute_ambient_state()
        assert isinstance(state, AmbientState)
        assert state.pressure_level in ("low", "medium", "high")
        assert state.user_engagement in ("active", "idle", "away")
        assert state.temporal_context in ("morning", "afternoon", "evening", "night")
        assert state.environment_health in ("healthy", "degraded", "offline")
        assert len(state.signals) > 0

    def test_should_proact_on_idle_and_low_pressure(self, sensorium):
        # Mock the state
        sensorium._latest_state = AmbientState(
            pressure_level="low",
            user_engagement="idle",
            temporal_context="afternoon",
            environment_health="healthy",
        )
        assert sensorium.should_proact()

    def test_should_proact_on_high_pressure(self, sensorium):
        sensorium._latest_state = AmbientState(
            pressure_level="high",
            user_engagement="active",
            temporal_context="morning",
            environment_health="healthy",
        )
        assert sensorium.should_proact()

    def test_should_not_proact_when_active_and_healthy(self, sensorium):
        sensorium._latest_state = AmbientState(
            pressure_level="low",
            user_engagement="active",
            temporal_context="morning",
            environment_health="healthy",
        )
        assert not sensorium.should_proact()

    def test_suggest_actions_high_pressure(self, sensorium):
        sensorium._latest_state = AmbientState(
            pressure_level="high",
            user_engagement="active",
            temporal_context="morning",
            environment_health="healthy",
        )
        actions = sensorium.suggest_actions()
        assert "reduce_inference_parallel" in actions
        assert "pause_background_tasks" in actions

    def test_suggest_actions_idle_low_pressure(self, sensorium):
        sensorium._latest_state = AmbientState(
            pressure_level="low",
            user_engagement="idle",
            temporal_context="afternoon",
            environment_health="healthy",
        )
        actions = sensorium.suggest_actions()
        assert "trigger_dream_cycle" in actions
        assert "run_memory_consolidation" in actions

    def test_suggest_actions_offline(self, sensorium):
        sensorium._latest_state = AmbientState(
            pressure_level="low",
            user_engagement="active",
            temporal_context="morning",
            environment_health="offline",
        )
        actions = sensorium.suggest_actions()
        assert "restart_model_server" in actions

    def test_suggest_actions_night_away(self, sensorium):
        sensorium._latest_state = AmbientState(
            pressure_level="low",
            user_engagement="away",
            temporal_context="night",
            environment_health="healthy",
        )
        actions = sensorium.suggest_actions()
        assert "deep_consolidation_mode" in actions

    def test_get_status(self, sensorium):
        sensorium.compute_ambient_state()
        status = sensorium.get_status()
        assert "running" in status
        assert "sources" in status
        assert "latest_state" in status
        assert status["latest_state"] is not None

    def test_start_stop_background(self, sensorium):
        sensorium._interval = 0.1
        sensorium.start_background()
        assert sensorium._running
        time.sleep(0.3)
        sensorium.stop_background()
        assert not sensorium._running
