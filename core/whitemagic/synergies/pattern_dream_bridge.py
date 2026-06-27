# ruff: noqa: BLE001
"""
Pattern-Dream Bridge — Connect pattern discovery to dream cycle.

When patterns are discovered during active operation, they're queued
for processing during the next dream cycle, enabling subconscious
synthesis of patterns into higher-order insights.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from whitemagic.config.paths import get_state_root

logger = logging.getLogger(__name__)


class PatternDreamBridge:
    """Bridges pattern discovery to dream cycle processing."""

    def __init__(self, data_dir: Path | None = None) -> None:
        if data_dir is None:
            data_dir = get_state_root() / "synergies"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.queue_file = self.data_dir / "pattern_queue.jsonl"
        self.synthesis_file = self.data_dir / "dream_syntheses.jsonl"
        self._pending: list[dict[str, Any]] = []

    def queue_pattern(self, pattern: dict[str, Any]) -> None:
        """Queue a pattern for dream cycle processing."""
        entry = {"pattern": pattern, "queued_at": time.time()}
        self._pending.append(entry)
        with open(self.queue_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
        logger.debug("Queued pattern for dream synthesis")

    def process_queue(self) -> list[dict[str, Any]]:
        """Process queued patterns (called during dream cycle)."""
        if not self._pending:
            self._load_queue()

        syntheses: list[dict[str, Any]] = []
        if len(self._pending) < 2:
            return syntheses

        # Group patterns by type
        by_type: dict[str, list[dict[str, Any]]] = {}
        for entry in self._pending:
            ptype = entry["pattern"].get("type", "unknown")
            by_type.setdefault(ptype, []).append(entry["pattern"])

        # Synthesize within each type
        for ptype, patterns in by_type.items():
            if len(patterns) >= 2:
                synthesis = {
                    "type": ptype,
                    "source_patterns": len(patterns),
                    "synthesis": f"Combined {len(patterns)} {ptype} patterns",
                    "timestamp": time.time(),
                }
                syntheses.append(synthesis)
                self._save_synthesis(synthesis)

        # Clear processed queue
        self._pending = []
        self.queue_file.unlink(missing_ok=True)

        return syntheses

    def _load_queue(self) -> None:
        if self.queue_file.exists():
            for line in self.queue_file.read_text().splitlines():
                if line.strip():
                    try:
                        self._pending.append(json.loads(line))
                    except Exception:
                        pass

    def _save_synthesis(self, synthesis: dict[str, Any]) -> None:
        with open(self.synthesis_file, "a") as f:
            f.write(json.dumps(synthesis) + "\n")

    def summary(self) -> dict[str, Any]:
        return {
            "pending_patterns": len(self._pending),
            "total_syntheses": self._count_syntheses(),
        }

    def _count_syntheses(self) -> int:
        if not self.synthesis_file.exists():
            return 0
        return len(self.synthesis_file.read_text().splitlines())


_bridge: PatternDreamBridge | None = None


def get_pattern_dream_bridge() -> PatternDreamBridge:
    global _bridge
    if _bridge is None:
        _bridge = PatternDreamBridge()
    return _bridge
