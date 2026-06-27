# ruff: noqa: BLE001
"""
Workflow Patterns — Code equivalent of global/workspace rules.

Codifies workflow patterns as executable Python code to ensure
consistent adoption across sessions.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


class WorkflowPatterns:
    """Executable workflow patterns for consistent development."""

    def __init__(self) -> None:
        self.patterns: dict[str, dict[str, Any]] = {}
        self._init_defaults()

    def _init_defaults(self) -> None:
        self.patterns = {
            "test_first": {
                "description": "Always run tests before and after changes",
                "steps": ["run_tests", "make_change", "run_tests", "commit"],
            },
            "minimal_edit": {
                "description": "Prefer minimal focused edits",
                "steps": ["identify_root_cause", "minimal_fix", "verify"],
            },
            "lint_before_commit": {
                "description": "Run ruff before every commit",
                "steps": ["ruff_check", "fix_issues", "ruff_check", "commit"],
            },
            "cross_reference": {
                "description": "Cross-reference before creating new modules",
                "steps": ["search_existing", "check_archive", "create_if_needed"],
            },
            "batch_commit": {
                "description": "Commit in scoped batches with clear messages",
                "steps": ["stage_files", "write_message", "commit", "push"],
            },
        }

    def get_pattern(self, name: str) -> dict[str, Any] | None:
        return self.patterns.get(name)

    def add_pattern(self, name: str, description: str, steps: list[str]) -> None:
        self.patterns[name] = {"description": description, "steps": steps}

    def execute_pattern(self, name: str, step_fn: Callable[[str], bool] | None = None) -> dict[str, Any]:
        """Execute a workflow pattern step by step."""
        pattern = self.patterns.get(name)
        if not pattern:
            return {"status": "error", "error": f"Pattern '{name}' not found"}

        results: list[dict[str, Any]] = []
        for step in pattern["steps"]:
            if step_fn:
                success = step_fn(step)
                results.append({"step": step, "success": success})
            else:
                results.append({"step": step, "success": True})

        all_success = all(r["success"] for r in results)
        return {
            "status": "success" if all_success else "partial",
            "pattern": name,
            "results": results,
        }

    def summary(self) -> dict[str, Any]:
        return {
            "total_patterns": len(self.patterns),
            "pattern_names": list(self.patterns.keys()),
        }


_patterns: WorkflowPatterns | None = None


def get_workflow_patterns() -> WorkflowPatterns:
    global _patterns
    if _patterns is None:
        _patterns = WorkflowPatterns()
    return _patterns
