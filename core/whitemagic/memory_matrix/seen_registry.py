# ruff: noqa: BLE001
"""
Seen Registry — "Have I seen this before?"

Tracks everything viewed to prevent re-introduction amnesia.
Inspired by the Akashic Records — nothing is ever truly forgotten.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any

from whitemagic.config.paths import get_state_root

logger = logging.getLogger(__name__)


class SeenRegistry:
    """Tracks everything the system has seen before."""

    def __init__(self, data_dir: Path | None = None) -> None:
        if data_dir is None:
            data_dir = get_state_root() / "memory_matrix"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.registry_file = self.data_dir / "seen_registry.json"
        self._seen: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if self.registry_file.exists():
            try:
                self._seen = json.loads(self.registry_file.read_text())
            except Exception:
                logger.debug("Using empty seen registry")

    def _save(self) -> None:
        self.registry_file.write_text(json.dumps(self._seen, indent=2))

    @staticmethod
    def _hash(content: str) -> str:
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def mark_seen(self, path: str, context: str = "") -> bool:
        """Mark a path as seen. Returns True if newly seen, False if already seen."""
        key = self._hash(path)
        if key in self._seen:
            self._seen[key]["times_seen"] += 1
            self._seen[key]["last_seen"] = time.time()
            self._save()
            return False
        self._seen[key] = {
            "path": path,
            "context": context,
            "first_seen": time.time(),
            "last_seen": time.time(),
            "times_seen": 1,
        }
        self._save()
        return True

    def has_seen(self, path: str) -> bool:
        """Check if a path has been seen before."""
        return self._hash(path) in self._seen

    def get_record(self, path: str) -> dict[str, Any] | None:
        """Get the seen record for a path."""
        return self._seen.get(self._hash(path))

    def summary(self) -> dict[str, Any]:
        return {
            "total_seen": len(self._seen),
            "unique_paths": len(set(r["path"] for r in self._seen.values())),
        }


_registry: SeenRegistry | None = None


def get_seen_registry() -> SeenRegistry:
    global _registry
    if _registry is None:
        _registry = SeenRegistry()
    return _registry
