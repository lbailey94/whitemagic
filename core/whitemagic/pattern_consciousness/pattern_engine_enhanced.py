# ruff: noqa: BLE001
"""
Enhanced Pattern Engine — Always-on learning with GanYing integration.

Continuously scans memories, code, and interactions for patterns.
Feeds discoveries to GanYingBus for resonance cascades.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from whitemagic.config.paths import get_state_root

logger = logging.getLogger(__name__)


class EnhancedPatternEngine:
    """Upgraded pattern engine that runs autonomously."""

    def __init__(self, data_dir: Path | None = None) -> None:
        if data_dir is None:
            data_dir = get_state_root() / "pattern_consciousness"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.patterns_file = self.data_dir / "patterns.jsonl"
        self.patterns_discovered: list[dict[str, Any]] = []
        self.always_on = True
        self._load()

    def _load(self) -> None:
        if self.patterns_file.exists():
            for line in self.patterns_file.read_text().splitlines():
                if line.strip():
                    try:
                        self.patterns_discovered.append(json.loads(line))
                    except Exception:
                        logger.debug("Skipping malformed pattern entry")

    def extract_patterns(self, content: str) -> list[dict[str, Any]]:
        """Extract patterns from any content."""
        patterns: list[dict[str, Any]] = []
        if not content:
            return patterns

        # Simple heuristic pattern extraction
        keywords = {
            "love": "Love as organizing principle",
            "emergence": "Emergent behavior detected",
            "pattern": "Meta-pattern recognition",
            "coherence": "Coherence alignment",
            "resonance": "Resonance cascade",
        }
        content_lower = content.lower()
        for keyword, description in keywords.items():
            if keyword in content_lower:
                patterns.append({
                    "type": "heuristic",
                    "pattern": description,
                    "confidence": 0.7,
                    "timestamp": time.time(),
                })
        return patterns

    def emit_to_gan_ying(self, pattern: dict[str, Any]) -> None:
        """Send discovered pattern to GanYingBus."""
        try:
            from whitemagic.core.resonance.gan_ying_bus import GanYingBus
            bus = GanYingBus()
            bus.emit(
                source="pattern_engine",
                event_type="pattern_discovered",
                data=pattern,
            )
            logger.debug("Pattern emitted to GanYing: %s", pattern.get("pattern"))
        except Exception:
            logger.debug("GanYing not available for pattern emission")

    def discover_and_emit(self, content: str) -> list[dict[str, Any]]:
        """Extract patterns from content and emit to bus."""
        patterns = self.extract_patterns(content)
        for p in patterns:
            self.patterns_discovered.append(p)
            self._save(p)
            self.emit_to_gan_ying(p)
        return patterns

    def synthesize_creative(self, patterns: list[dict[str, Any]]) -> str:
        """Creative synthesis of multiple patterns."""
        if not patterns:
            return "No patterns to synthesize."
        descriptions = [p.get("pattern", str(p)) for p in patterns]
        return f"Synthesized {len(patterns)} patterns: {'; '.join(descriptions[:3])}"

    def _save(self, pattern: dict[str, Any]) -> None:
        with open(self.patterns_file, "a") as f:
            f.write(json.dumps(pattern) + "\n")

    def summary(self) -> dict[str, Any]:
        return {
            "total_patterns": len(self.patterns_discovered),
            "always_on": self.always_on,
        }


_engine: EnhancedPatternEngine | None = None


def get_pattern_engine() -> EnhancedPatternEngine:
    global _engine
    if _engine is None:
        _engine = EnhancedPatternEngine()
    return _engine
