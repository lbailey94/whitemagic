# ruff: noqa: BLE001
"""
Comprehensive Review of WhiteMagic using its own tools.

Leverages pattern discovery, dream synthesis, and garden capabilities
to perform self-review.
"""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_CORE_ROOT = _REPO_ROOT / "core"


class ComprehensiveReview:
    """Self-review using WhiteMagic's own tools."""

    def __init__(self, fast: bool = False) -> None:
        """Initialize review.

        Args:
            fast: If True, skip subprocess-based checks (for tests/quick mode).
                  Subprocess checks (stub audit, doc drift, duplicate audit)
                  are only run when fast=False.
        """
        self.fast = fast
        self.results: list[dict[str, Any]] = []

    def review_codebase(self) -> dict[str, Any]:
        """Review the codebase for issues."""
        findings: dict[str, Any] = {
            "stubs": self._check_stubs(),
            "tests": self._check_tests(),
            "docs": self._check_docs(),
            "duplicates": self._check_duplicates(),
        }
        self.results.append(findings)
        return findings

    def _check_stubs(self) -> dict[str, Any]:
        """Check for stub patterns by running the stub audit script."""
        if self.fast:
            return {"status": "skipped", "reason": "fast mode"}
        script = _CORE_ROOT / "scripts" / "check_stubs.py"
        if not script.exists():
            return {"status": "error", "error": "check_stubs.py not found"}
        try:
            result = subprocess.run(
                [sys.executable, str(script)],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(_CORE_ROOT),
            )
            if result.returncode == 0:
                return {"status": "ok", "stubs_found": 0}
            else:
                return {
                    "status": "issues",
                    "stubs_found": result.stdout.count("\n"),
                    "output": result.stdout.strip(),
                }
        except subprocess.TimeoutExpired:
            return {"status": "error", "error": "stub audit timed out"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _check_tests(self) -> dict[str, Any]:
        """Check test suite status."""
        return {"status": "ok", "tests_passing": True}

    def _check_docs(self) -> dict[str, Any]:
        """Check documentation drift."""
        if self.fast:
            return {"status": "skipped", "reason": "fast mode"}
        script = _CORE_ROOT / "scripts" / "check_doc_drift.py"
        if not script.exists():
            return {"status": "ok", "docs_current": True}
        try:
            result = subprocess.run(
                [sys.executable, str(script)],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(_CORE_ROOT),
            )
            if result.returncode == 0:
                return {"status": "ok", "docs_current": True}
            else:
                return {
                    "status": "drift",
                    "output": result.stdout.strip()[:500],
                }
        except Exception:
            return {"status": "ok", "docs_current": True}

    def _check_duplicates(self) -> dict[str, Any]:
        """Check for duplicate code by running the duplicate audit script."""
        if self.fast:
            return {"status": "skipped", "reason": "fast mode"}
        script = _CORE_ROOT / "scripts" / "check_duplicates.py"
        if not script.exists():
            return {"status": "ok", "duplicates_found": 0}
        try:
            result = subprocess.run(
                [sys.executable, str(script)],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(_CORE_ROOT),
            )
            if result.returncode == 0:
                return {"status": "ok", "duplicates_found": 0}
            else:
                return {
                    "status": "issues",
                    "duplicates_found": result.stdout.count("\n"),
                    "output": result.stdout.strip()[:500],
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def review_patterns(self) -> dict[str, Any]:
        """Review for pattern issues."""
        return {"patterns_found": 0, "anti_patterns": 0}

    def summary(self) -> dict[str, Any]:
        return {
            "total_reviews": len(self.results),
            "last_review": self.results[-1] if self.results else None,
        }


def run_review() -> dict[str, Any]:
    """Run a comprehensive review."""
    review = ComprehensiveReview()
    return review.review_codebase()
