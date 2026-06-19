"""Bridge module: archaeology operations (Group A — resurfaced from archive)."""

from typing import Any


def _get_archaeology():
    """Lazy import with graceful degradation if whitemagic.archaeology is missing."""
    try:
        from whitemagic.archaeology import (
            create_daily_wisdom_digest,
            extract_wisdom,
            find_unread,
            get_archaeologist,
            mark_read,
            mark_written,
            process_wisdom_archives,
            wisdom_report,
        )
        return {
            "process_wisdom_archives": process_wisdom_archives,
            "create_daily_wisdom_digest": create_daily_wisdom_digest,
            "mark_read": mark_read,
            "mark_written": mark_written,
            "find_unread": find_unread,
            "get_archaeologist": get_archaeologist,
            "extract_wisdom": extract_wisdom,
            "wisdom_report": wisdom_report,
        }
    except ImportError:
        return None


def archaeology_process_wisdom(limit_files: int = 1000, memory_type: str = "long_term", **kwargs: Any) -> dict[str, Any]:
    """Extract insights from memory archives and store as wisdom memories."""
    api = _get_archaeology()
    if api is None:
        return {"status": "unavailable", "error": "whitemagic.archaeology module not yet implemented"}
    return api["process_wisdom_archives"](limit_files=limit_files, memory_type=memory_type)


def archaeology_daily_digest(**kwargs: Any) -> dict[str, Any]:
    """Create a daily wisdom digest from recent insights."""
    api = _get_archaeology()
    if api is None:
        return {"status": "unavailable", "error": "whitemagic.archaeology module not yet implemented"}
    return {"digest_path": api["create_daily_wisdom_digest"]()}


def archaeology_mark_read(file_path: str, context: str | None = None, notes: str | None = None, **kwargs: Any) -> dict[str, Any]:
    """Mark a file as read."""
    api = _get_archaeology()
    if api is None:
        return {"status": "unavailable", "error": "whitemagic.archaeology module not yet implemented"}
    entry = api["mark_read"](file_path, context, notes)
    return {
        "path": entry.path,
        "first_read": entry.first_read if hasattr(entry, "first_read") else str(entry.timestamp) if hasattr(entry, "timestamp") else "unknown",
        "read_count": getattr(entry, "read_count", 1),
    }


def archaeology_mark_written(file_path: str, context: str | None = None, notes: str | None = None, **kwargs: Any) -> dict[str, Any]:
    """Mark a file as written."""
    api = _get_archaeology()
    if api is None:
        return {"status": "unavailable", "error": "whitemagic.archaeology module not yet implemented"}
    entry = api["mark_written"](file_path, context, notes)
    return {
        "path": entry.path,
        "last_write": entry.last_write,
        "write_count": getattr(entry, "times_written", 1),
    }


def archaeology_find_unread(directory: str, patterns: list[str] | None = None, **kwargs: Any) -> dict[str, Any]:
    """Find unread files in a directory."""
    api = _get_archaeology()
    if api is None:
        return {"status": "unavailable", "error": "whitemagic.archaeology module not yet implemented"}
    unread = api["find_unread"](directory, patterns)
    return {"unread_files": unread, "count": len(unread)}


def archaeology_find_changed(directory: str | None = None, **kwargs: Any) -> dict[str, Any]:
    """Find files that have changed since they were last read."""
    api = _get_archaeology()
    if api is None:
        return {"status": "unavailable", "error": "whitemagic.archaeology module not yet implemented"}
    changed = api["get_archaeologist"]().find_changed(directory)
    return {
        "changed_files": [entry.to_dict() for entry in changed],
        "count": len(changed),
    }


def archaeology_recent_reads(limit: int = 50, **kwargs: Any) -> dict[str, Any]:
    """Get recently read files."""
    api = _get_archaeology()
    if api is None:
        return {"status": "unavailable", "error": "whitemagic.archaeology module not yet implemented"}
    recent = api["get_archaeologist"]().get_recent_reads(limit)
    return {"recent": [entry.to_dict() for entry in recent]}


def archaeology_stats(scan_disk: bool = False, **kwargs: Any) -> dict[str, Any]:
    """Get archaeology statistics."""
    api = _get_archaeology()
    if api is None:
        return {"status": "unavailable", "error": "whitemagic.archaeology module not yet implemented"}
    stats = api["get_archaeologist"]().stats(scan_disk=scan_disk)
    return stats if isinstance(stats, dict) else {}


def archaeology_report(**kwargs: Any) -> dict[str, Any]:
    """Generate a human-readable archaeology report."""
    api = _get_archaeology()
    if api is None:
        return {"status": "unavailable", "error": "whitemagic.archaeology module not yet implemented"}
    return {"report": api["get_archaeologist"]().reading_report()}


def archaeology_search(query: str, **kwargs: Any) -> dict[str, Any]:
    """Search archaeology entries by path, notes, or insights."""
    api = _get_archaeology()
    if api is None:
        return {"status": "unavailable", "error": "whitemagic.archaeology module not yet implemented"}
    results = api["get_archaeologist"]().search(query)
    return {"results": [entry.to_dict() for entry in results]}


def archaeology_extract_wisdom(**kwargs: Any) -> dict[str, Any]:
    """Extract wisdom from memory archives."""
    api = _get_archaeology()
    if api is None:
        return {"status": "unavailable", "error": "whitemagic.archaeology module not yet implemented"}
    wisdom = api["extract_wisdom"]()
    result = {
        "quotes": wisdom.quotes[:10] if wisdom.quotes else [],
        "principles": wisdom.principles[:10] if wisdom.principles else [],
    }
    if hasattr(wisdom, "patterns") and wisdom.patterns:
        result["patterns"] = wisdom.patterns[:10]
    return result


def archaeology_generate_report(**kwargs: Any) -> dict[str, Any]:
    """Generate archaeology report."""
    api = _get_archaeology()
    if api is None:
        return {"status": "unavailable", "error": "whitemagic.archaeology module not yet implemented"}
    report = api["wisdom_report"]()
    return {"report": report}


def archaeology_scan_directory(
    directory: str,
    depth: int = 3,
    patterns: list[str] | None = None,
    recursive: bool = True,
    **kwargs: Any,
) -> dict[str, Any]:
    """Scan a directory and track files."""
    api = _get_archaeology()
    if api is None:
        return {"status": "unavailable", "error": "whitemagic.archaeology module not yet implemented"}
    arch = api["get_archaeologist"]()
    found_files = arch.find_unread(directory, patterns) if recursive else []
    stats = arch.stats(scan_disk=True)
    return {
        "directory": directory,
        "depth": depth,
        "recursive": recursive,
        "new_files_found": len(found_files),
        "total_files_tracked": stats.get("total_files", 0),
        "disk_usage_mb": stats.get("disk_usage_mb", 0),
        "artifacts": stats.get("artifacts", {}),
        "message": f'Scan complete. Found {len(found_files)} new files. Disk usage: {stats.get("disk_usage_mb", 0)} MB',
    }
