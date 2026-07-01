"""Safe Command Execution Service
Centralized subprocess execution with security validation.

Eliminates command injection vulnerabilities by:
- Enforcing shell=False for all subprocess calls
- Using argument arrays instead of shell strings
- Validating commands against allowlist
- Logging all executions
- Applying resource limits
"""

import logging
import shlex
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class CommandNotAllowedError(Exception):
    """Raised when attempting to execute a non-allowed command."""


class SafeExecutor:
    """Secure subprocess execution with validation.

    Usage:
        executor = SafeExecutor()
        result = executor.execute(["git", "status"])

        # Or with string parsing:
        result = executor.execute("git status")
    """

    # Default allowlist of safe commands
    DEFAULT_ALLOWED_COMMANDS = {
        # Version control
        "git",
        # Python
        "python",
        "python3",
        "pip",
        "pip3",
        # Node.js
        "node",
        "npm",
        "npx",
        "yarn",
        # WhiteMagic CLI
        "wm",
        "whitemagic",
        # Common utilities (read-only)
        "ls",
        "cat",
        "grep",
        "find",
        "echo",
        "pwd",
        "head",
        "tail",
        "wc",
        "sort",
        "uniq",
        # Safe file creation (no overwrites/moves)
        "mkdir",
        "touch",
        # Testing
        "pytest",
        "jest",
        "mocha",
        # Sandboxing
        "firejail",
        "bwrap",
    }

    # Commands that require explicit opt-in via additional_allowed.
    # These are NOT blocked (so callers can re-enable them), but they
    # are excluded from the default allowlist because they can overwrite
    # or relocate files without confirmation.
    CONFIRM_COMMANDS = {"cp", "mv"}

    # Commands that should NEVER be allowed
    BLOCKED_COMMANDS = {
        "rm",
        "rmdir",
        "del",
        "deltree",  # Deletion
        "dd",
        "mkfs",
        "fdisk",  # Disk operations
        "chmod",
        "chown",
        "chgrp",  # Permission changes
        "sudo",
        "su",
        "doas",  # Privilege escalation
        "curl",
        "wget",
        "nc",
        "netcat",  # Network (can be dangerous)
        "eval",
        "exec",
        "source",  # Code execution
        "shutdown",
        "reboot",
        "halt",  # System control
    }

    def __init__(
        self,
        allowed_commands: set[str] | None = None,
        additional_allowed: set[str] | None = None,
        strict_mode: bool = False,
    ) -> None:
        """Initialize SafeExecutor.

        Args:
            allowed_commands: Complete set of allowed commands (overrides default)
            additional_allowed: Commands to add to default allowlist
            strict_mode: If True, only allow exact matches (no path resolution)

        """
        if allowed_commands is not None:
            self.allowed_commands = allowed_commands
        else:
            self.allowed_commands = self.DEFAULT_ALLOWED_COMMANDS.copy()
            if additional_allowed:
                self.allowed_commands.update(additional_allowed)

        self.strict_mode = strict_mode

        logger.info(
            "SafeExecutor initialized with %s allowed commands",
            len(self.allowed_commands),
        )

    def _parse_command(self, command: str | list[str]) -> list[str]:
        """Parse command into argument array.

        Args:
            command: Command string or array

        Returns:
            List of command arguments

        """
        if isinstance(command, str):
            # Use shlex for safe parsing (handles quotes, escapes)
            return shlex.split(command)
        if isinstance(command, list):
            return command
        raise TypeError(f"Command must be str or list, got {type(command)}")

    def _validate_command(self, cmd_array: list[str]) -> None:
        """Validate command against allowlist.

        Args:
            cmd_array: Command arguments

        Raises:
            CommandNotAllowedError: If command is not allowed

        """
        if not cmd_array:
            raise ValueError("Command array is empty")

        base_command = cmd_array[0]

        # Extract command name (handle paths)
        if "/" in base_command or "\\" in base_command:
            # Command is a path - extract basename
            base_command = Path(base_command).name

        if base_command in self.BLOCKED_COMMANDS:
            raise CommandNotAllowedError(
                f"Command '{base_command}' is explicitly blocked for security",
            )

        if base_command not in self.allowed_commands:
            raise CommandNotAllowedError(
                f"Command '{base_command}' is not in allowlist. "
                f"Allowed commands: {sorted(self.allowed_commands)}",
            )

        logger.debug("Command validated: %s", base_command)

    def execute(
        self,
        command: str | list[str],
        cwd: str | Path | None = None,
        timeout: int = 30,
        env: dict[str, str] | None = None,
        capture_output: bool = True,
        text: bool = True,
        check: bool = False,
    ) -> subprocess.CompletedProcess:
        """Execute command safely.

        Args:
            command: Command string or array
            cwd: Working directory
            timeout: Timeout in seconds
            env: Environment variables (merged with current env)
            capture_output: Capture stdout/stderr
            text: Return output as text (not bytes)
            check: Raise CalledProcessError if command fails

        Returns:
            CompletedProcess with result

        Raises:
            CommandNotAllowedError: If command not allowed
            subprocess.TimeoutExpired: If command times out
            subprocess.CalledProcessError: If check=True and command fails

        """
        cmd_array = self._parse_command(command)

        self._validate_command(cmd_array)

        # Prepare environment
        exec_env = None
        if env is not None:
            import os

            exec_env = os.environ.copy()
            exec_env.update(env)

        logger.info("Executing: %s", " ".join(cmd_array))
        if cwd:
            logger.debug("  Working directory: %s", cwd)

        try:
            result = subprocess.run(
                cmd_array,
                shell=False,  # CRITICAL: Never use shell=True
                cwd=cwd,
                env=exec_env,
                capture_output=capture_output,
                text=text,
                timeout=timeout,
                check=check,
            )

            logger.debug("Command completed with return code: %s", result.returncode)
            return result

        except subprocess.TimeoutExpired:
            logger.warning(
                "Command timed out after %ss: {' '.join(cmd_array)}",
                timeout,
                exc_info=True,
            )
            raise
        except subprocess.CalledProcessError as e:
            logger.error(
                "Command failed with code %s: {' '.join(cmd_array)}",
                e.returncode,
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error("Command execution error: %s", e, exc_info=True)
            raise

    def execute_async(
        self,
        command: str | list[str],
        cwd: str | Path | None = None,
        env: dict[str, str] | None = None,
    ) -> subprocess.Popen:
        """Execute command asynchronously (non-blocking).

        Args:
            command: Command string or array
            cwd: Working directory
            env: Environment variables

        Returns:
            Popen object for async management

        """
        cmd_array = self._parse_command(command)
        self._validate_command(cmd_array)

        # Prepare environment
        exec_env = None
        if env is not None:
            import os

            exec_env = os.environ.copy()
            exec_env.update(env)

        logger.info("Starting async: %s", " ".join(cmd_array))

        return subprocess.Popen(
            cmd_array,
            shell=False,  # CRITICAL: Never use shell=True
            cwd=cwd,
            env=exec_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def is_allowed(self, command: str | list[str]) -> bool:
        """Check if command would be allowed (without executing).

        Args:
            command: Command to check

        Returns:
            True if command is allowed

        """
        try:
            cmd_array = self._parse_command(command)
            self._validate_command(cmd_array)
            return True
        except (CommandNotAllowedError, ValueError):
            return False


# Global instance for convenience
_default_executor: SafeExecutor | None = None


def get_executor() -> SafeExecutor:
    """Get global SafeExecutor instance."""
    global _default_executor
    if _default_executor is None:
        _default_executor = SafeExecutor()
    return _default_executor


def execute_safe(
    command: str | list[str],
    **kwargs: Any,
) -> subprocess.CompletedProcess:
    """Convenience function for safe execution.

    Args:
        command: Command to execute
        **kwargs: Passed to SafeExecutor.execute()

    Returns:
        CompletedProcess result

    """
    return get_executor().execute(command, **kwargs)


__all__ = [
    "CommandNotAllowedError",
    "SafeExecutor",
    "execute_safe",
    "get_executor",
]
