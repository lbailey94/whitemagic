# ruff: noqa: BLE001
"""
Memory Matrix — 2D grid visualization of memory connections.

The unified interface for all memory operations.
Provides the "never forget" infrastructure.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from whitemagic.config.paths import get_state_root

logger = logging.getLogger(__name__)


class MemoryMatrix:
    """2D grid of memory connections for total recall."""

    def __init__(self, data_dir: Path | None = None) -> None:
        if data_dir is None:
            data_dir = get_state_root() / "memory_matrix"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.matrix_file = self.data_dir / "matrix.jsonl"
        self._interactions: list[dict[str, Any]] = []

    def record_interaction(
        self, action: str, target: str, metadata: dict[str, Any] | None = None
    ) -> None:
        """Record an interaction in the memory matrix."""
        entry = {
            "action": action,
            "target": target,
            "metadata": metadata or {},
            "timestamp": time.time(),
        }
        self._interactions.append(entry)
        with open(self.matrix_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def get_interactions(
        self, limit: int = 50, action_filter: str | None = None
    ) -> list[dict[str, Any]]:
        """Retrieve recent interactions."""
        results = (
            self._interactions
            if not action_filter
            else [i for i in self._interactions if i["action"] == action_filter]
        )
        return results[-limit:]

    def find_connections(self, target: str) -> list[dict[str, Any]]:
        """Find all interactions related to a target."""
        return [i for i in self._interactions if target in i["target"]]

    def summary(self) -> dict[str, Any]:
        return {
            "total_interactions": len(self._interactions),
            "unique_targets": len(set(i["target"] for i in self._interactions)),
            "actions": list(set(i["action"] for i in self._interactions)),
        }


_matrix: MemoryMatrix | None = None


def get_matrix() -> MemoryMatrix:
    global _matrix
    if _matrix is None:
        _matrix = MemoryMatrix()
    return _matrix
