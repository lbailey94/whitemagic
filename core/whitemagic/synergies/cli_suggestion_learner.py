# ruff: noqa: BLE001
"""
CLI Suggestion Learner — Learn from CLI usage patterns.

Tracks which commands are used frequently and suggests relevant
commands based on context, reducing cognitive load for users.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from whitemagic.config.paths import get_state_root

logger = logging.getLogger(__name__)


class CLISuggestionLearner:
    """Learns from CLI usage to suggest commands."""

    def __init__(self, data_dir: Path | None = None) -> None:
        if data_dir is None:
            data_dir = get_state_root() / "synergies"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.usage_file = self.data_dir / "cli_usage.jsonl"
        self._usage: dict[str, int] = {}
        self._sequences: list[list[str]] = []
        self._load()

    def _load(self) -> None:
        if self.usage_file.exists():
            for line in self.usage_file.read_text().splitlines():
                if line.strip():
                    try:
                        d = json.loads(line)
                        cmd = d.get("command", "")
                        self._usage[cmd] = self._usage.get(cmd, 0) + 1
                        if "sequence" in d:
                            self._sequences.append(d["sequence"])
                    except Exception:
                        pass

    def record(
        self, command: str, context: str = "", sequence: list[str] | None = None
    ) -> None:
        """Record a command usage."""
        entry = {
            "command": command,
            "context": context,
            "timestamp": time.time(),
        }
        if sequence:
            entry["sequence"] = sequence
            self._sequences.append(sequence)
        self._usage[command] = self._usage.get(command, 0) + 1
        with open(self.usage_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def suggest(
        self, current_context: str = "", limit: int = 5
    ) -> list[dict[str, Any]]:
        """Suggest commands based on usage patterns."""
        sorted_cmds = sorted(self._usage.items(), key=lambda x: -x[1])
        return [
            {"command": cmd, "frequency": count} for cmd, count in sorted_cmds[:limit]
        ]

    def suggest_next(self, last_command: str) -> list[str]:
        """Suggest next command based on sequence patterns."""
        suggestions: list[str] = []
        for seq in self._sequences:
            for i, cmd in enumerate(seq):
                if cmd == last_command and i + 1 < len(seq):
                    suggestions.append(seq[i + 1])
        # Return most common next commands
        from collections import Counter

        counts = Counter(suggestions)
        return [cmd for cmd, _ in counts.most_common(5)]

    def summary(self) -> dict[str, Any]:
        return {
            "unique_commands": len(self._usage),
            "total_uses": sum(self._usage.values()),
            "sequences_tracked": len(self._sequences),
        }


_learner: CLISuggestionLearner | None = None


def get_suggestion_learner() -> CLISuggestionLearner:
    global _learner
    if _learner is None:
        _learner = CLISuggestionLearner()
    return _learner
