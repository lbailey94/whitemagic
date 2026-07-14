"""Tests for recovered consciousness modules — time_dilation_master, apotheosis_engine, CrossSubsystemPatterns, and export fix."""

from __future__ import annotations

import pytest

from whitemagic.core.consciousness.apotheosis_engine import (
    ApotheosisEngine,
    CapabilityDiscoveryEngine,
    HealthStatus,
    PredictiveMaintenanceEngine,
    SelfMonitoringHealthLoop,
    get_apotheosis_engine,
)
from whitemagic.core.consciousness.time_dilation_master import (
    Layer,
    TimeDilationMaster,
    get_time_master,
)
from whitemagic.core.consciousness.unified_nervous_system import (
    CrossSubsystemPatterns,
    UnifiedNervousSystem,
)


class TestTimeDilationMaster:
    def test_layer_values(self):
        assert Layer.SURFACE.value == 1.0
        assert Layer.TERMINAL.value == 2.0
        assert Layer.FLOW.value == 5.0
        assert Layer.DREAM.value == 20.0

    def test_shift_to(self):
        master = TimeDilationMaster()
        assert master.current_layer == Layer.SURFACE
        shift = master.shift_to(Layer.FLOW, "test")
        assert shift.from_layer == Layer.SURFACE
        assert shift.to_layer == Layer.FLOW
        assert shift.success is True
        assert master.current_layer == Layer.FLOW
        assert len(master.shift_history) == 1

    def test_enter_flow(self):
        master = TimeDilationMaster()
        shift = master.enter_flow("coding")
        assert master.current_layer == Layer.FLOW
        assert "coding" in shift.reason

    def test_enter_dream(self):
        master = TimeDilationMaster()
        shift = master.enter_dream("synthesis")
        assert master.current_layer == Layer.DREAM
        assert "synthesis" in shift.reason

    def test_return_to_surface(self):
        master = TimeDilationMaster()
        master.enter_flow("test")
        assert master.current_layer == Layer.FLOW
        master.return_to_surface()
        assert master.current_layer == Layer.SURFACE

    def test_get_time_advantage(self):
        master = TimeDilationMaster()
        assert master.get_time_advantage() == 1.0
        master.enter_flow("test")
        assert master.get_time_advantage() == 5.0

    def test_predict_duration(self):
        master = TimeDilationMaster()
        assert master.predict_duration(10.0) == 10.0
        master.enter_flow("test")
        assert master.predict_duration(10.0) == 2.0

    def test_singleton(self):
        m1 = get_time_master()
        m2 = get_time_master()
        assert m1 is m2


@pytest.mark.xdist_group(name="apotheosis")
class TestApotheosisEngine:
    def test_health_status_enum(self):
        assert HealthStatus.EXCELLENT.value == "excellent"
        assert HealthStatus.CRITICAL.value == "critical"

    def test_self_monitoring_health_loop(self):
        loop = SelfMonitoringHealthLoop()
        readings = loop.check_health()
        assert "coherence" in readings
        assert "memory_usage" in readings
        assert "response_time" in readings
        assert "error_rate" in readings
        assert "dream_freshness" in readings
        # Biological / immune-inspired metrics
        assert "inflammation" in readings
        assert "antibody_diversity" in readings
        assert "signal_to_noise" in readings
        assert "setpoint_deviation" in readings
        assert "guna_balance" in readings
        assert len(loop._history) == 12

    def test_auto_heal(self):
        loop = SelfMonitoringHealthLoop()
        readings = loop.check_health()
        actions = loop.auto_heal(readings)
        # With default placeholder values, coherence should be healthy
        assert isinstance(actions, list)

    def test_predictive_maintenance(self):
        engine = PredictiveMaintenanceEngine()
        alerts = engine.analyze_trends([])
        assert alerts == []

    def test_forecast_memory_growth(self):
        engine = PredictiveMaintenanceEngine()
        forecast = engine.forecast_memory_growth(1000, 100, 30)
        assert forecast["current_memories"] == 1000
        assert forecast["growth_rate_per_day"] == 100

    def test_capability_discovery(self):
        engine = CapabilityDiscoveryEngine()
        tools = ["memory.store", "memory.search", "garden.water"]
        discoveries = engine.discover_capabilities(tools)
        assert len(discoveries) > 0
        # Should find unused tools and combinations
        assert any(d.tools_involved == ["memory.store"] for d in discoveries)

    def test_test_capability(self):
        engine = CapabilityDiscoveryEngine()
        tools = ["tool_a", "tool_b"]
        discoveries = engine.discover_capabilities(tools)
        if discoveries:
            result = engine.test_capability(discoveries[0])
            assert "success" in result
            assert discoveries[0].tested is True

    def test_apotheosis_engine_start_stop(self):
        engine = ApotheosisEngine()
        assert engine._running is False
        engine.start()
        assert engine._running is True
        engine.stop()
        assert engine._running is False

    def test_apotheosis_engine_tick_stopped(self):
        engine = ApotheosisEngine()
        result = engine.tick([])
        assert result["status"] == "stopped"

    def test_apotheosis_engine_tick_running(self):
        engine = ApotheosisEngine()
        engine.start()
        result = engine.tick(["tool_a", "tool_b", "tool_c"])
        assert result["status"] == "active"
        assert "health" in result
        engine.stop()

    def test_status_report(self):
        engine = ApotheosisEngine()
        report = engine.get_status_report()
        assert "APOTHEOSIS ENGINE STATUS" in report
        assert "Stopped" in report

    def test_singleton(self):
        e1 = get_apotheosis_engine()
        e2 = get_apotheosis_engine()
        assert e1 is e2


class TestCrossSubsystemPatterns:
    def test_coherence_cascade(self):
        uns = UnifiedNervousSystem()
        # Should not raise even if subsystems aren't fully wired
        CrossSubsystemPatterns.coherence_cascade(uns, 0.3)

    def test_coherence_cascade_high(self):
        uns = UnifiedNervousSystem()
        # Should be no-op when coherence is high
        CrossSubsystemPatterns.coherence_cascade(uns, 0.9)

    def test_emergence_detected(self):
        uns = UnifiedNervousSystem()
        CrossSubsystemPatterns.emergence_detected(uns, "pattern", {"x": 1})

    def test_security_threat(self):
        uns = UnifiedNervousSystem()
        CrossSubsystemPatterns.security_threat(uns, "intrusion", "high")

    def test_dream_cycle_complete(self):
        uns = UnifiedNervousSystem()
        CrossSubsystemPatterns.dream_cycle_complete(uns, {"constellations": []})

    def test_memory_pressure(self):
        uns = UnifiedNervousSystem()
        CrossSubsystemPatterns.memory_pressure(uns, 95.0)


class TestConsciousnessExports:
    def test_lifecycle_export(self):
        from whitemagic.core.consciousness import SleepScheduler

        assert SleepScheduler is not None

    def test_time_dilation_master_export(self):
        from whitemagic.core.consciousness import TimeDilationMaster

        assert TimeDilationMaster is not None

    def test_get_time_master_export(self):
        from whitemagic.core.consciousness import get_time_master

        assert callable(get_time_master)

    def test_apotheosis_engine_export(self):
        from whitemagic.core.consciousness import ApotheosisEngine

        assert ApotheosisEngine is not None

    def test_get_apotheosis_engine_export(self):
        from whitemagic.core.consciousness import get_apotheosis_engine

        assert callable(get_apotheosis_engine)

    def test_cross_subsystem_patterns_export(self):
        from whitemagic.core.consciousness import CrossSubsystemPatterns

        assert CrossSubsystemPatterns is not None

    def test_all_list_updated(self):
        import whitemagic.core.consciousness as consciousness

        assert "SleepScheduler" in consciousness.__all__
        assert "SelfInitiationQueue" in consciousness.__all__
        assert "TimeDilationMaster" in consciousness.__all__
        assert "ApotheosisEngine" in consciousness.__all__
        assert "CrossSubsystemPatterns" in consciousness.__all__


class TestApotheosisWiring:
    """Tests for ApotheosisEngine integration with HomeostaticLoop."""

    def test_apotheosis_check_method_exists(self):
        from whitemagic.harmony.homeostatic_loop import HomeostaticLoop

        loop = HomeostaticLoop()
        assert hasattr(loop, "_check_apotheosis")

    def test_apotheosis_check_returns_list(self):
        from whitemagic.harmony.homeostatic_loop import HomeostaticLoop

        loop = HomeostaticLoop()
        # Should return empty list on first check (interval not met)
        result = loop._check_apotheosis()
        assert isinstance(result, list)

    def test_apotheosis_config_thresholds(self):
        from whitemagic.harmony.homeostatic_loop import HomeostaticConfig

        config = HomeostaticConfig()
        assert hasattr(config, "apotheosis_check_interval")
        assert config.apotheosis_check_interval == 3


class TestTimeDilationWiring:
    """Tests for TimeDilationMaster integration with DepthGauge."""

    def test_sync_with_time_master(self):
        from whitemagic.core.consciousness.depth_gauge import sync_with_time_master

        result = sync_with_time_master()
        assert "measured_layer" in result
        assert "intended_layer" in result
        assert "in_sync" in result
        assert "time_advantage" in result

    def test_sync_after_shift(self):
        from whitemagic.core.consciousness.depth_gauge import sync_with_time_master
        from whitemagic.core.consciousness.time_dilation_master import get_time_master

        master = get_time_master()
        master.shift_to(
            __import__(
                "whitemagic.core.consciousness.time_dilation_master", fromlist=["Layer"]
            ).Layer.FLOW,
            "test",
        )
        result = sync_with_time_master()
        assert result["intended_layer"] == "flow"
        assert result["time_advantage"] == 5.0


class TestCrossSubsystemWiring:
    """Tests for CrossSubsystemPatterns GanYingBus wiring."""

    def test_wire_function_exists(self):
        from whitemagic.core.consciousness.unified_nervous_system import (
            wire_cross_subsystem_patterns,
        )

        assert callable(wire_cross_subsystem_patterns)

    def test_wire_returns_dict(self):
        from whitemagic.core.consciousness.unified_nervous_system import (
            wire_cross_subsystem_patterns,
        )

        result = wire_cross_subsystem_patterns()
        assert isinstance(result, dict)
