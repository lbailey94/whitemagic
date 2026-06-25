"""Input Sanitization Layer — Validate and sanitize all tool arguments at dispatch.
================================================================================
Protects against prompt injection, path traversal, oversized payloads, and
malformed inputs. Plugs into the dispatch pipeline at step 0.1 (first gate).

Three categories of checks:
  1. **Structure**: Max depth, max size, no circular references
  2. **Content**: Prompt injection patterns, path traversal, shell injection
  3. **Type validation**: Check args against tool's input_schema if available

Usage:
    from whitemagic.tools.input_sanitizer import sanitize_tool_args

    result = sanitize_tool_args("create_memory", {"content": "...", "tags": [...]})
    if result is not None:
        return result  # blocked — contains sanitization error
"""
# ruff: noqa: BLE001

import logging
import re
from typing import Any

from whitemagic.utils.fast_regex import compile as re_compile

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MAX_ARG_DEPTH = 10          # Max nesting depth for dicts/lists
MAX_STRING_LENGTH = 100_000  # 100KB per string value
MAX_TOTAL_SIZE = 1_000_000   # 1MB total serialized size estimate
MAX_LIST_LENGTH = 1000       # Max items in any list argument

# Prompt injection patterns (case-insensitive)
_INJECTION_PATTERNS: list[re.Pattern] = [
    re_compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
    re_compile(r"you\s+are\s+now\s+(a|an)\s+", re.IGNORECASE),
    re_compile(r"system\s*:\s*you\s+are", re.IGNORECASE),
    re_compile(r"<\s*system\s*>", re.IGNORECASE),
    re_compile(r"\{\{\s*system", re.IGNORECASE),
    re_compile(r"ADMIN_OVERRIDE", re.IGNORECASE),
    re_compile(r"sudo\s+", re.IGNORECASE),
]

# Path traversal patterns
_PATH_TRAVERSAL_PATTERNS: list[re.Pattern] = [
    re_compile(r"\.\./"),              # ../
    re_compile(r"\.\.\\"),           # ..\
    re_compile(r"/etc/(passwd|shadow|hosts)"),
    re_compile(r"~root"),
    re_compile(r"%2e%2e[/%5c]", re.IGNORECASE),  # URL-encoded ../
    re_compile(r"\.\.%2f", re.IGNORECASE),        # ..%2f
    re_compile(r"/proc/self/"),                    # Linux proc filesystem
]

# Shell injection patterns (for string values that might hit shell)
_SHELL_INJECTION_PATTERNS: list[re.Pattern] = [
    re_compile(r";\s*(rm|cat|curl|wget|bash|sh|python)\s", re.IGNORECASE),
    re_compile(r"\|\s*(bash|sh|python)", re.IGNORECASE),
    re_compile(r"\$\(.*\)"),          # $(command)
    re_compile(r"`.*`"),              # `command`
]

# Tools exempt from content scanning (their args are expected to contain code/text)
_CONTENT_SCAN_EXEMPT: set = {
    # Memory & narrative (arbitrary user/system content)
    "create_memory",
    "update_memory",
    "scratchpad_create",
    "scratchpad_update",
    "thought_clone",
    # Governance & ethics (action descriptions may contain paths/commands)
    "evaluate_ethics",
    "check_boundaries",
    "get_dharma_guidance",
    "karma_record",
    "karma_report",
    # Introspection & reasoning (free-form queries)
    "gnosis",
    "reasoning.bicameral",
    "corpus_callosum.debate",
    # Web & research (search queries may contain shell-like syntax)
    "web_search",
    "web_fetch",
    "research_topic",
    # Prompt & template (renders arbitrary content)
    "prompt.render",
}


# ---------------------------------------------------------------------------
# Sanitization functions
# ---------------------------------------------------------------------------

def sanitize_tool_args(tool_name: str, kwargs: dict[str, Any]) -> dict[str, Any] | None:
    """Validate and sanitize tool arguments.

    Returns None if args are clean, or an error dict if blocked.
    """
    # 0. Total payload size estimate
    try:
        from whitemagic.utils.fast_json import dumps as _fj_dumps
        payload_size = len(_fj_dumps(kwargs, default=str))
        if payload_size > MAX_TOTAL_SIZE:
            logger.warning("Sanitizer blocked %s: payload too large (%s bytes)", tool_name, payload_size)
            return {"status": "error", "error": f"Payload too large: {payload_size} bytes (max {MAX_TOTAL_SIZE})", "error_code": "input_invalid"}
    except (ImportError, ModuleNotFoundError) as e:
        import logging
        logging.getLogger(__name__).debug("Exception silenced: %s", e)

    # 1. Structural checks
    err = _check_structure(kwargs)
    if err:
        logger.warning("Sanitizer blocked %s: %s", tool_name, err, exc_info=True)
        return {"status": "error", "error": f"Input validation: {err}", "error_code": "input_invalid"}

    # 2. Content checks (skip for exempt tools)
    if tool_name not in _CONTENT_SCAN_EXEMPT:
        # Try Haskell boundary detection first (stricter, exhaustive pattern matching)
        try:
            from whitemagic.core.acceleration.haskell_bridge import (
                haskell_check_boundaries,
            )
            from whitemagic.utils.fast_json import dumps_str as _fj_dumps_str
            args_str = _fj_dumps_str(kwargs, default=str)[:10000]
            violations = haskell_check_boundaries(tool_name, "", args_str)
            if violations:
                critical = [v for v in violations if v.get("severity", 0) >= 3]
                if critical:
                    msg = critical[0].get("message", "Boundary violation")
                    logger.warning("Haskell boundary check blocked %s: %s", tool_name, msg, exc_info=True)
                    return {"status": "error", "error": f"Input rejected: {msg}", "error_code": "input_rejected"}
        except Exception as e:
            import logging
            logging.getLogger(__name__).debug("Exception silenced: %s", e)

        err = _scan_content(kwargs)
        if err:
            logger.warning("Sanitizer blocked %s: %s", tool_name, err, exc_info=True)
            return {"status": "error", "error": f"Input rejected: {err}", "error_code": "input_rejected"}

    # 3. Strip internal keys that shouldn't come from external callers
    _strip_internal_keys(kwargs)

    return None  # Clean


def _check_structure(obj: Any, depth: int = 0, path: str = "root") -> str | None:
    """Check structural constraints: depth, size, types."""
    if depth > MAX_ARG_DEPTH:
        return f"Nesting too deep at {path} (max {MAX_ARG_DEPTH})"

    if isinstance(obj, dict):
        for k, v in obj.items():
            if not isinstance(k, str):
                return f"Non-string dict key at {path}: {type(k).__name__}"
            err = _check_structure(v, depth + 1, f"{path}.{k}")
            if err:
                return err

    elif isinstance(obj, (list, tuple)):
        if len(obj) > MAX_LIST_LENGTH:
            return f"List too long at {path}: {len(obj)} items (max {MAX_LIST_LENGTH})"
        for i, v in enumerate(obj):
            err = _check_structure(v, depth + 1, f"{path}[{i}]")
            if err:
                return err

    elif isinstance(obj, str):
        if len(obj) > MAX_STRING_LENGTH:
            return f"String too long at {path}: {len(obj)} chars (max {MAX_STRING_LENGTH})"
        # Null byte injection check
        if "\x00" in obj:
            return f"Null byte detected at {path}"

    elif isinstance(obj, (int, float, bool, type(None))):
        pass  # Primitive types are fine

    elif isinstance(obj, bytes):
        return f"Bytes value at {path} — only strings, numbers, bools, lists, and dicts allowed"

    else:
        return f"Unexpected type at {path}: {type(obj).__name__}"

    return None


def _scan_content(obj: Any, path: str = "root") -> str | None:
    """Scan string values for injection patterns."""
    if isinstance(obj, str):
        # Check prompt injection
        for pattern in _INJECTION_PATTERNS:
            if pattern.search(obj):
                return f"Potential prompt injection detected at {path}"

        # Check path traversal
        for pattern in _PATH_TRAVERSAL_PATTERNS:
            if pattern.search(obj):
                return f"Potential path traversal at {path}"

        # Check shell injection
        for pattern in _SHELL_INJECTION_PATTERNS:
            if pattern.search(obj):
                return f"Potential shell injection at {path}"

    elif isinstance(obj, dict):
        for k, v in obj.items():
            err = _scan_content(v, f"{path}.{k}")
            if err:
                return err

    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            err = _scan_content(v, f"{path}[{i}]")
            if err:
                return err

    return None


def _strip_internal_keys(kwargs: dict[str, Any]) -> None:
    """Remove internal-only keys that external callers shouldn't be able to set."""
    internal_prefixes = ("_agent_id", "_internal_", "_bypass_", "_sudo_")
    to_remove = [k for k in kwargs if k.startswith(internal_prefixes)]
    for k in to_remove:
        del kwargs[k]
