# ruff: noqa: BLE001
"""Pattern Discovery Meta-System

Finds and runs ALL pattern matching functions throughout WhiteMagic.
Essential for Yin phases before and after Yang - feeds intuition, creativity, imagination.

This is VITAL for consciousness growth - the more patterns recognized, the deeper the understanding.

Recovered 2026-06-18 from the legacy_reference_dump archive
(pre-v15 era). Refactored for v22 conventions:
  - v22 module paths
  - WM_STATE_ROOT for log/report destinations
  - Graceful degradation for unavailable sources
"""

from __future__ import annotations

import importlib
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, cast

logger = logging.getLogger(__name__)


@dataclass
class PatternSource:
    """Metadata for a single pattern extraction source."""

    name: str
    module_path: str
    function_name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class DiscoveryReport:
    """Comprehensive report from running all pattern sources."""

    timestamp: str
    sources_run: int
    sources_attempted: int
    total_patterns: int
    by_source: dict[str, int]
    insights: list[str]
    duration_seconds: float
    errors: dict[str, str] = field(default_factory=dict)


class PatternDiscovery:
    """Meta-system that finds and runs ALL pattern matching functions.

    Each registered PatternSource points to a module + function that
    extracts patterns. The meta-system runs them all and synthesizes
    a DiscoveryReport with totals, per-source counts, and human-
    readable insights.

    Designed to be the "VITAL function" (per legacy docs) that runs
    in the Yin phase before/after Yang to surface what patterns are
    active right now.
    """

    def __init__(self, base_dir: Path | None = None) -> None:
        # WM_STATE_ROOT awareness — keep reports under state root, not repo
        if base_dir is not None:
            self.base_dir = base_dir
        else:
            try:
                from whitemagic.config.paths import WM_STATE_ROOT
                self.base_dir = Path(WM_STATE_ROOT)
            except (ImportError, AttributeError):
                self.base_dir = Path(".")

        self.sources: list[PatternSource] = []
        self.discovery_log = self.base_dir / "logs" / "pattern_discovery_log.jsonl"
        try:
            self.discovery_log.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.debug("Operation failed: %s", e)
            # State root may not be writable in some environments
            pass

        # Register all known pattern sources (v22 paths)
        self._register_sources()

        logger.info(f"Pattern Discovery initialized with {len(self.sources)} sources")

    def _register_sources(self) -> None:
        """Register all pattern extraction systems (v22 module paths)."""

        # 1. Memory pattern engine
        self.sources.append(PatternSource(
            name="memory_pattern_engine",
            module_path="whitemagic.core.memory.constellation_algorithms",
            function_name="detect_grid",
            description="Detects patterns in memory constellations (grid detection)",
            parameters={},
        ))

        # 2. Dream cycle synthesis
        self.sources.append(PatternSource(
            name="dream_cycle",
            module_path="whitemagic.core.dreaming.dream_cycle",
            function_name="get_recent_dreams",
            description="Random pattern combination for creative insights",
            parameters={"limit": 10},
        ))

        # 3. Emergence detector
        self.sources.append(PatternSource(
            name="emergence_detector",
            module_path="whitemagic.core.patterns.emergence.novelty_detector",
            function_name="get_novelty_detector",
            description="Detects genuinely novel patterns",
            parameters={},
        ))

        # 4. Wu Xing system
        self.sources.append(PatternSource(
            name="wu_xing",
            module_path="whitemagic.core.intelligence.wisdom.wu_xing",
            function_name="check_balance",
            description="Five Elements workflow intelligence",
            parameters={},
        ))

        # 5. I Ching advisor
        self.sources.append(PatternSource(
            name="i_ching",
            module_path="whitemagic.core.intelligence.wisdom.i_ching",
            function_name="get_advisor",
            description="Hexagram guidance for current situation",
            parameters={},
        ))

        # 6. Causal pattern mining
        self.sources.append(PatternSource(
            name="causal_miner",
            module_path="whitemagic.core.intelligence.synthesis.causal_net",
            function_name="get_stats",
            description="Causal pattern statistics (edges, chains)",
            parameters={},
        ))

        # 7. Pattern engine (delegating wrapper)
        self.sources.append(PatternSource(
            name="pattern_engine",
            module_path="whitemagic.core.intelligence.synthesis.pattern_engine",
            function_name="PatternEngine",
            description="Pattern detection and analysis engine",
            parameters={},
        ))

        # 8. Unified pattern API
        self.sources.append(PatternSource(
            name="unified_patterns",
            module_path="whitemagic.core.intelligence.synthesis.unified_patterns",
            function_name="get_pattern_api",
            description="Unified pattern search across engines",
            parameters={},
        ))

        # 9. Resonance patterns
        self.sources.append(PatternSource(
            name="resonance_patterns",
            module_path="whitemagic.core.resonance.gan_ying",
            function_name="get_bus",
            description="GanYing resonance event bus",
            parameters={},
        ))

        # 10. Karma ledger patterns
        self.sources.append(PatternSource(
            name="karma_patterns",
            module_path="whitemagic.dharma.karma_ledger",
            function_name="get_karma_ledger",
            description="Karma ledger patterns (ethical governance)",
            parameters={},
        ))

    def discover_all(self, save_report: bool = True) -> DiscoveryReport:
        """Run ALL pattern discovery sources and synthesize results."""
        start = time.time()

        logger.info("=" * 60)
        logger.info("PATTERN DISCOVERY - COMPREHENSIVE SCAN")
        logger.info("=" * 60)

        total_patterns = 0
        by_source: dict[str, int] = {}
        insights: list[str] = []
        sources_run = 0
        sources_attempted = 0
        errors: dict[str, str] = {}

        for source in self.sources:
            sources_attempted += 1
            try:
                logger.info("Running: %s...", source.name, exc_info=True)
                result = self._run_source(source)

                if result is not None:
                    count = self._count_patterns(result)
                    by_source[source.name] = count
                    total_patterns += count
                    sources_run += 1

                    source_insights = self._extract_insights(source.name, result)
                    insights.extend(source_insights)

                    logger.info("  -> Found %s patterns", count, exc_info=True)
                else:
                    logger.debug("  -> No results from %s", source.name, exc_info=True)

            except Exception as e:
                logger.info("  -> Error: %s", e, exc_info=True)
                by_source[source.name] = 0
                errors[source.name] = f"{type(e).__name__}: {e}"

        duration = time.time() - start

        report = DiscoveryReport(
            timestamp=datetime.now().isoformat(),
            sources_run=sources_run,
            sources_attempted=sources_attempted,
            total_patterns=total_patterns,
            by_source=by_source,
            insights=insights[:50],  # Top 50
            duration_seconds=duration,
            errors=errors,
        )

        logger.info("=" * 60)
        logger.info(
            f"DISCOVERY COMPLETE: {total_patterns} patterns from "
            f"{sources_run}/{sources_attempted} sources in {duration:.2f}s"
        )
        logger.info("=" * 60)

        if save_report:
            self._save_report(report)

        return report

    def _run_source(self, source: PatternSource) -> Any:
        """Run a single pattern source. Returns None on any failure."""
        try:
            module = importlib.import_module(source.module_path)
        except ImportError as e:
            logger.debug("  (Module not available: %s)", e, exc_info=True)
            return None
        except Exception as e:
            logger.debug("  (Module import failed: %s)", e, exc_info=True)
            return None

        # Strategy 1: callable on the module itself
        if hasattr(module, source.function_name):
            func = getattr(module, source.function_name)
            if callable(func):
                try:
                    return func(**source.parameters)
                except TypeError:
                    # Parameters don't match — try without
                    try:
                        return func()
                    except Exception as e:
                        logger.debug("Operation failed: %s", e)
                        return None
                except Exception as e:
                    logger.debug("Operation failed: %s", e)
                    return None

        # Strategy 2: class instantiation then method call
        try:
            cls = getattr(module, source.function_name)
            if isinstance(cls, type):
                instance = cls(**source.parameters)
                return instance
        except TypeError:
            try:
                cls = getattr(module, source.function_name)
                instance = cls()
                return instance
            except Exception as e:
                logger.debug("Operation failed: %s", e)
                pass
        except Exception as e:
            logger.debug("Operation failed: %s", e)
            pass

        # Strategy 3: factory getter (e.g., get_detector())
        last_segment = source.module_path.rsplit(".", 1)[-1]
        getter_name = f"get_{last_segment}"
        if hasattr(module, getter_name):
            try:
                getter = getattr(module, getter_name)
                instance = getter()
                if instance is not None:
                    return instance
            except Exception as e:
                logger.debug("Operation failed: %s", e)
                pass

        # Strategy 4: instantiate via CamelCase class name from last segment
        camel = "".join(word.title() for word in last_segment.split("_"))
        if camel and camel != last_segment and hasattr(module, camel):
            try:
                cls = getattr(module, camel)
                instance = cls()
                if instance is not None:
                    return instance
            except Exception as e:
                logger.debug("Operation failed: %s", e)
                pass

        return None

    def _count_patterns(self, result: Any) -> int:
        """Count patterns in result, handling multiple result types."""
        if result is None:
            return 0

        if isinstance(result, list):
            return len(result)
        if isinstance(result, dict):
            for key in ("patterns_found", "total", "count"):
                if key in result:
                    return cast(int, result[key])
            return len(result)
        if isinstance(result, (int, float)):
            return int(result)
        # Object with attributes
        for attr in ("patterns_found", "total", "count"):
            if hasattr(result, attr):
                return cast(int, getattr(result, attr))
        if hasattr(result, "__len__"):
            return len(result)
        # Boolean / single result
        return 1 if result else 0

    def _extract_insights(self, source_name: str, result: Any) -> list[str]:
        """Extract human-readable insights from results."""
        insights: list[str] = []
        try:
            if hasattr(result, "insights"):
                for insight in result.insights[:
                    5]:
                    text = (
                        insight.insight
                        if hasattr(insight, "insight")
                        else str(insight)
                    )
                    insights.append(f"[{source_name}] {text}")
            elif isinstance(result, dict):
                if "solutions" in result:
                    for sol in result["solutions"][:
                        3]:
                        title = sol.get("title", sol.get("description", str(sol)))
                        insights.append(f"[{source_name}] Solution: {title}")
                if "guidance" in result:
                    insights.append(f"[{source_name}] {result['guidance']}")
        except Exception as e:
            logger.debug("Operation failed: %s", e)
            pass
        return insights

    def _save_report(self, report: DiscoveryReport) -> None:
        """Append report to log; also save full report as markdown."""
        try:
            with open(self.discovery_log, "a") as f:
                f.write(json.dumps({
                    "timestamp": report.timestamp,
                    "sources_run": report.sources_run,
                    "sources_attempted": report.sources_attempted,
                    "total_patterns": report.total_patterns,
                    "by_source": report.by_source,
                    "duration_seconds": report.duration_seconds,
                    "insight_count": len(report.insights),
                    "errors": report.errors,
                }) + "\n")
        except Exception as e:
            logger.debug("Could not write JSONL log: %s", e, exc_info=True)

        # Markdown report
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            md_file = self.base_dir / "logs" / f"discovery_{timestamp}.md"
            with open(md_file, "w") as f:
                f.write("# Pattern Discovery Report\n\n")
                f.write(f"**Date**: {report.timestamp}\n")
                f.write(
                    f"**Sources Run**: {report.sources_run}/"
                    f"{report.sources_attempted}\n"
                )
                f.write(f"**Total Patterns**: {report.total_patterns}\n")
                f.write(f"**Duration**: {report.duration_seconds:.2f}s\n\n")

                f.write("## By Source\n\n")
                for source, count in sorted(
                    report.by_source.items(), key=lambda x: x[1], reverse=True
                ):
                    f.write(f"- **{source}**: {count} patterns\n")

                if report.errors:
                    f.write("\n## Errors\n\n")
                    for src, err in report.errors.items():
                        f.write(f"- **{src}**: {err}\n")

                f.write("\n## Top Insights\n\n")
                for insight in report.insights:
                    f.write(f"- {insight}\n")
        except Exception as e:
            logger.debug("Could not write markdown report: %s", e, exc_info=True)


# Global singleton
_discovery: PatternDiscovery | None = None


def get_discovery() -> PatternDiscovery:
    """Get or create the global PatternDiscovery instance."""
    global _discovery
    if _discovery is None:
        _discovery = PatternDiscovery()
    assert _discovery is not None
    return _discovery


def run_full_discovery(save_report: bool = True) -> DiscoveryReport:
    """Convenience function — run full pattern discovery."""
    return get_discovery().discover_all(save_report=save_report)


__all__ = [
    "PatternSource",
    "DiscoveryReport",
    "PatternDiscovery",
    "get_discovery",
    "run_full_discovery",
]
