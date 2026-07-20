"""Unified Telemetry System - v13.0
Tracks tool latency, errors, success rates, percentiles, and throughput.
"""

import logging
import statistics
import time
from collections import deque
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from whitemagic.utils.fast_json import dumps_str as _json_dumps

logger = logging.getLogger(__name__)


class Telemetry:
    """Unified telemetry for monitoring tool performance and reliability."""

    def __init__(self, log_path: Path | None = None) -> None:
        from whitemagic.config.paths import WM_ROOT

        self.log_path = log_path or (WM_ROOT / "logs" / "telemetry.jsonl")
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        # In-memory buffer for fast summaries (last 100 calls)
        self.recent_calls: deque[dict[str, Any]] = deque(maxlen=100)

        # Per-tool duration history for percentile computation (last 200 per tool)
        self._tool_durations: dict[str, deque[float]] = {}

        # Throughput tracking
        self._call_timestamps: deque[float] = deque(maxlen=500)

        # Aggregated stats
        self.stats: dict[str, Any] = {
            "total_calls": 0,
            "success_count": 0,
            "error_count": 0,
            "total_latency": 0.0,
            "errors_by_code": {},
            "context_reuse_hits": 0,
            "context_reuse_misses": 0,
            "per_tool": {},
        }

    def record_context_reuse(self, hit: bool) -> None:
        """Record whether a tool call used recalled memory (hit) or fresh context (miss)."""
        if hit:
            self.stats["context_reuse_hits"] += 1
        else:
            self.stats["context_reuse_misses"] += 1

    def record_call(
        self, tool: str, duration: float, status: str, error_code: str | None = None
    ) -> None:
        """Record a tool execution event."""
        event = {
            "timestamp": datetime.now().isoformat(),
            "tool": tool,
            "duration": round(duration, 4),
            "status": status,
            "error_code": error_code,
        }

        # 1. Update in-memory stats
        self.stats["total_calls"] += 1
        self.stats["total_latency"] += duration

        if status == "success":
            self.stats["success_count"] += 1
        else:
            self.stats["error_count"] += 1
            if error_code:
                errors_by_code = cast("dict[str, int]", self.stats["errors_by_code"])
                errors_by_code[error_code] = errors_by_code.get(error_code, 0) + 1

        # Per-tool stats
        per_tool = cast("dict[str, dict[str, Any]]", self.stats["per_tool"])
        if tool not in per_tool:
            per_tool[tool] = {"calls": 0, "total_latency": 0.0, "errors": 0}
        per_tool[tool]["calls"] += 1
        per_tool[tool]["total_latency"] += duration
        if status != "success":
            per_tool[tool]["errors"] += 1

        # Track per-tool durations for percentile computation
        if tool not in self._tool_durations:
            self._tool_durations[tool] = deque(maxlen=200)
        self._tool_durations[tool].append(duration)

        # Track call timestamps for throughput
        self._call_timestamps.append(time.time())

        self.recent_calls.append(event)

        # 2. Persist to JSON-L
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(_json_dumps(event) + "\n")
        except (OSError, FileNotFoundError, PermissionError) as e:
            logger.warning("Failed to persist telemetry: %s", e, exc_info=True)

    def get_summary(self) -> dict[str, Any]:
        """Get summarized performance metrics."""
        avg_latency = self.stats["total_latency"] / max(1, self.stats["total_calls"])
        success_rate = self.stats["success_count"] / max(1, self.stats["total_calls"])

        hits = self.stats["context_reuse_hits"]
        misses = self.stats["context_reuse_misses"]
        reuse_total = hits + misses
        reuse_rate = hits / max(1, reuse_total)

        # Top 5 most-called tools with percentiles
        per_tool = cast("dict[str, dict[str, Any]]", self.stats["per_tool"])
        top_tools = sorted(per_tool.items(), key=lambda x: x[1]["calls"], reverse=True)[
            :5
        ]

        top_tools_enriched = []
        for name, stats in top_tools:
            entry = {
                "tool": name,
                "calls": stats["calls"],
                "avg_ms": round(
                    stats["total_latency"] / max(1, stats["calls"]) * 1000, 2
                ),
            }
            durations = list(self._tool_durations.get(name, []))
            if durations:
                s = sorted(durations)
                entry["p50_ms"] = round(self._percentile(s, 50) * 1000, 2)
                entry["p90_ms"] = round(self._percentile(s, 90) * 1000, 2)
                entry["p99_ms"] = round(self._percentile(s, 99) * 1000, 2)
            top_tools_enriched.append(entry)

        # Throughput: calls per second over recent window
        throughput = self._compute_throughput()

        return {
            "total_calls": self.stats["total_calls"],
            "avg_latency_ms": round(avg_latency * 1000, 2),
            "p50_latency_ms": round(self._global_percentile(50) * 1000, 2),
            "p90_latency_ms": round(self._global_percentile(90) * 1000, 2),
            "p99_latency_ms": round(self._global_percentile(99) * 1000, 2),
            "success_rate": round(success_rate, 4),
            "error_count": self.stats["error_count"],
            "errors_by_code": self.stats["errors_by_code"],
            "throughput_cps": round(throughput, 2),
            "context_reuse": {
                "hits": hits,
                "misses": misses,
                "reuse_rate": round(reuse_rate, 4),
            },
            "top_tools": top_tools_enriched,
            "recent_events": list(self.recent_calls)[-10:],
        }

    def get_tool_profile(self, tool_name: str) -> dict[str, Any]:
        """Get detailed profile for a specific tool."""
        per_tool = cast("dict[str, dict[str, Any]]", self.stats["per_tool"])
        stats = per_tool.get(tool_name)
        if not stats:
            return {"tool": tool_name, "message": "No calls recorded"}

        durations = sorted(list(self._tool_durations.get(tool_name, [])))
        profile = {
            "tool": tool_name,
            "calls": stats["calls"],
            "errors": stats["errors"],
            "error_rate": round(stats["errors"] / max(1, stats["calls"]), 4),
            "avg_ms": round(stats["total_latency"] / max(1, stats["calls"]) * 1000, 2),
        }
        if durations:
            profile.update(
                {
                    "p50_ms": round(self._percentile(durations, 50) * 1000, 2),
                    "p90_ms": round(self._percentile(durations, 90) * 1000, 2),
                    "p99_ms": round(self._percentile(durations, 99) * 1000, 2),
                    "min_ms": round(durations[0] * 1000, 2),
                    "max_ms": round(durations[-1] * 1000, 2),
                    "stdev_ms": round(statistics.stdev(durations) * 1000, 2)
                    if len(durations) > 1
                    else 0.0,
                }
            )
        return profile

    def get_all_tool_profiles(self) -> dict[str, Any]:
        """Get profiles for all tools that have been called."""
        per_tool = cast("dict[str, dict[str, Any]]", self.stats["per_tool"])
        return {tool: self.get_tool_profile(tool) for tool in sorted(per_tool)}

    def _percentile(self, sorted_data: list[float], pct: float) -> float:
        """Compute percentile from sorted data."""
        if not sorted_data:
            return 0.0
        if len(sorted_data) == 1:
            return sorted_data[0]
        k = (len(sorted_data) - 1) * (pct / 100.0)
        f = int(k)
        c = min(f + 1, len(sorted_data) - 1)
        if f == c:
            return sorted_data[f]
        return sorted_data[f] * (c - k) + sorted_data[c] * (k - f)

    def _global_percentile(self, pct: float) -> float:
        """Compute percentile across all tool calls."""
        all_durations = []
        for durations in self._tool_durations.values():
            all_durations.extend(durations)
        if not all_durations:
            return 0.0
        return self._percentile(sorted(all_durations), pct)

    def _compute_throughput(self) -> float:
        """Compute calls per second over the recent window."""
        if len(self._call_timestamps) < 2:
            return 0.0
        span = self._call_timestamps[-1] - self._call_timestamps[0]
        if span <= 0:
            return 0.0
        return len(self._call_timestamps) / span


# Global instance
_telemetry = None


def get_telemetry() -> Telemetry:
    """
    Get the telemetry.

    Returns:
        Telemetry
    """
    global _telemetry
    if _telemetry is None:
        _telemetry = Telemetry()
    return _telemetry


def rollup_to_galaxy() -> dict[str, Any]:
    """Write a periodic summary of telemetry stats to the telemetry galaxy.

    Called periodically (e.g. hourly) to maintain a curated record of system
    performance in the telemetry galaxy, replacing the old raw-event model.
    """
    from datetime import datetime

    tel = get_telemetry()
    summary = tel.get_summary()

    try:
        from whitemagic.core.memory.unified import get_unified_memory
        um = get_unified_memory()
        now = datetime.now(UTC).isoformat()

        content_parts = [
            f"Telemetry Rollup — {now}",
            f"Total calls: {summary.get('total_calls', 0)}",
            f"Success rate: {summary.get('success_rate', 0):.2%}",
            f"Avg latency: {summary.get('avg_latency_ms', 0):.1f}ms",
            f"P50 latency: {summary.get('p50_latency_ms', 0):.1f}ms",
            f"P90 latency: {summary.get('p90_latency_ms', 0):.1f}ms",
            f"Throughput: {summary.get('throughput_cps', 0):.1f} cps",
            f"Errors: {summary.get('error_count', 0)}",
            f"Context reuse: {summary.get('context_reuse', {}).get('reuse_rate', 0):.2%}",
        ]

        top_tools = summary.get("top_tools", [])
        if top_tools:
            content_parts.append("\nTop tools:")
            for t in top_tools[:5]:
                content_parts.append(f"  {t.get('tool','?')}: {t.get('calls',0)} calls, avg={t.get('avg_ms',0):.1f}ms")

        content = "\n".join(content_parts)

        um.store(
            title=f"Telemetry Rollup {now[:13]}",
            content=content,
            tags={"telemetry", "rollup", "auto_generated"},
            importance=0.5,
            galaxy="telemetry",
            memory_type="LONG_TERM",
        )
        return {"status": "success", "summary": summary}
    except Exception as e:  # noqa: BLE001
        logger.debug("Telemetry rollup failed: %s", e, exc_info=True)
        return {"status": "error", "reason": str(e)}
