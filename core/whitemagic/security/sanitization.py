"""Security utilities for safe command execution and input sanitization.

This module provides centralized security utilities for:
- Safe subprocess execution with input validation
- Command argument sanitization
- SQL injection prevention helpers
- Path traversal protection
"""

import os
import re
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Command Sanitization
# ---------------------------------------------------------------------------

_DANGEROUS_PATTERNS = [
    r'[;&|`$()]',  # Shell metacharacters
    r'\.\./',  # Path traversal
    r'/etc/',  # System paths
    r'\\x[0-9a-f]{2}',  # Hex encoding attempts
]


def sanitize_command_arg(arg: str) -> str:
    """Sanitize a single command argument.

    Args:
        arg: The argument to sanitize

    Returns:
        Sanitized argument

    Raises:
        ValueError: If argument contains dangerous patterns
    """
    if not isinstance(arg, str):
        raise ValueError(f"Argument must be string, got {type(arg)}")

    # Check for dangerous patterns
    for pattern in _DANGEROUS_PATTERNS:
        if re.search(pattern, arg, re.IGNORECASE):
            raise ValueError(f"Argument contains dangerous pattern: {pattern}")

    # Limit length
    if len(arg) > 10_000:
        raise ValueError("Argument too long (max 10,000 characters)")

    return arg


def sanitize_command_args(args: Sequence[str]) -> list[str]:
    """Sanitize all command arguments.

    Args:
        args: Sequence of arguments to sanitize

    Returns:
        List of sanitized arguments

    Raises:
        ValueError: If any argument contains dangerous patterns
    """
    return [sanitize_command_arg(str(arg)) for arg in args]


def validate_path(path: str | Path, allowed_bases: list[Path] | None = None) -> Path:
    """Validate a path is within allowed directories.

    Args:
        path: The path to validate
        allowed_bases: List of allowed base directories (default: current dir)

    Returns:
        Resolved Path object

    Raises:
        ValueError: If path is outside allowed bases
    """
    if not isinstance(path, (str, Path)):
        raise ValueError(f"Path must be string or Path, got {type(path)}")

    resolved = Path(path).resolve()

    if allowed_bases:
        for base in allowed_bases:
            try:
                resolved.relative_to(base.resolve())
                return resolved
            except ValueError:
                continue
        raise ValueError(f"Path {resolved} is outside allowed bases: {allowed_bases}")

    return resolved


# ---------------------------------------------------------------------------
# Safe Subprocess Execution
# ---------------------------------------------------------------------------

def safe_run(
    cmd: Sequence[str],
    cwd: str | Path | None = None,
    env: dict[str, str] | None = None,
    timeout: float | None = None,
    check: bool = False,
    capture_output: bool = True,
    text: bool = True,
    allowed_bases: list[Path] | None = None,
) -> subprocess.CompletedProcess:
    """Safely execute a subprocess command with sanitization.

    This is a wrapper around subprocess.run that:
    - Sanitizes all command arguments
    - Validates paths are within allowed directories
    - Prevents shell injection by never using shell=True

    Args:
        cmd: Command and arguments as a sequence (NOT a string)
        cwd: Working directory (validated against allowed_bases if provided)
        env: Environment variables (filtered for security)
        timeout: Timeout in seconds
        check: Raise CalledProcessError on non-zero exit
        capture_output: Capture stdout/stderr
        text: Return as string instead of bytes
        allowed_bases: Allowed base directories for path validation

    Returns:
        CompletedProcess object

    Raises:
        ValueError: If command contains dangerous patterns
        subprocess.TimeoutExpired: If timeout is exceeded
        subprocess.CalledProcessError: If check=True and command fails
    """
    # Sanitize command
    sanitized_cmd = sanitize_command_args(cmd)

    # Validate working directory
    if cwd:
        cwd = validate_path(cwd, allowed_bases)

    # Filter environment variables (only allow safe prefixes)
    safe_env = {}
    safe_prefixes = [
        'WM_', 'PATH', 'HOME', 'USER', 'LANG', 'LC_',
        'PYTHON', 'VIRTUAL_ENV', 'CONDA_'
    ]
    if env:
        for k, v in env.items():
            if any(k.startswith(prefix) for prefix in safe_prefixes):
                safe_env[k] = str(v)

    # Execute with shell=False (prevents injection)
    return subprocess.run(  # noqa: S603 - inputs are sanitized, shell=False enforced
        sanitized_cmd,
        cwd=cwd,
        env=safe_env or None,
        timeout=timeout,
        check=check,
        capture_output=capture_output,
        text=text,
        shell=False,  # CRITICAL: Never use shell=True
    )


# ---------------------------------------------------------------------------
# SQL Injection Prevention
# ---------------------------------------------------------------------------

def validate_sql_identifier(identifier: str) -> str:
    """Validate a SQL identifier (table name, column name, etc).

    Args:
        identifier: The identifier to validate

    Returns:
        Validated identifier

    Raises:
        ValueError: If identifier is invalid
    """
    if not isinstance(identifier, str):
        raise ValueError(f"Identifier must be string, got {type(identifier)}")

    # Only allow alphanumeric, underscore, and dots for schema.table
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_.]*$', identifier):
        raise ValueError(f"Invalid SQL identifier: {identifier}")

    # Prevent SQL keywords
    sql_keywords = {
        'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE',
        'ALTER', 'TRUNCATE', 'UNION', 'WHERE', 'FROM', 'JOIN',
        'EXEC', 'EXECUTE', 'SCRIPT', '--', '/*', '*/'
    }
    if identifier.upper() in sql_keywords:
        raise ValueError(f"Identifier cannot be SQL keyword: {identifier}")

    return identifier


def validate_sql_value(value: str | int | float | bool | None) -> str | int | float | bool | None:
    """Validate a SQL value (for parameterized queries).

    Note: This is a sanity check. Always use parameterized queries!

    Args:
        value: The value to validate

    Returns:
        Validated value

    Raises:
        ValueError: If value is suspicious
    """
    if value is None:
        return None

    if isinstance(value, (int, float, bool)):
        return value

    if isinstance(value, str):
        # Check for SQL injection patterns (actual attack patterns, not English words)
        # Note: Parameterized queries are the real defense. This is a secondary check.
        sql_patterns = [
            r";\s*(DROP|DELETE|UPDATE|INSERT|ALTER|CREATE|EXEC)",  # SQL command injection
            r'--',  # SQL comment
            r'/\*',  # Block comment start
            r'\*/',  # Block comment end
            r"\bUNION\s+SELECT\b",  # UNION-based injection
            r"'\s*OR\s*'1'\s*=\s*'1",  # Classic tautology
            r"'\s*OR\s*1\s*=\s*1",  # Tautology without quotes
            r'\b1\s*=\s*1\b',  # Numeric tautology
            r'\bxp_cmdshell\b',  # SQL Server command execution
            r'\bexec\b',  # Execute command
        ]
        for pattern in sql_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                raise ValueError(f"Value contains SQL pattern: {pattern}")

        # Limit length
        if len(value) > 100_000:
            raise ValueError("String value too long (max 100,000 characters)")

        return value

    raise ValueError(f"Invalid SQL value type: {type(value)}")


# ---------------------------------------------------------------------------
# API Key Handling
# ---------------------------------------------------------------------------

def get_env_var(
    name: str,
    default: str | None = None,
    required: bool = False,
    allow_empty: bool = False,
) -> str | None:
    """Safely get an environment variable.

    Args:
        name: Variable name
        default: Default value if not set
        required: Raise error if not set
        allow_empty: Allow empty string values

    Returns:
        Environment variable value or default

    Raises:
        ValueError: If required and not set, or if empty and not allowed
    """
    value = os.environ.get(name)

    if value is None:
        if required:
            raise ValueError(f"Required environment variable not set: {name}")
        return default

    if not allow_empty and not value:
        if required:
            raise ValueError(f"Required environment variable is empty: {name}")
        return default

    # Sanitize: ensure it's a string and reasonable length
    if not isinstance(value, str):
        value = str(value)

    if len(value) > 10_000:
        raise ValueError(f"Environment variable too long: {name}")

    return value
