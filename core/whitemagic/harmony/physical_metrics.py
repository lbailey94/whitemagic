"""Physical Metrics Source — laptop-optimizer integration.

Synthesizes laptop-optimizer's physical homeostasis model (adaptive targets,
thermal anomaly detection, predictive forecasting, health scoring) with
WhiteMagic's cognitive homeostasis (HarmonyVector, HomeostaticLoop).

When laptop-optimizer is running on localhost:3456, this module fetches
real-time hardware metrics via HTTP. When not available, it gracefully
degrades — the cognitive homeostasis loop continues independently.

Architecture:
  PhysicalMetricsSource
    ├── HTTPClient (localhost:3456) — live data when laptop-optimizer runs
    ├── ContextAdapter — AC/battery, time-of-day, load context
    ├── ThermalAnomalyDetector — spike/rise/critical patterns
    ├── ForecastEngine — linear regression with confidence grading
    └── HealthScorer — 0-100 composite with sub-scores
"""
# ruff: noqa: BLE001

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_LAPTOP_OPTIMIZER_URL = "http://127.0.0.1:3456"
_HTTP_TIMEOUT = 3.0


class PowerContext(StrEnum):
    AC = "ac"
    BATTERY = "battery"
    UNKNOWN = "unknown"


class TimeContext(StrEnum):
    DAY = "day"
    NIGHT = "night"


class LoadContext(StrEnum):
    IDLE = "idle"
    ACTIVE = "active"
    PEAK = "peak"


@dataclass
class PhysicalMetrics:
    """Snapshot of physical system metrics from laptop-optimizer."""

    cpu_temp: float | None = None
    cpu_usage: float | None = None
    battery_percent: float | None = None
    battery_status: str | None = None
    memory_percent: float | None = None
    swap_percent: float | None = None
    disk_usage: float | None = None
    psi_cpu: float | None = None
    power_draw: float | None = None
    fan_rpm: float | None = None
    thermal_throttling: int = 0
    health_score: float | None = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def is_available(self) -> bool:
        return self.cpu_temp is not None or self.cpu_usage is not None


@dataclass
class AdaptiveTargets:
    """Adaptive homeostasis targets that shift based on context.

    Ported from laptop-optimizer's EDGE_AI_STEWARD.md spec.
    """

    cpu_temp_max: float = 65.0
    battery_min: float = 20.0
    memory_max: float = 75.0
    swap_max: float = 10.0
    psi_cpu_max: float = 30.0
    disk_max: float = 85.0

    def adapt(
        self, power: PowerContext, time_ctx: TimeContext, load: LoadContext
    ) -> None:
        if power == PowerContext.AC:
            self.cpu_temp_max = 70.0
        elif power == PowerContext.BATTERY:
            self.cpu_temp_max = 60.0

        if time_ctx == TimeContext.NIGHT:
            self.cpu_temp_max -= 5.0
            self.memory_max -= 5.0

        if load == LoadContext.PEAK:
            self.cpu_temp_max += 10.0


@dataclass
class ThermalAnomaly:
    """A detected thermal anomaly."""

    pattern: str  # spike, sustained_rise, critical_jump
    current_temp: float
    threshold: float
    message: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class ThermalAnomalyDetector:
    """Detects thermal anomalies using laptop-optimizer's patterns.

    Patterns:
      - Spike: >5°C increase in 30 seconds
      - Sustained rise: >2°C/min sustained over 2 minutes
      - Critical jump: <80°C → >90°C in 10 seconds
    """

    def __init__(self) -> None:
        self._history: list[tuple[float, float]] = []  # (timestamp, temp)
        self._max_history = 120  # 10 min at 5s intervals
        self._lock = threading.Lock()

    def check(self, temp: float) -> ThermalAnomaly | None:
        if temp is None:
            return None

        now = time.time()
        with self._lock:
            self._history.append((now, temp))
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history :]

            if len(self._history) < 2:
                return None

            # Spike: >5°C in 30s
            cutoff_30s = now - 30.0
            temps_30s = [t for ts, t in self._history if ts >= cutoff_30s]
            if temps_30s and len(temps_30s) >= 2:
                if temp - temps_30s[0] > 5.0:
                    return ThermalAnomaly(
                        pattern="spike",
                        current_temp=temp,
                        threshold=temps_30s[0] + 5.0,
                        message=f"Thermal spike: {temp - temps_30s[0]:.1f}°C rise in 30s",
                    )

            # Sustained rise: >2°C/min over 2 min
            cutoff_2min = now - 120.0
            temps_2min = [t for ts, t in self._history if ts >= cutoff_2min]
            if len(temps_2min) >= 4:
                rise = temp - temps_2min[0]
                if rise > 4.0:  # 2°C/min × 2 min
                    return ThermalAnomaly(
                        pattern="sustained_rise",
                        current_temp=temp,
                        threshold=temps_2min[0] + 4.0,
                        message=f"Sustained thermal rise: {rise:.1f}°C over 2 min",
                    )

            # Critical jump: <80°C → >90°C in 10s
            cutoff_10s = now - 10.0
            temps_10s = [t for ts, t in self._history if ts >= cutoff_10s]
            if temps_10s and len(temps_10s) >= 2:
                if temps_10s[0] < 80.0 and temp > 90.0:
                    return ThermalAnomaly(
                        pattern="critical_jump",
                        current_temp=temp,
                        threshold=90.0,
                        message=f"Critical thermal jump: {temps_10s[0]:.0f}°C → {temp:.0f}°C in 10s",
                    )

        return None


@dataclass
class Forecast:
    """A predictive forecast for a metric."""

    metric: str
    current_value: float
    predicted_5min: float
    predicted_15min: float
    confidence: str  # high, medium, low
    r_squared: float = 0.0


class ForecastEngine:
    """Linear regression forecasting with confidence grading.

    Ported from laptop-optimizer's predictive forecasting model.
    Confidence: high (R²>0.7, span>60s), medium (R²>0.4, span>30s), low otherwise.
    """

    @staticmethod
    def forecast(history: list[tuple[float, float]], metric: str) -> Forecast | None:
        if len(history) < 5:
            return None

        times = [ts for ts, _ in history]
        values = [v for _, v in history]

        # Normalize time to seconds from start
        t0 = times[0]
        x = [t - t0 for t in times]
        y = values

        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_x2 = sum(xi * xi for xi in x)

        denom = n * sum_x2 - sum_x * sum_x
        if denom == 0:
            return None

        slope = (n * sum_xy - sum_x * sum_y) / denom
        intercept = (sum_y - slope * sum_x) / n

        # R²
        mean_y = sum_y / n
        ss_tot = sum((yi - mean_y) ** 2 for yi in y)
        ss_res = sum((yi - (slope * xi + intercept)) ** 2 for xi, yi in zip(x, y))
        r_sq = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

        # Predictions
        current_t = x[-1]
        pred_5 = slope * (current_t + 300) + intercept
        pred_15 = slope * (current_t + 900) + intercept

        # Sanity caps
        pred_5 = max(30.0, min(105.0, pred_5))
        pred_15 = max(30.0, min(105.0, pred_15))

        span = x[-1] - x[0]
        if r_sq > 0.7 and span > 60:
            confidence = "high"
        elif r_sq > 0.4 and span > 30:
            confidence = "medium"
        else:
            confidence = "low"

        return Forecast(
            metric=metric,
            current_value=y[-1],
            predicted_5min=pred_5,
            predicted_15min=pred_15,
            confidence=confidence,
            r_squared=r_sq,
        )


class PhysicalMetricsSource:
    """Fetches physical system metrics from laptop-optimizer and provides
    adaptive homeostasis targets, thermal anomaly detection, and forecasting.

    Graceful degradation: when laptop-optimizer is not running, returns
    empty metrics and the cognitive homeostasis loop continues independently.
    """

    def __init__(self, api_url: str = _LAPTOP_OPTIMIZER_URL) -> None:
        self._api_url = api_url
        self._cache: PhysicalMetrics | None = None
        self._cache_time: float = 0.0
        self._cache_ttl: float = 5.0  # 5 second cache
        self._lock = threading.Lock()
        self._thermal_detector = ThermalAnomalyDetector()
        self._temp_history: list[tuple[float, float]] = []
        self._targets = AdaptiveTargets()

    def _fetch_stats(self) -> dict[str, Any] | None:
        """Fetch stats from laptop-optimizer API."""
        try:
            import urllib.request

            req = urllib.request.Request(
                f"{self._api_url}/api/stats",
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT) as resp:
                return json.loads(resp.read())
        except Exception:
            return None

    def _fetch_psutil_fallback(self) -> dict[str, Any] | None:
        """Direct sensor reading via psutil + /sys when laptop-optimizer is absent.

        Returns a dict in the same format as laptop-optimizer's /api/stats,
        or None if psutil is not installed.
        """
        try:
            import psutil
        except ImportError:
            return None

        try:
            # CPU usage
            cpu_usage = psutil.cpu_percent(interval=0.5)

            # CPU temperature from /sys/class/thermal
            temps: list[dict[str, Any]] = []
            thermal_zones = list(Path("/sys/class/thermal").glob("thermal_zone*/temp"))
            for tz in thermal_zones:
                try:
                    val = int(tz.read_text().strip()) / 1000.0
                    if 20 < val < 120:
                        zone_name = tz.parent.name
                        temps.append({"type": zone_name, "temp": val})
                except (ValueError, OSError):
                    continue
            next((t["temp"] for t in temps), None)

            # Memory
            mem = psutil.virtual_memory()
            swap = psutil.swap_memory()

            # Battery
            battery = psutil.sensors_battery()
            power: dict[str, Any] = {}
            if battery:
                power["battery_cap"] = battery.percent
                power["battery_status"] = (
                    "Discharging" if not battery.power_plugged else "Charging"
                )

            # Disk
            disk = psutil.disk_usage("/")

            return {
                "cpu": {"usage": cpu_usage, "temps": temps},
                "power": power,
                "memory": {"used": mem.used, "total": mem.total},
                "swap": {"percent": swap.percent},
                "disk": {"percent": disk.percent},
            }
        except Exception as e:
            logger.debug("psutil fallback failed: %s", e)
            return None

    def get_metrics(self) -> PhysicalMetrics:
        """Get current physical metrics, with caching."""
        now = time.time()
        with self._lock:
            if self._cache and (now - self._cache_time) < self._cache_ttl:
                return self._cache

        raw = self._fetch_stats()
        if raw is None:
            # Fallback: direct sensor reading via psutil + /sys
            raw = self._fetch_psutil_fallback()
        if raw is None:
            metrics = PhysicalMetrics()
        else:
            cpu = raw.get("cpu", {})
            power = raw.get("power", {})
            mem = raw.get("memory", {})
            temps = cpu.get("temps", [])
            pkg_temp = next(
                (t["temp"] for t in temps if t.get("type") == "x86_pkg_temp"),
                None,
            )

            metrics = PhysicalMetrics(
                cpu_temp=pkg_temp,
                cpu_usage=cpu.get("usage"),
                battery_percent=power.get("battery_cap"),
                battery_status=power.get("battery_status"),
                memory_percent=(mem.get("used", 0) / mem.get("total", 1) * 100)
                if mem.get("total")
                else None,
                swap_percent=raw.get("swap", {}).get("percent"),
                disk_usage=raw.get("disk", {}).get("percent"),
                psi_cpu=raw.get("psi", {}).get("cpu"),
                power_draw=power.get("power_draw"),
                fan_rpm=raw.get("thermal", {}).get("fan_rpm"),
                thermal_throttling=raw.get("thermal", {}).get("throttling_count", 0),
                health_score=raw.get("_health_score", {}).get("score")
                if isinstance(raw.get("_health_score"), dict)
                else None,
            )

            # Feed thermal detector
            if metrics.cpu_temp is not None:
                self._temp_history.append((now, metrics.cpu_temp))
                if len(self._temp_history) > 120:
                    self._temp_history = self._temp_history[-120:]

        with self._lock:
            self._cache = metrics
            self._cache_time = now

        return metrics

    def get_context(self) -> tuple[PowerContext, TimeContext, LoadContext]:
        """Determine current operational context."""
        metrics = self.get_metrics()

        if metrics.battery_status:
            power = (
                PowerContext.BATTERY
                if "Discharg" in metrics.battery_status
                else PowerContext.AC
            )
        else:
            power = PowerContext.UNKNOWN

        hour = datetime.now().hour
        time_ctx = TimeContext.NIGHT if hour >= 22 or hour < 8 else TimeContext.DAY

        if metrics.cpu_usage is not None:
            if metrics.cpu_usage > 70:
                load = LoadContext.PEAK
            elif metrics.cpu_usage > 20:
                load = LoadContext.ACTIVE
            else:
                load = LoadContext.IDLE
        else:
            load = LoadContext.IDLE

        return power, time_ctx, load

    def get_adaptive_targets(self) -> AdaptiveTargets:
        """Get current adaptive targets based on context."""
        power, time_ctx, load = self.get_context()
        targets = AdaptiveTargets()
        targets.adapt(power, time_ctx, load)
        return targets

    def check_thermal_anomaly(self) -> ThermalAnomaly | None:
        """Check for thermal anomalies."""
        metrics = self.get_metrics()
        if metrics.cpu_temp is None:
            return None
        return self._thermal_detector.check(metrics.cpu_temp)

    def get_thermal_forecast(self) -> Forecast | None:
        """Get thermal forecast."""
        if len(self._temp_history) < 5:
            return None
        return ForecastEngine.forecast(self._temp_history, "cpu_temp")

    def get_health_score(self) -> float | None:
        """Get the laptop-optimizer health score (0-100)."""
        metrics = self.get_metrics()
        return metrics.health_score

    def is_available(self) -> bool:
        """Check if laptop-optimizer is running."""
        metrics = self.get_metrics()
        return metrics.is_available

    def evaluate_homeostasis(self) -> list[dict[str, Any]]:
        """Evaluate current metrics against adaptive targets.

        Returns a list of recommendations, similar to laptop-optimizer's
        SystemSteward.evaluate() method.
        """
        metrics = self.get_metrics()
        if not metrics.is_available:
            return []

        targets = self.get_adaptive_targets()
        recommendations: list[dict[str, Any]] = []

        if metrics.cpu_temp is not None and metrics.cpu_temp > targets.cpu_temp_max:
            recommendations.append(
                {
                    "type": "thermal",
                    "severity": "warn",
                    "message": f"CPU temperature {metrics.cpu_temp:.0f}°C exceeds target ({targets.cpu_temp_max:.0f}°C)",
                    "action": "Consider increasing TCC offset or closing CPU-heavy apps",
                    "auto_eligible": False,
                }
            )

        if (
            metrics.battery_percent is not None
            and metrics.battery_status
            and "Discharg" in metrics.battery_status
            and metrics.battery_percent < targets.battery_min
        ):
            recommendations.append(
                {
                    "type": "power",
                    "severity": "critical",
                    "message": f"Battery at {metrics.battery_percent:.0f}%",
                    "action": "Switch to powersave mode or connect AC adapter",
                    "auto_eligible": True,
                }
            )

        if (
            metrics.memory_percent is not None
            and metrics.memory_percent > targets.memory_max
        ):
            recommendations.append(
                {
                    "type": "memory",
                    "severity": "warn",
                    "message": f"Memory at {metrics.memory_percent:.0f}%",
                    "action": "Close unused applications or browser tabs",
                    "auto_eligible": False,
                }
            )

        if metrics.swap_percent is not None and metrics.swap_percent > targets.swap_max:
            recommendations.append(
                {
                    "type": "memory",
                    "severity": "warn",
                    "message": f"Swap at {metrics.swap_percent:.0f}%",
                    "action": "Memory pressure high — close heavy applications",
                    "auto_eligible": False,
                }
            )

        if metrics.psi_cpu is not None and metrics.psi_cpu > targets.psi_cpu_max:
            recommendations.append(
                {
                    "type": "pressure",
                    "severity": "warn",
                    "message": f"CPU PSI pressure at {metrics.psi_cpu:.0f}",
                    "action": "System under CPU pressure — investigate top processes",
                    "auto_eligible": False,
                }
            )

        if metrics.thermal_throttling > 0:
            recommendations.append(
                {
                    "type": "thermal",
                    "severity": "critical",
                    "message": f"{metrics.thermal_throttling} cores throttling",
                    "action": "Recommend cooling intervention",
                    "auto_eligible": True,
                }
            )

        return recommendations


_physical_source: PhysicalMetricsSource | None = None
_source_lock = threading.Lock()


def get_physical_metrics_source() -> PhysicalMetricsSource:
    """Get the singleton PhysicalMetricsSource."""
    global _physical_source
    if _physical_source is None:
        with _source_lock:
            if _physical_source is None:
                _physical_source = PhysicalMetricsSource()
    return _physical_source
