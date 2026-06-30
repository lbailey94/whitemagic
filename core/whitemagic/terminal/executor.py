# ruff: noqa: BLE001
"""Core execution engine for terminal commands."""

from __future__ import annotations

import logging
import subprocess
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result of a command execution."""

    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration_s: float


class Executor:
    """Executes commands with safety checks."""

    def __init__(self, timeout: int = 30) -> None:
        self.timeout = timeout

    def execute(self, command: str, cwd: str | None = None) -> ExecutionResult:
        """Execute a command and return the result."""
        start = time.monotonic()
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=cwd,
            )
            elapsed = time.monotonic() - start
            return ExecutionResult(
                command=command,
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                duration_s=elapsed,
            )
        except subprocess.TimeoutExpired:
            elapsed = time.monotonic() - start
            return ExecutionResult(
                command=command,
                exit_code=-1,
                stdout="",
                stderr=f"Timeout after {self.timeout}s",
                duration_s=elapsed,
            )
        except Exception as e:
            elapsed = time.monotonic() - start
            return ExecutionResult(
                command=command,
                exit_code=-1,
                stdout="",
                stderr=str(e),
                duration_s=elapsed,
            )

    def execute_safe(
        self, command: str, allowlist: Any | None = None
    ) -> ExecutionResult:
        """Execute with allowlist check."""
        if allowlist and not allowlist.is_allowed(command):
            return ExecutionResult(
                command=command,
                exit_code=-1,
                stdout="",
                stderr="Command not in allowlist",
                duration_s=0.0,
            )
        return self.execute(command)
