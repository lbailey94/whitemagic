# ruff: noqa: BLE001
"""Temporal Memory Weaving - Connecting Memories Across Time.

Biological inspiration: Hippocampal replay connects experiences
across time, finding patterns and relationships.

Recovered from v0.1 archive and adapted for v23.3.0.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from whitemagic.config.paths import WM_ROOT
from whitemagic.utils.fileio import atomic_write, file_lock

logger = logging.getLogger(__name__)


class MemoryThread:
    """A thread connecting related memories across time."""

    def __init__(self, name: str, theme: str | None = None) -> None:
        self.name = name
        self.theme = theme
        self.beads: list[dict[str, Any]] = []
        self.created = datetime.now()
        self.last_updated = datetime.now()

    def add_bead(
        self,
        memory_id: str,
        context: str | None = None,
        timestamp: datetime | None = None,
    ) -> None:
        """Add a memory bead to this thread."""
        bead = {
            "memory_id": memory_id,
            "context": context,
            "added_at": datetime.now().isoformat(),
            "original_timestamp": (timestamp or datetime.now()).isoformat(),
        }
        self.beads.append(bead)
        self.last_updated = datetime.now()

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "theme": self.theme,
            "beads": self.beads,
            "created": self.created.isoformat(),
            "last_updated": self.last_updated.isoformat(),
        }


class TemporalWeaver:
    """Weaves memories together across time."""

    def __init__(self, memory_dir: Path | None = None) -> None:
        self.memory_dir = memory_dir or WM_ROOT / "temporal"
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.threads: dict[str, MemoryThread] = {}
        self._load_threads()

    def _load_threads(self) -> None:
        """Load existing threads."""
        threads_file = self.memory_dir / "threads.json"
        if threads_file.exists():
            try:
                with file_lock(threads_file):
                    data: dict[str, Any] = json.loads(threads_file.read_text()) or {}
                for name, thread_data in data.items():
                    thread = MemoryThread(name, thread_data.get("theme"))
                    thread.beads = thread_data.get("beads", [])
                    self.threads[name] = thread
            except Exception as e:
                logger.debug("Could not load temporal threads: %s", e, exc_info=True)

    def _save_threads(self) -> None:
        """Persist threads."""
        threads_file = self.memory_dir / "threads.json"
        data = {name: t.to_dict() for name, t in self.threads.items()}
        with file_lock(threads_file):
            atomic_write(threads_file, json.dumps(data, indent=2))

    def create_thread(self, name: str, theme: str | None = None) -> MemoryThread:
        """Create a new memory thread."""
        thread = MemoryThread(name, theme)
        self.threads[name] = thread
        self._save_threads()
        return thread

    def add_to_thread(
        self,
        thread_name: str,
        memory_id: str,
        context: str | None = None,
    ) -> bool:
        """Add a memory to an existing thread."""
        if thread_name not in self.threads:
            return False
        self.threads[thread_name].add_bead(memory_id, context)
        self._save_threads()
        return True

    def find_similar_moments(self, query: str, days_back: int = 30) -> list[dict[str, Any]]:
        """Find similar moments from the past."""
        results: list[dict[str, Any]] = []

        for thread in self.threads.values():
            for bead in thread.beads:
                if bead.get("context") and query.lower() in bead["context"].lower():
                    results.append({
                        "thread": thread.name,
                        "memory_id": bead["memory_id"],
                        "context": bead["context"],
                        "when": bead["original_timestamp"],
                    })
        return results

    def get_thread_timeline(self, thread_name: str) -> list[dict[str, Any]]:
        """Get chronological timeline of a thread."""
        if thread_name not in self.threads:
            return []
        beads = self.threads[thread_name].beads
        return sorted(beads, key=lambda b: b.get("original_timestamp", ""))

    def weave_connection(self, memory1: str, memory2: str, relationship: str) -> str:
        """Create a connection between two memories."""
        thread_name = f"connection_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        thread = self.create_thread(thread_name, theme=relationship)
        thread.add_bead(memory1, f"Connected via: {relationship}")
        thread.add_bead(memory2, f"Connected via: {relationship}")
        self._save_threads()
        return thread_name

    def list_threads(self) -> list[dict[str, Any]]:
        """List all temporal threads."""
        return [
            {
                "name": t.name,
                "theme": t.theme,
                "bead_count": len(t.beads),
                "created": t.created.isoformat(),
                "last_updated": t.last_updated.isoformat(),
            }
            for t in self.threads.values()
        ]


# Singleton
_weaver: TemporalWeaver | None = None


def get_temporal_weaver() -> TemporalWeaver:
    """Get the temporal weaver singleton."""
    global _weaver
    if _weaver is None:
        _weaver = TemporalWeaver()
    return _weaver
