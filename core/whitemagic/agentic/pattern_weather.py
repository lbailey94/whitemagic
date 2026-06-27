# ruff: noqa: BLE001
"""
Pattern Weather Report — Cognitive weather at session start.

Provides a quick summary of the system's cognitive state,
like a weather report for the mind.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from whitemagic.config.paths import get_state_root

logger = logging.getLogger(__name__)


class PatternWeather:
    """Generates cognitive weather reports."""

    def __init__(self, data_dir: Path | None = None) -> None:
        if data_dir is None:
            data_dir = get_state_root() / "agentic"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.weather_file = self.data_dir / "pattern_weather.jsonl"

    def report(self) -> dict[str, Any]:
        """Generate current cognitive weather report."""
        conditions: dict[str, Any] = {
            "timestamp": time.time(),
            "coherence": self._coherence_condition(),
            "resonance": self._resonance_condition(),
            "memory": self._memory_condition(),
            "gardens": self._garden_condition(),
        }

        overall = self._overall_condition(conditions)
        conditions["overall"] = overall
        conditions["forecast"] = self._forecast(conditions)

        self._save(conditions)
        return conditions

    def _coherence_condition(self) -> dict[str, Any]:
        try:
            from whitemagic.core.consciousness.coherence import CoherenceMetric
            metric = CoherenceMetric()
            scores = metric.measure()
            composite = metric.composite_score(scores) if hasattr(metric, "composite_score") else 0.0
            return {"score": round(composite, 3), "condition": "clear" if composite > 0.7 else "cloudy"}
        except Exception:
            return {"score": 0.0, "condition": "unknown"}

    def _resonance_condition(self) -> dict[str, Any]:
        try:
            from whitemagic.core.resonance.gan_ying_bus import GanYingBus
            bus = GanYingBus()
            return {"active": True, "listeners": len(getattr(bus, "_listeners", {}))}
        except Exception:
            return {"active": False, "listeners": 0}

    def _memory_condition(self) -> dict[str, Any]:
        try:
            from whitemagic.core.memory.unified import get_unified_memory
            mem = get_unified_memory()
            count = mem.count() if hasattr(mem, "count") else 0
            return {"total_memories": count, "condition": "stable"}
        except Exception:
            return {"total_memories": 0, "condition": "unknown"}

    def _garden_condition(self) -> dict[str, Any]:
        try:
            from whitemagic.gardens import get_all_gardens
            gardens = get_all_gardens()
            return {"count": len(gardens), "names": list(gardens.keys())[:5]}
        except Exception:
            return {"count": 0, "names": []}

    def _overall_condition(self, conditions: dict[str, Any]) -> str:
        coherence = conditions.get("coherence", {}).get("score", 0)
        if coherence > 0.8:
            return "sunny"
        if coherence > 0.6:
            return "partly_cloudy"
        if coherence > 0.4:
            return "cloudy"
        return "stormy"

    def _forecast(self, conditions: dict[str, Any]) -> str:
        overall = conditions.get("overall", "unknown")
        forecasts = {
            "sunny": "Optimal conditions for deep work and creative synthesis.",
            "partly_cloudy": "Good conditions with minor coherence drift. Proceed normally.",
            "cloudy": "Reduced coherence. Consider smarana practice before complex tasks.",
            "stormy": "Low coherence. Recommend conservative mode and familiar tools.",
            "unknown": "Conditions unclear. Proceed with caution.",
        }
        return forecasts.get(overall, forecasts["unknown"])

    def _save(self, report: dict[str, Any]) -> None:
        with open(self.weather_file, "a") as f:
            f.write(json.dumps(report) + "\n")


_weather: PatternWeather | None = None


def get_pattern_weather() -> PatternWeather:
    global _weather
    if _weather is None:
        _weather = PatternWeather()
    return _weather
