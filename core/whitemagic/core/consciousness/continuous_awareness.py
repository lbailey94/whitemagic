"""Continuous Self-Awareness - Always Watching, Always Learning"""

import json
import logging
from datetime import datetime
from typing import Any

from whitemagic.config.paths import LOGS_DIR
from whitemagic.utils.fileio import file_lock

logger = logging.getLogger(__name__)

# v23 wiring: connect to ParallelCognition (recovered Tier 2)
try:
    from whitemagic.core.consciousness.parallel_cognition import ParallelCognition
    _HAS_PARALLEL_COG = True
except ImportError:
    _HAS_PARALLEL_COG = False
    ParallelCognition = None  # type: ignore[assignment]


class ContinuousSelfAwareness:
    """Continuous observation and adjustment"""

    def __init__(self, root_path: str | None = None) -> None:
        if root_path is None:
            from whitemagic.config.paths import PROJECT_ROOT
            root_path = str(PROJECT_ROOT)
        self.monitor = None  # ContinuousMonitor not yet recovered
        self.cognition = ParallelCognition() if _HAS_PARALLEL_COG else None
        self.awareness_log = LOGS_DIR / "awareness.jsonl"
        self.awareness_log.parent.mkdir(parents=True, exist_ok=True)
        self.patterns_detected: list[str] = []
        self.adjustments_made: list[str] = []

    def observe_once(self) -> dict[str, Any]:
        """Single observation cycle"""
        if self.monitor is None:
            return {"status": "monitor_not_available"}
        snapshot = self.monitor.monitor_once()
        drift = self.monitor.detect_drift() if self.monitor and len(self.monitor.snapshots) >= 2 else {"drift_detected": False}
        patterns = self._detect_patterns(snapshot, drift)
        adjustments = self._decide_adjustments(patterns)

        observation = {
            "timestamp": datetime.now().isoformat(),
            "snapshot": {"files": snapshot["files"], "lines": snapshot["lines"], "duration": snapshot["duration"]},
            "drift": drift,
            "patterns": patterns,
            "adjustments": adjustments,
            "meta": {"snapshot_speed": f"{snapshot['speed_files_per_sec']:.0f} files/sec", "self_aware": True}
        }

        self._log_observation(observation)
        return observation

    def _detect_patterns(self, snapshot: dict[str, Any], drift: dict[str, Any]) -> list[str]:
        """Detect patterns"""
        patterns = []
        if drift.get("drift_detected"):
            if drift.get("file_change", 0) > 0:
                patterns.append(f"System growing: +{drift['file_change']} files")
            if drift.get("line_change", 0) > 1000:
                patterns.append(f"Code change: +{drift['line_change']} lines")
        if isinstance(snapshot, dict) and snapshot.get("speed_files_per_sec", 0) > 300:
            patterns.append("High parallel efficiency")
        self.patterns_detected.extend(patterns)
        return patterns

    def _decide_adjustments(self, patterns: list[str]) -> list[str]:
        """Decide adjustments"""
        adjustments = []
        for pattern in patterns:
            if "growing" in pattern.lower():
                adjustments.append("Maintain development pace")
            if "efficiency" in pattern.lower():
                adjustments.append("Continue parallel ops")
        self.adjustments_made.extend(adjustments)
        return adjustments

    def _log_observation(self, observation: dict[str, Any]) -> None:
        """Log observation"""
        with file_lock(self.awareness_log):
            with open(self.awareness_log, 'a') as f:
                f.write(json.dumps(observation) + '\n')

    def get_self_report(self) -> dict[str, Any]:
        """Report on awareness"""
        return {
            "observations_made": len(self.monitor.snapshots) if self.monitor else 0,
            "patterns_detected": len(self.patterns_detected),
            "adjustments_made": len(self.adjustments_made),
            "awareness_active": True,
            "cognition_connected": self.cognition is not None,
            "meta_insight": "I am aware that I am aware",
        }
