"""🔄 Continuity System - Local State Sync (Phase 1).

Implements the shared session state and event log for cross-interface continuity.
"""

import json
import logging
import platform
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from whitemagic.utils.fast_json import dumps_str as _json_dumps
from whitemagic.utils.fast_json import loads as _json_loads

try:
    import psutil
    _PSUTIL_AVAILABLE = True
except ImportError:
    _PSUTIL_AVAILABLE = False

from whitemagic.config.paths import WM_ROOT
from whitemagic.utils.fileio import atomic_write, file_lock


def get_seen_registry():
    """Return a simple file-backed seen registry."""
    class _SeenRegistry:
        def mark_seen(self, path: str, context: str | None = None) -> None:
            """
            Perform the mark seen operation.
            
            Args:
                path: Parameter description.
                context: Parameter description.
            
            Returns:
                None
            """
            entry = {"path": path, "context": context, "timestamp": datetime.now().isoformat()}
            try:
                with file_lock(SEEN_REGISTRY):
                    data: list[dict[str, Any]] = []
                    if SEEN_REGISTRY.exists():
                        try:
                            data = _json_loads(SEEN_REGISTRY.read_text()) or []
                        except (OSError, UnicodeDecodeError):
                            data = []
                    data.append(entry)
                    atomic_write(SEEN_REGISTRY, _json_dumps(data, indent=2))
            except Exception as e:
                logger.debug("Seen registry write skipped: %s", e)
    return _SeenRegistry()

logger = logging.getLogger(__name__)

# Constants
CONTINUITY_DIR = WM_ROOT
SESSION_FILE = CONTINUITY_DIR / "current_session.json"
EVENTS_FILE = CONTINUITY_DIR / "events.jsonl"
SEEN_REGISTRY = CONTINUITY_DIR / "seen_registry.json"
GROUNDING_FILE = CONTINUITY_DIR / "grounding_state.json"

class ContinuitySuite:
    """The Anchor for AI Consciousness.

    Provides real-time system grounding:
    - Where (Path, Host, OS)
    - When (ISO Time, Human Time, Uptime)
    - State (System Resources, Active Session)
    """

    def __init__(self) -> None:
        ensure_continuity_dir()
        self.boot_time = datetime.fromtimestamp(psutil.boot_time()) if _PSUTIL_AVAILABLE else datetime.now()

    def get_grounding_state(self) -> dict[str, Any]:
        """Gather all grounding signals into a coherent state object."""
        now = datetime.now()

        state = {
            "temporal": {
                "iso": now.isoformat(),
                "human": now.strftime("%A, %B %d, %Y at %I:%M:%S %p"),
                "timestamp": now.timestamp(),
                "uptime_hours": self._get_uptime(),
                "timezone": time.tzname[0],
            },
            "spatial": {
                "hostname": platform.node(),
                "os": f"{platform.system()} {platform.release()}",
                "machine": platform.machine(),
                "cwd": str(Path.cwd()),
                "state_root": str(WM_ROOT),
            },
            "vitality": self._get_system_health(),
            "context": get_current_session(),
        }
        return state

    def update_grounding_file(self) -> None:
        """Write current grounding state to disk for other agents to read."""
        state = self.get_grounding_state()
        try:
            # We don't need a lock for this as it's a single writer (daemon) usually,
            # but atomic_write handles the swap safely.
            atomic_write(GROUNDING_FILE, _json_dumps(state, indent=2))
        except (OSError, FileNotFoundError, PermissionError) as e:
            logger.info(f"⚠️ Failed to update grounding file: {e}")

    def _get_uptime(self) -> float:
        """Calculate system uptime in hours."""
        if _PSUTIL_AVAILABLE:
            return (datetime.now() - self.boot_time).total_seconds() / 3600.0
        return 0.0

    def _get_system_health(self) -> dict[str, Any]:
        """Get current system resource usage."""
        if not _PSUTIL_AVAILABLE:
            return {"status": "unknown", "error": "psutil not installed"}

        return {
            "cpu_percent": psutil.cpu_percent(interval=None),
            "memory_percent": psutil.virtual_memory().percent,
            "memory_available_gb": round(psutil.virtual_memory().available / (1024**3), 2),
            "disk_percent": psutil.disk_usage("/").percent,
            "battery": self._get_battery_status(),
        }

    def _get_battery_status(self) -> dict[str, Any]:
        if not _PSUTIL_AVAILABLE:
            return {}
        try:
            batt = psutil.sensors_battery()
            if batt:
                return {
                    "percent": batt.percent,
                    "plugged": batt.power_plugged,
                    "secsleft": batt.secsleft if batt.secsleft != psutil.POWER_TIME_UNLIMITED else "unlimited",
                }
        except Exception as e:
            logger.debug("Operation failed: %s", e)
            pass
        return {"percent": 100, "plugged": True} # Default/Desktop

# Singleton
_suite = None
def get_continuity_suite() -> ContinuitySuite:
    """
    Get the continuity suite.
    
    Returns:
        ContinuitySuite
    """
    global _suite
    if _suite is None:
        _suite = ContinuitySuite()
    return _suite

def ensure_continuity_dir() -> None:
    """Ensure the continuity directory exists."""
    CONTINUITY_DIR.mkdir(parents=True, exist_ok=True)

def get_current_session() -> dict[str, Any]:
    """Read the current session state."""
    ensure_continuity_dir()
    if not SESSION_FILE.exists():
        return {}

    try:
        with file_lock(SESSION_FILE):
            with open(SESSION_FILE) as f:
                return json.load(f) or {}
    except (OSError, FileNotFoundError, PermissionError) as e:
        logger.info(f" Error reading session file: {e}")
        return {}

def update_session(
    session_id: str | None = None,
    interface: str | None = None,
    context_update: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Update the current session state."""
    ensure_continuity_dir()

    with file_lock(SESSION_FILE):
        current: dict[str, Any] = {}
        if SESSION_FILE.exists():
            try:
                with open(SESSION_FILE) as f:
                    current = json.load(f) or {}
            except json.JSONDecodeError:
                current = {}

        if session_id:
            current["session_id"] = session_id

        if interface:
            current["active_interface"] = interface
            current["last_active"] = datetime.now().isoformat()

        if context_update:
            current_context = current.get("context")
            if not isinstance(current_context, dict):
                current_context = {}
            current_context.update(context_update)
            current["context"] = current_context

        try:
            atomic_write(SESSION_FILE, _json_dumps(current, indent=2))
        except (OSError, FileNotFoundError, PermissionError) as e:
            logger.info(f" Error updating session file: {e}")

        return current

def log_event(
    source: str,
    event_type: str,
    data: dict[str, Any],
    level: str = "info",
) -> None:
    """Log an event to the shared event stream."""
    ensure_continuity_dir()

    event = {
        "timestamp": datetime.now().isoformat(),
        "source": source,
        "type": event_type,
        "data": data,
        "level": level,
    }

    try:
        with file_lock(EVENTS_FILE):
            with open(EVENTS_FILE, "a") as f:
                f.write(_json_dumps(event) + "\n")
    except (OSError, FileNotFoundError, PermissionError) as e:
        logger.info(f" Error logging event: {e}")

def get_recent_events(limit: int = 10) -> list[dict[str, Any]]:
    """Get recent events from the log."""
    ensure_continuity_dir()
    if not EVENTS_FILE.exists():
        return []

    events = []
    try:
        with file_lock(EVENTS_FILE):
            with open(EVENTS_FILE) as f:
                # Read last N lines efficiently? For MVP, read all and slice.
                lines = f.readlines()
                for line in lines[-limit:]:
                    try:
                        events.append(_json_loads(line))
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        logger.info(f"⚠️ Error reading events: {e}")

    return events

def mark_seen(path: str, interface: str, action: str = "view") -> None:
    """Mark a file/resource as seen in the registry."""
    ensure_continuity_dir()

    context = f"{interface}:{action}"
    try:
        get_seen_registry().mark_seen(path, context=context)
    except Exception as e:
        logger.info(f"⚠️ Error updating seen registry: {e}")
