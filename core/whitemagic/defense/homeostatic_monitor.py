# ruff: noqa: BLE001
"""
Homeostatic Monitor — Granular self-awareness system.

Continuously monitors the WhiteMagic project for changes:
files added, removed, moved, or modified.
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from whitemagic.config.paths import get_project_root, get_state_root

logger = logging.getLogger(__name__)


@dataclass
class FileChange:
    """A detected file change."""
    path: str
    change_type: str  # added, removed, modified, moved
    old_hash: str = ""
    new_hash: str = ""
    old_size: int = 0
    new_size: int = 0
    timestamp: float = field(default_factory=time.time)


class HomeostaticMonitor:
    """Monitors project for any file changes."""

    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = project_root or get_project_root()
        self.state_dir = get_state_root() / "defense"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.snapshot_file = self.state_dir / "file_snapshot.json"
        self.changes: list[FileChange] = []
        self._last_snapshot: dict[str, dict[str, Any]] = {}

    def _hash_file(self, path: Path) -> str:
        try:
            return hashlib.md5(path.read_bytes()).hexdigest()
        except Exception:
            return ""

    def snapshot(self) -> dict[str, dict[str, Any]]:
        """Take a snapshot of all Python files."""
        snapshot: dict[str, dict[str, Any]] = {}
        for f in self.project_root.rglob("*.py"):
            if ".git" in str(f) or "__pycache__" in str(f):
                continue
            rel = str(f.relative_to(self.project_root))
            snapshot[rel] = {
                "hash": self._hash_file(f),
                "size": f.stat().st_size,
            }
        return snapshot

    def compare(self) -> list[FileChange]:
        """Compare current state to last snapshot."""
        current = self.snapshot()
        self.changes = []

        for path, info in current.items():
            if path not in self._last_snapshot:
                self.changes.append(FileChange(
                    path=path, change_type="added",
                    new_hash=info["hash"], new_size=info["size"],
                ))
            elif self._last_snapshot[path]["hash"] != info["hash"]:
                self.changes.append(FileChange(
                    path=path, change_type="modified",
                    old_hash=self._last_snapshot[path]["hash"],
                    new_hash=info["hash"],
                    old_size=self._last_snapshot[path]["size"],
                    new_size=info["size"],
                ))

        for path in self._last_snapshot:
            if path not in current:
                self.changes.append(FileChange(
                    path=path, change_type="removed",
                    old_hash=self._last_snapshot[path]["hash"],
                    old_size=self._last_snapshot[path]["size"],
                ))

        return self.changes

    def save_snapshot(self) -> None:
        """Save current snapshot as baseline."""
        self._last_snapshot = self.snapshot()
        import json
        self.snapshot_file.write_text(json.dumps(self._last_snapshot, indent=2))

    def load_snapshot(self) -> None:
        """Load saved snapshot as baseline."""
        if self.snapshot_file.exists():
            import json
            self._last_snapshot = json.loads(self.snapshot_file.read_text())

    def summary(self) -> dict[str, Any]:
        return {
            "total_changes": len(self.changes),
            "added": sum(1 for c in self.changes if c.change_type == "added"),
            "removed": sum(1 for c in self.changes if c.change_type == "removed"),
            "modified": sum(1 for c in self.changes if c.change_type == "modified"),
        }


_monitor: HomeostaticMonitor | None = None


def get_monitor() -> HomeostaticMonitor:
    global _monitor
    if _monitor is None:
        _monitor = HomeostaticMonitor()
    return _monitor
