"""Neurotransmitter Vectors — Biochemical Analogues for System Health.
===================================================================

Expands the Harmony Vector with 7 neurotransmitter analogues that make
system health intuitive and grounded in computational signals.

| Neurotransmitter | Computational Analogue        | Source Signal                        |
|------------------|------------------------------|--------------------------------------|
| Dopamine         | Reward prediction error      | Expected vs actual tool outcome      |
| Oxytocin         | Trust / social bonding       | Agent cooperation, mesh sync         |
| Serotonin        | Mood stability               | Rolling variance of Harmony Vector   |
| Cortisol         | Stress / alarm               | Error rate, circuit breaker trips    |
| Acetylcholine    | Attention / focus            | Salience Arbiter spotlight density   |
| GABA             | Inhibition / calm            | PROCEED_WITH_CAUTION rate            |
| Glutamate        | Excitation / drive           | Creative bridge rate (bicameral)     |

Each neurotransmitter is normalized to [0.0, 1.0] where 0.5 = baseline.
Values >0.7 indicate high activity; <0.3 indicate low activity.

Usage:
    from whitemagic.core.monitoring.neurotransmitter_vector import get_neurotransmitter_vector
    nt = get_neurotransmitter_vector()
    snapshot = nt.snapshot()

The vector is auto-fed by ``call_tool()`` on every invocation.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class NeurotransmitterSnapshot:
    """Immutable snapshot safe for JSON serialization."""

    dopamine: float = 0.5      # reward prediction error
    oxytocin: float = 0.5      # trust / social bonding
    serotonin: float = 0.5     # mood stability
    cortisol: float = 0.5      # stress / alarm
    acetylcholine: float = 0.5 # attention / focus
    gaba: float = 0.5          # inhibition / calm
    glutamate: float = 0.5     # excitation / drive

    # Interpretation
    dominant: str = "baseline"
    interpretation: str = "System is in baseline state."
    timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to/from dict.

        Returns:
            dict[str, Any]
        """
        return asdict(self)


class _SignalWindow:
    """Thread-safe rolling window for signal history."""

    def __init__(self, window_seconds: float = 300.0, max_events: int = 2000):
        self._lock = threading.Lock()
        self._events: deque[tuple[float, float]] = deque(maxlen=max_events)  # (timestamp, value)
        self._window = window_seconds

    def push(self, value: float) -> None:
        """
        Perform the push operation.

        Args:
            value: Parameter description.

        Returns:
            None
        """
        with self._lock:
            self._events.append((time.time(), value))

    def recent(self) -> list[float]:
        """
        Perform the recent operation.

        Returns:
            list[float]
        """
        cutoff = time.time() - self._window
        with self._lock:
            return [v for t, v in self._events if t >= cutoff]

    def mean(self) -> float:
        """
        Perform the mean operation.

        Returns:
            float
        """
        vals = self.recent()
        return sum(vals) / len(vals) if vals else 0.5

    def variance(self) -> float:
        """
        Perform the variance operation.

        Returns:
            float
        """
        vals = self.recent()
        if len(vals) < 2:
            return 0.0
        m = sum(vals) / len(vals)
        return sum((v - m) ** 2 for v in vals) / len(vals)


class NeurotransmitterVector:
    """Living biochemical profile of the system.

    Auto-fed by call_tool() on every invocation. Query via snapshot().
    """

    def __init__(self, window_seconds: float = 300.0) -> None:
        self._window = window_seconds

        # Per-neurotransmitter signal windows
        self._dopamine = _SignalWindow(window_seconds)
        self._oxytocin = _SignalWindow(window_seconds)
        self._serotonin = _SignalWindow(window_seconds)
        self._cortisol = _SignalWindow(window_seconds)
        self._acetylcholine = _SignalWindow(window_seconds)
        self._gaba = _SignalWindow(window_seconds)
        self._glutamate = _SignalWindow(window_seconds)

        # Counters for rate-based signals
        self._tool_calls_total = 0
        self._tool_calls_success = 0
        self._caution_count = 0
        self._creative_bridge_count = 0
        self._error_count = 0
        self._lock = threading.Lock()

        self._latest = NeurotransmitterSnapshot(
            timestamp=datetime.now().isoformat(),
        )

    # ------------------------------------------------------------------
    # Signal collectors
    # ------------------------------------------------------------------

    def record_tool_call(self, success: bool, result: dict[str, Any] | None = None) -> None:
        """Called on every tool invocation."""
        with self._lock:
            self._tool_calls_total += 1
            if success:
                self._tool_calls_success += 1
            else:
                self._error_count += 1

        # Dopamine: reward prediction error
        # High when success rate is above expectation (0.95 baseline)
        expected_success_rate = 0.95
        if self._tool_calls_total > 10:
            actual_rate = self._tool_calls_success / self._tool_calls_total
            reward_error = actual_rate - expected_success_rate
            dopamine_val = 0.5 + (reward_error * 5.0)  # scale: ±0.1 rate → ±0.5 dopamine
            self._dopamine.push(max(0.0, min(1.0, dopamine_val)))
        else:
            self._dopamine.push(0.5)

        # Cortisol: stress from errors
        if not success:
            self._cortisol.push(0.8)
        else:
            self._cortisol.push(0.3)

        # GABA: caution signals
        if result and isinstance(result, dict):
            verdict = result.get("verdict", "")
            if "CAUTION" in str(verdict):
                with self._lock:
                    self._caution_count += 1
                self._gaba.push(0.7)
            else:
                self._gaba.push(0.4)

            # Oxytocin: cooperation signals (multi-agent, mesh, voting)
            tool_name = result.get("tool", "")
            if any(t in tool_name for t in ("agent.", "mesh.", "vote.", "swarm.", "broker.")):
                self._oxytocin.push(0.8)
            else:
                self._oxytocin.push(0.4)

            # Acetylcholine: focus from salience
            salience = result.get("details", {}).get("salience", {})
            if salience:
                composite = salience.get("composite", 0.5)
                self._acetylcholine.push(0.3 + composite * 0.7)
            else:
                self._acetylcholine.push(0.5)
        else:
            self._gaba.push(0.5)
            self._oxytocin.push(0.5)
            self._acetylcholine.push(0.5)

        # Serotonin: stability (inverse of variance)
        recent_errors = self._cortisol.recent()
        if len(recent_errors) > 5:
            var = self._cortisol.variance()
            stability = max(0.0, 1.0 - var * 4.0)
            self._serotonin.push(stability)
        else:
            self._serotonin.push(0.5)

        # Glutamate: drive / creative energy
        # Default to moderate; boosted by creative bridge events
        self._glutamate.push(0.5)

    def record_creative_bridge(self, confidence: float) -> None:
        """Called by bicameral reasoner when a creative bridge is detected."""
        with self._lock:
            self._creative_bridge_count += 1
        # Low confidence bridges boost glutamate more (drive to explore)
        boost = 0.5 + (1.0 - confidence) * 0.5
        self._glutamate.push(min(1.0, boost))

    def record_circuit_breaker_trip(self) -> None:
        """Called when a circuit breaker trips."""
        self._cortisol.push(0.95)

    def record_rate_limit_hit(self) -> None:
        """Called when rate limiter throttles a call."""
        self._cortisol.push(0.85)

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> NeurotransmitterSnapshot:
        """Return current neurotransmitter profile."""
        snap = NeurotransmitterSnapshot(
            dopamine=round(self._dopamine.mean(), 3),
            oxytocin=round(self._oxytocin.mean(), 3),
            serotonin=round(self._serotonin.mean(), 3),
            cortisol=round(self._cortisol.mean(), 3),
            acetylcholine=round(self._acetylcholine.mean(), 3),
            gaba=round(self._gaba.mean(), 3),
            glutamate=round(self._glutamate.mean(), 3),
            timestamp=datetime.now().isoformat(),
        )

        # Determine dominant neurotransmitter
        values = {
            "dopamine": snap.dopamine,
            "oxytocin": snap.oxytocin,
            "serotonin": snap.serotonin,
            "cortisol": snap.cortisol,
            "acetylcholine": snap.acetylcholine,
            "gaba": snap.gaba,
            "glutamate": snap.glutamate,
        }
        max_nt = max(values, key=values.get)  # type: ignore[arg-type]
        min(values, key=values.get)  # type: ignore[arg-type]
        snap.dominant = max_nt

        # Generate interpretation
        interpretations = []
        if snap.cortisol > 0.7:
            interpretations.append("System is stressed — errors or throttling detected.")
        if snap.dopamine > 0.7:
            interpretations.append("Reward signals are strong — tools are succeeding above expectation.")
        if snap.glutamate > 0.7:
            interpretations.append("Creative drive is high — many novel connections being explored.")
        if snap.serotonin < 0.3:
            interpretations.append("Mood instability — error variance is high.")
        if snap.oxytocin > 0.7:
            interpretations.append("Social bonding is active — multi-agent coordination thriving.")
        if snap.acetylcholine > 0.7:
            interpretations.append("Attention is highly focused — salient events dominating.")
        if snap.gaba > 0.7:
            interpretations.append("Inhibition is high — many caution signals being raised.")
        if not interpretations:
            interpretations.append("System is in baseline biochemical state.")

        snap.interpretation = " ".join(interpretations)
        self._latest = snap
        return snap


# Singleton
_nt_vector: NeurotransmitterVector | None = None
_nt_lock = threading.Lock()


def get_neurotransmitter_vector() -> NeurotransmitterVector:
    """Return the global NeurotransmitterVector singleton."""
    global _nt_vector
    if _nt_vector is None:
        with _nt_lock:
            if _nt_vector is None:
                _nt_vector = NeurotransmitterVector()
    return _nt_vector
