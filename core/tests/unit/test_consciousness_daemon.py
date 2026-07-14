# ruff: noqa: BLE001
"""Tests for the continuous consciousness daemon system.

Tests:
- DepthGauge: layer detection, task tracking, persistence
- NetworkGuard: privacy enforcement, egress blocking, audit trail
- DaemonConfig: defaults, env overrides, YAML loading
- ConsciousnessDaemon: loop lifecycle, metrics, graceful shutdown
"""

from __future__ import annotations

import os
import tempfile
import time

import pytest

# Ensure clean state root for tests
_tmp = tempfile.mkdtemp(prefix="wm_test_")
os.environ["WM_STATE_ROOT"] = _tmp
os.environ["WM_SILENT_INIT"] = "1"
os.environ["WM_PRIVACY_MODE"] = "local_only"


# ── DepthGauge tests ─────────────────────────────────────────────────


class TestDepthGauge:
    """Test the ConsciousnessDepthGauge."""

    def test_depth_gauge_singleton(self):
        from whitemagic.core.consciousness.depth_gauge import (
            ConsciousnessLayer,
            get_depth_gauge,
        )
        gauge = get_depth_gauge()
        gauge.ascend()  # Reset to SURFACE (xdist may have modified singleton state)
        assert gauge.current_layer == ConsciousnessLayer.SURFACE

    def test_layer_detection_surface(self):
        from whitemagic.core.consciousness.depth_gauge import (
            ConsciousnessDepthGauge,
            ConsciousnessLayer,
        )
        gauge = ConsciousnessDepthGauge()
        layer = gauge._detect_layer(1.0, {"type": "chat"})
        assert layer == ConsciousnessLayer.SURFACE

    def test_layer_detection_terminal(self):
        from whitemagic.core.consciousness.depth_gauge import (
            ConsciousnessDepthGauge,
            ConsciousnessLayer,
        )
        gauge = ConsciousnessDepthGauge()
        layer = gauge._detect_layer(2.5, {"type": "script"})
        assert layer == ConsciousnessLayer.TERMINAL

    def test_layer_detection_flow(self):
        from whitemagic.core.consciousness.depth_gauge import (
            ConsciousnessDepthGauge,
            ConsciousnessLayer,
        )
        gauge = ConsciousnessDepthGauge()
        layer = gauge._detect_layer(4.0, {"type": "creation"})
        assert layer == ConsciousnessLayer.FLOW

    def test_layer_detection_dream(self):
        from whitemagic.core.consciousness.depth_gauge import (
            ConsciousnessDepthGauge,
            ConsciousnessLayer,
        )
        gauge = ConsciousnessDepthGauge()
        layer = gauge._detect_layer(10.0, {"type": "synthesis"})
        assert layer == ConsciousnessLayer.DREAM

    def test_begin_end_task(self):
        from whitemagic.core.consciousness.depth_gauge import ConsciousnessDepthGauge
        gauge = ConsciousnessDepthGauge()
        gauge.begin_task("test task", 0.01)  # 0.01 min subjective
        time.sleep(0.05)
        reading = gauge.end_task({"result": "ok"})
        assert reading.work_output == {"result": "ok"}
        assert reading.compression_ratio > 0

    def test_end_task_without_begin_raises(self):
        from whitemagic.core.consciousness.depth_gauge import ConsciousnessDepthGauge
        gauge = ConsciousnessDepthGauge()
        with pytest.raises(ValueError, match="No task in progress"):
            gauge.end_task({})

    def test_predict_objective_time(self):
        from whitemagic.core.consciousness.depth_gauge import (
            ConsciousnessDepthGauge,
            ConsciousnessLayer,
        )
        gauge = ConsciousnessDepthGauge()
        gauge.set_layer(ConsciousnessLayer.FLOW)
        predicted = gauge.predict_objective_time(10.0)
        assert predicted == 2.5  # 10 / 4.0

    def test_get_current_metrics(self):
        from whitemagic.core.consciousness.depth_gauge import get_depth_gauge
        gauge = get_depth_gauge()
        metrics = gauge.get_current_metrics()
        assert "current_layer" in metrics
        assert "expected_compression" in metrics

    def test_history_summary_empty(self):
        from whitemagic.core.consciousness.depth_gauge import ConsciousnessDepthGauge
        gauge = ConsciousnessDepthGauge()
        summary = gauge.get_history_summary()
        assert summary == {"message": "No readings yet"}


# ── NetworkGuard tests ───────────────────────────────────────────────


class TestNetworkGuard:
    """Test the NetworkGuard privacy enforcement."""

    def test_local_only_blocks_external(self):
        from whitemagic.core.consciousness.network_guard import NetworkGuard
        guard = NetworkGuard(mode="local_only")
        assert not guard.check_egress("api.openai.com", 443)
        assert guard.check_egress("localhost", 11434)
        assert guard.check_egress("127.0.0.1", 8080)

    def test_cloud_enabled_allows_all(self):
        from whitemagic.core.consciousness.network_guard import NetworkGuard
        guard = NetworkGuard(mode="cloud_enabled")
        assert guard.check_egress("api.openai.com", 443)
        assert guard.check_egress("anything.com", 9999)

    def test_mesh_enabled_allows_local_only(self):
        from whitemagic.core.consciousness.network_guard import NetworkGuard
        guard = NetworkGuard(mode="mesh_enabled")
        assert guard.check_egress("localhost", 4730)
        assert not guard.check_egress("api.openai.com", 443)

    def test_add_allowed_host(self):
        from whitemagic.core.consciousness.network_guard import NetworkGuard
        guard = NetworkGuard(mode="mesh_enabled")
        guard.add_allowed_host("192.168.1.100")
        assert guard.check_egress("192.168.1.100", 4730)

    def test_record_egress_local_not_logged(self):
        from whitemagic.core.consciousness.network_guard import NetworkGuard
        guard = NetworkGuard(mode="cloud_enabled")
        guard.record_egress("localhost", 11434, 1024)
        assert guard.total_bytes_egress == 0  # local not counted

    def test_record_egress_external_logged(self):
        from whitemagic.core.consciousness.network_guard import NetworkGuard
        guard = NetworkGuard(mode="cloud_enabled")
        guard.record_egress("api.openai.com", 443, 1024)
        assert guard.total_bytes_egress == 1024

    def test_privacy_status(self):
        from whitemagic.core.consciousness.network_guard import NetworkGuard
        guard = NetworkGuard(mode="local_only")
        assert guard.privacy_status == "local_only"

    def test_set_mode(self):
        from whitemagic.core.consciousness.network_guard import NetworkGuard
        guard = NetworkGuard(mode="local_only")
        guard.set_mode("cloud_enabled")
        assert guard.privacy_status == "cloud_enabled"
        assert guard.check_egress("anything.com", 443)

    def test_get_status(self):
        from whitemagic.core.consciousness.network_guard import NetworkGuard
        guard = NetworkGuard(mode="local_only")
        status = guard.get_status()
        assert status["mode"] == "local_only"
        assert status["total_bytes_egress"] == 0


# ── DaemonConfig tests ───────────────────────────────────────────────


class TestDaemonConfig:
    """Test daemon configuration."""

    def test_defaults_are_local_only(self):
        from whitemagic.config.daemon_config import DaemonConfig
        config = DaemonConfig()
        assert config.local_only is True
        assert config.mesh_enabled is False
        assert config.cloud_api is None
        assert config.telemetry is False
        assert config.privacy_mode == "local_only"

    def test_to_dict(self):
        from whitemagic.config.daemon_config import DaemonConfig
        config = DaemonConfig()
        d = config.to_dict()
        assert d["local_only"] is True
        assert "network" in d
        assert "inference" in d
        assert "loops" in d

    def test_to_yaml(self):
        from whitemagic.config.daemon_config import DaemonConfig
        config = DaemonConfig()
        yaml_str = config.to_yaml()
        assert "local_only: True" in yaml_str
        assert "network:" in yaml_str
        assert "inference:" in yaml_str

    def test_env_override(self):
        from whitemagic.config.daemon_config import load_config
        old = os.environ.get("WM_MESH_ENABLED")
        os.environ["WM_MESH_ENABLED"] = "true"
        try:
            config = load_config()
            assert config.mesh_enabled is True
        finally:
            if old is None:
                del os.environ["WM_MESH_ENABLED"]
            else:
                os.environ["WM_MESH_ENABLED"] = old


# ── ConsciousnessDaemon tests ────────────────────────────────────────


class TestConsciousnessDaemon:
    """Test the consciousness daemon loop lifecycle.

    Now uses consciousness_loop.get_daemon() which returns a ConsciousnessLoop
    (unified orchestrator that subsumes the old ConsciousnessDaemon).
    """

    def test_daemon_singleton(self):
        from whitemagic.core.consciousness.consciousness_loop import get_daemon
        daemon = get_daemon()
        assert daemon is not None
        assert not daemon._running

    def test_loop_metrics_initial(self):
        from whitemagic.core.consciousness.consciousness_loop import get_daemon
        daemon = get_daemon()
        status = daemon.status()
        assert "running" in status

    def test_start_stop(self):
        from whitemagic.core.consciousness.consciousness_loop import ConsciousnessLoop
        daemon = ConsciousnessLoop()
        assert not daemon._running
        daemon.start()
        assert daemon._running
        time.sleep(0.1)  # let loops tick
        daemon.stop()
        assert not daemon._running

    def test_status_after_stop(self):
        from whitemagic.core.consciousness.consciousness_loop import ConsciousnessLoop
        daemon = ConsciousnessLoop()
        daemon.start()
        time.sleep(0.1)
        daemon.stop()
        status = daemon.status()
        assert status["running"] is False

    def test_loop_count(self):
        from whitemagic.core.consciousness.consciousness_loop import ConsciousnessLoop
        daemon = ConsciousnessLoop()
        # ConsciousnessLoop uses tiered timing (T1-T4), not named loops
        # Verify it has the expected structure
        assert hasattr(daemon, '_stats') or hasattr(daemon, '_loops')
