# ruff: noqa: BLE001
"""
Pattern Discovery Meta-System — Discover patterns across all subsystems.

Runs discovery across multiple sources (memory, code, interactions)
and aggregates results into a unified report with insights.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from whitemagic.config.paths import get_state_root

logger = logging.getLogger(__name__)


@dataclass
class DiscoveryReport:
    """Report from a pattern discovery run."""
    timestamp: float = field(default_factory=time.time)
    sources_run: int = 0
    total_patterns: int = 0
    by_source: dict[str, int] = field(default_factory=dict)
    duration_seconds: float = 0.0
    insights: list[str] = field(default_factory=list)


class PatternDiscovery:
    """Meta-system for discovering patterns across all subsystems."""

    def __init__(self, data_dir: Path | None = None) -> None:
        if data_dir is None:
            data_dir = get_state_root() / "emergence"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.discovery_log = self.data_dir / "discovery_log.jsonl"
        self._sources: dict[str, Any] = {}

    def register_source(self, name: str, source: Any) -> None:
        self._sources[name] = source

    def discover_all(self) -> DiscoveryReport:
        """Run discovery across all registered sources."""
        start = time.monotonic()
        report = DiscoveryReport()
        report.sources_run = len(self._sources)

        for name, source in self._sources.items():
            try:
                count = self._run_source(name, source)
                report.by_source[name] = count
                report.total_patterns += count
            except Exception as e:
                logger.debug("Discovery source %s failed: %s", name, e)
                report.by_source[name] = 0

        report.duration_seconds = time.monotonic() - start
        self._save_report(report)
        return report

    def _run_source(self, name: str, source: Any) -> int:
        """Run a single discovery source and return pattern count."""
        if hasattr(source, "discover"):
            result = source.discover()
        elif callable(source):
            result = source()
        else:
            return 0

        if isinstance(result, list):
            return len(result)
        elif isinstance(result, dict):
            return result.get("patterns_found", result.get("total", 0))
        elif hasattr(result, "patterns_found"):
            return result.patterns_found
        elif hasattr(result, "__len__"):
            return len(result)
        return 1

    def _save_report(self, report: DiscoveryReport) -> None:
        with open(self.discovery_log, "a") as f:
            f.write(json.dumps(asdict(report)) + "\n")


_discovery: PatternDiscovery | None = None


def get_discovery() -> PatternDiscovery:
    global _discovery
    if _discovery is None:
        _discovery = PatternDiscovery()
    return _discovery


def run_full_discovery() -> DiscoveryReport:
    return get_discovery().discover_all()
