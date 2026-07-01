# ruff: noqa: BLE001
"""Test watcher — auto-run tests on file changes."""

from __future__ import annotations

import hashlib
import logging
import subprocess
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class TestWatcher:
    """Watch files and auto-run tests on changes."""

    def __init__(
        self, watch_dir: Path | None = None, test_cmd: list[str] | None = None
    ) -> None:
        self.watch_dir = watch_dir or Path(".")
        self.test_cmd = test_cmd or [
            "python",
            "-m",
            "pytest",
            "tests/unit/",
            "-q",
            "--timeout=10",
        ]
        self._file_hashes: dict[str, str] = {}
        self._running = False
        self._last_run: float = 0.0
        self._results: list[dict[str, Any]] = []

    def _hash_files(self) -> dict[str, str]:
        hashes: dict[str, str] = {}
        for f in self.watch_dir.rglob("*.py"):
            if ".git" in str(f) or "__pycache__" in str(f) or ".venv" in str(f):
                continue
            try:
                hashes[str(f)] = hashlib.md5(f.read_bytes()).hexdigest()
            except Exception:
                logger.debug("Swallowed exception", exc_info=True)
        return hashes

    def check_changes(self) -> list[str]:
        """Check for changed files since last scan."""
        current = self._hash_files()
        changed: list[str] = []

        for path, hash_val in current.items():
            if path not in self._file_hashes or self._file_hashes[path] != hash_val:
                changed.append(path)

        # Check for deleted files
        for path in list(self._file_hashes):
            if path not in current:
                changed.append(path)

        self._file_hashes = current
        return changed

    def run_tests(self) -> dict[str, Any]:
        """Run the test command."""
        start = time.monotonic()
        try:
            result = subprocess.run(
                self.test_cmd,
                capture_output=True,
                text=True,
                timeout=120,
            )
            success = result.returncode == 0
            output = result.stdout + result.stderr
        except Exception as e:
            success = False
            output = str(e)

        entry = {
            "success": success,
            "output": output[:500],
            "duration_s": time.monotonic() - start,
            "timestamp": time.time(),
        }
        self._results.append(entry)
        self._last_run = time.time()
        return entry

    def watch_once(self) -> dict[str, Any]:
        """Check for changes and run tests if needed."""
        changed = self.check_changes()
        if not changed:
            return {"changed": False, "files": []}

        result = self.run_tests()
        return {"changed": True, "files": changed, "test_result": result}

    def summary(self) -> dict[str, Any]:
        return {
            "watching": str(self.watch_dir),
            "tracked_files": len(self._file_hashes),
            "total_runs": len(self._results),
            "last_run": self._last_run,
        }
