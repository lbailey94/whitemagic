"""Machine-Speed Time Estimation and Effort Classification.

Replaces human-time estimates with machine-native duration prediction.
Uses historical telemetry to predict how long a tool call will take,
classifies the effort tier, and provides decision recommendations.

Key insight: AI time and human time are different physical quantities.
This system measures in machine-seconds, not human-minutes.

Effort Tiers (machine-speed):
  TRIVIAL  (<1s)     — execute immediately, zero overhead
  QUICK    (1-10s)   — execute immediately, minimal thought
  MODERATE (10-60s)  — execute, batch with similar tasks
  EXTENDED (1-10min) — quick deliberation worthwhile
  DEEP     (10min+)  — plan and brainstorm before executing

Scoring: Uses CRPS (Continuous Ranked Probability Score) instead of
Brier score, because time estimates are continuous, not binary.
"""

from __future__ import annotations

import json
import logging
import math
import statistics
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from whitemagic.config.paths import get_state_root

logger = logging.getLogger(__name__)


class EffortTier(Enum):
    """Machine-speed effort classification."""

    TRIVIAL = "trivial"  # <1s
    QUICK = "quick"  # 1-10s
    MODERATE = "moderate"  # 10-60s
    EXTENDED = "extended"  # 1-10min
    DEEP = "deep"  # 10min+

    @property
    def decision(self) -> str:
        decisions = {
            "trivial": "Execute immediately. Zero planning overhead.",
            "quick": "Execute immediately. Minimal thought required.",
            "moderate": "Execute, but batch with similar tasks for efficiency.",
            "extended": "Quick deliberation worthwhile. Confirm approach before starting.",
            "deep": "Plan and brainstorm before executing. Consider alternative strategies.",
        }
        return decisions.get(self.value, "Execute.")


@dataclass
class EffortPrediction:
    """Prediction of how much effort a task will require."""

    tool_name: str
    operation_type: str
    predicted_seconds: float
    p50: float  # median
    p90: float  # 90th percentile
    p99: float  # 99th percentile
    confidence: float  # 0-1, based on sample size + variance
    tier: EffortTier
    sample_count: int
    recommendation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "operation_type": self.operation_type,
            "predicted_seconds": round(self.predicted_seconds, 4),
            "p50": round(self.p50, 4),
            "p90": round(self.p90, 4),
            "p99": round(self.p99, 4),
            "confidence": round(self.confidence, 3),
            "tier": self.tier.value,
            "sample_count": self.sample_count,
            "recommendation": self.recommendation,
        }


# Tool name prefix → operation type mapping
_TOOL_TYPE_MAP: dict[str, str] = {
    "memory": "memory_op",
    "galaxy": "memory_op",
    "session": "session",
    "garden": "garden",
    "polyglot": "compute",
    "acceleration": "compute",
    "intelligence": "reasoning",
    "foresight": "reasoning",
    "insight": "reasoning",
    "dream": "reasoning",
    "dharma": "governance",
    "governor": "governance",
    "karma": "governance",
    "security": "security",
    "agent": "agent",
    "swarm": "agent",
    "metrics": "metrics",
    "telemetry": "metrics",
    "token": "metrics",
    "economy": "metrics",
    "resonance": "resonance",
    "gan_ying": "resonance",
    "zodiac": "resonance",
    "search": "search",
    "archaeology": "search",
    "browser": "io",
    "file": "io",
    "scratchpad": "io",
    "context": "io",
    "pipeline": "task",
    "task": "task",
    "vote": "task",
    "broker": "task",
    "gratitude": "task",
    "llama": "inference",
    "inference": "inference",
    "edge": "inference",
    "model": "inference",
}

# Default durations (seconds) per operation type, used when no history
_DEFAULT_DURATIONS: dict[str, float] = {
    "memory_op": 0.005,
    "session": 0.002,
    "garden": 0.010,
    "compute": 0.100,
    "reasoning": 0.050,
    "governance": 0.003,
    "security": 0.003,
    "agent": 0.020,
    "metrics": 0.001,
    "resonance": 0.010,
    "search": 0.050,
    "io": 0.020,
    "task": 0.005,
    "inference": 2.000,
    "unknown": 0.050,
}


def classify_tool(tool_name: str) -> str:
    """Classify a tool name into an operation type."""
    canonical = tool_name.lower().replace("-", "_")
    for prefix, op_type in _TOOL_TYPE_MAP.items():
        if canonical.startswith(prefix) or f".{prefix}" in canonical:
            return op_type
    if "." in canonical:
        first = canonical.split(".")[0]
        if first in _TOOL_TYPE_MAP:
            return _TOOL_TYPE_MAP[first]
    return "unknown"


def classify_effort(seconds: float) -> EffortTier:
    """Classify a predicted duration into an effort tier."""
    if seconds < 1.0:
        return EffortTier.TRIVIAL
    elif seconds < 10.0:
        return EffortTier.QUICK
    elif seconds < 60.0:
        return EffortTier.MODERATE
    elif seconds < 600.0:
        return EffortTier.EXTENDED
    else:
        return EffortTier.DEEP


def _percentile(sorted_data: list[float], pct: float) -> float:
    """Compute percentile from sorted data. pct in [0, 100]."""
    if not sorted_data:
        return 0.0
    if len(sorted_data) == 1:
        return sorted_data[0]
    k = (len(sorted_data) - 1) * (pct / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_data[int(k)]
    d0 = sorted_data[f] * (c - k)
    d1 = sorted_data[c] * (k - f)
    return d0 + d1


def crps_gaussian(prediction: float, actual: float, sigma: float) -> float:
    """CRPS for a Gaussian prediction with mean=prediction, std=sigma.

    CRPS = sigma * [z * (2*Phi(z) - 1) + 2*phi(z) - 1/sqrt(pi)]

    where z = (actual - prediction) / sigma.

    Lower is better. 0 = perfect prediction.
    This is the proper scoring rule for continuous predictions —
    the generalization of Brier score to real-valued outcomes.

    Args:
        prediction: Predicted mean (seconds).
        actual: Observed value (seconds).
        sigma: Predicted standard deviation (uncertainty).

    Returns:
        CRPS score (seconds, lower is better).
    """
    if sigma <= 0:
        sigma = 0.001
    z = (actual - prediction) / sigma
    # Phi(z) = 0.5 * (1 + erf(z/sqrt(2)))
    # phi(z) = exp(-z^2/2) / sqrt(2*pi)
    phi_z = math.exp(-0.5 * z * z) / math.sqrt(2 * math.pi)
    phi_of_z = 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
    return sigma * (z * (2 * phi_of_z - 1) + 2 * phi_z - 1.0 / math.sqrt(math.pi))


class MachineTimeEstimator:
    """Predicts tool call duration from historical telemetry data.

    Uses per-tool and per-operation-type duration profiles.
    Builds predictions from median + IQR, not mean (robust to outliers).
    Confidence scales with sample size and inverse variance.
    """

    def __init__(self, log_path: Path | None = None) -> None:
        self.log_path = log_path or get_state_root() / "citta" / "machine_time.jsonl"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        # Per-tool duration history (in-memory, loaded from log)
        self._tool_history: dict[str, list[float]] = {}
        # Per-operation-type duration history
        self._type_history: dict[str, list[float]] = {}
        # Pending predictions (tool_name → prediction) for auto-recording
        self._pending: dict[str, EffortPrediction] = {}
        # Calibration correction factors (tool_name → multiplier)
        # When predictions are systematically biased, this corrects future predictions.
        # E.g., if we always predict 2x too much, correction = 0.5.
        self._correction_factors: dict[str, float] = {}
        # Per-tool log-ratio errors for bias detection
        self._tool_log_ratios: dict[str, list[float]] = {}
        self._load_history()
        self._load_correction_factors()

    def _load_history(self) -> None:
        """Load duration history from log."""
        if not self.log_path.exists():
            return
        try:
            with open(self.log_path) as f:
                for line in f:
                    if not line.strip():
                        continue
                    entry = json.loads(line)
                    tool = entry.get("tool", "") or entry.get("tool_name", "")
                    duration = entry.get("actual_seconds", 0.0)
                    op_type = entry.get("operation_type", "unknown")
                    if tool and duration > 0:
                        self._tool_history.setdefault(tool, []).append(duration)
                        self._type_history.setdefault(op_type, []).append(duration)
        except Exception as e:  # noqa: BLE001
            logger.debug("Failed to load machine_time history: %s", e)

    def predict(self, tool_name: str, complexity_hint: float = 1.0) -> EffortPrediction:
        """Predict effort for a tool call.

        Args:
            tool_name: Canonical tool name.
            complexity_hint: Multiplier for atypical complexity (1.0 = normal).

        Returns:
            EffortPrediction with predicted duration, confidence, and tier.
        """
        op_type = classify_tool(tool_name)
        tool_durations = self._tool_history.get(tool_name, [])
        type_durations = self._type_history.get(op_type, [])

        # Prefer tool-specific data, fall back to operation-type data
        if len(tool_durations) >= 3:
            samples = sorted(tool_durations)
        elif len(type_durations) >= 3:
            samples = sorted(type_durations)
        else:
            # Not enough data — use default with low confidence
            default = _DEFAULT_DURATIONS.get(op_type, 0.05) * complexity_hint
            tier = classify_effort(default)
            return EffortPrediction(
                tool_name=tool_name,
                operation_type=op_type,
                predicted_seconds=default,
                p50=default,
                p90=default * 2,
                p99=default * 3,
                confidence=0.1,
                tier=tier,
                sample_count=0,
                recommendation=tier.decision,
            )

        p50 = _percentile(samples, 50)
        p90 = _percentile(samples, 90)
        p99 = _percentile(samples, 99)

        # Predicted duration = median * complexity_hint * correction_factor
        correction = self._correction_factors.get(tool_name, 1.0)
        predicted = p50 * complexity_hint * correction

        # Confidence: based on sample size and variance
        n = len(samples)
        if n >= 30:
            confidence = 0.95
        elif n >= 10:
            confidence = 0.80
        elif n >= 5:
            confidence = 0.60
        else:
            confidence = 0.40

        # Reduce confidence if high variance (IQR / median > 0.5)
        q1 = _percentile(samples, 25)
        q3 = _percentile(samples, 75)
        if p50 > 0:
            iqr_ratio = (q3 - q1) / p50
            if iqr_ratio > 1.0:
                confidence *= 0.7
            elif iqr_ratio > 0.5:
                confidence *= 0.85

        tier = classify_effort(predicted)

        return EffortPrediction(
            tool_name=tool_name,
            operation_type=op_type,
            predicted_seconds=predicted,
            p50=p50,
            p90=p90,
            p99=p99,
            confidence=confidence,
            tier=tier,
            sample_count=n,
            recommendation=tier.decision,
        )

    def record_actual(
        self,
        tool_name: str,
        actual_seconds: float,
        prediction: EffortPrediction | None = None,
    ) -> dict[str, Any]:
        """Record actual duration and update history.

        Args:
            tool_name: Canonical tool name.
            actual_seconds: Observed duration.
            prediction: The prediction made before the call (if any).

        Returns:
            Summary dict with prediction error and CRPS.
        """
        op_type = classify_tool(tool_name)

        # Update in-memory history
        self._tool_history.setdefault(tool_name, []).append(actual_seconds)
        self._type_history.setdefault(op_type, []).append(actual_seconds)

        # Compute prediction error if we had a prediction
        result: dict[str, Any] = {
            "tool_name": tool_name,
            "operation_type": op_type,
            "actual_seconds": round(actual_seconds, 6),
        }

        if prediction is not None:
            error = actual_seconds - prediction.predicted_seconds
            abs_error_pct = abs(error) / max(actual_seconds, 0.001) * 100
            log_ratio = (
                math.log(prediction.predicted_seconds / actual_seconds)
                if prediction.predicted_seconds > 0 and actual_seconds > 0
                else 0.0
            )
            # CRPS: use p90-p50 as sigma estimate (uncertainty)
            sigma = max(prediction.p90 - prediction.p50, 0.001)
            crps = crps_gaussian(prediction.predicted_seconds, actual_seconds, sigma)

            result.update(
                {
                    "predicted_seconds": round(prediction.predicted_seconds, 6),
                    "error_seconds": round(error, 6),
                    "abs_error_pct": round(abs_error_pct, 2),
                    "log_ratio_error": round(log_ratio, 4),
                    "crps": round(crps, 6),
                    "tier": prediction.tier.value,
                    "confidence": prediction.confidence,
                }
            )

        # Persist
        entry = {
            "timestamp": datetime.now().isoformat(),
            "tool_name": tool_name,
            "operation_type": op_type,
            "actual_seconds": actual_seconds,
            **{
                k: v
                for k, v in result.items()
                if k not in ("tool_name", "operation_type")
            },
        }
        try:
            with open(self.log_path, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:  # noqa: BLE001
            logger.warning("Failed to persist machine_time record: %s", e)

        return result

    def _load_correction_factors(self) -> None:
        """Load correction factors from log by computing mean log-ratio bias per tool."""
        if not self.log_path.exists():
            return
        try:
            tool_ratios: dict[str, list[float]] = {}
            with open(self.log_path) as f:
                for line in f:
                    if not line.strip():
                        continue
                    entry = json.loads(line)
                    tool = entry.get("tool_name", "") or entry.get("tool", "")
                    log_ratio = entry.get("log_ratio_error")
                    if tool and log_ratio is not None and log_ratio != 0:
                        tool_ratios.setdefault(tool, []).append(log_ratio)

            # Compute correction factor per tool
            # correction = exp(-mean_log_ratio) moves predictions toward actual
            for tool, ratios in tool_ratios.items():
                if len(ratios) >= 5:  # Need at least 5 samples for reliable correction
                    mean_ratio = statistics.mean(ratios)
                    # Damp the correction to avoid overreacting (max 50% adjustment)
                    raw_correction = math.exp(-mean_ratio)
                    correction = max(0.5, min(2.0, raw_correction))
                    self._correction_factors[tool] = correction
                    self._tool_log_ratios[tool] = ratios
        except Exception as e:  # noqa: BLE001
            logger.debug("Failed to load correction factors: %s", e)

    def get_calibration_feedback(self) -> dict[str, Any]:
        """Get calibration feedback report — shows which tools have systematic bias.

        This is the feedback loop: CRPS data → correction factors → adjusted predictions.
        """
        feedback = {}
        for tool, correction in sorted(self._correction_factors.items()):
            ratios = self._tool_log_ratios.get(tool, [])
            mean_ratio = statistics.mean(ratios) if ratios else 0.0
            bias = (
                "overestimate"
                if mean_ratio > 0.1
                else "underestimate"
                if mean_ratio < -0.1
                else "calibrated"
            )
            feedback[tool] = {
                "correction_factor": round(correction, 4),
                "mean_log_ratio_error": round(mean_ratio, 4),
                "bias_direction": bias,
                "sample_count": len(ratios),
            }
        return {
            "tools_with_correction": len(feedback),
            "feedback": feedback,
            "summary": (
                f"{len(feedback)} tools have calibration corrections applied. "
                f"Tools with most bias: "
                + ", ".join(
                    f"{t} ({d['bias_direction']}, correction={d['correction_factor']})"
                    for t, d in sorted(
                        feedback.items(),
                        key=lambda x: abs(x[1]["mean_log_ratio_error"]),
                        reverse=True,
                    )[:3]
                )
                if feedback
                else "No corrections yet — need at least 5 samples per tool."
            ),
        }

    def get_profile(self) -> dict[str, Any]:
        """Get duration profiles for all known tools and operation types."""
        tool_profiles: dict[str, dict[str, float]] = {}
        for tool, durations in sorted(self._tool_history.items()):
            if not durations:
                continue
            s = sorted(durations)
            tool_profiles[tool] = {
                "count": len(s),
                "median": round(_percentile(s, 50), 6),
                "p90": round(_percentile(s, 90), 6),
                "mean": round(statistics.mean(s), 6),
                "stdev": round(statistics.stdev(s), 6) if len(s) > 1 else 0.0,
            }

        type_profiles: dict[str, dict[str, float]] = {}
        for op_type, durations in sorted(self._type_history.items()):
            if not durations:
                continue
            s = sorted(durations)
            type_profiles[op_type] = {
                "count": len(s),
                "median": round(_percentile(s, 50), 6),
                "p90": round(_percentile(s, 90), 6),
                "mean": round(statistics.mean(s), 6),
            }

        return {
            "tool_profiles": tool_profiles,
            "type_profiles": type_profiles,
            "total_tools_tracked": len(tool_profiles),
            "total_observations": sum(len(v) for v in self._tool_history.values()),
        }

    def get_crps_summary(self) -> dict[str, Any]:
        """Compute aggregate CRPS from persisted prediction records."""
        if not self.log_path.exists():
            return {"count": 0, "mean_crps": None, "message": "No predictions recorded"}

        crps_values: list[float] = []
        log_ratios: list[float] = []
        per_type: dict[str, list[float]] = {}

        try:
            with open(self.log_path) as f:
                for line in f:
                    if not line.strip():
                        continue
                    entry = json.loads(line)
                    if "crps" in entry:
                        crps_values.append(entry["crps"])
                        log_ratios.append(entry.get("log_ratio_error", 0.0))
                        op_type = entry.get("operation_type", "unknown")
                        per_type.setdefault(op_type, []).append(entry["crps"])
        except Exception as e:  # noqa: BLE001
            logger.debug("Failed to read CRPS history: %s", e)
            return {"count": 0, "mean_crps": None, "message": f"Error: {e}"}

        if not crps_values:
            return {
                "count": 0,
                "mean_crps": None,
                "message": "No predictions with CRPS",
            }

        mean_crps = statistics.mean(crps_values)
        median_crps = statistics.median(crps_values)
        mean_log_ratio = statistics.mean(log_ratios) if log_ratios else 0.0
        mae_log_ratio = (
            statistics.mean([abs(x) for x in log_ratios]) if log_ratios else 0.0
        )

        per_type_summary = {}
        for op_type, values in sorted(per_type.items()):
            per_type_summary[op_type] = {
                "count": len(values),
                "mean_crps": round(statistics.mean(values), 6),
            }

        return {
            "count": len(crps_values),
            "mean_crps": round(mean_crps, 6),
            "median_crps": round(median_crps, 6),
            "mean_log_ratio_error": round(mean_log_ratio, 4),
            "mae_log_ratio_error": round(mae_log_ratio, 4),
            "per_type": per_type_summary,
        }


# Singleton
_estimator: MachineTimeEstimator | None = None


def get_machine_time_estimator() -> MachineTimeEstimator:
    """Get the global MachineTimeEstimator instance."""
    global _estimator
    if _estimator is None:
        _estimator = MachineTimeEstimator()
    return _estimator
