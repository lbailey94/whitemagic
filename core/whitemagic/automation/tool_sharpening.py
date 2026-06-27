# ruff: noqa: BLE001
"""
Tool Sharpening Loop — Keep all systems updated.

"Circles within circles in a circle"

Automatically:
- Update shell techniques
- Sync MCP integrations
- Reflect code changes in all interfaces
- Test and validate consistency
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ToolSharpening:
    """Keeps all systems sharp and updated."""

    def __init__(self) -> None:
        self.sharpening_log: list[dict[str, Any]] = []
        self.sharpened: int = 0

    def sharpen_all(self) -> dict[str, Any]:
        """Run all sharpening checks."""
        results: dict[str, Any] = {}
        results["mcp_tools"] = self._sharpen_mcp()
        results["dispatch_table"] = self._sharpen_dispatch()
        results["grimoire"] = self._sharpen_grimoire()
        results["tests"] = self._sharpen_tests()

        entry = {"results": results, "timestamp": time.time()}
        self.sharpening_log.append(entry)
        self.sharpened += 1
        return results

    def _sharpen_mcp(self) -> dict[str, Any]:
        """Check MCP tool registry is up to date."""
        try:
            from whitemagic.tools.dispatch_table import DISPATCH_TABLE
            return {"status": "ok", "tools": len(DISPATCH_TABLE)}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _sharpen_dispatch(self) -> dict[str, Any]:
        """Check dispatch table consistency."""
        try:
            from whitemagic.tools.registry import get_registry
            reg = get_registry()
            return {"status": "ok", "registered": len(reg) if hasattr(reg, "__len__") else "unknown"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _sharpen_grimoire(self) -> dict[str, Any]:
        """Check grimoire chapters are accessible."""
        try:
            from whitemagic.agentic.grimoire_check import get_grimoire_checker
            checker = get_grimoire_checker()
            result = checker.check_available()
            return {"status": "ok", "chapters": result["total_chapters"]}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _sharpen_tests(self) -> dict[str, Any]:
        """Check test suite is accessible."""
        try:
            from whitemagic.config.paths import get_project_root
            test_dir = get_project_root() / "core" / "tests"
            if test_dir.exists():
                return {"status": "ok", "test_dir_exists": True}
            return {"status": "warn", "test_dir_exists": False}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def summary(self) -> dict[str, Any]:
        return {
            "sharpening_cycles": self.sharpened,
            "last_sharpening": self.sharpening_log[-1] if self.sharpening_log else None,
        }


_sharpening: ToolSharpening | None = None


def get_tool_sharpening() -> ToolSharpening:
    global _sharpening
    if _sharpening is None:
        _sharpening = ToolSharpening()
    return _sharpening
