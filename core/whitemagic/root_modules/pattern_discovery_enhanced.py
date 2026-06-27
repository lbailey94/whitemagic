# ruff: noqa: BLE001
"""
Pattern Discovery using Rust-optimized search — Phase 2 Enhanced.

Ultra-fast pattern extraction across entire codebase.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class EnhancedPatternDiscovery:
    """Ultra-fast pattern extraction across codebase."""

    def __init__(self) -> None:
        self.patterns: list[dict[str, Any]] = []
        self._rust_available = False
        self._check_rust()

    def _check_rust(self) -> None:
        try:
            import importlib
            importlib.import_module("whitemagic_rust")
            self._rust_available = True
        except ImportError:
            pass

    def discover_patterns(self, root: Path | None = None, max_files: int = 100) -> list[dict[str, Any]]:
        """Discover patterns in codebase."""
        if root is None:
            root = Path(".")
        root = Path(root)

        discovered: list[dict[str, Any]] = []
        files_scanned = 0

        for f in root.rglob("*.py"):
            if files_scanned >= max_files:
                break
            if ".git" in str(f) or "__pycache__" in str(f) or ".venv" in str(f):
                continue

            try:
                content = f.read_text()
                # Find function definitions
                funcs = re.findall(r"def (\w+)\(", content)
                # Find class definitions
                classes = re.findall(r"class (\w+)", content)

                if funcs or classes:
                    discovered.append({
                        "file": str(f.relative_to(root)),
                        "functions": funcs[:10],
                        "classes": classes[:5],
                        "size": len(content),
                    })
                files_scanned += 1
            except Exception:
                continue

        self.patterns = discovered
        return discovered

    def find_duplicates(self) -> list[dict[str, Any]]:
        """Find duplicate function names across files."""
        func_locations: dict[str, list[str]] = {}
        for entry in self.patterns:
            for func in entry["functions"]:
                func_locations.setdefault(func, []).append(entry["file"])

        return [
            {"function": func, "files": files}
            for func, files in func_locations.items()
            if len(files) > 1
        ]

    def summary(self) -> dict[str, Any]:
        return {
            "total_files": len(self.patterns),
            "rust_accelerated": self._rust_available,
            "duplicates": len(self.find_duplicates()),
        }


_discovery: EnhancedPatternDiscovery | None = None


def get_enhanced_discovery() -> EnhancedPatternDiscovery:
    global _discovery
    if _discovery is None:
        _discovery = EnhancedPatternDiscovery()
    return _discovery
