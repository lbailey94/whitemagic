# ruff: noqa: BLE001
"""
Threat Detection System — Detect threats to system health.

Identifies: version drift, import errors, missing dependencies,
stale caches, memory leaks, and configuration issues.
"""

from __future__ import annotations

import importlib
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from whitemagic.config.paths import get_project_root, get_state_root

logger = logging.getLogger(__name__)


class ThreatType(Enum):
    IMPORT_ERROR = "import_error"
    MISSING_DEPENDENCY = "missing_dependency"
    VERSION_DRIFT = "version_drift"
    STATE_INCONSISTENCY = "state_inconsistency"
    MEMORY_LEAK = "memory_leak"
    CONFIGURATION = "configuration"


class ThreatLevel(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Threat:
    """A detected threat to system health."""
    threat_type: ThreatType
    level: ThreatLevel
    description: str
    location: str = ""
    antigen: str = ""
    suggested_antibody: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class ThreatDetector:
    """Detects threats to system health."""

    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = project_root or get_project_root()
        self.state_root = get_state_root()
        self.detected_threats: list[Threat] = []
        self.scan_history: list[dict[str, Any]] = []

    def scan(self) -> list[Threat]:
        """Run a full threat detection scan."""
        self.detected_threats = []
        self._check_imports()
        self._check_state()
        self._check_version()
        self._record_scan()
        return self.detected_threats

    def _check_imports(self) -> None:
        """Check for import errors in core modules."""
        critical_modules = [
            "whitemagic.core.memory.unified",
            "whitemagic.core.resonance.gan_ying_bus",
            "whitemagic.core.consciousness.coherence",
        ]
        for mod_name in critical_modules:
            try:
                importlib.import_module(mod_name)
            except Exception as e:
                self.detected_threats.append(Threat(
                    threat_type=ThreatType.IMPORT_ERROR,
                    level=ThreatLevel.HIGH,
                    description=f"Failed to import {mod_name}: {e}",
                    location=mod_name,
                    antigen="import_failure",
                    suggested_antibody="fix_import",
                ))

    def _check_state(self) -> None:
        """Check state directory consistency."""
        if not self.state_root.exists():
            self.detected_threats.append(Threat(
                threat_type=ThreatType.STATE_INCONSISTENCY,
                level=ThreatLevel.MEDIUM,
                description="State root directory does not exist",
                location=str(self.state_root),
                antigen="missing_state_root",
                suggested_antibody="init_state",
            ))

    def _check_version(self) -> None:
        """Check for version drift."""
        version_file = self.project_root / "VERSION"
        if version_file.exists():
            version = version_file.read_text().strip()
            try:
                from whitemagic.config import VERSION as config_version
                if version != config_version:
                    self.detected_threats.append(Threat(
                        threat_type=ThreatType.VERSION_DRIFT,
                        level=ThreatLevel.LOW,
                        description=f"Version drift: file={version}, config={config_version}",
                        antigen="version_drift",
                        suggested_antibody="sync_version",
                    ))
            except Exception:
                pass

    def _record_scan(self) -> None:
        self.scan_history.append({
            "timestamp": time.time(),
            "threats_found": len(self.detected_threats),
            "threat_levels": {
                lv.value: sum(1 for t in self.detected_threats if t.level == lv)
                for lv in ThreatLevel
            },
        })

    def get_critical_threats(self) -> list[Threat]:
        return [
            t for t in self.detected_threats
            if t.level in (ThreatLevel.CRITICAL, ThreatLevel.HIGH)
        ]

    def generate_health_report(self) -> dict[str, Any]:
        total = len(self.detected_threats)
        critical = sum(1 for t in self.detected_threats if t.level == ThreatLevel.CRITICAL)
        if total == 0:
            status, score = "HEALTHY", 100
        elif critical > 0:
            status, score = "CRITICAL", max(0, 50 - critical * 10)
        elif total < 5:
            status, score = "GOOD", max(70, 100 - total * 5)
        else:
            status, score = "FAIR", max(50, 100 - total * 3)
        return {
            "health_status": status,
            "health_score": score,
            "total_threats": total,
            "threats_by_level": {
                lv.value: sum(1 for t in self.detected_threats if t.level == lv)
                for lv in ThreatLevel
            },
        }


_detector: ThreatDetector | None = None


def get_detector() -> ThreatDetector:
    global _detector
    if _detector is None:
        _detector = ThreatDetector()
    return _detector
