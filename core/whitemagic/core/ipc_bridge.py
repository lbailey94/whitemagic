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
        logger.warning(f"IPC init failed (using fallback): {e}")
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

# Auto-initialize on first use if WM_AUTO_IPC is set
if os.environ.get("WM_AUTO_IPC", "0") == "1":
    init_ipc()
