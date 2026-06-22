# ruff: noqa: BLE001
"""Iceoryx2 IPC Bridge - Cross-process zero-copy communication.

Provides shared memory channels between WhiteMagic processes:
- wm/events: GanYing event bus
- wm/memories: Memory sync announcements
- wm/commands: Agent coordination
- wm/harmony: Health pulse broadcast
"""

import atexit
import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# Lazy import of Rust module
_whitemagic_rust = None
_ipc_initialized = False

def _get_rs():
    global _whitemagic_rust
    if _whitemagic_rust is None:
        try:
            import whitemagic_rust as rs
            _whitemagic_rust = rs
        except ImportError:
            _whitemagic_rust = False
    return _whitemagic_rust

def init_ipc(node_name: str | None = None) -> dict[str, Any]:
    """Initialize IPC bridge for this process."""
    global _ipc_initialized

    if _ipc_initialized:
        return {"initialized": True, "already": True}

    if node_name is None:
        import os
        node_name = f"wm_{os.getpid()}"

    rs = _get_rs()
    if not rs or not hasattr(rs, 'ipc_bridge'):
        return {"initialized": False, "error": "Rust bridge unavailable"}

    try:
        rs.ipc_bridge.ipc_init(node_name)
        _ipc_initialized = True
        atexit.register(shutdown_ipc)
        return {"initialized": True, "node": node_name}
    except Exception as e:
        logger.warning("IPC init failed (using fallback): %s", e, exc_info=True)
        return {"initialized": False, "error": str(e)}

def publish(channel: str, payload: bytes) -> dict[str, Any]:
    """Publish bytes to an IPC channel."""
    if not _ipc_initialized:
        init_ipc()

    rs = _get_rs()
    if not rs or not hasattr(rs, 'ipc_bridge'):
        return {"published": False, "error": "Rust bridge unavailable"}

    try:
        rs.ipc_bridge.ipc_publish(channel, payload)
        return {"published": True}
    except Exception as e:
        return {"published": False, "error": str(e)}

def publish_json(channel: str, data: dict) -> dict[str, Any]:
    """Publish JSON-serializable data to an IPC channel."""
    return publish(channel, json.dumps(data).encode())

def try_receive(channel: str, max_samples: int = 16) -> list[bytes]:
    """Non-blocking poll for up to `max_samples` pending messages on a channel.

    Returns a list of byte payloads (empty if no messages are pending or the
    Rust bridge / iceoryx2 is unavailable). Use this for in-process testing
    of the publish path; production consumers are expected to live in
    separate processes (e.g. the Nexus UI for wm/commands).
    """
    if not _ipc_initialized:
        init_ipc()

    rs = _get_rs()
    if not rs or not hasattr(rs, "ipc_bridge"):
        return []

    try:
        return list(rs.ipc_bridge.ipc_try_receive(channel, int(max_samples)))
    except Exception as e:
        logger.debug("ipc_try_receive(%s) failed: %s", channel, e, exc_info=True)
        return []

def try_receive_json(channel: str, max_samples: int = 16) -> list[dict]:
    """Like try_receive, but parse each payload as JSON and skip malformed entries."""
    out: list[dict] = []
    for raw in try_receive(channel, max_samples=max_samples):
        try:
            out.append(json.loads(raw.decode("utf-8")))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
    return out

def get_status() -> dict[str, Any]:
    """Get IPC bridge status."""
    rs = _get_rs()
    if not rs or not hasattr(rs, 'ipc_bridge'):
        return {"error": "Rust bridge unavailable"}

    try:
        res = rs.ipc_bridge.ipc_status()
        return dict(res) if res is not None else {"error": "empty status"}
    except Exception as e:
        return {"error": str(e)}

def shutdown_ipc():
    """Shutdown IPC (auto-called at exit)."""
    global _ipc_initialized
    _ipc_initialized = False


def tap_commands(max_samples: int = 100) -> list[dict]:
    """Tap the wm/commands channel for observability.

    Returns pending command messages (karmic consent requests, tool call
    notifications, agent coordination commands) as a list of dicts.
    Non-blocking: returns whatever is currently in the subscriber buffer.

    This is the observability consumer for the wm/commands channel that
    the middleware publishes to on every karmic consent event. Use it to
    audit consent decisions, monitor tool governance, or feed a dashboard.
    """
    return try_receive_json("wm/commands", max_samples=max_samples)


def tap_events(max_samples: int = 100) -> list[dict]:
    """Tap the wm/events channel for observability.

    Returns pending GanYing event bus messages as a list of dicts.
    Non-blocking: returns whatever is currently in the subscriber buffer.
    """
    return try_receive_json("wm/events", max_samples=max_samples)


def tap_harmony(max_samples: int = 10) -> list[dict]:
    """Tap the wm/harmony channel for health pulse monitoring.

    Returns pending harmony vector broadcast messages as a list of dicts.
    """
    return try_receive_json("wm/harmony", max_samples=max_samples)

# Auto-initialize on first use if WM_AUTO_IPC is set
if os.environ.get("WM_AUTO_IPC", "0") == "1":
    init_ipc()
