# ruff: noqa: BLE001
"""Terminal-based reasoning — use terminal for free composite reasoning."""

from __future__ import annotations

import logging
import subprocess
from typing import Any

logger = logging.getLogger(__name__)


class TerminalReasoning:
    """Use terminal commands for composite reasoning without AI tokens."""

    def __init__(self) -> None:
        self.history: list[dict[str, str]] = []

    def reason(self, query: str) -> dict[str, Any]:
        """Attempt to reason about a query using terminal tools."""
        result: dict[str, Any] = {
            "query": query,
            "method": "terminal",
            "output": "",
            "success": False,
        }

        try:
            if "grep" in query.lower() or "search" in query.lower():
                result["output"] = self._grep_search(query)
                result["success"] = bool(result["output"])
            elif "count" in query.lower():
                result["output"] = self._count_files(query)
                result["success"] = bool(result["output"])
            elif "git" in query.lower():
                result["output"] = self._git_info()
                result["success"] = bool(result["output"])
        except Exception as e:
            result["output"] = f"Terminal reasoning failed: {e}"
            logger.debug("Terminal reasoning error: %s", e)

        self.history.append(result)
        return result

    def _grep_search(self, query: str) -> str:
        words = [w for w in query.split() if len(w) > 3]
        if not words:
            return ""
        try:
            proc = subprocess.run(
                ["grep", "-rn", "--include=*.py", "-l", words[0], "."],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return proc.stdout[:2000]
        except Exception:
            return ""

    def _count_files(self, query: str) -> str:
        try:
            proc = subprocess.run(
                [
                    "find",
                    ".",
                    "-name",
                    "*.py",
                    "-not",
                    "-path",
                    "*/.git/*",
                    "-not",
                    "-path",
                    "*/__pycache__/*",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            count = len(proc.stdout.strip().splitlines())
            return f"Found {count} Python files"
        except Exception:
            return ""

    def _git_info(self) -> str:
        try:
            proc = subprocess.run(
                ["git", "log", "--oneline", "-5"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return proc.stdout
        except Exception:
            return ""


_reasoning: TerminalReasoning | None = None


def get_terminal_reasoning() -> TerminalReasoning:
    global _reasoning
    if _reasoning is None:
        _reasoning = TerminalReasoning()
    return _reasoning
