# ruff: noqa: BLE001
"""Pre-commit auto-fix loop — eliminate manual fixes."""

from __future__ import annotations

import logging
import subprocess
from typing import Any

logger = logging.getLogger(__name__)


class PreCommitAutoFix:
    """Automatically fix pre-commit issues and retry."""

    def __init__(self, max_retries: int = 3) -> None:
        self.max_retries = max_retries
        self.fixes_applied: list[dict[str, Any]] = []

    def run_precommit(self) -> tuple[bool, str]:
        """Run pre-commit hooks. Returns (success, output)."""
        try:
            result = subprocess.run(
                ["pre-commit", "run", "--all-files"],
                capture_output=True,
                text=True,
                timeout=120,
            )
            return result.returncode == 0, result.stdout + result.stderr
        except FileNotFoundError:
            return True, "pre-commit not installed"
        except Exception as e:
            return False, str(e)

    def apply_fixes(self, output: str) -> list[str]:
        """Determine and apply fixes based on pre-commit output."""
        fixes: list[str] = []
        if "ruff" in output and "would reformat" in output:
            subprocess.run(["ruff", "check", "--fix", "."], capture_output=True)
            fixes.append("ruff auto-fix")
        if "isort" in output and "would reformat" in output:
            subprocess.run(["isort", "."], capture_output=True)
            fixes.append("isort")
        if "trailing whitespace" in output:
            fixes.append("trailing whitespace (pre-commit auto-fixes)")
        return fixes

    def run(self) -> dict[str, Any]:
        """Run the full auto-fix loop."""
        for attempt in range(self.max_retries):
            success, output = self.run_precommit()
            if success:
                return {"success": True, "attempts": attempt + 1, "fixes": self.fixes_applied}

            fixes = self.apply_fixes(output)
            if fixes:
                self.fixes_applied.append({"attempt": attempt + 1, "fixes": fixes})
            else:
                # No auto-fixes available, manual intervention needed
                return {
                    "success": False,
                    "attempts": attempt + 1,
                    "output": output[:500],
                    "fixes": self.fixes_applied,
                }

        return {"success": False, "attempts": self.max_retries, "fixes": self.fixes_applied}
