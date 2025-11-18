"""Core execution engine."""

import os
import subprocess
import time
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class ExecutionResult:
    """Result of command execution."""

    exit_code: int
    stdout: str
    stderr: str
    duration_ms: float
    command: str


class Executor:
    """Execute commands safely."""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    def execute(
        self,
        cmd: str,
        args: Optional[List[str]] = None,
        cwd: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        env: Optional[Dict[str, str]] = None,
        stdin: Optional[str] = None,
    ) -> ExecutionResult:
        """Execute command.

        Args:
            cmd: Command to execute
            args: Command arguments
            cwd: Working directory
            timeout_ms: Timeout in milliseconds (overrides default)
            env: Environment variables to merge with process env
            stdin: Input to pipe to command
        """
        start = time.time()
        full_cmd = [cmd] + (args or [])

        # Convert timeout_ms to seconds, or use default
        timeout_sec = (timeout_ms / 1000.0) if timeout_ms is not None else self.timeout

        # Merge environment variables
        process_env = os.environ.copy()
        if env:
            process_env.update(env)

        try:
            result = subprocess.run(
                full_cmd,
                cwd=cwd,
                env=process_env,
                input=stdin,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
            )

            duration = (time.time() - start) * 1000

            return ExecutionResult(
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                duration_ms=round(duration, 2),
                command=" ".join(full_cmd),
            )
        except subprocess.TimeoutExpired:
            return ExecutionResult(
                exit_code=-1,
                stdout="",
                stderr=f"Timeout after {timeout_sec}s",
                duration_ms=(time.time() - start) * 1000,
                command=" ".join(full_cmd),
            )
        except Exception as e:
            return ExecutionResult(
                exit_code=-1,
                stdout="",
                stderr=str(e),
                duration_ms=(time.time() - start) * 1000,
                command=" ".join(full_cmd),
            )
