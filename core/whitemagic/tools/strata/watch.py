import os
import time
from pathlib import Path
from typing import Callable, Dict

__all__ = ["FileWatcher"]


class FileWatcher:
    """Polling-based file watcher using only the stdlib."""

    def __init__(self, project_path: Path, interval: float = 1.0):
        self.project_path = Path(project_path).resolve()
        self.interval = interval
        self._snapshots: Dict[str, float] = {}

    def _take_snapshot(self) -> Dict[str, float]:
        snap: Dict[str, float] = {}
        for root, dirs, files in os.walk(self.project_path):
            # Skip common non-project directories
            dirs[:] = [
                d for d in dirs
                if d not in {
                    ".venv", "venv", "node_modules", "target", "dist", "build",
                    ".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".tox",
                }
            ]
            for f in files:
                p = Path(root) / f
                try:
                    snap[str(p)] = p.stat().st_mtime
                except (OSError, FileNotFoundError):
                    continue
        return snap

    def _has_changes(self) -> bool:
        new_snap = self._take_snapshot()
        if not self._snapshots:
            self._snapshots = new_snap
            return True
        if new_snap != self._snapshots:
            self._snapshots = new_snap
            return True
        return False

    def run(self, callback: Callable[[], None]):
        """Poll for changes and invoke callback when detected."""
        # Initial run
        self._snapshots = self._take_snapshot()
        callback()
        print(f"\n👁️  Watching {self.project_path} for changes... (Ctrl+C to stop)\n")
        try:
            while True:
                time.sleep(self.interval)
                if self._has_changes():
                    callback()
        except KeyboardInterrupt:
            print("\n🛑 Watch mode stopped.")
