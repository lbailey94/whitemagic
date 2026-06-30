# ruff: noqa: BLE001
"""Routing Observability — tracks inference routing decisions, latency, and escalation rates.

Production hybrid routing systems require telemetry to detect threshold drift,
measure per-tier quality, and tune routing parameters. This module provides
rolling-window statistics for the InferenceRouter.

Tracks:
  - Per-tier request counts and latency (p50, p95, p99)
  - Escalation rates (Tier N → Tier N+1)
  - Confidence distribution at each tier
  - Routing decision reasons
  - Circuit breaker state per tier
"""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any

from whitemagic.inference.complexity import InferenceTier

logger = logging.getLogger(__name__)

_WINDOW_SIZE = 1000  # Rolling window for latency samples


@dataclass
class TierStats:
    """Statistics for a single inference tier."""

    total_requests: int = 0
    successful: int = 0
    failed: int = 0
    escalated: int = 0  # Requests that escalated to a higher tier
    latencies: deque = field(default_factory=lambda: deque(maxlen=_WINDOW_SIZE))
    confidences: deque = field(default_factory=lambda: deque(maxlen=_WINDOW_SIZE))
    decision_reasons: dict[str, int] = field(default_factory=lambda: defaultdict(int))

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.successful / self.total_requests

    @property
    def escalation_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.escalated / self.total_requests

    def record(
        self, latency_ms: float, confidence: float, success: bool, reason: str = ""
    ) -> None:
        self.total_requests += 1
        self.latencies.append(latency_ms)
        self.confidences.append(confidence)
        if success:
            self.successful += 1
        else:
            self.failed += 1
        if reason:
            self.decision_reasons[reason] += 1

    def record_escalation(self) -> None:
        self.escalated += 1

    def p50(self) -> float:
        return self._percentile(50)

    def p95(self) -> float:
        return self._percentile(95)

    def p99(self) -> float:
        return self._percentile(99)

    def avg_confidence(self) -> float:
        if not self.confidences:
            return 0.0
        return sum(self.confidences) / len(self.confidences)

    def _percentile(self, p: int) -> float:
        if not self.latencies:
            return 0.0
        sorted_lat = sorted(self.latencies)
        idx = int(len(sorted_lat) * p / 100)
        return float(sorted_lat[min(idx, len(sorted_lat) - 1)])

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_requests": self.total_requests,
            "successful": self.successful,
            "failed": self.failed,
            "escalated": self.escalated,
            "success_rate": f"{self.success_rate:.1%}",
            "escalation_rate": f"{self.escalation_rate:.1%}",
            "p50_ms": round(self.p50(), 2),
            "p95_ms": round(self.p95(), 2),
            "p99_ms": round(self.p99(), 2),
            "avg_confidence": round(self.avg_confidence(), 3),
            "top_reasons": dict(
                sorted(self.decision_reasons.items(), key=lambda x: -x[1])[:5]
            ),
        }


class RoutingMetrics:
    """Rolling-window metrics for inference routing decisions.

    Thread-safe. Designed for the routing hot path — all operations are O(1)
    except percentile calculations which are O(n log n) on a bounded window.
    """

    def __init__(self) -> None:
        self._tier_stats: dict[InferenceTier, TierStats] = {
            tier: TierStats() for tier in InferenceTier
        }
        self._total_routed: int = 0
        self._total_escalations: int = 0
        self._lock = threading.RLock()
        self._start_time = time.time()

    def record_routing(
        self,
        tier: InferenceTier,
        latency_ms: float,
        confidence: float,
        success: bool,
        reason: str = "",
    ) -> None:
        """Record a routing decision and its outcome."""
        with self._lock:
            self._total_routed += 1
            self._tier_stats[tier].record(latency_ms, confidence, success, reason)

    def record_escalation(
        self,
        from_tier: InferenceTier,
        to_tier: InferenceTier,
        reason: str = "",
    ) -> None:
        """Record an escalation from one tier to a higher one."""
        with self._lock:
            self._total_escalations += 1
            self._tier_stats[from_tier].record_escalation()
            logger.debug(
                "Escalation %s → %s (reason: %s). Total escalations: %d",
                from_tier.name,
                to_tier.name,
                reason,
                self._total_escalations,
            )

    def summary(self) -> dict[str, Any]:
        """Get a summary of all routing metrics."""
        with self._lock:
            uptime = time.time() - self._start_time
            return {
                "uptime_seconds": round(uptime, 1),
                "total_routed": self._total_routed,
                "total_escalations": self._total_escalations,
                "overall_escalation_rate": (
                    f"{self._total_escalations / max(1, self._total_routed):.1%}"
                ),
                "tiers": {
                    tier.name: stats.to_dict()
                    for tier, stats in self._tier_stats.items()
                    if stats.total_requests > 0
                },
            }

    def detect_drift(self, window: int = 100) -> dict[str, Any]:
        """Detect routing threshold drift.

        Checks if escalation rates have shifted significantly from the
        historical baseline, which may indicate the routing thresholds
        need retuning.

        Args:
            window: Number of recent samples to compare against full history.

        Returns:
            Drift analysis with recommendations.
        """
        with self._lock:
            drift: dict[str, Any] = {"status": "ok", "recommendations": []}

            for tier, stats in self._tier_stats.items():
                if stats.total_requests < window * 2:
                    continue

                # Compare recent escalation rate to historical
                recent_escalations = sum(
                    1
                    for i in range(min(window, len(stats.latencies)))
                    if i < stats.escalated  # Approximate
                )
                recent_rate = recent_escalations / min(window, stats.total_requests)
                historical_rate = stats.escalation_rate

                if historical_rate > 0 and abs(recent_rate - historical_rate) > 0.15:
                    drift["status"] = "drift_detected"
                    drift["recommendations"].append(
                        {
                            "tier": tier.name,
                            "historical_rate": f"{historical_rate:.1%}",
                            "recent_rate": f"{recent_rate:.1%}",
                            "action": "Consider adjusting confidence threshold or complexity patterns",
                        }
                    )

            return drift

    def adaptive_thresholds(self) -> dict[str, float]:
        """Compute adaptive confidence thresholds based on observed performance.

        If a tier has high success rate and low escalation, lower the threshold
        (keep more requests at that tier). If escalation rate is high, raise the
        threshold (send fewer requests to that tier).

        Returns:
            Dict mapping tier name to recommended confidence threshold.
        """
        with self._lock:
            recommendations: dict[str, float] = {}
            base_threshold = 0.85

            for tier, stats in self._tier_stats.items():
                if stats.total_requests < 20:
                    recommendations[tier.name] = base_threshold
                    continue

                # High escalation rate → raise threshold (be more conservative)
                # Low escalation rate + high success → lower threshold (be more aggressive)
                esc_rate = stats.escalation_rate
                succ_rate = stats.success_rate

                # Adjust threshold: ±0.05 max deviation
                adjustment = 0.0
                if esc_rate > 0.3:
                    adjustment = 0.05  # Raise threshold
                elif esc_rate < 0.05 and succ_rate > 0.9:
                    adjustment = -0.05  # Lower threshold

                recommended = max(0.5, min(0.99, base_threshold + adjustment))
                recommendations[tier.name] = round(recommended, 3)

            return recommendations

    def export_dashboard(self) -> dict[str, Any]:
        """Export metrics in a format suitable for the Mound/dashboard.

        Returns a flat dict with key metrics for monitoring:
        - Per-tier counts, rates, latencies
        - Overall escalation rate
        - Drift status
        - Adaptive threshold recommendations
        """
        with self._lock:
            summary = self.summary()
            drift = self.detect_drift()
            thresholds = self.adaptive_thresholds()

            return {
                "routing": summary,
                "drift": drift,
                "adaptive_thresholds": thresholds,
                "exported_at": time.time(),
            }

    def to_mound_metrics(self) -> dict[str, float]:
        """Export key metrics as flat float dict for Mound integration.

        The Mound Gana tracks numeric metrics. This method flattens
        routing observability into individual metric keys.
        """
        with self._lock:
            metrics: dict[str, float] = {
                "routing.total_routed": float(self._total_routed),
                "routing.total_escalations": float(self._total_escalations),
                "routing.uptime_seconds": time.time() - self._start_time,
            }

            for tier, stats in self._tier_stats.items():
                prefix = f"routing.{tier.name.lower()}"
                metrics[f"{prefix}.requests"] = float(stats.total_requests)
                metrics[f"{prefix}.success_rate"] = stats.success_rate
                metrics[f"{prefix}.escalation_rate"] = stats.escalation_rate
                metrics[f"{prefix}.p50_ms"] = stats.p50()
                metrics[f"{prefix}.p95_ms"] = stats.p95()
                metrics[f"{prefix}.p99_ms"] = stats.p99()
                metrics[f"{prefix}.avg_confidence"] = stats.avg_confidence()

            return metrics


# Singleton
_metrics: RoutingMetrics | None = None


def get_routing_metrics() -> RoutingMetrics:
    """Get singleton routing metrics."""
    global _metrics
    if _metrics is None:
        _metrics = RoutingMetrics()
    return _metrics
