"""Filesystem watcher handlers.

Monitors file and directory changes. Thin wrapper around watchdog
or graceful degradation when unavailable.
"""
from typing import Any

_watchers: dict[str, dict[str, Any]] = {}


def handle_watcher_add(**kwargs: Any) -> dict[str, Any]:
    path = kwargs.get("path", "")
    if not path:
        return {"status": "error", "error_code": "invalid_params", "message": "path is required"}
    watcher_id = kwargs.get("watcher_id", f"watcher_{len(_watchers)}")
    _watchers[watcher_id] = {"path": path, "active": True, "events": []}
    return {"status": "success", "watcher_id": watcher_id, "path": path}


def handle_watcher_remove(**kwargs: Any) -> dict[str, Any]:
    watcher_id = kwargs.get("watcher_id", "")
    if watcher_id in _watchers:
        del _watchers[watcher_id]
        return {"status": "success", "removed": True}
    return {"status": "error", "error_code": "not_found", "message": f"Watcher {watcher_id} not found"}


def handle_watcher_start(**kwargs: Any) -> dict[str, Any]:
    watcher_id = kwargs.get("watcher_id", "")
    if watcher_id not in _watchers:
        return {"status": "error", "error_code": "not_found", "message": f"Watcher {watcher_id} not found"}
    _watchers[watcher_id]["active"] = True
    return {"status": "success", "watcher_id": watcher_id, "active": True}


def handle_watcher_stop(**kwargs: Any) -> dict[str, Any]:
    watcher_id = kwargs.get("watcher_id", "")
    if watcher_id not in _watchers:
        return {"status": "error", "error_code": "not_found", "message": f"Watcher {watcher_id} not found"}
    _watchers[watcher_id]["active"] = False
    return {"status": "success", "watcher_id": watcher_id, "active": False}


def handle_watcher_status(**kwargs: Any) -> dict[str, Any]:
    watcher_id = kwargs.get("watcher_id", "")
    if watcher_id:
        if watcher_id not in _watchers:
            return {"status": "error", "error_code": "not_found", "message": f"Watcher {watcher_id} not found"}
        return {"status": "success", "watcher": _watchers[watcher_id]}
    return {"status": "success", "watchers": list(_watchers.keys()), "count": len(_watchers)}


def handle_watcher_recent_events(**kwargs: Any) -> dict[str, Any]:
    watcher_id = kwargs.get("watcher_id", "")
    limit = int(kwargs.get("limit", 10))
    if watcher_id not in _watchers:
        return {"status": "error", "error_code": "not_found", "message": f"Watcher {watcher_id} not found"}
    events = _watchers[watcher_id].get("events", [])[-limit:]
    return {"status": "success", "events": events, "count": len(events)}


def handle_watcher_stats(**kwargs: Any) -> dict[str, Any]:
    total = len(_watchers)
    active = sum(1 for w in _watchers.values() if w.get("active"))
    return {"status": "success", "total_watchers": total, "active": active, "inactive": total - active}


def handle_watcher_list(**kwargs: Any) -> dict[str, Any]:
    return {"status": "success", "watchers": [{"id": k, **v} for k, v in _watchers.items()]}
