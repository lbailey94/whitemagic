# ruff: noqa: BLE001
"""Ambient Sensorium Layer — Continuous background context sensing.
================================================================
Monitors system pressure, user engagement patterns, temporal
context, and environment health. Feeds into the consciousness
loop and system prompt for proactive awareness.

Usage::

    from whitemagic.core.consciousness.ambient_sensorium import get_ambient_sensorium

    sensorium = get_ambient_sensorium()
    state = sensorium.compute_ambient_state()
    if sensorium.should_proact():
        actions = sensorium.suggest_actions()
"""
from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Protocol

logger = logging.getLogger(__name__)


# ── Dataclasses ──────────────────────────────────────────────────────


@dataclass
class AmbientSignal:
    """A single ambient reading from a sensor source."""

    source: str
    signal_type: str
    value: float
    confidence: float = 1.0
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AmbientState:
    """Aggregated ambient state from all sensors."""

    pressure_level: str = "low"  # low, medium, high
    user_engagement: str = "idle"  # active, idle, away
    temporal_context: str = "morning"  # morning, afternoon, evening, night
    environment_health: str = "healthy"  # healthy, degraded, offline
    signals: list[AmbientSignal] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "pressure_level": self.pressure_level,
            "user_engagement": self.user_engagement,
            "temporal_context": self.temporal_context,
            "environment_health": self.environment_health,
            "signal_count": len(self.signals),
            "timestamp": self.timestamp,
        }


# ── Sensor Source Protocol ───────────────────────────────────────────


class SensorSource(Protocol):
    """Protocol for ambient sensor sources."""

    source_name: str

    def read(self) -> list[AmbientSignal]: ...
    def is_available(self) -> bool: ...


# ── Concrete Sensor Sources ──────────────────────────────────────────


class SystemPressureSensor:
    """Monitors CPU, memory, and disk pressure."""

    source_name = "system"

    def is_available(self) -> bool:
        import importlib.util

        return importlib.util.find_spec("psutil") is not None

    def read(self) -> list[AmbientSignal]:
        signals: list[AmbientSignal] = []
        try:
            import psutil

            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            signals.append(
                AmbientSignal(
                    source=self.source_name,
                    signal_type="cpu_pressure",
                    value=cpu_percent,
                    confidence=0.9,
                )
            )

            # Memory pressure
            mem = psutil.virtual_memory()
            signals.append(
                AmbientSignal(
                    source=self.source_name,
                    signal_type="memory_pressure",
                    value=mem.percent,
                    confidence=0.9,
                    metadata={"available_mb": mem.available // (1024 * 1024)},
                )
            )

            # Disk usage
            disk = psutil.disk_usage("/")
            signals.append(
                AmbientSignal(
                    source=self.source_name,
                    signal_type="disk_usage",
                    value=disk.percent,
                    confidence=0.9,
                )
            )
        except Exception as e:
            logger.debug("SystemPressureSensor read failed: %s", e)
        return signals


class UserPatternSensor:
    """Tracks user idle time and request patterns."""

    source_name = "user_pattern"

    def __init__(self) -> None:
        self._last_activity: float = time.time()
        self._request_count: int = 0

    def record_activity(self) -> None:
        """Call this when user interacts with the system."""
        self._last_activity = time.time()
        self._request_count += 1

    def is_available(self) -> bool:
        return True

    def read(self) -> list[AmbientSignal]:
        now = time.time()
        idle_seconds = now - self._last_activity
        signals: list[AmbientSignal] = [
            AmbientSignal(
                source=self.source_name,
                signal_type="idle_time",
                value=idle_seconds,
                confidence=1.0,
            ),
            AmbientSignal(
                source=self.source_name,
                signal_type="request_count",
                value=float(self._request_count),
                confidence=1.0,
            ),
        ]
        return signals


class TemporalSensor:
    """Classifies time of day, day of week."""

    source_name = "temporal"

    def is_available(self) -> bool:
        return True

    def read(self) -> list[AmbientSignal]:
        now = time.localtime()
        hour = now.tm_hour

        # Classify time of day
        if 5 <= hour < 12:
            tod = 0.0  # morning
        elif 12 <= hour < 17:
            tod = 1.0  # afternoon
        elif 17 <= hour < 21:
            tod = 2.0  # evening
        else:
            tod = 3.0  # night

        # Day of week (0=Monday, 6=Sunday)
        dow = float(now.tm_wday)
        is_weekend = 1.0 if now.tm_wday >= 5 else 0.0

        return [
            AmbientSignal(
                source=self.source_name,
                signal_type="time_of_day",
                value=tod,
                confidence=1.0,
                metadata={"hour": hour, "label": ["morning", "afternoon", "evening", "night"][int(tod)]},
            ),
            AmbientSignal(
                source=self.source_name,
                signal_type="day_of_week",
                value=dow,
                confidence=1.0,
                metadata={"is_weekend": is_weekend == 1.0},
            ),
        ]


class EnvironmentSensor:
    """Checks network connectivity and model availability."""

    source_name = "environment"

    def is_available(self) -> bool:
        return True

    def read(self) -> list[AmbientSignal]:
        signals: list[AmbientSignal] = []

        # Check if local model server is running
        model_available = 0.0
        try:
            import requests

            resp = requests.get("http://localhost:8080/health", timeout=1.0)
            model_available = 1.0 if resp.status_code == 200 else 0.0
        except Exception:
            model_available = 0.0

        signals.append(
            AmbientSignal(
                source=self.source_name,
                signal_type="model_available",
                value=model_available,
                confidence=0.8,
            )
        )

        # Check network connectivity (non-blocking, fast)
        network_ok = 1.0
        try:
            import socket

            socket.create_connection(("8.8.8.8", 53), timeout=1.0).close()
        except Exception:
            network_ok = 0.0

        signals.append(
            AmbientSignal(
                source=self.source_name,
                signal_type="network_connectivity",
                value=network_ok,
                confidence=0.9,
            )
        )

        return signals


# ── Ambient Sensorium ────────────────────────────────────────────────


class AmbientSensorium:
    """Aggregates sensor readings and computes ambient state."""

    def __init__(self) -> None:
        self._sources: list[SensorSource] = []
        self._latest_state: AmbientState | None = None
        self._lock = threading.RLock()
        self._thread: threading.Thread | None = None
        self._running = False
        self._interval = float(os.environ.get("WM_AMBIENT_INTERVAL", "30"))

    def add_source(self, source: SensorSource) -> None:
        self._sources.append(source)

    def read_all(self) -> list[AmbientSignal]:
        """Poll all sources and aggregate signals."""
        all_signals: list[AmbientSignal] = []
        for source in self._sources:
            if not source.is_available():
                continue
            try:
                signals = source.read()
                all_signals.extend(signals)
            except Exception as e:
                logger.debug("Sensor %s read failed: %s", source.source_name, e)
        return all_signals

    def compute_ambient_state(self) -> AmbientState:
        """Compute aggregated ambient state from all signals."""
        signals = self.read_all()

        # ── Pressure level ──
        cpu = next((s for s in signals if s.signal_type == "cpu_pressure"), None)
        mem = next((s for s in signals if s.signal_type == "memory_pressure"), None)
        max_pressure = max(
            cpu.value if cpu else 0,
            mem.value if mem else 0,
        )
        if max_pressure > 80:
            pressure = "high"
        elif max_pressure > 50:
            pressure = "medium"
        else:
            pressure = "low"

        # ── User engagement ──
        idle = next((s for s in signals if s.signal_type == "idle_time"), None)
        if idle:
            if idle.value < 60:
                engagement = "active"
            elif idle.value < 300:
                engagement = "idle"
            else:
                engagement = "away"
        else:
            engagement = "idle"

        # ── Temporal context ──
        tod = next((s for s in signals if s.signal_type == "time_of_day"), None)
        if tod:
            labels = ["morning", "afternoon", "evening", "night"]
            temporal = labels[int(tod.value)]
        else:
            temporal = "morning"

        # ── Environment health ──
        net = next((s for s in signals if s.signal_type == "network_connectivity"), None)
        model = next((s for s in signals if s.signal_type == "model_available"), None)
        net_ok = net.value > 0 if net else True
        model_ok = model.value > 0 if model else True
        if net_ok and model_ok:
            env_health = "healthy"
        elif net_ok or model_ok:
            env_health = "degraded"
        else:
            env_health = "offline"

        state = AmbientState(
            pressure_level=pressure,
            user_engagement=engagement,
            temporal_context=temporal,
            environment_health=env_health,
            signals=signals,
        )
        with self._lock:
            self._latest_state = state
        return state

    def should_proact(self) -> bool:
        """Determine if the system should take proactive action."""
        state = self._latest_state
        if state is None:
            state = self.compute_ambient_state()

        # User idle + system healthy → dream cycle / background processing
        if state.user_engagement in ("idle", "away") and state.pressure_level == "low":
            return True

        # High pressure → reduce load
        if state.pressure_level == "high":
            return True

        # Environment degraded → investigate
        if state.environment_health == "offline":
            return True

        return False

    def suggest_actions(self) -> list[str]:
        """Map ambient state to recommended actions."""
        state = self._latest_state
        if state is None:
            state = self.compute_ambient_state()

        actions: list[str] = []

        if state.pressure_level == "high":
            actions.append("reduce_inference_parallel")
            actions.append("pause_background_tasks")

        if state.user_engagement in ("idle", "away") and state.pressure_level == "low":
            actions.append("trigger_dream_cycle")
            actions.append("run_memory_consolidation")

        if state.environment_health == "degraded":
            actions.append("check_model_server")
        if state.environment_health == "offline":
            actions.append("restart_model_server")
            actions.append("check_network")

        if state.temporal_context == "night" and state.user_engagement == "away":
            actions.append("deep_consolidation_mode")

        return actions

    def start_background(self) -> None:
        """Start background polling thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop_background(self) -> None:
        """Stop background polling."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)

    def _poll_loop(self) -> None:
        while self._running:
            try:
                self.compute_ambient_state()
            except Exception as e:
                logger.debug("Ambient poll error: %s", e)
            time.sleep(self._interval)

    def get_status(self) -> dict[str, Any]:
        """Return sensorium status for MCP tool."""
        state = self._latest_state
        return {
            "running": self._running,
            "interval": self._interval,
            "sources": [s.source_name for s in self._sources],
            "latest_state": state.to_dict() if state else None,
            "should_proact": self.should_proact() if state else False,
            "suggested_actions": self.suggest_actions() if state else [],
        }


# ── Singleton ────────────────────────────────────────────────────────

_sensorium: AmbientSensorium | None = None


def get_ambient_sensorium() -> AmbientSensorium:
    """Get the global AmbientSensorium singleton."""
    global _sensorium
    if _sensorium is None:
        _sensorium = AmbientSensorium()
        _sensorium.add_source(SystemPressureSensor())
        _sensorium.add_source(UserPatternSensor())
        _sensorium.add_source(TemporalSensor())
        _sensorium.add_source(EnvironmentSensor())
    return _sensorium
