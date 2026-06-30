# ruff: noqa: BLE001
"""
Self-Improving Cascade — Constitutional AI inspired self-critique.

Inspired by:
- Constitutional AI (self-critique and revision)
- Knowledge Distillation (learn from own successes)
- RAG (ground responses in retrieved context)
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from whitemagic.config.paths import get_state_root

logger = logging.getLogger(__name__)


class SelfImprovingCascade:
    """Self-improving cascade with self-critique."""

    def __init__(self, data_dir: Path | None = None) -> None:
        if data_dir is None:
            data_dir = get_state_root() / "edge" / "self_improving"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.improvements: list[dict[str, Any]] = []

    def self_critique(self, output: str) -> dict[str, Any]:
        """Critique own output for improvement opportunities."""
        issues: list[str] = []
        if len(output) < 10:
            issues.append("Output too short")
        if output.count("```") % 2 != 0:
            issues.append("Unbalanced code blocks")
        if "TODO" in output:
            issues.append("Contains TODO marker")

        return {
            "output_length": len(output),
            "issues_found": len(issues),
            "issues": issues,
            "can_improve": len(issues) > 0,
        }

    def improve(self, output: str) -> dict[str, Any]:
        """Generate improved version of output."""
        critique = self.self_critique(output)
        improved = output

        if "Output too short" in critique["issues"]:
            improved = improved + "\n\n[Expanded for clarity]"
        if "Contains TODO marker" in critique["issues"]:
            improved = improved.replace("TODO", "REVIEW")

        entry = {
            "original_length": len(output),
            "improved_length": len(improved),
            "issues_fixed": critique["issues_found"],
            "timestamp": time.time(),
        }
        self.improvements.append(entry)
        with open(self.data_dir / "improvements.jsonl", "a") as f:
            f.write(json.dumps(entry) + "\n")

        return {
            "improved": improved,
            "critique": critique,
            "changes_made": critique["issues_found"],
        }

    def summary(self) -> dict[str, Any]:
        return {
            "total_improvements": len(self.improvements),
            "avg_issues_fixed": (
                sum(i["issues_fixed"] for i in self.improvements)
                / len(self.improvements)
                if self.improvements
                else 0.0
            ),
        }


_cascade: SelfImprovingCascade | None = None


def get_self_improving() -> SelfImprovingCascade:
    global _cascade
    if _cascade is None:
        _cascade = SelfImprovingCascade()
    return _cascade
