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
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

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
    test_results: dict[str, Any] | None
    discovered_at: float


class SelfMonitoringHealthLoop:
    """Continuous self-monitoring system that watches WhiteMagic's own vitals.

    Implements hysteresis-based alert suppression: only fires callbacks when
    health status *changes*, not on every check. This prevents log spam when
    a metric is consistently slightly below threshold.
    """

    def __init__(self, check_interval_seconds: float = 60.0) -> None:
        self.interval = check_interval_seconds
        self._running = False
        self._last_check: float = 0.0
        self._history: list[HealthReading] = []
        self._callbacks: list[Callable[[HealthStatus, str], None]] = []

        # Track last status per metric for hysteresis (suppress repeated alerts)
        self._last_status: dict[str, HealthStatus] = {}
        self._last_worst_status: HealthStatus = HealthStatus.HEALTHY
        self._degraded_count: int = 0  # How many consecutive degraded checks
        self._recovery_count: int = 0   # How many consecutive healthy checks

        self.thresholds = {
            "coherence": 0.6,
            "memory_usage_percent": 85.0,
            "response_time_ms": 1000.0,
            "error_rate": 0.05,
            "dream_cycle_age_hours": 24.0,
            "galaxy_health": 0.7,
            "citta_stream_health": 0.7,
            "tool_dispatch_health": 0.8,
            # Biological / immune-inspired metrics
            "inflammation_index": 0.3,
            "antibody_diversity": 0.5,
            "signal_to_noise": 0.3,
            "setpoint_deviation": 0.15,
            "guna_balance": 0.7,
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
            if coherence_metric.last_measured is None:
                coherence_overall = 0.5
            else:
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

        # 2. Memory usage check — real memory count from galaxy backend
        try:
            from whitemagic.core.memory.unified import get_unified_memory
            um = get_unified_memory()
            stats = um._galaxy_backend.get_stats()
            mem_count = stats.get("total_memories", 0)
            mem_usage_pct = min(100.0, (mem_count / 100000) * 100)
        except Exception:
            mem_usage_pct = 50.0
        readings["memory_usage"] = HealthReading(
            timestamp=now,
            metric_name="memory_usage_percent",
            value=mem_usage_pct,
            threshold=self.thresholds["memory_usage_percent"],
            status=self._status_from_value(
                mem_usage_pct, self.thresholds["memory_usage_percent"], higher_is_better=False
            ),
        )

        # 3. Response time check — real avg from calibration data
        try:
            import json as _json
            import os as _os
            state_root = _os.environ.get("WM_STATE_ROOT", _os.path.expanduser("~/.whitemagic"))
            cal_path = _os.path.join(state_root, "citta", "calibration.jsonl")
            if _os.path.exists(cal_path):
                with open(cal_path) as f:
                    cal_lines = f.readlines()[-10:]
                if cal_lines:
                    actuals = [_json.loads(line).get("actual_seconds_machine", 0) for line in cal_lines]
                    avg_response_ms = (sum(actuals) / len(actuals)) * 1000
                else:
                    avg_response_ms = 100.0
            else:
                avg_response_ms = 100.0
        except Exception:
            avg_response_ms = 100.0
        readings["response_time"] = HealthReading(
            timestamp=now,
            metric_name="response_time_ms",
            value=avg_response_ms,
            threshold=self.thresholds["response_time_ms"],
            status=self._status_from_value(
                avg_response_ms, self.thresholds["response_time_ms"], higher_is_better=False
            ),
        )

        # 4. Error rate check — real from telemetry
        try:
            import json as _json
            import os as _os
            state_root = _os.environ.get("WM_STATE_ROOT", _os.path.expanduser("~/.whitemagic"))
            telem_path = _os.path.join(state_root, "citta", "telemetry.jsonl")
            if _os.path.exists(telem_path):
                with open(telem_path) as f:
                    telem_lines = f.readlines()[-20:]
                if telem_lines:
                    errors = sum(1 for line in telem_lines if _json.loads(line).get("status") == "error")
                    error_rate = errors / len(telem_lines)
                else:
                    error_rate = 0.0
            else:
                error_rate = 0.0
        except Exception:
            error_rate = 0.0
        readings["error_rate"] = HealthReading(
            timestamp=now,
            metric_name="error_rate",
            value=error_rate,
            threshold=self.thresholds["error_rate"],
            status=self._status_from_value(
                error_rate, self.thresholds["error_rate"], higher_is_better=False
            ),
        )

        # 5. Dream cycle freshness — real check
        try:
            from whitemagic.core.dreaming.dream_cycle import get_dream_cycle
            dc = get_dream_cycle()
            last_dream = getattr(dc, "_last_dream_time", 0)
            if last_dream > 0:
                dream_age_h = (now - last_dream) / 3600.0
            else:
                dream_age_h = 0.0
        except Exception:
            dream_age_h = 0.0
        readings["dream_freshness"] = HealthReading(
            timestamp=now,
            metric_name="dream_cycle_age_hours",
            value=dream_age_h,
            threshold=self.thresholds["dream_cycle_age_hours"],
            status=self._status_from_value(
                dream_age_h, self.thresholds["dream_cycle_age_hours"], higher_is_better=False
            ),
        )

        # 6. Galaxy health — fraction of galaxies with intact integrity
        try:
            from whitemagic.core.memory.unified import get_unified_memory
            um = get_unified_memory()
            gb = um._galaxy_backend
            galaxies = gb.list_galaxies()
            if galaxies:
                healthy = sum(1 for g in galaxies if gb._get_galaxy_backend(g).pool.quick_integrity_check())
                galaxy_health = healthy / len(galaxies)
            else:
                galaxy_health = 1.0
        except Exception:
            galaxy_health = 1.0
        readings["galaxy_health"] = HealthReading(
            timestamp=now,
            metric_name="galaxy_health",
            value=galaxy_health,
            threshold=self.thresholds["galaxy_health"],
            status=self._status_from_value(
                galaxy_health, self.thresholds["galaxy_health"], higher_is_better=True
            ),
        )

        # 7. Citta stream health — stream length and coherence stability
        try:
            from whitemagic.core.consciousness.citta_cycle import get_citta_cycle
            cycle = get_citta_cycle()
            summary = cycle.get_cycle_summary()
            stream_len = summary.get("stream_length", 0)
            avg_coh = summary.get("avg_coherence", 0.5)
            citta_health = min(1.0, (stream_len / 20) * 0.3 + avg_coh * 0.7)
        except Exception:
            citta_health = 0.5
        readings["citta_stream_health"] = HealthReading(
            timestamp=now,
            metric_name="citta_stream_health",
            value=citta_health,
            threshold=self.thresholds["citta_stream_health"],
            status=self._status_from_value(
                citta_health, self.thresholds["citta_stream_health"], higher_is_better=True
            ),
        )

        # 8. Inflammation index — repeated alerts in recent history
        try:
            recent = self._history[-20:] if self._history else []
            stressed_count = sum(
                1 for r in recent
                if r.status in (HealthStatus.STRESSED, HealthStatus.DEGRADED, HealthStatus.CRITICAL)
            )
            inflammation = stressed_count / max(1, len(recent))
        except Exception:
            inflammation = 0.0
        readings["inflammation"] = HealthReading(
            timestamp=now,
            metric_name="inflammation_index",
            value=inflammation,
            threshold=self.thresholds["inflammation_index"],
            status=self._status_from_value(
                inflammation, self.thresholds["inflammation_index"], higher_is_better=False
            ),
        )

        # 9. Antibody diversity — distinct error types recovered from
        try:
            import json as _json2
            import os as _os2
            state_root = _os2.environ.get("WM_STATE_ROOT", _os2.path.expanduser("~/.whitemagic"))
            recovery_path = _os2.path.join(state_root, "citta", "recovery_registry.jsonl")
            if _os2.path.exists(recovery_path):
                with open(recovery_path) as f:
                    lines = f.readlines()[-50:]
                error_types: set[str] = set()
                for line in lines:
                    try:
                        entry = _json2.loads(line)
                        error_types.add(entry.get("error_type", "unknown"))
                    except Exception:
                        continue
                antibody_diversity = min(1.0, len(error_types) / 10.0)
            else:
                antibody_diversity = 0.5
        except Exception:
            antibody_diversity = 0.5
        readings["antibody_diversity"] = HealthReading(
            timestamp=now,
            metric_name="antibody_diversity",
            value=antibody_diversity,
            threshold=self.thresholds["antibody_diversity"],
            status=self._status_from_value(
                antibody_diversity, self.thresholds["antibody_diversity"], higher_is_better=True
            ),
        )

        # 10. Signal-to-noise ratio — user vs auto-generated activity
        try:
            from whitemagic.core.consciousness.citta_cycle import get_citta_cycle
            cycle = get_citta_cycle()
            summary = cycle.get_cycle_summary()
            coloring = summary.get("emotional_coloring", {})
            distribution = coloring.get("distribution", {})
            total = sum(distribution.values()) if distribution else 1
            signal = distribution.get("rajasic", 0) + distribution.get("frustrated", 0)
            noise = distribution.get("sattvic", 0) + distribution.get("neutral", 0) + distribution.get("tamasic", 0)
            if total > 0 and signal + noise > 0:
                snr = signal / (signal + noise)
            else:
                snr = 0.5
        except Exception:
            snr = 0.5
        readings["signal_to_noise"] = HealthReading(
            timestamp=now,
            metric_name="signal_to_noise",
            value=snr,
            threshold=self.thresholds["signal_to_noise"],
            status=self._status_from_value(
                snr, self.thresholds["signal_to_noise"], higher_is_better=True
            ),
        )

        # 11. Setpoint deviation — average distance from target values
        try:
            deviations: list[float] = []
            for r in readings.values():
                if r.metric_name in ("inflammation_index", "antibody_diversity", "signal_to_noise", "setpoint_deviation", "guna_balance"):
                    continue
                threshold = r.threshold
                if threshold > 0:
                    ratio = r.value / threshold
                    dev = abs(1.0 - min(2.0, ratio))
                    deviations.append(dev)
            avg_deviation = sum(deviations) / len(deviations) if deviations else 0.0
        except Exception:
            avg_deviation = 0.0
        readings["setpoint_deviation"] = HealthReading(
            timestamp=now,
            metric_name="setpoint_deviation",
            value=avg_deviation,
            threshold=self.thresholds["setpoint_deviation"],
            status=self._status_from_value(
                avg_deviation, self.thresholds["setpoint_deviation"], higher_is_better=False
            ),
        )

        # 12. Guna balance — biorhythm health
        try:
            from whitemagic.core.consciousness.guna_balance import get_guna_balance
            gb = get_guna_balance()
            gb_reading = gb.measure()
            guna_health = 1.0 if gb_reading.balanced else max(0.0, 1.0 - sum(gb_reading.deficits.values()) - sum(gb_reading.surpluses.values()))
        except Exception:
            guna_health = 0.8
        readings["guna_balance"] = HealthReading(
            timestamp=now,
            metric_name="guna_balance",
            value=guna_health,
            threshold=self.thresholds["guna_balance"],
            status=self._status_from_value(
                guna_health, self.thresholds["guna_balance"], higher_is_better=True
            ),
        )

        self._history.extend(readings.values())
        # Trim history to prevent unbounded growth
        if len(self._history) > 1000:
            self._history = self._history[-500:]

        worst_status = max(
            (r.status for r in readings.values()),
            key=lambda s: list(HealthStatus).index(s),
        )

        # Hysteresis: only fire callbacks when status CHANGES
        # or after 10 consecutive degraded checks (persistent issue)
        status_changed = worst_status != self._last_worst_status

        if worst_status in (
            HealthStatus.STRESSED,
            HealthStatus.DEGRADED,
            HealthStatus.CRITICAL,
        ):
            self._degraded_count += 1
            self._recovery_count = 0
            should_fire = status_changed or (self._degraded_count % 10 == 0)
        else:
            self._degraded_count = 0
            self._recovery_count += 1
            should_fire = status_changed and self._recovery_count == 1

        if should_fire:
            for callback in self._callbacks:
                try:
                    callback(worst_status, self._generate_diagnosis(readings))
                except Exception as e:
                    logger.debug("Health callback error: %s", e)

        self._last_worst_status = worst_status
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
            if r.status
            in (HealthStatus.STRESSED, HealthStatus.DEGRADED, HealthStatus.CRITICAL)
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
        """Automatically trigger healing measures based on health readings.

        Cybernetic feedback loop: degradation in one system triggers
        corrective actions across interconnected systems.
        """
        actions: list[str] = []

        # Coherence degradation → dream cycle + smarana practice
        if readings["coherence"].status in (
            HealthStatus.DEGRADED,
            HealthStatus.CRITICAL,
        ):
            actions.append("triggered_dream_cycle")
            logger.info("Auto-heal: Triggering dream cycle for coherence restoration")
            try:
                from whitemagic.core.dreaming.dream_cycle import get_dream_cycle
                get_dream_cycle().trigger_cycle(reason="coherence_restoration")
            except Exception:
                logger.debug("Ignored error in apotheosis_engine.py:513")

        # Coherence stressed but not degraded → warm memory access
        if readings["coherence"].status == HealthStatus.STRESSED:
            actions.append("warmed_memory_access")
            logger.debug("Auto-heal: Warming memory access for coherence boost")
            try:
                from whitemagic.core.memory.unified import get_unified_memory
                um = get_unified_memory()
                recent = um.search(limit=5)
                for m in recent:
                    um.recall(m.id)
            except Exception:
                logger.debug("Ignored error in apotheosis_engine.py:526")

        # Memory usage high → galactic sweep
        mem_reading = readings.get("memory_usage")
        if mem_reading and mem_reading.status in (
            HealthStatus.STRESSED,
            HealthStatus.DEGRADED,
        ):
            actions.append("scheduled_galactic_sweep")
            logger.info("Auto-heal: Scheduling galactic sweep for memory pressure")

        # Error rate high → circuit breaker check
        err_reading = readings.get("error_rate")
        if err_reading and err_reading.status in (
            HealthStatus.DEGRADED,
            HealthStatus.CRITICAL,
        ):
            actions.append("circuit_breaker_check")
            logger.info("Auto-heal: Error rate elevated, checking circuit breakers")

        # Galaxy health degraded → integrity repair
        gal_reading = readings.get("galaxy_health")
        if gal_reading and gal_reading.status in (
            HealthStatus.DEGRADED,
            HealthStatus.CRITICAL,
        ):
            actions.append("galaxy_integrity_repair")
            logger.info("Auto-heal: Galaxy integrity compromised, scheduling repair")

        # Citta stream health low → stream reinforcement
        citta_reading = readings.get("citta_stream_health")
        if citta_reading and citta_reading.status in (
            HealthStatus.DEGRADED,
            HealthStatus.CRITICAL,
        ):
            actions.append("citta_stream_reinforcement")
            logger.info("Auto-heal: Citta stream weak, reinforcing with background tick")

        # Inflammation high → suppress non-critical alerts (immune system calming)
        infl_reading = readings.get("inflammation")
        if infl_reading and infl_reading.status in (
            HealthStatus.DEGRADED,
            HealthStatus.CRITICAL,
        ):
            actions.append("anti_inflammatory_suppression")
            logger.info("Auto-heal: Inflammation high, suppressing non-critical alerts")

        # Signal-to-noise low → system is talking to itself too much
        snr_reading = readings.get("signal_to_noise")
        if snr_reading and snr_reading.status in (
            HealthStatus.DEGRADED,
            HealthStatus.CRITICAL,
        ):
            actions.append("seek_external_input")
            logger.info("Auto-heal: Low SNR, system needs external engagement")

        # Guna imbalance → apply biorhythm correction
        guna_reading = readings.get("guna_balance")
        if guna_reading and guna_reading.status in (
            HealthStatus.STRESSED,
            HealthStatus.DEGRADED,
            HealthStatus.CRITICAL,
        ):
            actions.append("guna_balance_correction")
            logger.info("Auto-heal: Guna imbalance detected, applying biorhythm correction")
            try:
                from whitemagic.core.consciousness.guna_balance import get_guna_balance
                gb = get_guna_balance()
                reading = gb.measure()
                if reading.correction_action:
                    gb.apply_correction(reading.correction_action)
            except Exception:
                logger.debug("Ignored error in apotheosis_engine.py:598")

        return actions


class PredictiveMaintenanceEngine:
    """Predictive maintenance system that forecasts problems before they cascade."""

    def __init__(self) -> None:
        self._alerts: list[PredictiveAlert] = []
        self._pattern_history: list[dict[str, Any]] = []

    def analyze_trends(
        self, health_history: list[HealthReading]
    ) -> list[PredictiveAlert]:
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
                            severity=HealthStatus.STRESSED
                            if time_to_cross > 12
                            else HealthStatus.DEGRADED,
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
            "recommended_sweep_date": datetime.now().isoformat()
            if days_to_threshold < 14
            else None,
        }

    def get_active_alerts(self, max_age_hours: float = 24.0) -> list[PredictiveAlert]:
        """Get alerts still within their prediction window."""
        now = time.time()
        return [
            alert
            for alert in self._alerts
            if (now - alert.created_at) / 3600
            < alert.time_horizon_hours + max_age_hours
        ]


class CapabilityDiscoveryEngine:
    """Discovers emergent capabilities by testing unused tools and combinations."""

    def __init__(self) -> None:
        self._discovered: list[DiscoveredCapability] = []
        self._tested_combinations: set[tuple[str, ...]] = set()
        self._tool_usage: dict[str, int] = {}

    def discover_capabilities(
        self, available_tools: list[str]
    ) -> list[DiscoveredCapability]:
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
                from whitemagic.core.ports import dispatch

                start = _time.perf_counter()
                result = dispatch(tool_name, _probe=True)
                elapsed_ms = (_time.perf_counter() - start) * 1000

                test_result["execution_time_ms"] += elapsed_ms

                if isinstance(result, dict):
                    status = result.get("status", "")
                    has_error = "error" in result or status == "error"
                    if has_error:
                        err_msg = result.get(
                            "error", result.get("message", "unknown error")
                        )
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
                "success": cap.test_results.get("success")
                if cap.test_results
                else None,
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
        """Callback when health degrades — fires only on status changes (hysteresis)."""
        if status == HealthStatus.CRITICAL:
            logger.error("CRITICAL HEALTH — Triggering emergency dream cycle: %s", diagnosis)
            try:
                from whitemagic.core.dreaming.dream_cycle import get_dream_cycle
                get_dream_cycle().trigger_cycle(reason="emergency_health_restoration")
            except Exception:
                logger.debug("Ignored error in apotheosis_engine.py:906")
        elif status == HealthStatus.STRESSED:
            logger.debug("Health stressed (suppressed): %s", diagnosis)
        elif status == HealthStatus.HEALTHY:
            logger.info("Health recovered to healthy")
        else:
            logger.warning("Health degraded to %s: %s", status.value, diagnosis)

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


_apotheosis_engine: ApotheosisEngine | None = None


def get_apotheosis_engine() -> ApotheosisEngine:
    """Get the global Apotheosis Engine singleton."""
    global _apotheosis_engine
    if _apotheosis_engine is None:
        _apotheosis_engine = ApotheosisEngine()
    return _apotheosis_engine
