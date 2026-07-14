# ruff: noqa: BLE001
"""MCP tool handlers for the Error Pattern Library.

Tools:
    pattern.lookup   — Check if an error has been seen before
    pattern.avoid    — Get anti-patterns relevant to a task context
    pattern.resolve  — Get proven resolution for an error
    pattern.learn    — Teach the library a new error + resolution
    pattern.list     — List all known patterns
    pattern.summary  — Get library statistics
    pattern.ingest   — Ingest a full mining output dict
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from whitemagic.core.patterns.error_library import get_error_library


def handle_pattern_lookup(**kwargs: Any) -> dict[str, Any]:
    """Look up an error by text to see if it has been seen before."""
    error_text = kwargs.get("error_text") or kwargs.get("error") or ""
    if not error_text:
        return {"status": "error", "error": "error_text is required"}

    user_id = kwargs.get("user_id", "global")
    library = get_error_library(user_id=user_id)
    result = library.lookup(error_text)
    if result is None:
        return {
            "status": "not_found",
            "message": "No matching error pattern found in the library.",
            "error_text": error_text[:200],
            "suggestion": "Call pattern.learn with this error and its resolution to add it.",
        }
    return {"status": "success", "match": result}


def handle_pattern_avoid(**kwargs: Any) -> dict[str, Any]:
    """Get anti-patterns and error patterns relevant to a task context."""
    context = kwargs.get("context") or kwargs.get("task") or ""
    if not context:
        return {"status": "error", "error": "context is required"}

    user_id = kwargs.get("user_id", "global")
    library = get_error_library(user_id=user_id)
    return library.avoid(context)


def handle_pattern_resolve(**kwargs: Any) -> dict[str, Any]:
    """Get proven resolution for an error."""
    error_text = kwargs.get("error_text") or kwargs.get("error") or ""
    if not error_text:
        return {"status": "error", "error": "error_text is required"}

    user_id = kwargs.get("user_id", "global")
    library = get_error_library(user_id=user_id)
    return library.resolve(error_text)


def handle_pattern_learn(**kwargs: Any) -> dict[str, Any]:
    """Teach the library a new error and optionally its resolution."""
    error_text = kwargs.get("error_text") or kwargs.get("error") or ""
    if not error_text:
        return {"status": "error", "error": "error_text is required"}

    resolution = kwargs.get("resolution")
    session = kwargs.get("session", "")
    prevention = kwargs.get("prevention")
    user_id = kwargs.get("user_id", "global")

    library = get_error_library(user_id=user_id)
    fingerprint = library.learn_from_error(error_text, resolution, session)

    if prevention and fingerprint:
        # Update prevention guidance
        from whitemagic.core.patterns.error_library import _fingerprint
        fp = _fingerprint(error_text)
        if fp in library.error_patterns:
            library.error_patterns[fp].prevention = prevention
            library._save()

    return {
        "status": "success",
        "fingerprint": fingerprint,
        "message": "Error pattern learned.",
    }


def handle_pattern_list(**kwargs: Any) -> dict[str, Any]:
    """List all known error patterns, optionally filtered by category."""
    category = kwargs.get("category")
    user_id = kwargs.get("user_id", "global")
    library = get_error_library(user_id=user_id)
    return library.list_patterns(category=category)


def handle_pattern_summary(**kwargs: Any) -> dict[str, Any]:
    """Get a summary of the error pattern library."""
    user_id = kwargs.get("user_id", "global")
    library = get_error_library(user_id=user_id)
    return library.summary()


def handle_pattern_ingest(**kwargs: Any) -> dict[str, Any]:
    """Ingest a full mining output dict into the library.

    Accepts either a mine_output dict directly via 'mine_output' kwarg,
    or a path to a JSON file via 'file_path' kwarg.
    """
    mine_output = kwargs.get("mine_output")
    file_path = kwargs.get("file_path")

    if file_path and not mine_output:
        p = Path(file_path).expanduser()
        if not p.exists():
            return {"status": "error", "error": f"File not found: {p}"}
        try:
            mine_output = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            return {"status": "error", "error": f"Failed to read file: {e}"}

    if not mine_output or not isinstance(mine_output, dict):
        return {"status": "error", "error": "mine_output dict or file_path is required"}

    user_id = kwargs.get("user_id", "global")
    library = get_error_library(user_id=user_id)
    stats = library.learn_from_mining(mine_output)
    return {"status": "success", "ingest_stats": stats}
