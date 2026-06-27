# ruff: noqa: BLE001
"""
Dream State — Subconscious processing and memory consolidation.

Manages the system's 'sleep' phase where memories are consolidated,
patterns are synthesized, and creative connections are made without
active user interaction.
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
class DreamSequence:
    """A single dream sequence for memory consolidation."""
    timestamp: float = field(default_factory=time.time)
    memories_processed: int = 0
    connections_found: int = 0
    patterns_synthesized: int = 0
    insights: list[str] = field(default_factory=list)
    duration_s: float = 0.0


class DreamState:
    """Manages dream cycles for subconscious processing."""

    def __init__(self, data_dir: Path | None = None) -> None:
        if data_dir is None:
            data_dir = get_state_root() / "emergence"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.data_dir / "dreams.jsonl"
        self.sequences: list[DreamSequence] = []
        self._dreaming = False
        self._load()

    def _load(self) -> None:
        if self.log_file.exists():
            for line in self.log_file.read_text().splitlines():
                if line.strip():
                    try:
                        d = json.loads(line)
                        self.sequences.append(DreamSequence(**d))
                    except Exception:
                        logger.debug("Skipping malformed dream sequence")

    def is_dreaming(self) -> bool:
        return self._dreaming

    def dream(self, duration_s: float = 30.0) -> DreamSequence:
        """Run a dream cycle for memory consolidation."""
        self._dreaming = True
        start = time.monotonic()
        seq = DreamSequence()

        try:
            memories_processed = self._consolidate_memories()
            connections_found = self._find_connections()
            patterns_synthesized = self._synthesize_patterns()

            seq.memories_processed = memories_processed
            seq.connections_found = connections_found
            seq.patterns_synthesized = patterns_synthesized
            seq.duration_s = time.monotonic() - start

            self.sequences.append(seq)
            self._save(seq)
        finally:
            self._dreaming = False

        logger.info(
            "Dream cycle complete: %d memories, %d connections, %d patterns",
            seq.memories_processed, seq.connections_found, seq.patterns_synthesized,
        )
        return seq

    def _consolidate_memories(self) -> int:
        try:
            from whitemagic.core.memory.unified import get_unified_memory
            mem = get_unified_memory()
            recent = mem.recent(limit=50) if hasattr(mem, "recent") else []
            return len(recent)
        except Exception:
            return 0

    def _find_connections(self) -> int:
        try:
            from whitemagic.core.memory.temporal_weaving import TemporalWeaver
            weaver = TemporalWeaver()
            threads = weaver.list_threads() if hasattr(weaver, "list_threads") else []
            return len(threads)
        except Exception:
            return 0

    def _synthesize_patterns(self) -> int:
        try:
            from whitemagic.emergence.detector import get_detector
            detector = get_detector()
            recent = detector.recent_behaviors(limit=5)
            return len(recent)
        except Exception:
            return 0

    def _save(self, seq: DreamSequence) -> None:
        with open(self.log_file, "a") as f:
            f.write(json.dumps(asdict(seq)) + "\n")

    def last_dream(self) -> DreamSequence | None:
        return self.sequences[-1] if self.sequences else None

    def summary(self) -> dict[str, Any]:
        last = self.last_dream()
        return {
            "total_dreams": len(self.sequences),
            "currently_dreaming": self._dreaming,
            "last_dream_time": last.timestamp if last else 0,
            "total_memories_processed": sum(s.memories_processed for s in self.sequences),
            "total_connections": sum(s.connections_found for s in self.sequences),
        }


_dream: DreamState | None = None


def get_dream_state() -> DreamState:
    global _dream
    if _dream is None:
        _dream = DreamState()
    return _dream
