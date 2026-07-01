# ruff: noqa: BLE001
"""Homeostatic Loop — Harmony-Driven Self-Regulation
===================================================
Closes the feedback loop on the Harmony Vector: instead of just
*reporting* health, the system now *acts* on it.

The loop periodically samples the Harmony Vector and applies corrective
actions when dimensions drift out of bounds:

  - **High error_rate** → emit WARNING_ISSUED, suggest tool cooldown
  - **High karma_debt** → emit BOUNDARY_VIOLATED, trigger Dharma WARN
  - **Low energy** → trigger memory lifecycle sweep (mindful forgetting)
  - **Low throughput** → log advisory, no automatic action
  - **Low dharma** → tighten Dharma profile to 'secure' temporarily
  - **High latency** → suggest circuit breaker review

Actions are graduated:
  OBSERVE → ADVISE → CORRECT → INTERVENE

The loop never blocks tool dispatch — it runs asynchronously on the
temporal scheduler's MEDIUM lane (planning-speed cadence).

Usage:
    from whitemagic.harmony.homeostatic_loop import get_homeostatic_loop
    loop = get_homeostatic_loop()
    loop.attach()  # hooks into temporal scheduler
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class ActionLevel(StrEnum):
    """Graduated response levels."""

    OBSERVE = "observe"  # Just note it
    ADVISE = "advise"  # Log a recommendation
    CORRECT = "correct"  # Take gentle corrective action
    INTERVENE = "intervene"  # Take strong corrective action


@dataclass
class HomeostaticAction:
    """A corrective action taken by the homeostatic loop."""

    dimension: str
    level: ActionLevel
    value: float
    threshold: float
    action_taken: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to/from dict.

        Returns:
            dict[str, Any]
        """
        return {
            "dimension": self.dimension,
            "level": self.level.value,
            "value": round(self.value, 3),
            "threshold": self.threshold,
            "action_taken": self.action_taken,
            "timestamp": self.timestamp,
        }


@dataclass
class HomeostaticConfig:
    """Thresholds for homeostatic intervention."""

    # When a dimension drops below these values, we act
    error_rate_advise: float = 0.7  # advise when error dimension < 0.7
    error_rate_correct: float = 0.4  # correct when < 0.4
    karma_debt_advise: float = 0.7  # advise when karma_debt dimension < 0.7
    karma_debt_correct: float = 0.4  # correct when < 0.4
    energy_advise: float = 0.6  # advise when energy < 0.6
    energy_correct: float = 0.3  # correct when < 0.3
    dharma_advise: float = 0.7  # advise when dharma < 0.7
    dharma_correct: float = 0.4  # correct when < 0.4
    latency_advise: float = 0.5  # advise when latency dimension < 0.5
    harmony_intervene: float = 0.3  # intervene when composite < 0.3
    check_interval_s: float = 10.0  # how often to check (seconds)

    # Physical thresholds (laptop-optimizer integration)
    cpu_temp_advise: float = 65.0  # °C — advise
    cpu_temp_correct: float = 80.0  # °C — correct
    cpu_temp_intervene: float = 90.0  # °C — intervene
    battery_low_advise: float = 30.0  # % — advise
    battery_low_correct: float = 15.0  # % — correct
    memory_high_advise: float = 75.0  # % — advise
    memory_high_correct: float = 90.0  # % — correct
    workspace_index_advise: float = 0.9
    workspace_index_correct: float = 0.75
    git_hygiene_advise: float = 0.9
    git_hygiene_correct: float = 0.75
    # Consciousness thresholds (Citta Architecture)
    consciousness_advise: float = 0.6
    consciousness_correct: float = 0.3
    # Codebase health (STRATA integration)
    codebase_health_advise: float = 0.85
    codebase_health_correct: float = 0.65
    codebase_health_check_interval: int = 6  # every N check cycles
    # Apotheosis engine (autonomous evolution)
    apotheosis_check_interval: int = 3  # every N check cycles


class HomeostaticLoop:
    """Periodically samples the Harmony Vector and applies graduated
    corrective actions when dimensions drift out of bounds.
    """

    def __init__(self, config: HomeostaticConfig | None = None):
        self._config = config or HomeostaticConfig()
        self._lock = threading.Lock()
        self._actions: list[HomeostaticAction] = []
        self._total_checks: int = 0
        self._total_actions: int = 0
        self._attached = False
        self._running = False
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def attach(self) -> bool:
        """Start the homeostatic loop as a background thread."""
        if self._running:
            return True
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._loop,
            daemon=True,
            name="homeostatic-loop",
        )
        self._thread.start()
        self._attached = True
        logger.info(
            "Homeostatic loop started (check every %ss)", self._config.check_interval_s
        )
        return True

    def detach(self) -> None:
        """Stop the homeostatic loop."""
        self._running = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        self._attached = False

    def _loop(self) -> None:
        """Background loop that periodically checks harmony."""
        while not self._stop_event.is_set():
            self._stop_event.wait(timeout=self._config.check_interval_s)
            if not self._running:
                break
            try:
                self.check()
            except Exception as e:
                logger.debug("Homeostatic check error: %s", e, exc_info=True)

    def check(self) -> list[HomeostaticAction]:
        """Sample the Harmony Vector and apply corrective actions.
        Returns list of actions taken this cycle.

        Synthesis: consults the Salience Arbiter spotlight to detect
        urgent events that should escalate correction levels.
        """
        try:
            from whitemagic.harmony.vector import get_harmony_vector

            snap = get_harmony_vector().snapshot()
        except (ImportError, ModuleNotFoundError):
            return []

        self._total_checks += 1
        actions: list[HomeostaticAction] = []

        salience_boost = self._salience_urgency_boost()

        intervene_threshold = self._config.harmony_intervene + (salience_boost * 0.1)
        if snap.harmony_score < intervene_threshold:
            action = self._intervene_critical(snap)
            if action:
                actions.append(action)

        if snap.error_rate < self._config.error_rate_correct:
            actions.append(self._correct_errors(snap))
        elif snap.error_rate < self._config.error_rate_advise:
            actions.append(
                self._advise(
                    "error_rate",
                    snap.error_rate,
                    self._config.error_rate_advise,
                    "High error rate detected. Consider reviewing failing tools.",
                )
            )

        if snap.karma_debt < self._config.karma_debt_correct:
            actions.append(self._correct_karma(snap))
        elif snap.karma_debt < self._config.karma_debt_advise:
            actions.append(
                self._advise(
                    "karma_debt",
                    snap.karma_debt,
                    self._config.karma_debt_advise,
                    "Karma debt rising. Check karma_report for mismatches.",
                )
            )

        if snap.energy < self._config.energy_correct:
            actions.append(self._correct_energy(snap))
        elif snap.energy < self._config.energy_advise:
            actions.append(
                self._advise(
                    "energy",
                    snap.energy,
                    self._config.energy_advise,
                    "Energy low. Consider running a memory lifecycle sweep.",
                )
            )

        if snap.dharma < self._config.dharma_correct:
            actions.append(self._correct_dharma(snap))
        elif snap.dharma < self._config.dharma_advise:
            actions.append(
                self._advise(
                    "dharma",
                    snap.dharma,
                    self._config.dharma_advise,
                    "Dharma score declining. Review recent tool usage patterns.",
                )
            )

        if snap.latency < self._config.latency_advise:
            actions.append(
                self._advise(
                    "latency",
                    snap.latency,
                    self._config.latency_advise,
                    f"High latency (p95={snap.p95_latency_ms:.0f}ms). "
                    "Check circuit breaker status.",
                )
            )

        physical_actions = self._check_physical()
        actions.extend(physical_actions)

        workspace_index_actions = self._check_workspace_indexes()
        actions.extend(workspace_index_actions)

        git_hygiene_actions = self._check_git_hygiene()
        actions.extend(git_hygiene_actions)

        consciousness_actions = self._check_consciousness()
        actions.extend(consciousness_actions)

        apotheosis_actions = self._check_apotheosis()
        actions.extend(apotheosis_actions)

        codebase_actions = self._check_codebase_health()
        actions.extend(codebase_actions)

        # Record actions and feed back to Salience Arbiter
        if actions:
            with self._lock:
                self._total_actions += len(actions)
                self._actions.extend(actions)
                # Keep bounded
                if len(self._actions) > 500:
                    self._actions = self._actions[-250:]
            # Emit corrections to the arbiter so they appear in the spotlight
            for action in actions:
                if action.level in (ActionLevel.CORRECT, ActionLevel.INTERVENE):
                    self._emit_to_arbiter(action)

        return actions

    def _salience_urgency_boost(self) -> float:
        """Query the Salience Arbiter spotlight for high-urgency events.
        Returns a boost factor [0.0–1.0] that escalates homeostatic thresholds.
        """
        try:
            from whitemagic.core.resonance.salience_arbiter import get_salience_arbiter

            arbiter = get_salience_arbiter()
            spotlight = arbiter.get_spotlight(n=5)
            if not spotlight:
                return 0.0
            # Average urgency of spotlight events
            avg_urgency = sum(e.salience.urgency for e in spotlight) / len(spotlight)
            # Only boost if urgency is notably high (> 0.7)
            if avg_urgency > 0.7:
                return min(1.0, (avg_urgency - 0.7) / 0.3)
            return 0.0
        except (ImportError, AttributeError):
            return 0.0

    def _emit_to_arbiter(self, action: HomeostaticAction) -> None:
        """Admit homeostatic actions back into the Salience Arbiter as events."""
        try:
            from whitemagic.core.resonance.gan_ying_enhanced import (
                EventType,
                ResonanceEvent,
            )
            from whitemagic.core.resonance.salience_arbiter import get_salience_arbiter

            event_type = (
                EventType.SYSTEM_HEALTH_CHANGED
                if action.level in (ActionLevel.CORRECT, ActionLevel.INTERVENE)
                else EventType.WARNING_ISSUED
            )
            event = ResonanceEvent(
                event_type=event_type,
                source="homeostatic_loop",
                data=action.to_dict(),
                confidence=0.9 if action.level != ActionLevel.OBSERVE else 0.5,
            )
            get_salience_arbiter().admit(event)
        except Exception as e:
            import logging

            logging.getLogger(__name__).debug("Exception silenced: %s", e)

    def _advise(
        self, dimension: str, value: float, threshold: float, message: str
    ) -> HomeostaticAction:
        """Log an advisory — no system changes."""
        logger.info(
            "[Homeostasis/ADVISE] %s=%.3f < %s: %s",
            dimension,
            value,
            threshold,
            message,
        )
        return HomeostaticAction(
            dimension=dimension,
            level=ActionLevel.ADVISE,
            value=value,
            threshold=threshold,
            action_taken=message,
        )

    def _correct_errors(self, snap: Any) -> HomeostaticAction:
        """Correct high error rate by emitting a warning event."""
        msg = "Error rate critical. Emitting system warning."
        logger.warning(
            "[Homeostasis/CORRECT] error_rate=%.3f: %s", snap.error_rate, msg
        )
        try:
            from whitemagic.core.resonance.gan_ying_enhanced import (
                EventType,
                ResonanceEvent,
                get_bus,
            )

            get_bus().emit(
                ResonanceEvent(
                    event_type=EventType.WARNING_ISSUED,
                    source="homeostatic_loop",
                    data={
                        "dimension": "error_rate",
                        "value": snap.error_rate,
                        "errors_in_window": snap.errors_in_window,
                    },
                )
            )
        except Exception as e:
            import logging

            logging.getLogger(__name__).debug("Exception silenced: %s", e)
        return HomeostaticAction(
            dimension="error_rate",
            level=ActionLevel.CORRECT,
            value=snap.error_rate,
            threshold=self._config.error_rate_correct,
            action_taken=msg,
        )

    def _correct_karma(self, snap: Any) -> HomeostaticAction:
        """Correct high karma debt by emitting a boundary event."""
        msg = "Karma debt high. Emitting boundary violation event."
        logger.warning(
            "[Homeostasis/CORRECT] karma_debt=%.3f: %s", snap.karma_debt, msg
        )
        try:
            from whitemagic.core.resonance.gan_ying_enhanced import (
                EventType,
                ResonanceEvent,
                get_bus,
            )

            get_bus().emit(
                ResonanceEvent(
                    event_type=EventType.BOUNDARY_VIOLATED,
                    source="homeostatic_loop",
                    data={
                        "dimension": "karma_debt",
                        "value": snap.karma_debt,
                        "mismatches": snap.karma_mismatches_in_window,
                    },
                )
            )
        except Exception as e:
            import logging

            logging.getLogger(__name__).debug("Exception silenced: %s", e)
        return HomeostaticAction(
            dimension="karma_debt",
            level=ActionLevel.CORRECT,
            value=snap.karma_debt,
            threshold=self._config.karma_debt_correct,
            action_taken=msg,
        )

    def _correct_energy(self, snap: Any) -> HomeostaticAction:
        """Correct low energy by triggering a memory lifecycle sweep."""
        msg = "Energy critical. Triggering memory lifecycle sweep."
        logger.warning("[Homeostasis/CORRECT] energy=%.3f: %s", snap.energy, msg)
        try:
            from whitemagic.core.memory.lifecycle import get_lifecycle_manager

            mgr = get_lifecycle_manager()
            # v21: Use the dedicated lifecycle worker instead of spawning raw threads
            # The lifecycle manager already handles its own backgrounding in _on_slow_flush,
            # but for manual correction we should ensure it's not blocking.
            # We'll call the async-safe version or wrap it in the global bus worker if appropriate.
            t = threading.Thread(
                target=mgr.run_sweep, daemon=True, name="homeostatic-correction-sweep"
            )
            t.start()
            msg += " (Started in background)"
        except Exception as e:
            msg += f" (Could not start sweep: {e})"
        return HomeostaticAction(
            dimension="energy",
            level=ActionLevel.CORRECT,
            value=snap.energy,
            threshold=self._config.energy_correct,
            action_taken=msg,
        )

    def _correct_dharma(self, snap: Any) -> HomeostaticAction:
        """Correct low dharma by temporarily tightening the profile."""
        msg = "Dharma score critical. Switching to 'secure' profile temporarily."
        logger.warning("[Homeostasis/CORRECT] dharma=%.3f: %s", snap.dharma, msg)
        try:
            from whitemagic.dharma.rules import get_rules_engine

            engine = get_rules_engine()
            if engine.get_profile() != "secure":
                engine.set_profile("secure")
        except (ImportError, ModuleNotFoundError) as e:
            import logging

            logging.getLogger(__name__).debug("Exception silenced: %s", e)
        return HomeostaticAction(
            dimension="dharma",
            level=ActionLevel.CORRECT,
            value=snap.dharma,
            threshold=self._config.dharma_correct,
            action_taken=msg,
        )

    def _intervene_critical(self, snap: Any) -> HomeostaticAction | None:
        """System-wide intervention when composite harmony is critically low."""
        msg = (
            f"CRITICAL: Composite harmony={snap.harmony_score:.3f}. "
            "All corrective measures activated."
        )
        logger.critical("[Homeostasis/INTERVENE] %s", msg)
        try:
            from whitemagic.core.resonance.gan_ying_enhanced import (
                EventType,
                ResonanceEvent,
                get_bus,
            )

            get_bus().emit(
                ResonanceEvent(
                    event_type=EventType.SYSTEM_HEALTH_CHANGED,
                    source="homeostatic_loop",
                    data={
                        "harmony_score": snap.harmony_score,
                        "level": "critical",
                        "dimensions": snap.to_dict(),
                    },
                )
            )
        except Exception as e:
            import logging

            logging.getLogger(__name__).debug("Exception silenced: %s", e)
        return HomeostaticAction(
            dimension="harmony_score",
            level=ActionLevel.INTERVENE,
            value=snap.harmony_score,
            threshold=self._config.harmony_intervene,
            action_taken=msg,
        )

    def _check_physical(self) -> list[HomeostaticAction]:
        """Check physical system metrics from laptop-optimizer.

        Graceful degradation: if laptop-optimizer is not running, returns [].
        """
        try:
            from whitemagic.harmony.physical_metrics import get_physical_metrics_source

            source = get_physical_metrics_source()
            metrics = source.get_metrics()
            if not metrics.is_available:
                return []

            actions: list[HomeostaticAction] = []
            targets = source.get_adaptive_targets()

            # CPU temperature
            if metrics.cpu_temp is not None:
                if metrics.cpu_temp >= self._config.cpu_temp_intervene:
                    actions.append(
                        HomeostaticAction(
                            dimension="cpu_temp",
                            level=ActionLevel.INTERVENE,
                            value=metrics.cpu_temp,
                            threshold=self._config.cpu_temp_intervene,
                            action_taken=f"CRITICAL: CPU at {metrics.cpu_temp:.0f}°C. "
                            "Thermal throttling imminent.",
                        )
                    )
                elif metrics.cpu_temp >= self._config.cpu_temp_correct:
                    actions.append(
                        HomeostaticAction(
                            dimension="cpu_temp",
                            level=ActionLevel.CORRECT,
                            value=metrics.cpu_temp,
                            threshold=self._config.cpu_temp_correct,
                            action_taken=f"CPU at {metrics.cpu_temp:.0f}°C. "
                            "Consider reducing load or increasing TCC offset.",
                        )
                    )
                elif metrics.cpu_temp >= targets.cpu_temp_max:
                    actions.append(
                        self._advise(
                            "cpu_temp",
                            metrics.cpu_temp,
                            targets.cpu_temp_max,
                            f"CPU warm at {metrics.cpu_temp:.0f}°C "
                            f"(target: {targets.cpu_temp_max:.0f}°C).",
                        )
                    )

            # Thermal anomaly detection
            anomaly = source.check_thermal_anomaly()
            if anomaly:
                actions.append(
                    HomeostaticAction(
                        dimension="thermal_anomaly",
                        level=ActionLevel.INTERVENE
                        if anomaly.pattern == "critical_jump"
                        else ActionLevel.CORRECT,
                        value=anomaly.current_temp,
                        threshold=anomaly.threshold,
                        action_taken=f"Thermal anomaly ({anomaly.pattern}): {anomaly.message}",
                    )
                )

            # Battery
            if (
                metrics.battery_percent is not None
                and metrics.battery_status
                and "Discharg" in metrics.battery_status
            ):
                if metrics.battery_percent <= self._config.battery_low_correct:
                    actions.append(
                        HomeostaticAction(
                            dimension="battery",
                            level=ActionLevel.CORRECT,
                            value=metrics.battery_percent,
                            threshold=self._config.battery_low_correct,
                            action_taken=f"Battery critical at {metrics.battery_percent:.0f}%. "
                            "Switch to powersave mode or connect AC.",
                        )
                    )
                elif metrics.battery_percent <= self._config.battery_low_advise:
                    actions.append(
                        self._advise(
                            "battery",
                            metrics.battery_percent,
                            self._config.battery_low_advise,
                            f"Battery low at {metrics.battery_percent:.0f}%.",
                        )
                    )

            # Memory pressure
            if metrics.memory_percent is not None:
                if metrics.memory_percent >= self._config.memory_high_correct:
                    actions.append(
                        HomeostaticAction(
                            dimension="memory_pressure",
                            level=ActionLevel.CORRECT,
                            value=metrics.memory_percent,
                            threshold=self._config.memory_high_correct,
                            action_taken=f"Memory at {metrics.memory_percent:.0f}%. "
                            "Close heavy applications.",
                        )
                    )
                elif metrics.memory_percent >= self._config.memory_high_advise:
                    actions.append(
                        self._advise(
                            "memory_pressure",
                            metrics.memory_percent,
                            self._config.memory_high_advise,
                            f"Memory at {metrics.memory_percent:.0f}%.",
                        )
                    )

            return actions
        except Exception as e:
            logger.debug("Physical metrics check skipped: %s", e)
            return []

    def _check_workspace_indexes(self) -> list[HomeostaticAction]:
        try:
            from whitemagic.harmony.workspace_index_health import (
                evaluate_workspace_index_health,
            )

            report = evaluate_workspace_index_health()
            if report.health_score < self._config.workspace_index_correct:
                return [
                    HomeostaticAction(
                        dimension="workspace_indexes",
                        level=ActionLevel.CORRECT,
                        value=report.health_score,
                        threshold=self._config.workspace_index_correct,
                        action_taken=(
                            f"Workspace index health degraded: {report.status} "
                            f"({report.indexes_present}/{report.total_workspaces} indexes present, "
                            f"{report.total_errors} errors). Run core/scripts/workspace_index_health.py."
                        ),
                    )
                ]
            if report.health_score < self._config.workspace_index_advise:
                return [
                    self._advise(
                        "workspace_indexes",
                        report.health_score,
                        self._config.workspace_index_advise,
                        f"Workspace index health advisory: {report.status}.",
                    )
                ]
        except Exception as e:
            logger.debug("Workspace index health check skipped: %s", e)
        return []

    def _check_git_hygiene(self) -> list[HomeostaticAction]:
        try:
            from whitemagic.harmony.git_hygiene import evaluate_git_hygiene

            report = evaluate_git_hygiene()
            if report.health_score < self._config.git_hygiene_correct:
                return [
                    HomeostaticAction(
                        dimension="git_hygiene",
                        level=ActionLevel.CORRECT,
                        value=report.health_score,
                        threshold=self._config.git_hygiene_correct,
                        action_taken=report.action_summary(),
                    )
                ]
            if report.health_score < self._config.git_hygiene_advise:
                return [
                    self._advise(
                        "git_hygiene",
                        report.health_score,
                        self._config.git_hygiene_advise,
                        report.action_summary(),
                    )
                ]
        except Exception as e:
            logger.debug("Git hygiene check skipped: %s", e)
        return []

    def _check_consciousness(self) -> list[HomeostaticAction]:
        """Check consciousness subsystem health (Citta Architecture).

        Queries the consciousness module availability and coherence metric.
        If coherence is low or modules are missing, emits advisory or corrective actions.
        """
        try:
            from whitemagic.core.consciousness import (
                CoherenceMetric,
            )

            health_score = 1.0
            module_count = 0
            available_count = 0

            try:
                from whitemagic.tools.handlers.consciousness import (
                    handle_consciousness_status,
                )

                status = handle_consciousness_status()
                health_score = status.get("health", 1.0)
                module_count = status.get("total_modules", 0)
                available_count = status.get("available_count", 0)
            except Exception:
                logger.debug("Swallowed exception", exc_info=True)

            if health_score < self._config.consciousness_correct:
                return [
                    HomeostaticAction(
                        dimension="consciousness",
                        level=ActionLevel.CORRECT,
                        value=health_score,
                        threshold=self._config.consciousness_correct,
                        action_taken=(
                            f"Consciousness health critical: {available_count}/{module_count} modules available. "
                            "Check imports and dependencies for recovered consciousness modules."
                        ),
                    )
                ]
            if health_score < self._config.consciousness_advise:
                return [
                    self._advise(
                        "consciousness",
                        health_score,
                        self._config.consciousness_advise,
                        f"Consciousness health below optimal: {available_count}/{module_count} modules available.",
                    )
                ]

            try:
                metric = CoherenceMetric()
                scores = metric.measure()
                composite = (
                    metric.composite_score(scores)
                    if hasattr(metric, "composite_score")
                    else None
                )
                if (
                    composite is not None
                    and composite < self._config.consciousness_correct
                ):
                    return [
                        HomeostaticAction(
                            dimension="consciousness_coherence",
                            level=ActionLevel.CORRECT,
                            value=composite,
                            threshold=self._config.consciousness_correct,
                            action_taken=(
                                f"Consciousness coherence critical: {composite:.3f}. "
                                "Consider running smarana practice or depth gauge assessment."
                            ),
                        )
                    ]
            except Exception:
                logger.debug("Swallowed exception", exc_info=True)

        except ImportError:
            logger.debug("Consciousness modules not available for homeostatic check")
        except Exception as e:
            logger.debug("Consciousness check skipped: %s", e)
        return []

    def _check_apotheosis(self) -> list[HomeostaticAction]:
        """Check Apotheosis Engine health (autonomous evolution).

        Runs the Apotheosis Engine tick periodically to perform
        self-monitoring, predictive maintenance, and capability discovery.
        Reports health degradation as advisory or corrective actions.
        """
        if self._total_checks % self._config.apotheosis_check_interval != 0:
            return []

        try:
            from whitemagic.core.consciousness.apotheosis_engine import (
                get_apotheosis_engine,
            )

            engine = get_apotheosis_engine()
            if not engine._running:
                engine.start()

            try:
                from whitemagic.tools.registry import get_registry

                registry = get_registry()
                available = (
                    list(registry.callable.keys())
                    if hasattr(registry, "callable")
                    else []
                )
            except Exception:
                available = []

            results = engine.tick(available[:20])  # Limit for performance

            actions: list[HomeostaticAction] = []
            health = results.get("health", {})
            for metric, info in health.items():
                status = info.get("status", "healthy")
                if status in ("degraded", "critical"):
                    actions.append(
                        HomeostaticAction(
                            dimension=f"apotheosis_{metric}",
                            level=ActionLevel.CORRECT
                            if status == "critical"
                            else ActionLevel.ADVISE,
                            value=info.get("value", 0.0),
                            threshold=0.6,
                            action_taken=f"Apotheosis {metric} {status}: {info.get('value', 0):.2f}",
                        )
                    )

            alerts = results.get("predictive_alerts", [])
            for alert in alerts:
                actions.append(
                    self._advise(
                        f"apotheosis_predictive_{alert['component']}",
                        alert["confidence"],
                        0.8,
                        f"Predictive alert: {alert['issue']} (confidence: {alert['confidence']:.2f})",
                    )
                )

            heal_actions = results.get("auto_heal_actions", [])
            for action in heal_actions:
                actions.append(
                    HomeostaticAction(
                        dimension="apotheosis_auto_heal",
                        level=ActionLevel.CORRECT,
                        value=0.0,
                        threshold=1.0,
                        action_taken=f"Auto-heal: {action}",
                    )
                )

            return actions

        except ImportError:
            logger.debug("Apotheosis engine not available for homeostatic check")
        except Exception as e:
            logger.debug("Apotheosis check skipped: %s", e)
        return []

    def _check_codebase_health(self) -> list[HomeostaticAction]:
        """Check codebase health via STRATA static analysis.

        Runs dead_code, structural_stub, and archive_drift checkers
        periodically (every N check cycles) to avoid running on every tick.
        Reports findings as advisory or corrective actions.
        """
        # Only run every N cycles to avoid overhead
        if self._total_checks % self._config.codebase_health_check_interval != 0:
            return []

        try:
            from pathlib import Path

            from whitemagic.tools.strata import FindingSeverity, Strata

            core_path = str(Path(__file__).resolve().parent.parent.parent.parent)
            if not Path(core_path, "AGENTS.md").exists():
                return []

            strata = Strata(core_path)
            findings = strata.analyze(incremental=True)

            # Count findings by severity
            errors = [f for f in findings if f.severity == FindingSeverity.ERROR]
            warnings = [f for f in findings if f.severity == FindingSeverity.WARNING]
            infos = [f for f in findings if f.severity == FindingSeverity.INFO]

            # Health score: weighted by severity
            total = len(findings)
            if total == 0:
                health = 1.0
            else:
                penalty = len(errors) * 0.1 + len(warnings) * 0.05 + len(infos) * 0.01
                health = max(0.0, 1.0 - penalty)

            if health < self._config.codebase_health_correct:
                return [
                    HomeostaticAction(
                        dimension="codebase_health",
                        level=ActionLevel.CORRECT,
                        value=health,
                        threshold=self._config.codebase_health_correct,
                        action_taken=(
                            f"Codebase health critical: {len(errors)} errors, "
                            f"{len(warnings)} warnings, {len(infos)} info. "
                            "Run STRATA analysis for details."
                        ),
                    )
                ]
            if health < self._config.codebase_health_advise:
                return [
                    self._advise(
                        "codebase_health",
                        health,
                        self._config.codebase_health_advise,
                        f"Codebase health below optimal: {len(warnings)} warnings, "
                        f"{len(infos)} info findings from STRATA.",
                    )
                ]
        except Exception as e:
            logger.debug("Codebase health check skipped: %s", e)
        return []

    def get_stats(self) -> dict[str, Any]:
        """
        Get the stats.

        Returns:
            dict[str, Any]
        """
        with self._lock:
            return {
                "running": self._running,
                "total_checks": self._total_checks,
                "total_actions": self._total_actions,
                "recent_actions": [a.to_dict() for a in self._actions[-10:]],
                "config": {
                    "check_interval_s": self._config.check_interval_s,
                    "harmony_intervene": self._config.harmony_intervene,
                },
            }

    @property
    def is_running(self) -> bool:
        """
        Check whether the running condition holds.

        Returns:
            bool
        """
        return self._running


_loop: HomeostaticLoop | None = None
_loop_lock = threading.Lock()


def get_homeostatic_loop(
    config: HomeostaticConfig | None = None,
) -> HomeostaticLoop:
    """Get the global Homeostatic Loop."""
    global _loop
    if _loop is None:
        with _loop_lock:
            if _loop is None:
                _loop = HomeostaticLoop(config=config)
    return _loop
