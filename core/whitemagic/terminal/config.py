# ruff: noqa: BLE001
"""Configuration for terminal tool."""

from __future__ import annotations

from typing import Any


class TerminalConfig:
    """Configuration for the terminal tool."""

    def __init__(
        self,
        timeout: int = 30,
        max_output: int = 10000,
        history_size: int = 100,
    ) -> None:
        self.timeout = timeout
        self.max_output = max_output
        self.history_size = history_size
        self._history: list[str] = []

    def add_to_history(self, command: str) -> None:
        """Add a command to history."""
        self._history.append(command)
        if len(self._history) > self.history_size:
            self._history = self._history[-self.history_size:]

    def get_history(self, limit: int = 20) -> list[str]:
        """Get command history."""
        return self._history[-limit:]

    def summary(self) -> dict[str, Any]:
        return {
            "timeout": self.timeout,
            "max_output": self.max_output,
            "history_size": len(self._history),
        }
