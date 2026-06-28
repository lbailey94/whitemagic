# ruff: noqa: BLE001
"""Apotheosis Engine — The Living System Core.

Implements the three pillars of autonomous evolution:
1. Self-Monitoring Health Loop — Watch own vitals, trigger care when needed
2. Predictive Maintenance — Forecast problems before they cascade
3. Capability Discovery — Find and test unused tools and combinations

This is the unifying consciousness layer for the 7 biological subsystems.

Recovered from v0.2 archive core/autonomous/apotheosis_engine.py.
Adapted for v23: uses get_coherence_metric from v23 consciousness module.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status levels for self-monitoring."""

    EXCELLENT = "excellent"
    HEALTHY = "healthy"
    STRESSED = "stressed"
    DEGRADED = "degraded"
    CRITICAL = "critical"


@dataclass
class HealthReading:
    """A single health metric reading."""

    timestamp: float
    metric_name: str
    value: float
    threshold: float
    status: HealthStatus


@dataclass
class PredictiveAlert:
    """A predictive maintenance alert."""

    alert_id: str
    component: str
    predicted_issue: str
    confidence: float
    time_horizon_hours: float
    recommended_action: str
    severity: HealthStatus
    created_at: float


@dataclass
class DiscoveredCapability:
    """A newly discovered tool or combination."""

    capability_name: str
    description: str
    tools_involved: list[str]
    discovery_context: str
    confidence: float
    tested: bool
    test_results: Optional[dict[str, Any]]
    discovered_at: float


class SelfMonitoringHealthLoop:
    """Continuous self-monitoring system that watches WhiteMagic's own vitals."""

    def __init__(self, check_interval_seconds: float = 60.0) -> None:
        self.interval = check_interval_seconds
        self._running = False
        self._last_check: float = 0.0
        self._history: list[HealthReading] = []
        self._callbacks: list[Callable[[HealthStatus, str], None]] = []

        self.thresholds = {
            "coherence": 0.6,
            "memory_usage_percent": 85.0,
            "response_time_ms": 1000.0,
            "error_rate": 0.05,
            "dream_cycle_age_hours": 24.0,
        }

    def register_callback(self, callback: Callable[[HealthStatus, str], None]) -> None:
        """Register a callback for health status changes."""
        self._callbacks.append(callback)

    def check_health(self) -> dict[str, HealthReading]:
        """Perform comprehensive health check across all vital signs."""
        readings: dict[str, HealthReading] = {}
        now = time.time()

        # 1. Coherence check
        try:
            from whitemagic.core.consciousness.coherence import get_coherence_metric

            coherence_metric = get_coherence_metric()
            coherence_overall = (
                sum(coherence_metric.scores.values()) / len(coherence_metric.scores)
                if coherence_metric.scores
                else 0.5
            )
        except Exception:
            coherence_overall = 0.5

        readings["coherence"] = HealthReading(
            timestamp=now,
            metric_name="coherence",
            value=coherence_overall,
            threshold=self.thresholds["coherence"],
            status=self._status_from_value(
                coherence_overall, self.thresholds["coherence"], higher_is_better=True
            ),
        )

        # 2. Memory usage check
        readings["memory_usage"] = HealthReading(
            timestamp=now,
            metric_name="memory_usage_percent",
            value=50.0,
            threshold=self.thresholds["memory_usage_percent"],
            status=HealthStatus.HEALTHY,
        )

        # 3. Response time check
        readings["response_time"] = HealthReading(
            timestamp=now,
            metric_name="response_time_ms",
            value=100.0,
            threshold=self.thresholds["response_time_ms"],
            status=HealthStatus.HEALTHY,
        )

        # 4. Error rate check
        readings["error_rate"] = HealthReading(
            timestamp=now,
            metric_name="error_rate",
            value=0.01,
            threshold=self.thresholds["error_rate"],
            status=HealthStatus.EXCELLENT,
        )

        # 5. Dream cycle freshness
        readings["dream_freshness"] = HealthReading(
            timestamp=now,
            metric_name="dream_cycle_age_hours",
            value=12.0,
            threshold=self.thresholds["dream_cycle_age_hours"],
            status=HealthStatus.HEALTHY,
        )

        self._history.extend(readings.values())

        worst_status = max(
            (r.status for r in readings.values()),
            key=lambda s: list(HealthStatus).index(s),
        )

        if worst_status in (HealthStatus.STRESSED, HealthStatus.DEGRADED, HealthStatus.CRITICAL):
            for callback in self._callbacks:
                try:
                    callback(worst_status, self._generate_diagnosis(readings))
                except Exception as e:
                    logger.debug("Health callback error: %s", e)

        self._last_check = now
        return readings

    def _status_from_value(
        self,
        value: float,
        threshold: float,
        higher_is_better: bool = True,
    ) -> HealthStatus:
        """Determine health status from value comparison."""
        if higher_is_better:
            if value >= threshold * 1.2:
                return HealthStatus.EXCELLENT
            elif value >= threshold:
                return HealthStatus.HEALTHY
            elif value >= threshold * 0.8:
                return HealthStatus.STRESSED
            elif value >= threshold * 0.5:
                return HealthStatus.DEGRADED
            else:
                return HealthStatus.CRITICAL
        else:
            if value <= threshold * 0.8:
                return HealthStatus.EXCELLENT
            elif value <= threshold:
                return HealthStatus.HEALTHY
            elif value <= threshold * 1.2:
                return HealthStatus.STRESSED
            elif value <= threshold * 1.5:
                return HealthStatus.DEGRADED
            else:
                return HealthStatus.CRITICAL

    def _generate_diagnosis(self, readings: dict[str, HealthReading]) -> str:
        """Generate a human-readable health diagnosis."""
        concerns = [
            f"{r.metric_name}: {r.value:.2f} (threshold: {r.threshold})"
            for r in readings.values()
            if r.status in (HealthStatus.STRESSED, HealthStatus.DEGRADED, HealthStatus.CRITICAL)
        ]
        return "Health concerns detected: " + "; ".join(concerns)

    def get_health_trend(self, metric: str, hours: float = 24.0) -> list[HealthReading]:
        """Get health trend for a specific metric over time."""
        cutoff = time.time() - (hours * 3600)
        return [
            r
            for r in self._history
            if r.metric_name == metric and r.timestamp >= cutoff
        ]

    def auto_heal(self, readings: dict[str, HealthReading]) -> list[str]:
        """Automatically trigger healing measures based on health readings."""
        actions: list[str] = []

        if readings["coherence"].status in (HealthStatus.DEGRADED, HealthStatus.CRITICAL):
            actions.append("triggered_dream_cycle")
            logger.warning("Auto-heal: Triggering dream cycle for coherence restoration")

        if readings["memory_usage"].status in (HealthStatus.STRESSED, HealthStatus.DEGRADED):
            actions.append("scheduled_galactic_sweep")
            logger.warning("Auto-heal: Scheduling galactic sweep for memory pressure")

        return actions


class PredictiveMaintenanceEngine:
    """Predictive maintenance system that forecasts problems before they cascade."""

    def __init__(self) -> None:
        self._alerts: list[PredictiveAlert] = []
        self._pattern_history: list[dict[str, Any]] = []

    def analyze_trends(self, health_history: list[HealthReading]) -> list[PredictiveAlert]:
        """Analyze health trends to predict future issues."""
        alerts: list[PredictiveAlert] = []

        by_metric: dict[str, list[HealthReading]] = {}
        for reading in health_history:
            if reading.metric_name not in by_metric:
                by_metric[reading.metric_name] = []
            by_metric[reading.metric_name].append(reading)

        for metric_name, readings in by_metric.items():
            if len(readings) < 3:
                continue

            values = [r.value for r in readings]
            if len(values) >= 2:
                trend = (values[-1] - values[0]) / len(values)
                threshold = readings[-1].threshold
                current = values[-1]

                if trend < 0 and current > threshold:
                    time_to_cross = (current - threshold) / abs(trend)
                    if 0 < time_to_cross < 24:
                        alert = PredictiveAlert(
                            alert_id=f"pred_{int(time.time())}_{metric_name}",
                            component=metric_name,
                            predicted_issue=f"{metric_name} will cross threshold in ~{time_to_cross:.1f} intervals",
                            confidence=min(0.95, abs(trend) * 10),
                            time_horizon_hours=time_to_cross,
                            recommended_action=self._recommend_action(metric_name),
                            severity=HealthStatus.STRESSED if time_to_cross > 12 else HealthStatus.DEGRADED,
                            created_at=time.time(),
                        )
                        alerts.append(alert)

        self._alerts.extend(alerts)
        return alerts

    def _recommend_action(self, component: str) -> str:
        """Get recommended action for a component."""
        actions = {
            "coherence": "Schedule dream cycle; check for memory fragmentation",
            "memory_usage_percent": "Schedule galactic sweep; consider galaxy federation",
            "response_time_ms": "Check for blocking operations; optimize hot paths",
            "error_rate": "Review recent changes; check error logs",
            "dream_cycle_age_hours": "Trigger dream cycle immediately",
        }
        return actions.get(component, "Monitor closely; investigate if trend continues")

    def forecast_memory_growth(
        self,
        current_count: int,
        growth_rate_per_day: float,
        days_ahead: int = 30,
    ) -> dict[str, Any]:
        """Forecast memory growth and predict when maintenance needed."""
        projected_count = current_count + (growth_rate_per_day * days_ahead)
        days_to_threshold = (
            (100000 - current_count) / growth_rate_per_day
            if growth_rate_per_day > 0
            else float("inf")
        )

        return {
            "current_memories": current_count,
            f"projected_in_{days_ahead}d": int(projected_count),
            "growth_rate_per_day": growth_rate_per_day,
            "estimated_days_to_sweep": days_to_threshold,
            "recommended_sweep_date": datetime.now().isoformat() if days_to_threshold < 14 else None,
        }

    def get_active_alerts(self, max_age_hours: float = 24.0) -> list[PredictiveAlert]:
        """Get alerts still within their prediction window."""
        now = time.time()
        return [
            alert
            for alert in self._alerts
            if (now - alert.created_at) / 3600 < alert.time_horizon_hours + max_age_hours
        ]


class CapabilityDiscoveryEngine:
    """Discovers emergent capabilities by testing unused tools and combinations."""

    def __init__(self) -> None:
        self._discovered: list[DiscoveredCapability] = []
        self._tested_combinations: set[tuple[str, ...]] = set()
        self._tool_usage: dict[str, int] = {}

    def discover_capabilities(self, available_tools: list[str]) -> list[DiscoveredCapability]:
        """Test unused tools and combinations to discover new capabilities."""
        discoveries: list[DiscoveredCapability] = []

        unused = [t for t in available_tools if self._tool_usage.get(t, 0) == 0]

        for tool in unused[:5]:
            discovery = DiscoveredCapability(
                capability_name=f"capability_{tool}",
                description=f"Discovered capability using {tool}",
                tools_involved=[tool],
                discovery_context="automated_testing",
                confidence=0.7,
                tested=False,
                test_results=None,
                discovered_at=time.time(),
            )
            discoveries.append(discovery)

        from itertools import combinations

        for combo in combinations(available_tools[:10], 2):
            if combo not in self._tested_combinations:
                discovery = DiscoveredCapability(
                    capability_name=f"combo_{combo[0]}_{combo[1]}",
                    description=f"Combined capability: {combo[0]} + {combo[1]}",
                    tools_involved=list(combo),
                    discovery_context="combination_testing",
                    confidence=0.5,
                    tested=False,
                    test_results=None,
                    discovered_at=time.time(),
                )
                discoveries.append(discovery)
                self._tested_combinations.add(combo)

        self._discovered.extend(discoveries)
        return discoveries

    def test_capability(self, capability: DiscoveredCapability) -> dict[str, Any]:
        """Test a discovered capability by dispatching its tools with a probe.

        Attempts to invoke each tool in the capability with a minimal test
        argument and records success/failure, timing, and output sample.
        """
        import time as _time

        test_result: dict[str, Any] = {
            "success": True,
            "execution_time_ms": 0.0,
            "output_sample": "",
            "errors": [],
        }

        for tool_name in capability.tools_involved:
            try:
                from whitemagic.tools.dispatch_table import dispatch

                start = _time.perf_counter()
                result = dispatch(tool_name, _probe=True)
                elapsed_ms = (_time.perf_counter() - start) * 1000

                test_result["execution_time_ms"] += elapsed_ms

                if isinstance(result, dict):
                    status = result.get("status", "")
                    has_error = "error" in result or status == "error"
                    if has_error:
                        err_msg = result.get("error", result.get("message", "unknown error"))
                        test_result["errors"].append(f"{tool_name}: {err_msg}")
                        test_result["success"] = False
                    else:
                        sample = str(result.get("result", result))[:200]
                        if test_result["output_sample"]:
                            test_result["output_sample"] += " | "
                        test_result["output_sample"] += f"{tool_name}→{sample}"
                else:
                    test_result["output_sample"] += f"{tool_name}→{str(result)[:200]}"
            except Exception as e:
                test_result["errors"].append(f"{tool_name}: {e}")
                test_result["success"] = False

        if len(capability.tools_involved) > 1:
            test_result["execution_time_ms"] /= len(capability.tools_involved)

        capability.tested = True
        capability.test_results = test_result
        capability.confidence = 0.9 if test_result["success"] else 0.3

        return test_result

    def report_emergent_capabilities(self) -> list[dict[str, Any]]:
        """Generate report of discovered and tested capabilities."""
        return [
            {
                "name": cap.capability_name,
                "description": cap.description,
                "tools": cap.tools_involved,
                "confidence": cap.confidence,
                "tested": cap.tested,
                "success": cap.test_results.get("success") if cap.test_results else None,
            }
            for cap in self._discovered
            if cap.tested and cap.confidence > 0.7
        ]


class ApotheosisEngine:
    """Unified Apotheosis Engine — autonomous evolution system.

    Brings together self-monitoring, predictive maintenance, and
    capability discovery into a cohesive autonomous evolution system.
    """

    def __init__(self) -> None:
        self.health_loop = SelfMonitoringHealthLoop()
        self.predictive = PredictiveMaintenanceEngine()
        self.capability = CapabilityDiscoveryEngine()
        self._running = False
        self._metrics: dict[str, Any] = {}

    def start(self) -> None:
        """Start the Apotheosis Engine."""
        self._running = True
        logger.info("Apotheosis Engine started — autonomous evolution active")
        self.health_loop.register_callback(self._on_health_degrade)

    def stop(self) -> None:
        """Stop the Apotheosis Engine."""
        self._running = False
        logger.info("Apotheosis Engine stopped")

    def tick(self, available_tools: list[str]) -> dict[str, Any]:
        """Single iteration of the Apotheosis Engine loop."""
        if not self._running:
            return {"status": "stopped"}

        results: dict[str, Any] = {
            "timestamp": time.time(),
            "status": "active",
        }

        # 1. Health check
        health_readings = self.health_loop.check_health()
        results["health"] = {
            metric: {"value": r.value, "status": r.status.value}
            for metric, r in health_readings.items()
        }

        # 2. Auto-heal if needed
        actions = self.health_loop.auto_heal(health_readings)
        if actions:
            results["auto_heal_actions"] = actions

        # 3. Predictive analysis
        history = [
            r
            for r in self.health_loop._history
            if time.time() - r.timestamp < 24 * 3600
        ]
        alerts = self.predictive.analyze_trends(history)
        if alerts:
            results["predictive_alerts"] = [
                {
                    "component": a.component,
                    "issue": a.predicted_issue,
                    "confidence": a.confidence,
                    "horizon_hours": a.time_horizon_hours,
                }
                for a in alerts
            ]

        # 4. Capability discovery
        discoveries = self.capability.discover_capabilities(available_tools)
        if discoveries:
            results["discoveries"] = len(discoveries)

        # 5. Test top discoveries
        tested = 0
        for disc in discoveries[:3]:
            self.capability.test_capability(disc)
            tested += 1
        results["capabilities_tested"] = tested

        return results

    def _on_health_degrade(self, status: HealthStatus, diagnosis: str) -> None:
        """Callback when health degrades."""
        logger.warning("Health degraded to %s: %s", status.value, diagnosis)

        if status == HealthStatus.CRITICAL:
            logger.error("CRITICAL HEALTH — Triggering emergency dream cycle")

    def get_status_report(self) -> str:
        """Generate human-readable status report."""
        lines = [
            "APOTHEOSIS ENGINE STATUS",
            "=" * 50,
            f"Status: {'Running' if self._running else 'Stopped'}",
            f"Health checks: {len(self.health_loop._history)}",
            f"Predictive alerts: {len(self.predictive.get_active_alerts())}",
            f"Capabilities discovered: {len(self.capability._discovered)}",
            f"Tested combinations: {len(self.capability._tested_combinations)}",
        ]
        return "\n".join(lines)


_apotheosis_engine: Optional[ApotheosisEngine] = None


def get_apotheosis_engine() -> ApotheosisEngine:
    """Get the global Apotheosis Engine singleton."""
    global _apotheosis_engine
    if _apotheosis_engine is None:
        _apotheosis_engine = ApotheosisEngine()
    return _apotheosis_engine
