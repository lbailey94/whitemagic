# ruff: noqa: BLE001
"""Continuous Self-Awareness (Group A — resurfaced from archive).

Original implementation depended on whitemagic.autonomous.parallel_cognition
and whitemagic.fileio, which are not yet implemented in v22.2.3. The module
is ported with defensive try/except so the public API works gracefully
and reports the dependency status honestly.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _get_implementation():
    """Lazy-load the underlying machinery, returning None if unavailable."""
    try:
        from whitemagic.autonomous.parallel_cognition import (
            ContinuousMonitor,
            ParallelCognition,
        )
        from whitemagic.fileio import file_lock

        return {
            "ParallelCognition": ParallelCognition,
            "ContinuousMonitor": ContinuousMonitor,
            "file_lock": file_lock,
        }
    except ImportError:
        return None


class ContinuousSelfAwareness:
    """Continuous observation and adjustment."""

    def __init__(self, root_path: str | None = None) -> None:
        self._impl = _get_implementation()
        if root_path is None:
            from whitemagic.config import PROJECT_ROOT

            root_path = str(PROJECT_ROOT)
        self.root_path = root_path
        if self._impl is not None:
            self.monitor = self._impl["ContinuousMonitor"](
                root_path, interval_seconds=30
            )
            self.cognition = self._impl["ParallelCognition"]()
        state_dir = self._get_state_dir()
        self.awareness_log = state_dir / "awareness.jsonl"
        self.awareness_log.parent.mkdir(parents=True, exist_ok=True)
        self.patterns_detected: list[str] = []
        self.adjustments_made: list[str] = []

    @staticmethod
    def _get_state_dir() -> Path:
        """Get the runtime state directory via canonical paths config."""
        from whitemagic.config.paths import WM_STATE_ROOT

        return Path(WM_STATE_ROOT) / "awareness"

    def observe_once(self) -> dict[str, Any]:
        """Single observation cycle."""
        if self._impl is None:
            return {
                "status": "unavailable",
                "reason": "whitemagic.autonomous.parallel_cognition or whitemagic.fileio not yet implemented",
                "timestamp": datetime.now().isoformat(),
            }
        snapshot = self.monitor.monitor_once()
        drift = (
            self.monitor.detect_drift()
            if len(self.monitor.snapshots) >= 2
            else {"drift_detected": False}
        )
        patterns = self._detect_patterns(snapshot, drift)
        adjustments = self._decide_adjustments(patterns)
        observation = {
            "timestamp": datetime.now().isoformat(),
            "snapshot": {
                "files": snapshot["files"],
                "lines": snapshot["lines"],
                "duration": snapshot["duration"],
            },
            "drift": drift,
            "patterns": patterns,
            "adjustments": adjustments,
            "meta": {
                "snapshot_speed": f"{snapshot['speed_files_per_sec']:.0f} files/sec",
                "self_aware": True,
            },
        }
        self._log_observation(observation)
        return observation

    def _detect_patterns(
        self, snapshot: dict[str, Any], drift: dict[str, Any]
    ) -> list[str]:
        patterns = []
        if drift.get("drift_detected"):
            if drift.get("file_change", 0) > 0:
                patterns.append(f"System growing: +{drift['file_change']} files")
            if drift.get("line_change", 0) > 1000:
                patterns.append(f"Code change: +{drift['line_change']} lines")
        if snapshot["speed_files_per_sec"] > 300:
            patterns.append("High parallel efficiency")
        self.patterns_detected.extend(patterns)
        return patterns

    def _decide_adjustments(self, patterns: list[str]) -> list[str]:
        adjustments = []
        for pattern in patterns:
            if "growing" in pattern.lower():
                adjustments.append("Maintain development pace")
            if "efficiency" in pattern.lower():
                adjustments.append("Continue parallel ops")
        self.adjustments_made.extend(adjustments)
        return adjustments

    def _log_observation(self, observation: dict[str, Any]) -> None:
        file_lock = self._impl["file_lock"]
        with file_lock(self.awareness_log):
            with open(self.awareness_log, "a") as f:
                f.write(json.dumps(observation) + "\n")

    def get_self_report(self) -> dict[str, Any]:
        if self._impl is None:
            return {
                "status": "unavailable",
                "reason": "underlying machinery not implemented",
                "awareness_active": False,
            }
        return {
            "observations_made": len(self.monitor.snapshots),
            "patterns_detected": len(self.patterns_detected),
            "adjustments_made": len(self.adjustments_made),
            "awareness_active": True,
            "meta_insight": "I am aware that I am aware",
        }
