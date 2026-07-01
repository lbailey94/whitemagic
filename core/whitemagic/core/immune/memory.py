# ruff: noqa: BLE001
"""
Immune Memory System — Store and recall past immune responses.

Remembers which antibodies worked for which antigens, enabling
faster and more effective responses to previously encountered threats.
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
class ImmuneMemoryEntry:
    """A record of a past immune response."""

    antigen: str
    antibody_used: str
    successful: bool
    timestamp: float = field(default_factory=time.time)
    context: str = ""


class ImmuneMemory:
    """Stores and recalls past immune responses."""

    def __init__(self, data_dir: Path | None = None) -> None:
        if data_dir is None:
            data_dir = get_state_root() / "immune"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.memory_file = self.data_dir / "immune_memory.jsonl"
        self.entries: list[ImmuneMemoryEntry] = []
        self._load()

    def _load(self) -> None:
        if self.memory_file.exists():
            for line in self.memory_file.read_text().splitlines():
                if line.strip():
                    try:
                        d = json.loads(line)
                        self.entries.append(ImmuneMemoryEntry(**d))
                    except Exception:
                        logger.debug("Skipping malformed immune memory entry")

    def record(
        self, antigen: str, antibody: str, successful: bool, context: str = ""
    ) -> None:
        entry = ImmuneMemoryEntry(
            antigen=antigen,
            antibody_used=antibody,
            successful=successful,
            context=context,
        )
        self.entries.append(entry)
        with open(self.memory_file, "a") as f:
            f.write(json.dumps(asdict(entry)) + "\n")

    def recall(self, antigen: str) -> list[ImmuneMemoryEntry]:
        """Recall past responses for a specific antigen."""
        return [e for e in self.entries if e.antigen == antigen]

    def best_antibody(self, antigen: str) -> str | None:
        """Find the most successful antibody for an antigen."""
        entries = self.recall(antigen)
        if not entries:
            return None
        successful = [e for e in entries if e.successful]
        if not successful:
            return None
        counts: dict[str, int] = {}
        for e in successful:
            counts[e.antibody_used] = counts.get(e.antibody_used, 0) + 1
        return max(counts, key=counts.get)

    def summary(self) -> dict[str, Any]:
        return {
            "total_entries": len(self.entries),
            "successful": sum(1 for e in self.entries if e.successful),
            "unique_antigens": len(set(e.antigen for e in self.entries)),
        }


_memory: ImmuneMemory | None = None


def get_immune_memory() -> ImmuneMemory:
    global _memory
    if _memory is None:
        _memory = ImmuneMemory()
    return _memory
