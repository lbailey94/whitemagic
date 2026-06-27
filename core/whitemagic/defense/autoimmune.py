# ruff: noqa: BLE001
"""
Autoimmune Defense System — Transform anti-patterns into active defenses.

Scans for known anti-patterns in the codebase and converts them
into learned defenses, preventing future occurrences.
"""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Any

from whitemagic.config.paths import get_state_root

logger = logging.getLogger(__name__)


class AutoimmuneDefense:
    """Transform anti-patterns into active defenses."""

    ANTIPATTERNS: list[dict[str, str]] = [
        {"pattern": r"Path\.home\(\)", "name": "path_home_violation",
         "fix": "Use get_state_root() from whitemagic.config.paths"},
        {"pattern": r"\.expanduser\(\)", "name": "expanduser_violation",
         "fix": "Use get_state_root() from whitemagic.config.paths"},
        {"pattern": r"except\s+Exception\s*:\s*pass\s*$", "name": "silent_exception",
         "fix": "Add logging or specific exception handling"},
        {"pattern": r"TODO", "name": "todo_marker",
         "fix": "Use NotImplementedError with reason and date"},
    ]

    def __init__(self, data_dir: Path | None = None) -> None:
        if data_dir is None:
            data_dir = get_state_root() / "defense"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.findings_file = self.data_dir / "autoimmune_findings.jsonl"
        self.findings: list[dict[str, Any]] = []

    def scan_file(self, file_path: Path) -> list[dict[str, Any]]:
        """Scan a single file for anti-patterns."""
        results: list[dict[str, Any]] = []
        if not file_path.exists() or file_path.suffix != ".py":
            return results

        try:
            content = file_path.read_text()
            for ap in self.ANTIPATTERNS:
                for match in re.finditer(ap["pattern"], content, re.MULTILINE):
                    line_num = content[:match.start()].count("\n") + 1
                    results.append({
                        "file": str(file_path),
                        "line": line_num,
                        "antipattern": ap["name"],
                        "fix": ap["fix"],
                        "timestamp": time.time(),
                    })
        except Exception:
            pass

        return results

    def scan_directory(self, directory: Path) -> list[dict[str, Any]]:
        """Scan a directory for anti-patterns."""
        all_findings: list[dict[str, Any]] = []
        for f in directory.rglob("*.py"):
            if ".git" in str(f) or "__pycache__" in str(f):
                continue
            findings = self.scan_file(f)
            all_findings.extend(findings)
            for finding in findings:
                self._save(finding)
        self.findings.extend(all_findings)
        return all_findings

    def _save(self, finding: dict[str, Any]) -> None:
        with open(self.findings_file, "a") as f:
            f.write(json.dumps(finding) + "\n")

    def summary(self) -> dict[str, Any]:
        return {
            "total_findings": len(self.findings),
            "by_type": self._group_by_type(),
        }

    def _group_by_type(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for f in self.findings:
            name = f["antipattern"]
            counts[name] = counts.get(name, 0) + 1
        return counts


_autoimmune: AutoimmuneDefense | None = None


def get_autoimmune() -> AutoimmuneDefense:
    global _autoimmune
    if _autoimmune is None:
        _autoimmune = AutoimmuneDefense()
    return _autoimmune
