# ruff: noqa: BLE001
"""Metaplasticity — plasticity of plasticity for memory strength updates.

The threshold for changing a memory's strength varies based on recent
activity history. Frequently accessed memories become harder to modify
(homeostatic metaplasticity), while rarely accessed memories are more
plastic. Based on neuromimetic metaplasticity research (Frontiers, 2025).

Architecture:
- Python orchestrator manages per-memory modification thresholds
- Rust compute kernel (optional) for batch threshold updates
- SQLite persistence for cross-session threshold state
"""

from __future__ import annotations

import json
import logging
import math
import os
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_STATE_ROOT = Path(os.environ.get("WM_STATE_ROOT", "/tmp/whitemagic"))
_META_DIR = _STATE_ROOT / "metaplasticity"
_META_FILE = _META_DIR / "thresholds.json"

# Bienenstock-Cooper-Munro (BCM) inspired parameters
_THETA_BASE = 0.5       # base modification threshold
_THETA_MIN = 0.1        # minimum threshold (very plastic)
_THETA_MAX = 2.0        # maximum threshold (very stable)
_THETA_LEARNING_RATE = 0.05
_ACTIVITY_DECAY = 0.95   # per-update activity decay
_HOMEOSTATIC_TARGET = 0.5  # target average activity


class MetaplasticityEngine:
    """Manages per-memory modification thresholds based on activity history.

    Uses a BCM-inspired rule: threshold increases when activity is high
    (making the memory harder to modify) and decreases when activity is low
    (making it more plastic). This prevents over-strengthening of frequently
    accessed memories and allows forgotten memories to be more easily updated.
    """

    def __init__(self):
        self._thresholds: dict[str, dict[str, Any]] = {}
        self._total_updates = 0
        self._total_applied = 0
        self._load()

    def _load(self) -> None:
        """Load thresholds from disk."""
        try:
            if _META_FILE.exists():
                data = json.loads(_META_FILE.read_text())
                self._thresholds = data.get("thresholds", {})
                self._total_updates = data.get("total_updates", 0)
                self._total_applied = data.get("total_applied", 0)
        except Exception as e:
            logger.debug("Failed to load metaplasticity state: %s", e, exc_info=True)

    def _save(self) -> None:
        """Save thresholds to disk."""
        try:
            _META_DIR.mkdir(parents=True, exist_ok=True)
            data = {
                "thresholds": self._thresholds,
                "total_updates": self._total_updates,
                "total_applied": self._total_applied,
            }
            _META_FILE.write_text(json.dumps(data))
        except Exception as e:
            logger.debug("Failed to save metaplasticity state: %s", e, exc_info=True)

    def get_threshold(self, memory_id: str) -> float:
        """Get the current modification threshold for a memory."""
        entry = self._thresholds.get(memory_id)
        if entry is None:
            return _THETA_BASE
        return entry.get("theta", _THETA_BASE)

    def record_access(self, memory_id: str, strength_delta: float = 0.0) -> float:
        """Record an access event and update the modification threshold.

        Returns the new threshold value.
        """
        self._total_updates += 1
        entry = self._thresholds.setdefault(memory_id, {
            "theta": _THETA_BASE,
            "activity": 0.0,
            "access_count": 0,
            "last_access": 0.0,
        })

        # Decay previous activity
        entry["activity"] = entry.get("activity", 0.0) * _ACTIVITY_DECAY
        # Add new activity (1.0 per access + delta)
        entry["activity"] += 1.0 + abs(strength_delta)
        entry["access_count"] = entry.get("access_count", 0) + 1
        entry["last_access"] = time.time()

        # BCM-inspired threshold update:
        # theta = theta_base + learning_rate * (activity - homeostatic_target)
        activity_excess = entry["activity"] - _HOMEOSTATIC_TARGET
        new_theta = entry["theta"] + _THETA_LEARNING_RATE * activity_excess
        entry["theta"] = max(_THETA_MIN, min(_THETA_MAX, new_theta))

        return entry["theta"]

    def can_modify(self, memory_id: str, proposed_delta: float) -> bool:
        """Check if a proposed modification exceeds the threshold.

        A modification is allowed if |proposed_delta| > threshold * base_sensitivity.
        """
        threshold = self.get_threshold(memory_id)
        return abs(proposed_delta) > threshold * 0.1

    def apply_modification(self, memory_id: str, delta: float) -> dict[str, Any]:
        """Apply a strength modification, gated by metaplasticity.

        Returns the actual applied delta (may be reduced if threshold is high).
        """
        self._total_applied += 1
        threshold = self.get_threshold(memory_id)

        # The higher the threshold, the more the delta is attenuated
        attenuation = 1.0 / (1.0 + threshold * 0.5)
        actual_delta = delta * attenuation

        # Record the access
        new_threshold = self.record_access(memory_id, actual_delta)

        return {
            "memory_id": memory_id,
            "requested_delta": delta,
            "applied_delta": actual_delta,
            "attenuation": attenuation,
            "threshold_before": threshold,
            "threshold_after": new_threshold,
        }

    def batch_update(self, updates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Batch process multiple memory modifications."""
        return [self.apply_modification(u["memory_id"], u.get("delta", 0.0)) for u in updates]

    def get_plasticity_score(self, memory_id: str) -> float:
        """Get how plastic a memory is (0 = very stable, 1 = very plastic)."""
        theta = self.get_threshold(memory_id)
        return 1.0 - (theta - _THETA_MIN) / (_THETA_MAX - _THETA_MIN)

    def decay_all(self) -> int:
        """Decay all activity counters (e.g., during sleep cycle)."""
        count = 0
        for entry in self._thresholds.values():
            entry["activity"] = entry.get("activity", 0.0) * _ACTIVITY_DECAY
            # Also relax thresholds toward base
            entry["theta"] = entry.get("theta", _THETA_BASE) * 0.98 + _THETA_BASE * 0.02
            if entry["activity"] > 0.01:
                count += 1
        return count

    def stats(self) -> dict[str, Any]:
        return {
            "total_updates": self._total_updates,
            "total_applied": self._total_applied,
            "tracked_memories": len(self._thresholds),
            "avg_threshold": (
                sum(e.get("theta", _THETA_BASE) for e in self._thresholds.values()) /
                max(len(self._thresholds), 1)
            ),
        }

    def save(self) -> None:
        """Persist state to disk."""
        self._save()


# Singleton

_engine: MetaplasticityEngine | None = None


def get_metaplasticity() -> MetaplasticityEngine:
    global _engine
    if _engine is None:
        _engine = MetaplasticityEngine()
    return _engine
